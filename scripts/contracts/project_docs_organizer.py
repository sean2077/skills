"""Contract guards for the `project-docs-organizer` catalog skill.

Loaded and dispatched by `contracts.run_all()`; edit this file alone when the
`project-docs-organizer` skill contract changes.
"""

from __future__ import annotations

import re
from pathlib import Path

from catalog_core import README, SKILLS_DIR, errors, readme_skill_rows

SKILL = "project-docs-organizer"


PROJECT_DOC_METHOD_CARDS = (
    "Reader role",
    "Task or journey",
    "Domain capability, ownership, and language",
    "Product, subsystem, or interface surface",
    "Content purpose or information type",
    "Lifecycle or authority",
)


PROJECT_DOC_METHOD_FIELDS = (
    "Signals",
    "Ask",
    "Fits when",
    "Fails when",
    "Axis role",
    "Micro-example",
)


PROJECT_DOC_METHOD_FIELD = re.compile(
    r"^-[ \t]+\*\*(Signals|Ask|Fits when|Fails when|Axis role|Micro-example)\*\*:"
    r"[ \t]*(.*)$",
    re.MULTILINE,
)


PROJECT_DOC_H2 = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)


PROJECT_DOC_FENCE = re.compile(r"^[ \t]*(?:```|~~~)", re.MULTILINE)


PROJECT_DOC_TREE_ENTRY = re.compile(
    r"^\s*(?:[│├└─+|`\\-]+\s*)?[A-Za-z0-9_.-]+(?:/|\.mdx?)\s*$"
)


PROJECT_DOC_FIXED_RANGE = (
    re.compile(r"(?i)(?<![A-Za-z0-9])`?[0-9]+x`?(?![A-Za-z0-9])"),
    re.compile(
        r"(?i)(?<![0-9])`?[0-9]{1,2}\s*(?:-|–|—|\.\.|to|through)\s*"
        r"[0-9]{1,2}`?(?![0-9])"
    ),
)


PROJECT_DOC_FORCED_NUMBERING = (
    re.compile(
        r"(?i)(?<!not )(?<!never )\balways\s+(?:number|prefix)\b[^\n.!?]{0,80}"
    ),
    re.compile(
        r"(?i)\b(?:numbering|numeric prefixes?)\b[^\n.!?]{0,20}"
        r"\b(?:is|are|remain|remains|become|becomes)\s+"
        r"(?:(?:always|universally)\s+)?(?:required|mandatory)\b"
    ),
    re.compile(
        r"(?i)(?<!not )(?<!never )\b(?:every|all)\s+"
        r"(?:project|repository|documentation tree|docs tree)s?\b"
        r"[^\n.!?]{0,60}\b(?:must|shall)\b[^\n.!?]{0,40}"
        r"\b(?:numbering|numbered|numeric prefixes?)\b"
    ),
    re.compile(
        r"(?i)\b(?:numbering|numeric prefixes?)\b[^\n.!?]{0,40}"
        r"\b(?:cannot|must not|may not|never)\s+be\s+disabled\b"
    ),
    re.compile(
        r"(?i)(?<!not )(?<!never )\b(?:enable|apply|add|use)\s+"
        r"(?:numbering|numeric prefixes?)\s+"
        r"(?:for|to|in)\s+(?:all|every)\s+"
        r"(?:project|repository|documentation tree|docs tree)s?\b"
    ),
    re.compile(
        r"(?i)(?<!not )(?<!never )(?<!not always )(?<!never always )"
        r"\b(?:number|prefix)\s+(?:all|every)\s+"
        r"(?:project|repository|documentation tree|docs tree)s?\b"
    ),
    re.compile(
        r"(?i)(?<!not )(?<!never )\b(?:every|all)\s+"
        r"(?:project|repository|documentation tree|docs tree)s?\b[^\n.!?]{0,30}"
        r"\b(?:is|are|remain|remains|stay|stays)\s+(?:always\s+)?numbered\b"
    ),
    re.compile(
        r"(?i)\bnumbering\s+(?:always\s+)?(?:applies|is applied)\s+"
        r"(?:to|in)\s+(?:all|every)\s+"
        r"(?:project|repository|documentation tree|docs tree)s?\b"
    ),
)


PROJECT_DOC_DEFAULT_ON_NUMBERING = (
    re.compile(
        r"(?i)(?<!not )(?<!never )(?<!n't )\b(?:enable|use|apply)\s+"
        r"(?:local\s+)?numbering\s+by\s+default\b"
    ),
    re.compile(r"(?i)\boptional\s+default-on(?:\s+local)?\s+numbering\b"),
)


