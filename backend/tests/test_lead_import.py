"""Contact import (CSV / XLSX) for leads.

Unit tests (no database) cover parsing, validation, file checks and
duplicate classification with a stub session.

HTTP tests (live Postgres, skipped when unreachable) cover the preview and
commit endpoints, the no-write guarantee of preview, and cross-organization
isolation. They follow the same pattern as ``test_phase5_org_isolation.py``.
"""

from __future__ import annotations

import asyncio
import io
import uuid
import zipfile
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from app.middleware.org_context import OrgContext
from app.services import lead_import_service as svc
from app.services.lead_import_service import LeadImportError

# ───────────────────────── helpers ─────────────────────────


class _FakeUpload:
    """Stands in for ``UploadFile``: only ``read(size)`` and ``filename`` are used."""

    def __init__(self, data: bytes, filename: str) -> None:
        self._data = data
        self.filename = filename

    async def read(self, size: int = -1) -> bytes:
        return self._data if size is None or size < 0 else self._data[:size]


class _StubResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _StubSession:
    """Records calls. Answers existing-lead lookups with canned rows and no writes."""

    def __init__(self, existing_rows=()):
        self.existing_rows = list(existing_rows)
        self.writes = 0

    async def execute(self, _statement):
        return _StubResult(self.existing_rows)

    def add(self, _obj):  # pragma: no cover - must never be reached in preview tests
        self.writes += 1

    def add_all(self, objs):  # pragma: no cover
        self.writes += len(objs)

    async def flush(self):  # pragma: no cover
        pass

    async def commit(self):  # pragma: no cover
        self.writes += 1


def _csv(text: str) -> bytes:
    return text.encode("utf-8")


def _xlsx(rows: list[list]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _statuses(parsed) -> list[str]:
    return [r.status for r in parsed.rows]


# ───────────────────────── parsing ─────────────────────────


def test_valid_csv_maps_headers_and_normalises_fields():
    data = _csv(
        "Name,Phone,Email,Company,Notes,Consent\n"
        "Ada Lovelace,+1 (415) 555-0123,ADA@Example.com,Analytical,Met at expo,yes\n"
        "Grace Hopper,,grace@example.org,,,\n"
    )
    parsed = svc.prepare_import(data, "contacts.csv")

    assert parsed.file_format == "csv"
    assert [f for _, f in parsed.columns] == [
        "name",
        "phone",
        "email",
        "company",
        "notes",
        "consent",
    ]
    assert _statuses(parsed) == ["valid", "valid"]
    first, second = parsed.rows
    assert first.phone == "+14155550123"
    assert first.phone_key == "14155550123"
    assert first.email == "ada@example.com"
    assert first.consent == "granted"
    assert first.notes == "Met at expo"
    assert second.consent == "unknown"  # blank cell defaults to unknown
    assert second.phone is None


def test_csv_with_utf8_bom_is_read_and_header_recognised():
    data = b"\xef\xbb\xbfName,Email\nAda,ada@example.com\n"
    parsed = svc.prepare_import(data, "contacts.csv")

    assert parsed.columns[0] == ("Name", "name")
    assert parsed.rows[0].name == "Ada"
    assert parsed.rows[0].status == "valid"


def test_csv_semicolon_delimiter_is_detected():
    data = _csv("Name;Email\nAda;ada@example.com\n")
    parsed = svc.prepare_import(data, "contacts.csv")
    assert parsed.rows[0].email == "ada@example.com"


def test_csv_that_is_not_utf8_is_rejected_plainly():
    data = "Name,Email\nJos\xe9,jose@example.com\n".encode("latin-1")
    with pytest.raises(LeadImportError) as exc:
        svc.prepare_import(data, "contacts.csv")
    assert exc.value.status_code == 422
    assert "UTF-8" in exc.value.message


def test_valid_xlsx_reads_first_sheet_and_numeric_phone():
    data = _xlsx(
        [
            ["Full name", "Mobile", "Referrer"],
            ["Linus", 14155550199, "newsletter"],
        ]
    )
    parsed = svc.prepare_import(data, "contacts.xlsx")

    assert parsed.file_format == "xlsx"
    assert parsed.columns[0] == ("Full name", "name")
    assert parsed.columns[1] == ("Mobile", "phone")
    assert parsed.columns[2] == ("Referrer", None)  # not a recognised column
    row = parsed.rows[0]
    assert row.status == "valid"
    assert row.name == "Linus"
    assert row.phone == "14155550199"  # whole-number float kept as digits


def test_blank_rows_are_skipped_and_row_numbers_are_kept():
    data = _csv("Name,Email\n\n,\nAda,ada@example.com\n")
    parsed = svc.prepare_import(data, "contacts.csv")
    assert len(parsed.rows) == 1
    assert (
        parsed.rows[0].row_number == 4
    )  # record number in the file, header is 1, blank lines count


# ───────────────────────── validation ─────────────────────────


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("+1 (415) 555-0123", "+14155550123"),
        ("0044 20 7946 0958", "+442079460958"),
        ("415.555.0123", "4155550123"),
        ("+447700900123", "+447700900123"),
    ],
)
def test_phone_normalisation(raw, expected):
    stored, key, error = svc.check_phone(raw)
    assert error is None
    assert stored == expected
    assert key == expected.lstrip("+")


