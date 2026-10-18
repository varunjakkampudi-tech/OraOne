"""Lead import scenarios: a spreadsheet is parsed and checked row by row, consent is recorded
only when the file says so, duplicates are caught, unsupported or corrupt files are refused,
and duplicate checks only look inside the importing organization.

Parsing and validation are pure. The duplicate check uses a scripted session with no rows.
"""

from __future__ import annotations

import pytest

from app.services import lead_import_service as imports
from app.services.lead_import_service import LeadImportError
from scenario_support import ORG_A, ORG_B, FakeSession, sql

CLEAN_CSV = (
    b"Name,Email,Phone,Company,Consent\n"
    b"Ada Lovelace,ada@example.test,+44 7700 900123,Analytical Ltd,yes\n"
    b"Grace Hopper,grace@example.test,,Navy Labs,\n"
)


# ───────────────────────── happy path ─────────────────────────


@pytest.mark.smoke
async def test_clean_csv_is_imported_with_consent_exactly_as_the_file_states_it():
    parsed = imports.prepare_import(CLEAN_CSV, "contacts.csv")
    await imports.classify_rows(FakeSession(), organization_id=ORG_A, parsed=parsed)

    assert parsed.file_format == "csv"
    assert imports.summarise(parsed) == {
        "valid": 2,
        "duplicate_existing": 0,
        "duplicate_in_file": 0,
        "invalid": 0,
    }
    ada, grace = parsed.rows
    assert ada.phone == "+447700900123"
    assert ada.consent == "granted"
    assert grace.consent == "unknown"


# ───────────────────────── refusals ─────────────────────────


@pytest.mark.critical
def test_consent_cell_that_is_not_yes_no_or_blank_rejects_the_row():
    data = b"Name,Email,Consent\nMaybe Person,maybe@example.test,probably\n"

    parsed = imports.prepare_import(data, "contacts.csv")

    row = parsed.rows[0]
    assert row.status == imports.ROW_INVALID
    assert "Consent must be yes, no, or left blank" in row.reason
    assert row.consent is None


@pytest.mark.critical
def test_blank_consent_is_recorded_as_unknown_never_as_granted():
    data = b"Name,Email\nNo Consent,noconsent@example.test\n"

    parsed = imports.prepare_import(data, "contacts.csv")

    assert parsed.rows[0].status == imports.ROW_VALID
    assert parsed.rows[0].consent == "unknown"


@pytest.mark.critical
def test_unsupported_file_type_is_refused_before_it_is_parsed():
    with pytest.raises(LeadImportError):
        imports.prepare_import(CLEAN_CSV, "contacts.pdf")


@pytest.mark.critical
def test_row_without_any_way_to_reach_the_contact_is_skipped():
    data = b"Name,Company\nNo Route,Acme\n"

    parsed = imports.prepare_import(data, "contacts.csv")

    assert parsed.rows[0].status == imports.ROW_INVALID
    assert "Add a phone number or an email address" in parsed.rows[0].reason


# ───────────────────────── external failure ─────────────────────────


@pytest.mark.regression
def test_corrupt_spreadsheet_is_a_clean_refusal_not_a_server_error():
    corrupt = b"PK\x03\x04 this is not really a workbook"

    with pytest.raises(LeadImportError):
        imports.prepare_import(corrupt, "contacts.xlsx")


@pytest.mark.regression
def test_file_with_headings_but_no_contacts_is_refused_with_a_reason():
    with pytest.raises(LeadImportError) as refused:
        imports.prepare_import(b"Name,Email\n", "contacts.csv")

    assert refused.value.status_code == 422


# ───────────────────────── tenant isolation ─────────────────────────


@pytest.mark.critical
async def test_duplicate_check_only_looks_inside_the_importing_organization():
    parsed = imports.prepare_import(CLEAN_CSV, "contacts.csv")
    session = FakeSession()

    await imports.classify_rows(session, organization_id=ORG_A, parsed=parsed)

    statement = sql(session.statements[0])
    assert str(ORG_A) in statement
    assert str(ORG_B) not in statement
    assert "deleted_at IS NULL" in statement


@pytest.mark.regression
async def test_repeated_address_in_one_file_is_flagged_as_a_duplicate():
    data = b"Name,Email\nFirst,repeat@example.test\nSecond,repeat@example.test\n"
    parsed = imports.prepare_import(data, "contacts.csv")

    await imports.classify_rows(FakeSession(), organization_id=ORG_A, parsed=parsed)

    assert [r.status for r in parsed.rows] == [
        imports.ROW_VALID,
        imports.ROW_DUPLICATE_IN_FILE,
    ]