def markdown_h2_sections(text: str) -> dict[str, list[str]]:
    """Return level-two Markdown sections without treating deeper headings as peers."""
    matches = list(PROJECT_DOC_H2.finditer(text))
    sections: dict[str, list[str]] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.setdefault(match.group(1).strip(), []).append(text[match.end() : end])
    return sections


def method_example_is_tree(field_block: str) -> bool:
    """Reject fenced or visibly tree-shaped examples while allowing ordinary prose."""
    if PROJECT_DOC_FENCE.search(field_block) or any(
        marker in field_block for marker in ("├──", "└──", "│")
    ):
        return True
    tree_entries = [
        line for line in field_block.splitlines() if PROJECT_DOC_TREE_ENTRY.fullmatch(line)
    ]
    return len(tree_entries) >= 2


def validate_project_doc_method_cards(method_text: str) -> None:
    """Require the six method cards and their reasoning fields card by card."""
    sections = markdown_h2_sections(method_text)
    invalid_cards = [
        f"{title} ({len(sections.get(title, []))})"
        for title in PROJECT_DOC_METHOD_CARDS
        if len(sections.get(title, [])) != 1
    ]
    if invalid_cards:
        errors.append(
            "project-docs-organizer/references/classification-methods.md: "
            f"method-card set is incomplete or duplicated: {invalid_cards}"
        )

    for title in PROJECT_DOC_METHOD_CARDS:
        card_bodies = sections.get(title, [])
        if len(card_bodies) != 1:
            continue
        body = card_bodies[0]
        field_matches = list(PROJECT_DOC_METHOD_FIELD.finditer(body))
        field_counts = {
            field: sum(match.group(1) == field for match in field_matches)
            for field in PROJECT_DOC_METHOD_FIELDS
        }
        invalid_fields = [
            f"{field} ({count})" for field, count in field_counts.items() if count != 1
        ]
        empty_fields = [match.group(1) for match in field_matches if not match.group(2).strip()]
        invalid_fields.extend(f"{field} (empty)" for field in empty_fields)
        if invalid_fields:
            errors.append(
                "project-docs-organizer/references/classification-methods.md: "
                f"{title} method card must contain each reasoning field exactly once: "
                f"{invalid_fields}"
            )
            continue

        micro_index = next(
            index
            for index, match in enumerate(field_matches)
            if match.group(1) == "Micro-example"
        )
        micro_start = field_matches[micro_index].start()
        micro_end = (
            field_matches[micro_index + 1].start()
            if micro_index + 1 < len(field_matches)
            else len(body)
        )
        if method_example_is_tree(body[micro_start:micro_end]):
            errors.append(
                "project-docs-organizer/references/classification-methods.md: "
                f"{title} micro-example must be prose, not a directory tree"
            )


def validate_project_doc_numbering_semantics(
    numbering_text: str, *, combined_text: str | None = None
) -> None:
    """Reject global numeric taxonomies and unconditional or default-on numbering."""
    fixed_ranges = sorted(
        {
            match.group(0)
            for pattern in PROJECT_DOC_FIXED_RANGE
            for match in pattern.finditer(numbering_text)
        }
    )
    if fixed_ranges:
        errors.append(
            "project-docs-organizer: fixed numeric range notation is prohibited; "
            f"use sibling-local ordering tokens only: {fixed_ranges}"
        )

    forced_rules = sorted(
        {
            match.group(0).strip()
            for pattern in PROJECT_DOC_FORCED_NUMBERING
            for match in pattern.finditer(numbering_text)
        }
    )
    if forced_rules:
        errors.append(
            "project-docs-organizer/references/numbering-patterns.md: "
            f"unconditional numbering mandate contradicts project opt-outs: {forced_rules}"
        )
    default_on_rules = sorted(
        {
            match.group(0).strip()
            for pattern in PROJECT_DOC_DEFAULT_ON_NUMBERING
            for match in pattern.finditer(combined_text or numbering_text)
        }
    )
    if default_on_rules:
        errors.append(
            "project-docs-organizer: default-on numbering contradicts the evidence gate: "
            f"{default_on_rules}"
        )