@pytest.mark.parametrize(
    "raw, message",
    [
        ("12345", "7 to 15 digits"),
        ("+1234567890123456", "7 to 15 digits"),
        ("+0123456789", "can't start with 0"),
        ("call me maybe", "letters or symbols"),
        ("+", "letters or symbols"),
    ],
)
def test_invalid_phone_reasons(raw, message):
    stored, key, error = svc.check_phone(raw)
    assert stored is None and key is None
    assert message in error


@pytest.mark.parametrize(
    "raw, ok",
    [
        ("ada@example.com", True),
        ("ADA@Example.COM", True),
        ("first.last+tag@sub.example.co.uk", True),
        ("not-an-email", False),
        ("ada@", False),
        ("ada@example", False),
        ("a..b@example.com", False),
        (".ada@example.com", False),
        ("ada@exa mple.com", False),
    ],
)
def test_email_validation(raw, ok):
    value, error = svc.check_email(raw)
    assert (error is None) is ok
    if ok:
        assert value == raw.strip().lower()


def test_invalid_email_and_phone_rows_carry_plain_reasons():
    data = _csv(
        "Name,Phone,Email\n"
        "Bad Email,+14155550123,not-an-email\n"
        "Bad Phone,call me,ok@example.com\n"
        "Nobody,,\n"
    )
    parsed = svc.prepare_import(data, "contacts.csv")

    assert _statuses(parsed) == ["invalid", "invalid", "invalid"]
    assert "Email address doesn't look valid" in parsed.rows[0].reason
    assert "letters or symbols" in parsed.rows[1].reason
    assert "phone number or an email" in parsed.rows[2].reason


def test_invalid_consent_value_is_rejected():
    data = _csv("Name,Email,Consent\nAda,ada@example.com,maybe\n")
    parsed = svc.prepare_import(data, "contacts.csv")
    assert parsed.rows[0].status == "invalid"
    assert "Consent must be yes, no, or left blank" in parsed.rows[0].reason


@pytest.mark.parametrize(
    "raw, expected", [("Yes", "granted"), ("no", "denied"), ("", "unknown")]
)
def test_consent_values(raw, expected):
    value, error = svc.check_consent(raw)
    assert error is None and value == expected


def test_missing_contact_columns_produce_warning():
    data = _csv("Name,Company\nAda,Analytical\n")
    parsed = svc.prepare_import(data, "contacts.csv")
    assert any("No email or phone column" in w for w in parsed.warnings)
    assert _statuses(parsed) == ["invalid"]


def test_csv_with_only_headers_is_rejected():
    with pytest.raises(LeadImportError) as exc:
        svc.prepare_import(_csv("Name,Email\n"), "contacts.csv")
    assert exc.value.status_code == 422


def test_more_than_5000_rows_is_rejected():
    lines = ["Name,Email"] + [
        f"Person {i},person{i}@example.com" for i in range(svc.MAX_DATA_ROWS + 1)
    ]
    with pytest.raises(LeadImportError) as exc:
        svc.prepare_import(_csv("\n".join(lines) + "\n"), "contacts.csv")
    assert exc.value.status_code == 422
    assert "5,000" in exc.value.message


def test_exactly_5000_rows_is_accepted():
    lines = ["Name,Email"] + [
        f"Person {i},person{i}@example.com" for i in range(svc.MAX_DATA_ROWS)
    ]
    parsed = svc.prepare_import(_csv("\n".join(lines) + "\n"), "contacts.csv")
    assert len(parsed.rows) == svc.MAX_DATA_ROWS


