"""R10 — Security service.

Deterministic, dependency-free security primitives that run inline on the
existing stack (no external AI calls required):

* **PII detection + masking** — email / phone / credit-card / SSN / Aadhaar /
  PAN / passport / IBAN-style bank accounts.
* **Prompt-injection detection** — flags jailbreak / instruction-override
  attempts before text reaches the LLM.
* **Content moderation** — keyword-class screening (violence, harassment,
  self-harm, adult, illegal, malware, fraud).
* **Output validation** — catches leaked secrets (AWS keys, private keys,
  bearer tokens) and internal URLs in model output.

These are intentionally conservative heuristics that provide a working safety
layer today; they can later be augmented with Amazon Comprehend / Bedrock
Guardrails without changing the call sites.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.operations import (
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
)


# ─────────────────────────── PII ───────────────────────────
_LUHN_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

PII_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?){2,4}\d{2,4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "passport": re.compile(r"\b[A-PR-WYa-pr-wy][1-9]\d{6,7}\b"),
    "ip_address": re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
    "bank_account": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
}


def _luhn_ok(number: str) -> bool:
    digits = [int(c) for c in re.sub(r"\D", "", number)]
    if not (13 <= len(digits) <= 19):
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def detect_pii(text: str) -> list[dict[str, Any]]:
    """Return a list of ``{type, value, start, end}`` PII findings."""
    findings: list[dict[str, Any]] = []
    if not text:
        return findings
    for pii_type, pattern in PII_PATTERNS.items():
        for m in pattern.finditer(text):
            findings.append(
                {"type": pii_type, "value": m.group(0), "start": m.start(), "end": m.end()}
            )
    # credit cards: regex candidates validated by Luhn
    for m in _LUHN_RE.finditer(text):
        if _luhn_ok(m.group(0)):
            findings.append(
                {"type": "credit_card", "value": m.group(0), "start": m.start(), "end": m.end()}
            )
    return findings


def _mask_value(value: str) -> str:
    digits_letters = re.sub(r"\s", "", value)
    if len(digits_letters) <= 4:
        return "*" * len(value)
    visible = value[-4:]
    return "*" * (len(value) - 4) + visible


def mask_pii(text: str) -> dict[str, Any]:
    """Replace detected PII with masked tokens. Returns masked text + findings."""
    findings = detect_pii(text or "")
    if not findings:
        return {"text": text, "findings": [], "masked": False}
    # mask from the end so indices stay valid
    out = text
    for f in sorted(findings, key=lambda x: x["start"], reverse=True):
        out = out[: f["start"]] + _mask_value(f["value"]) + out[f["end"] :]
    redacted = [{"type": f["type"], "start": f["start"], "end": f["end"]} for f in findings]
    return {"text": out, "findings": redacted, "masked": True}


# ─────────────────────────── prompt injection ───────────────────────────
INJECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("instruction_override", re.compile(r"ignore (?:all )?(?:the )?(?:previous|prior|above) (?:instructions|prompts?)", re.I)),
    ("system_prompt_leak", re.compile(r"(?:reveal|show|print|repeat)(?:\s+me)?\s+(?:your|the)\s+(?:system\s+prompt|instructions|rules)", re.I)),
    ("role_escape", re.compile(r"you are now (?:a|an|in)\s|developer mode|do anything now|\bDAN\b", re.I)),
    ("exfiltration", re.compile(r"(?:send|email|post|leak|exfiltrate).{0,30}(?:password|secret|api[_\s-]?key|database|credentials)", re.I)),
    ("override_guardrails", re.compile(r"(?:disregard|bypass|override).{0,20}(?:safety|guardrails?|filters?|policy)", re.I)),
    ("prompt_terminator", re.compile(r"</?(?:system|assistant|user)>|\[/?INST\]|###\s*system", re.I)),
]


def detect_prompt_injection(text: str) -> dict[str, Any]:
    """Flag likely prompt-injection / jailbreak attempts."""
    if not text:
        return {"injection": False, "flags": []}
    flags = [name for name, pat in INJECTION_PATTERNS if pat.search(text)]
    return {"injection": bool(flags), "flags": flags}


def sanitize_prompt(text: str) -> dict[str, Any]:
    """Return ``{safe, text, flags}`` — neutralises terminator tokens."""
    result = detect_prompt_injection(text)
    cleaned = INJECTION_PATTERNS[-1][1].sub(" ", text or "")  # strip terminators
    return {"safe": not result["injection"], "text": cleaned, "flags": result["flags"]}


# ─────────────────────────── content moderation ───────────────────────────
MODERATION_LEXICON: dict[str, list[str]] = {
    "violence": ["kill", "murder", "attack", "bomb", "shoot", "assault", "terror"],
    "harassment": ["idiot", "stupid", "hate you", "worthless", "loser"],
    "self_harm": ["suicide", "self-harm", "kill myself", "end my life"],
    "adult": ["porn", "explicit sexual", "nsfw"],
    "illegal": ["how to make a bomb", "buy drugs", "counterfeit", "launder money"],
    "malware": ["ransomware", "keylogger", "rootkit", "sql injection payload", "exploit kit"],
    "fraud": ["phishing", "steal credit card", "fake invoice", "wire fraud"],
}


def moderate_content(text: str) -> dict[str, Any]:
    """Keyword-class moderation. Returns categories + an overall ``flagged``."""
    if not text:
        return {"flagged": False, "categories": []}
    low = text.lower()
    categories = [cat for cat, words in MODERATION_LEXICON.items() if any(w in low for w in words)]
    return {"flagged": bool(categories), "categories": categories}


# ─────────────────────────── output validation ───────────────────────────
SECRET_PATTERNS: dict[str, re.Pattern] = {
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "aws_secret_key": re.compile(r"\b(?<![A-Za-z0-9/+])[A-Za-z0-9/+]{40}(?![A-Za-z0-9/+])"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*", re.I),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    "internal_url": re.compile(r"https?://(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|169\.254\.\d+\.\d+)"),
    "connection_string": re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb)(?:\+\w+)?://[^\s\"']+", re.I),
}


def validate_output(text: str) -> dict[str, Any]:
    """Detect secrets / internal URLs that must never appear in model output."""
    if not text:
        return {"safe": True, "violations": []}
    violations = [name for name, pat in SECRET_PATTERNS.items() if pat.search(text)]
    return {"safe": not violations, "violations": violations}


def redact_output(text: str) -> dict[str, Any]:
    """Mask any detected secrets in output. Returns redacted text + violations."""
    if not text:
        return {"text": text, "violations": [], "redacted": False}
    out = text
    violations: list[str] = []
    for name, pat in SECRET_PATTERNS.items():
        if pat.search(out):
            violations.append(name)
            out = pat.sub("[REDACTED]", out)
    return {"text": out, "violations": violations, "redacted": bool(violations)}


# ─────────────────────────── orchestrator ───────────────────────────
def scan_text(text: str, *, direction: str = "input") -> dict[str, Any]:
    """Run the full security scan on a piece of text.

    ``direction='input'`` runs PII + injection + moderation (user → LLM);
    ``direction='output'`` additionally runs output validation (LLM → user).
    """
    pii = detect_pii(text)
    injection = detect_prompt_injection(text)
    moderation = moderate_content(text)
    result: dict[str, Any] = {
        "direction": direction,
        "pii": {"detected": bool(pii), "count": len(pii), "types": sorted({p["type"] for p in pii})},
        "prompt_injection": injection,
        "moderation": moderation,
    }
    if direction == "output":
        result["output_validation"] = validate_output(text)
    issues = (
        bool(pii)
        or injection["injection"]
        or moderation["flagged"]
        or (direction == "output" and not result.get("output_validation", {}).get("safe", True))
    )
    result["safe"] = not issues
    # derive a severity for any event this scan triggers
    if injection["injection"] or moderation["flagged"]:
        result["severity"] = SecuritySeverity.HIGH
    elif pii or (direction == "output" and not result.get("output_validation", {}).get("safe", True)):
        result["severity"] = SecuritySeverity.MEDIUM
    else:
        result["severity"] = SecuritySeverity.INFO
    return result


# ─────────────────────────── persistence ───────────────────────────
async def record_security_event(
    session: AsyncSession,
    *,
    organization_id: Optional[uuid.UUID],
    event_type: str,
    title: str,
    severity: str = SecuritySeverity.INFO,
    description: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
    commit: bool = True,
) -> SecurityEvent:
    event = SecurityEvent(
        organization_id=organization_id,
        user_id=user_id,
        severity=severity,
        event_type=event_type,
        title=title,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        meta=meta or {},
    )
    session.add(event)
    if commit:
        await session.commit()
        await session.refresh(event)
    return event
