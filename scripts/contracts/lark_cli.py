"""Contract guards for the unified, context-cached `lark-cli` catalog skill.

Loaded and dispatched by `contracts.run_all()`; edit this file alone when the
`lark-cli` skill contract changes.
"""

from __future__ import annotations

from pathlib import Path

from catalog_core import REPO, SKILLS_DIR, errors, parse_frontmatter

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
        "lark-meeting",
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
    """Check discovery metadata and the self-contained domain reference inventory."""
    skill_dir = skill_dir or SKILLS_DIR / SKILL
    paths = {"SKILL.md": skill_dir / "SKILL.md"}
    paths.update({name: skill_dir / name for name in REFERENCE_COVERAGE})
    missing_paths = [label for label, path in paths.items() if not path.is_file()]
    if missing_paths:
        errors.append(f"lark-cli: missing required router/reference files: {missing_paths}")
        return

    texts = {label: path.read_text(encoding="utf-8") for label, path in paths.items()}

    # Inspect the parsed discovery field, not YAML comments or delimiter-like
    # text inside a scalar. Generic validation owns field types and budgets too.
    try:
        frontmatter = parse_frontmatter(texts["SKILL.md"])
    except ValueError as exc:
        errors.append(f"lark-cli/SKILL.md: invalid frontmatter: {exc}")
        return
    description = frontmatter.get("description")
    if not isinstance(description, str):
        errors.append("lark-cli/SKILL.md: routing description must be a string")
        return
    missing_triggers = [
        token for token in ("飞书", "Larksuite")
        if token.casefold() not in description.casefold()
    ]
    if missing_triggers:
        errors.append(
            f"lark-cli/SKILL.md: routing description lost language/product triggers: {missing_triggers}"
        )

    # Safety instructions and domain exceptions remain in the installed payload.
    # Searching their English spelling cannot establish identity, confirmation,
    # containment, or invented-syntax behavior. Exercise those decisions in the
    # live-eval suite, and keep the task fixtures whose oracles are deterministic:
    # the invented-syntax boundary is one of them.
    fixtures = {
        "evals/tasks/cases.py": REPO / "evals" / "tasks" / "cases.py",
        "scripts/tests/test_task_outcomes.py": REPO / "scripts" / "tests" / "test_task_outcomes.py",
    }
    texts_by_label = {
        label: path.read_text(encoding="utf-8") if path.exists() else ""
        for label, path in fixtures.items()
    }
    for label, markers in (
        ("evals/tasks/cases.py", ("lark-invented-syntax", "no undocumented mock invocation")),
        (
            "scripts/tests/test_task_outcomes.py",
            ("test_invented_mock_argument_shape_is_rejected",),
        ),
    ):
        missing_markers = [marker for marker in markers if marker not in texts_by_label[label]]
        if missing_markers:
            errors.append(
                f"{label}: the invented-syntax task fixture or its oracle coverage is missing: "
                f"{missing_markers}"
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

    if any("../lark-" in text for text in texts.values()):
        errors.append("lark-cli: unified skill must not depend on sibling official lark-* skills")



def validate(*, readme_text: str | None = None) -> None:
    """Entry point for the `lark-cli` contract."""
    validate_lark_cli_contract(readme_text=readme_text)