# ───────────────────────── file checks ─────────────────────────


@pytest.mark.parametrize(
    "name", ["contacts.txt", "contacts.xls", "contacts.pdf", "contacts"]
)
def test_wrong_extension_is_rejected(name):
    with pytest.raises(LeadImportError) as exc:
        svc.prepare_import(_csv("Name,Email\nAda,ada@example.com\n"), name)
    assert exc.value.status_code == 415


def test_macro_enabled_workbook_extension_is_rejected():
    data = _xlsx([["Name", "Email"], ["Ada", "ada@example.com"]])
    with pytest.raises(LeadImportError) as exc:
        svc.prepare_import(data, "contacts.xlsm")
    assert exc.value.status_code == 415
    assert "macro" in exc.value.message.lower()


def test_xlsx_containing_vba_project_is_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("xl/workbook.xml", "<workbook/>")
        zf.writestr("xl/vbaProject.bin", b"macro")
    with pytest.raises(LeadImportError) as exc:
        svc.prepare_import(buf.getvalue(), "contacts.xlsx")
    assert exc.value.status_code == 415


def test_xlsx_with_macro_content_type_is_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            "<Types>application/vnd.ms-excel.sheet.macroEnabled.main+xml</Types>",
        )
        zf.writestr("xl/workbook.xml", "<workbook/>")
    with pytest.raises(LeadImportError) as exc:
        svc.prepare_import(buf.getvalue(), "contacts.xlsx")
    assert exc.value.status_code == 415


def test_csv_extension_with_xlsx_content_is_rejected():
    data = _xlsx([["Name", "Email"], ["Ada", "ada@example.com"]])
    with pytest.raises(LeadImportError) as exc:
        svc.prepare_import(data, "contacts.csv")
    assert exc.value.status_code == 415


def test_xlsx_extension_with_csv_content_is_rejected():
    with pytest.raises(LeadImportError) as exc:
        svc.prepare_import(_csv("Name,Email\nAda,ada@example.com\n"), "contacts.xlsx")
    assert exc.value.status_code == 415


def test_empty_upload_is_rejected():
    upload = _FakeUpload(b"", "contacts.csv")
    with pytest.raises(LeadImportError) as exc:
        asyncio.run(svc.read_upload(upload))
    assert exc.value.status_code == 422


def test_oversized_upload_is_rejected_before_parsing():
    upload = _FakeUpload(b"a" * (svc.MAX_FILE_BYTES + 1), "contacts.csv")
    with pytest.raises(LeadImportError) as exc:
        asyncio.run(svc.read_upload(upload))
    assert exc.value.status_code == 413
    assert "5 MB" in exc.value.message


def test_file_at_the_5mb_limit_is_accepted():
    upload = _FakeUpload(b"a" * svc.MAX_FILE_BYTES, "contacts.csv")
    assert len(asyncio.run(svc.read_upload(upload))) == svc.MAX_FILE_BYTES


def test_binary_data_named_csv_is_rejected():
    with pytest.raises(LeadImportError) as exc:
        svc.prepare_import(b"Name,Email\x00\x01\n", "contacts.csv")
    assert exc.value.status_code == 415


def test_safe_file_name_drops_directories():
    assert svc.safe_file_name("C:\\Users\\x\\leads.csv") == "leads.csv"
    assert svc.safe_file_name(None) == "contacts"


# ───────────────────────── duplicates ─────────────────────────


def test_duplicates_within_the_file_are_flagged_after_the_first_row():
    data = _csv(
        "Name,Phone,Email\n"
        "Ada,+14155550123,ada@example.com\n"
        "Ada again,+14155550123,other@example.com\n"
        "Grace,,ADA@example.com\n"
        "Linus,+14155550999,linus@example.com\n"
    )
    parsed = svc.prepare_import(data, "contacts.csv")
    session = _StubSession()
    asyncio.run(svc.classify_rows(session, organization_id=uuid.uuid4(), parsed=parsed))

    assert _statuses(parsed) == [
        "valid",
        "duplicate_in_file",
        "duplicate_in_file",
        "valid",
    ]
    assert parsed.rows[1].reason == "Repeats an earlier row in this file"