def validate_project_docs_organizer_contract(
    skill_dir: Path | None = None, *, readme_text: str | None = None
) -> None:
    """Keep documentation structure evidence-led and local numbering project-owned."""
    skill_dir = skill_dir or SKILLS_DIR / "project-docs-organizer"
    paths = {
        "SKILL.md": skill_dir / "SKILL.md",
        "references/information-architecture.md": skill_dir / "references" / "information-architecture.md",
        "references/classification-methods.md": skill_dir / "references" / "classification-methods.md",
        "references/numbering-patterns.md": skill_dir / "references" / "numbering-patterns.md",
        "references/migration-and-links.md": skill_dir / "references" / "migration-and-links.md",
    }
    retired_zone_catalog = skill_dir / "references" / "zone-catalog.md"
    if retired_zone_catalog.exists():
        errors.append("project-docs-organizer: retired references/zone-catalog.md still exists")
    missing_files = [label for label, path in paths.items() if not path.exists()]
    if missing_files:
        errors.append(f"project-docs-organizer: missing required files: {missing_files}")
        return
    texts = {label: path.read_text(encoding="utf-8") for label, path in paths.items()}
    if readme_text is None:
        readme_text = README.read_text(encoding="utf-8") if README.exists() else ""
    public_summary = readme_skill_rows(readme_text, "project-docs-organizer")
    normalized = {label: " ".join(text.split()) for label, text in texts.items()}
    normalized_skill = normalized["SKILL.md"]
    project_owned_contract = (
        "The target project owns its information architecture",
        "smallest structure",
        "preserve a coherent established convention",
        "one primary axis per tree level",
        "documentation IA decision record",
        "two or three candidates",
        "wait for the user before mutation",
        "No empty category",
        "Resolve the target project root",
    )
    missing = [value for value in project_owned_contract if value not in normalized_skill]
    if missing:
        errors.append(
            "project-docs-organizer/SKILL.md: project-owned information architecture lost fixtures: "
            f"{missing}"
        )
    architecture_contract = (
        "Reader-route separation",
        "Vocabulary and ownership cohesion",
        "Lifecycle consistency",
        "Stability under change",
        "Duplication pressure",
        "Choose one primary axis",
        "secondary lenses",
        "representative placement test",
        "two or three candidates",
        "wait for the user before mutation",
        "absence of a convention",
        "not evidence for numbering",
        "stable sibling",
        "path/link churn",
    )
    missing_architecture = [
        value
        for value in architecture_contract
        if value not in normalized["references/information-architecture.md"]
    ]
    if missing_architecture:
        errors.append(
            "project-docs-organizer/references/information-architecture.md: "
            f"evidence-led selection contract is incomplete: {missing_architecture}"
        )
    validate_project_doc_method_cards(texts["references/classification-methods.md"])
    numbering_contract = (
        "Keep numbering disabled by default",
        "stable sibling",
        "observed reader route",
        "path/link churn",
        "coherent established convention",
        "documentation generator owns ordering or navigation",
        "sibling-local position",
        "`10-`",
        "`20-`",
        "`00-`",
        "genuine reading or execution order",
        "not category meaning",
    )
    missing_numbering = [
        value
        for value in numbering_contract
        if value not in normalized["references/numbering-patterns.md"]
    ]
    if missing_numbering:
        errors.append(
            "project-docs-organizer/references/numbering-patterns.md: "
            f"evidence and opt-out numbering contract is incomplete: {missing_numbering}"
        )
    combined = "\n".join((*texts.values(), public_summary))
    validate_project_doc_numbering_semantics(
        texts["references/numbering-patterns.md"], combined_text=combined
    )
    stale_template_rules = (
        "## Default Zone Model",
        "# Optional Documentation Zone Catalog",
        "## Candidate zone catalog",
        "`00-start-here`",
        "`20-development-overview`",
        "The developer area is `2x`",
        "one-class-per-zone rule",
        "semantic numbered zones",
    )
    found_stale = [value for value in stale_template_rules if value in combined]
    if found_stale:
        errors.append(
            "project-docs-organizer: retired zone-template semantics remain: "
            f"{found_stale}"
        )
    migration_contract = (
        "Build the migration map",
        "Before deleting",
        "rg -n -F 'old/path.md' <project-root>",
        "external wikis or issue trackers",
        "git diff --check",
    )
    missing_migration = [
        value for value in migration_contract if value not in texts["references/migration-and-links.md"]
    ]
    if missing_migration:
        errors.append(
            "project-docs-organizer/references/migration-and-links.md: migration evidence lost fixtures: "
            f"{missing_migration}"
        )


def validate(*, readme_text: str | None = None) -> None:
    """Entry point for the `project-docs-organizer` contract."""
    validate_project_docs_organizer_contract(readme_text=readme_text)
