"""Google Sheet schema/contract validation helpers."""

from __future__ import annotations

from dataclasses import dataclass


RANKED_TOPICS_CONTRACT_VERSION = "v2-ranked-topics-workflow"

RANKED_TOPICS_REQUIRED_COLUMNS = [
    "topic_id",
    "rank",
    "title",
    "summary",
    "primary_region",
    "stakeholder_tags",
    "source_references",
    "decision",
    "channels",
    "linkedin_voice",
    "blog_lens",
    "edited_title",
    "edited_summary",
    "content_guidance",
    "reviewer_notes",
]


class SheetContractError(RuntimeError):
    """Raised when sheet schema/version does not match expected contract."""


@dataclass
class SheetContractStatus:
    ok: bool
    version: str | None
    missing_columns: list[str]


def validate_ranked_topics_contract(sheets) -> SheetContractStatus:
    """Validate Ranked Topics column contract and optional version marker."""
    ws = sheets._ws("Ranked Topics")
    data = ws.get_all_values()
    if not data:
        return SheetContractStatus(
            ok=False,
            version=None,
            missing_columns=list(RANKED_TOPICS_REQUIRED_COLUMNS),
        )

    headers = data[0]
    missing = [c for c in RANKED_TOPICS_REQUIRED_COLUMNS if c not in headers]
    version = _read_contract_version(sheets)
    ok = (not missing) and (version in (None, RANKED_TOPICS_CONTRACT_VERSION))
    return SheetContractStatus(ok=ok, version=version, missing_columns=missing)


def ensure_ranked_topics_contract(sheets) -> None:
    """Raise a clear error if Ranked Topics schema/version is incompatible."""
    status = validate_ranked_topics_contract(sheets)
    issues: list[str] = []
    if status.missing_columns:
        issues.append(
            "missing required columns: " + ", ".join(status.missing_columns)
        )
    if status.version not in (None, RANKED_TOPICS_CONTRACT_VERSION):
        issues.append(
            f"contract version mismatch: expected '{RANKED_TOPICS_CONTRACT_VERSION}', "
            f"found '{status.version}'"
        )
    if issues:
        raise SheetContractError(
            "Ranked Topics sheet contract validation failed (" + "; ".join(issues) + "). "
            "Run setup_sheet.py to align headers and update Reference contract version."
        )


def upsert_contract_version_marker(sheets) -> None:
    """Write/update sheet contract version marker in Reference tab."""
    ws = sheets._ws("Reference")
    data = ws.get_all_values()
    marker = ["Contract", "ranked_topics_workflow", RANKED_TOPICS_CONTRACT_VERSION, "Do not edit manually"]

    if not data:
        ws.update("A1", [["Category", "Key", "Label", "Description"], marker])
        return

    headers = data[0]
    if len(headers) < 4:
        # Keep behavior simple and safe; setup_sheet.py should own header shape.
        return

    for i, row in enumerate(data[1:], start=2):
        if len(row) >= 2 and row[0] == "Contract" and row[1] == "ranked_topics_workflow":
            ws.update(f"A{i}:D{i}", [marker])
            return

    ws.append_rows([marker], value_input_option="USER_ENTERED")


def _read_contract_version(sheets) -> str | None:
    """Return version marker from Reference tab, if present."""
    try:
        ws = sheets._ws("Reference")
        data = ws.get_all_values()
    except Exception:
        return None

    if len(data) < 2:
        return None

    for row in data[1:]:
        if len(row) >= 3 and row[0] == "Contract" and row[1] == "ranked_topics_workflow":
            return row[2] or None
    return None