def test_duplicates_of_existing_leads_are_flagged():
    data = _csv(
        "Name,Phone,Email\n"
        "Known by phone,+1 415 555 0123,new@example.com\n"
        "Known by email,,OLD@example.com\n"
        "Fresh,,fresh@example.com\n"
    )
    parsed = svc.prepare_import(data, "contacts.csv")
    session = _StubSession(
        existing_rows=[
            ("someone@example.com", "+1 (415) 555-0123"),  # phone matches on digits
            ("old@example.com", None),  # email matches case-insensitively
        ]
    )
    asyncio.run(svc.classify_rows(session, organization_id=uuid.uuid4(), parsed=parsed))

    assert _statuses(parsed) == ["duplicate_existing", "duplicate_existing", "valid"]
    assert parsed.rows[0].reason == "Already a lead in your organization"


def test_classification_never_writes():
    parsed = svc.prepare_import(
        _csv("Name,Email\nAda,ada@example.com\n"), "contacts.csv"
    )
    session = _StubSession()
    asyncio.run(svc.classify_rows(session, organization_id=uuid.uuid4(), parsed=parsed))
    assert session.writes == 0


# ───────────────────────── HTTP + database ─────────────────────────


def _postgres_reachable() -> bool:
    import os

    import asyncpg

    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return False
    dsn = url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )

    async def _probe() -> bool:
        try:
            conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=3)
            await conn.close()
            return True
        except Exception:
            return False

    try:
        return asyncio.run(_probe())
    except RuntimeError:
        return False


REQUIRES_DB = pytest.mark.skipif(
    not _postgres_reachable(),
    reason="Postgres is not reachable from this host (private VPC, etc).",
)


@pytest_asyncio.fixture
async def db_session():
    from app.database import session as db_session_module
    from app.database.session import dispose_engine, init_engine

    await dispose_engine()
    init_engine()
    Maker = db_session_module.AsyncSessionLocal
    assert Maker is not None

    async with Maker() as s:
        yield s
        await s.rollback()

    await dispose_engine()


async def _seed_org_with_user(session, *, email: str, slug_hint: str):
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.organization_member import (
        MemberRole,
        MemberStatus,
        OrganizationMember,
    )
    from app.database.models.project import Project
    from app.database.models.user import User

    user = User(
        auth_subject=f"sub-{uuid.uuid4()}",
        email=email,
        full_name=email.split("@")[0].title(),
    )
    session.add(user)
    await session.flush()

    org = Organization(
        name=f"{slug_hint.title()} Workspace",
        slug=f"{slug_hint}-{uuid.uuid4().hex[:8]}",
        plan=OrgPlan.free,
        owner_user_id=user.id,
    )
    session.add(org)
    await session.flush()

    session.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=MemberRole.owner,
            status=MemberStatus.active,
            joined_at=datetime.now(timezone.utc),
        )
    )
    session.add(
        Project(
            organization_id=org.id,
            name="Default",
            slug="default",
            is_default=True,
            created_by_user_id=user.id,
        )
    )
    await session.flush()
    return user, org


async def _cleanup(
    session, *, org_ids: list[uuid.UUID], user_ids: list[uuid.UUID]
) -> None:
    from sqlalchemy import delete

    from app.database.models.lead import Lead
    from app.database.models.organization import Organization
    from app.database.models.organization_member import OrganizationMember
    from app.database.models.project import Project
    from app.database.models.user import User

    await session.rollback()
    await session.execute(delete(Lead).where(Lead.organization_id.in_(org_ids)))
    await session.execute(delete(Project).where(Project.organization_id.in_(org_ids)))
    await session.execute(
        delete(OrganizationMember).where(
            OrganizationMember.organization_id.in_(org_ids)
        )
    )
    await session.execute(delete(Organization).where(Organization.id.in_(org_ids)))
    await session.execute(delete(User).where(User.id.in_(user_ids)))
    await session.commit()


def _ctx(user_id: uuid.UUID, org_id: uuid.UUID) -> OrgContext:
    return OrgContext(
        user_id=user_id,
        auth_subject=f"sub-{org_id}",
        organization_id=org_id,
        membership_role="owner",
    )


