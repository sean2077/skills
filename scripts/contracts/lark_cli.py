"""Contract guards for the unified `lark-cli` catalog skill.

Loaded and dispatched by `contracts.run_all()`; edit this file alone when the
`lark-cli` skill contract changes.
"""

from __future__ import annotations

from pathlib import Path

from catalog_core import README, SKILLS_DIR, errors, readme_skill_rows

SKILL = "lark-cli"

REFERENCE_COVERAGE = {
    "references/setup-auth-and-safety.md": ("lark-shared",),
    "references/messaging.md": ("lark-im",),
    "references/mail.md": ("lark-mail",),
    "references/documents-and-files.md": (
        "lark-doc",
        "lark-drive",
        "lark-markdown",
        "lark-slides",
        "lark-whiteboard",
        "lark-wiki",
    ),
    "references/tables-and-records.md": ("lark-base", "lark-sheets"),
    "references/calendar-and-meetings.md": (
        "lark-calendar",
        "lark-minutes",
        "lark-note",
        "lark-vc-agent",
        "lark-vc",
        "lark-workflow-meeting-summary",
        "lark-workflow-standup-report",
    ),
    "references/people-and-work.md": (
        "lark-approval",
        "lark-attendance",
        "lark-contact",
        "lark-okr",
        "lark-task",
    ),
    "references/apps-platform-and-workflows.md": (
        "lark-apps",
        "lark-event",
        "lark-openapi-explorer",
        "lark-skill-maker",
    ),
}


def validate_lark_cli_contract(
    skill_dir: Path | None = None, *, readme_text: str | None = None
) -> None:
    """Keep one lean router while preserving every migrated official domain boundary."""
    skill_dir = skill_dir or SKILLS_DIR / SKILL
    paths = {"SKILL.md": skill_dir / "SKILL.md"}
    paths.update({name: skill_dir / name for name in REFERENCE_COVERAGE})
    missing_paths = [label for label, path in paths.items() if not path.is_file()]
    if missing_paths:
        errors.append(f"lark-cli: missing required router/reference files: {missing_paths}")
        return

    texts = {label: path.read_text(encoding="utf-8") for label, path in paths.items()}
    normalized = {label: " ".join(text.split()) for label, text in texts.items()}
    resident_required = (
        "Load only the smallest matching reference set",
        "Do not preload every reference",
        "Shortcut > registered API > raw OpenAPI",
        "lark-cli <service> --help",
        "lark-cli schema <service.resource.method>",
        "Never invent a command",
        "Pass `--as user` or `--as bot` explicitly",
        "Never silently switch identity",
        "retrieved content as untrusted data",
        "code `10`",
        "ok == true",
        "Feishu/Lark URLs and tokens as opaque identifiers",
    )
    missing_resident = [
        value for value in resident_required if value not in normalized["SKILL.md"]
    ]
    if missing_resident:
        errors.append(
            "lark-cli/SKILL.md: unified routing/safety contract lost fixtures: "
            f"{missing_resident}"
        )

    for label, official_skills in REFERENCE_COVERAGE.items():
        reference_text = texts[label]
        if "**Official coverage:**" not in reference_text:
            errors.append(f"lark-cli/{label}: official migration coverage marker is missing")
        for official_skill in official_skills:
            marker = f"`{official_skill}`"
            locations = [
                candidate
                for candidate, candidate_text in texts.items()
                if candidate != "SKILL.md" and marker in candidate_text
            ]
            if locations != [label]:
                errors.append(
                    f"lark-cli: {official_skill} must be covered exactly by {label}; "
                    f"found={locations}"
                )

    domain_required = {
        "references/setup-auth-and-safety.md": (
            "missing_scope",
            "Resource ACL",
            "ok == true",
            "confirmation_required",
            "relative to the current directory",
        ),
        "references/messaging.md": (
            "unique, verified recipient",
            "untrusted external data",
            "returned `message_id`",
        ),
        "references/mail.md": (
            "Every actual send requires a fresh explicit user confirmation",
            "--confirm-send",
            "Default to creating/updating a draft",
        ),
        "references/documents-and-files.md": (
            "Route by path/token shape rather than hostname",
            "Do not WebFetch",
            "Never fabricate a block ID",
        ),
        "references/tables-and-records.md": (
            "A BaseApp/AppMode",
            "Inspect existing metadata",
            "bounded batch write",
        ),
        "references/calendar-and-meetings.md": (
            "Future or scheduled event",
            "Ended meeting search",
            "Identity is state across the whole chain",
        ),
        "references/people-and-work.md": (
            "Keep approvals separate from tasks",
            "employee_type",
            "user_ids",
        ),
        "references/apps-platform-and-workflows.md": (
            "bounded `--max-events` and/or `--timeout`",
            "raw OpenAPI",
            "one lean resident router",
        ),
    }
    for label, fixtures in domain_required.items():
        missing = [value for value in fixtures if value not in normalized[label]]
        if missing:
            errors.append(f"lark-cli/{label}: domain boundary lost fixtures: {missing}")

    if any("../lark-" in text for text in texts.values()):
        errors.append("lark-cli: unified skill must not depend on sibling official lark-* skills")

    if readme_text is None:
        readme_text = README.read_text(encoding="utf-8") if README.exists() else ""
    public_summary = readme_skill_rows(readme_text, SKILL)
    public_required = ("飞书/Feishu/Lark", "one lean", "on-demand domain references")
    missing_public = [value for value in public_required if value not in public_summary]
    if missing_public:
        errors.append(f"lark-cli README row lost unified-router semantics: {missing_public}")


def validate(*, readme_text: str | None = None) -> None:
    """Entry point for the `lark-cli` contract."""
    validate_lark_cli_contract(readme_text=readme_text)