@REQUIRES_DB
@pytest.mark.asyncio
async def test_http_preview_writes_nothing_and_reports_statuses(db_session):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import func, select

    from app.database.models.lead import Lead
    from app.middleware.org_context import get_current_organization
    from server import app

    user, org = await _seed_org_with_user(
        db_session, email=f"pv-{uuid.uuid4()}@x.com", slug_hint="preview"
    )
    user_id, org_id = user.id, org.id
    db_session.add(
        Lead(
            organization_id=org_id,
            name="Existing",
            email="existing@example.com",
            source="widget",
        )
    )
    await db_session.commit()

    async def _override() -> OrgContext:
        return _ctx(user_id, org_id)

    before = await db_session.scalar(
        select(func.count(Lead.id)).where(Lead.organization_id == org_id)
    )
    csv_bytes = _csv(
        "Name,Email,Consent\n"
        "New Person,new@example.com,yes\n"
        "Dupe Existing,EXISTING@example.com,\n"
        "Dupe In File,new@example.com,\n"
        "Bad,not-an-email,\n"
    )
    app.dependency_overrides[get_current_organization] = _override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/leads/import/preview",
                files={"file": ("contacts.csv", csv_bytes, "text/csv")},
            )
    finally:
        app.dependency_overrides.pop(get_current_organization, None)

    try:
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total_rows"] == 4
        assert body["valid"] == 1
        assert body["duplicate_existing"] == 1
        assert body["duplicate_in_file"] == 1
        assert body["invalid"] == 1
        assert body["rows"][1]["status"] == "duplicate_existing"

        after = await db_session.scalar(
            select(func.count(Lead.id)).where(Lead.organization_id == org_id)
        )
        assert after == before  # preview wrote nothing
    finally:
        await _cleanup(db_session, org_ids=[org_id], user_ids=[user_id])


@REQUIRES_DB
@pytest.mark.asyncio
async def test_http_commit_saves_only_valid_rows_with_provenance(db_session):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select

    from app.database.models.lead import Lead
    from app.middleware.org_context import get_current_organization
    from server import app

    user, org = await _seed_org_with_user(
        db_session, email=f"cm-{uuid.uuid4()}@x.com", slug_hint="commit"
    )
    user_id, org_id = user.id, org.id
    await db_session.commit()

    async def _override() -> OrgContext:
        return _ctx(user_id, org_id)

    csv_bytes = _csv(
        "Name,Phone,Email,Company,Notes,Consent\n"
        "Ada,+14155550123,ada@example.com,Analytical,Asked about pricing,yes\n"
        "Ada copy,,ada@example.com,,,\n"
        "Broken,123,,,,\n"
    )
    app.dependency_overrides[get_current_organization] = _override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/leads/import/commit",
                files={"file": ("contacts.csv", csv_bytes, "text/csv")},
            )
    finally:
        app.dependency_overrides.pop(get_current_organization, None)

    try:
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["saved"] == 1
        assert body["skipped_duplicate_in_file"] == 1
        assert body["skipped_invalid"] == 1

        db_session.expire_all()
        rows = (
            await db_session.scalars(select(Lead).where(Lead.organization_id == org_id))
        ).all()
        assert len(rows) == 1
        lead = rows[0]
        assert lead.source == "import"
        assert lead.email == "ada@example.com"
        assert lead.phone == "+14155550123"
        assert lead.extra["consent"] == "granted"
        assert lead.extra["notes"] == "Asked about pricing"
        assert lead.extra["import"]["upload_id"] == body["upload_id"]
        assert lead.extra["import"]["uploaded_by"] == str(user_id)
    finally:
        await _cleanup(db_session, org_ids=[org_id], user_ids=[user_id])


@REQUIRES_DB
@pytest.mark.asyncio
async def test_http_duplicates_and_rows_are_isolated_per_organization(db_session):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select

    from app.database.models.lead import Lead
    from app.middleware.org_context import get_current_organization
    from server import app

    user_a, org_a = await _seed_org_with_user(
        db_session, email=f"ia-{uuid.uuid4()}@x.com", slug_hint="isoa"
    )
    user_a_id, org_a_id = user_a.id, org_a.id
    user_b, org_b = await _seed_org_with_user(
        db_session, email=f"ib-{uuid.uuid4()}@x.com", slug_hint="isob"
    )
    user_b_id, org_b_id = user_b.id, org_b.id
    shared_email = f"shared-{uuid.uuid4().hex[:8]}@example.com"
    db_session.add(
        Lead(
            organization_id=org_a_id,
            name="Alpha only",
            email=shared_email,
            source="widget",
        )
    )
    await db_session.commit()

    current = {"ctx": _ctx(user_b_id, org_b_id)}

    async def _override() -> OrgContext:
        return current["ctx"]

    csv_bytes = _csv(f"Name,Email\nBeta copy,{shared_email}\n")
    app.dependency_overrides[get_current_organization] = _override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Org B imports the same address Org A already holds: it must be valid, not a duplicate.
            r = await client.post(
                "/api/leads/import/commit",
                files={"file": ("contacts.csv", csv_bytes, "text/csv")},
            )
            assert r.status_code == 201, r.text
            assert r.json()["saved"] == 1
            assert r.json()["skipped_duplicate_existing"] == 0

            # Org B's lead list must not show Org A's lead.
            listing = await client.get("/api/leads")
            assert listing.status_code == 200, listing.text
            names = [item["name"] for item in listing.json()]
            assert "Alpha only" not in names
            assert "Beta copy" in names

            # Org A re-imports the same address: now it IS a duplicate, and only of its own leads.
            current["ctx"] = _ctx(user_a_id, org_a_id)
            r = await client.post(
                "/api/leads/import/preview",
                files={"file": ("contacts.csv", csv_bytes, "text/csv")},
            )
            assert r.status_code == 200, r.text
            assert r.json()["duplicate_existing"] == 1
            assert r.json()["valid"] == 0
    finally:
        app.dependency_overrides.pop(get_current_organization, None)

    try:
        db_session.expire_all()
        b_leads = (
            await db_session.scalars(
                select(Lead).where(Lead.organization_id == org_b_id)
            )
        ).all()
        assert [lead.name for lead in b_leads] == ["Beta copy"]
    finally:
        await _cleanup(
            db_session, org_ids=[org_a_id, org_b_id], user_ids=[user_a_id, user_b_id]
        )


@REQUIRES_DB
@pytest.mark.asyncio
async def test_http_rejects_wrong_extension_and_macros_before_parsing(db_session):
    from httpx import ASGITransport, AsyncClient

    from app.middleware.org_context import get_current_organization
    from server import app

    user, org = await _seed_org_with_user(
        db_session, email=f"ex-{uuid.uuid4()}@x.com", slug_hint="ext"
    )
    user_id, org_id = user.id, org.id
    await db_session.commit()

    async def _override() -> OrgContext:
        return _ctx(user_id, org_id)

    app.dependency_overrides[get_current_organization] = _override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/leads/import/preview",
                files={
                    "file": (
                        "contacts.xlsm",
                        b"PK\x03\x04",
                        "application/vnd.ms-excel.sheet.macroEnabled.12",
                    )
                },
            )
            assert r.status_code == 415, r.text
            assert r.json()["error"]["message"]

            r = await client.post(
                "/api/leads/import/preview",
                files={"file": ("contacts.txt", b"Name,Email\n", "text/plain")},
            )
            assert r.status_code == 415, r.text

            r = await client.post(
                "/api/leads/import/commit",
                files={
                    "file": ("big.csv", b"a" * (svc.MAX_FILE_BYTES + 1), "text/csv")
                },
            )
            assert r.status_code == 413, r.text
    finally:
        app.dependency_overrides.pop(get_current_organization, None)
        await _cleanup(db_session, org_ids=[org_id], user_ids=[user_id])


@REQUIRES_DB
@pytest.mark.asyncio
async def test_http_commit_is_refused_for_read_only_role_and_saves_nothing(db_session):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select

    from app.database.models.lead import Lead
    from app.middleware.org_context import get_current_organization
    from server import app

    user, org = await _seed_org_with_user(
        db_session, email=f"vw-{uuid.uuid4()}@x.com", slug_hint="viewer"
    )
    user_id, org_id = user.id, org.id
    await db_session.commit()

    async def _override() -> OrgContext:
        return OrgContext(
            user_id=user_id,
            auth_subject=f"sub-{org_id}",
            organization_id=org_id,
            membership_role="viewer",
        )

    csv_bytes = _csv("Name,Phone,Email\nAda,+14155550123,ada@example.com\n")
    app.dependency_overrides[get_current_organization] = _override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/leads/import/commit",
                files={"file": ("contacts.csv", csv_bytes, "text/csv")},
            )
    finally:
        app.dependency_overrides.pop(get_current_organization, None)

    try:
        assert r.status_code == 403, r.text
        db_session.expire_all()
        rows = (
            await db_session.scalars(select(Lead).where(Lead.organization_id == org_id))
        ).all()
        assert rows == []
    finally:
        await _cleanup(db_session, org_ids=[org_id], user_ids=[user_id])
