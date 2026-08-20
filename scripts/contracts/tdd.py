"""Contract guards for the stack-neutral `tdd` catalog skill.

Loaded and dispatched by `contracts.run_all()`; edit this file alone when the
`tdd` skill contract changes.
"""

from __future__ import annotations

import re
from pathlib import Path

from catalog_core import README, SKILLS_DIR, errors, readme_skill_rows

SKILL = "tdd"

REFERENCE_FILES = (
    "references/test-design.md",
    "references/test-doubles-and-effects.md",
    "references/cross-stack-execution.md",
    "references/legacy-and-hard-cases.md",
)

CROSS_STACK_MARKERS = (
    "JavaScript/TypeScript",
    "Python",
    "Go",
    "Rust",
    "JVM",
    ".NET",
    "C/C++",
    "Ruby",
    "PHP",
    "Swift/Objective-C",
    "Elixir/Erlang",
    "Dart/Flutter",
    "Infrastructure/data",
    "Embedded/hardware",
)

FORBIDDEN_DOGMAS = (
    (re.compile(r"(?i)\bconfirm (?:them|the seams?) with the user\b"), "ritual seam approval"),
    (re.compile(r"(?i)\bno test is written at an unconfirmed seam\b"), "unconfirmed-seam ban"),
    (re.compile(r"(?i)\btests live at seams, never against internals\b"), "absolute seam rule"),
    (re.compile(r"(?i)\bone logical assertion per test\b"), "one-assertion dogma"),
    (re.compile(r"(?i)\bmock at system boundaries only\b"), "absolute mocking rule"),
    (re.compile(r"(?i)\brefactoring is not part of the loop\b"), "refactor exclusion"),
    (
        re.compile(
            r"(?i)\balways use (?:an? |the )?(?:unit|integration|end-to-end|e2e) tests?\b"
        ),
        "universal test-level mandate",
    ),
)

PUBLIC_STACK_ASSUMPTIONS = (
    re.compile(r"(?i)\bNode\.js\b"),
    re.compile(r"(?i)\bTypeScript\b"),
    re.compile(r"(?i)\bJavaScript\b"),
    re.compile(r"(?i)\b(?:npm|pnpm|yarn|bun)\s+(?:test|run)\b"),
    re.compile(r"(?i)\b(?:Jest|Vitest|Mocha|pytest)\b"),
    re.compile(r"(?i)\b(?:go|cargo|dotnet|mix|dart|flutter|swift)\s+test\b"),
    re.compile(r"(?i)\b(?:gradlew?|mvnw?|maven)\s+test\b"),
    re.compile(r"(?i)\b(?:ctest|phpunit|rspec|xctest)\b"),
    re.compile(r"(?i)\bxcodebuild\b"),
)


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _frontmatter_text(skill_text: str) -> str:
    """Return the leading frontmatter block for trigger-specific contract checks."""
    lines = skill_text.splitlines()
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[: index + 1])
    return ""


def _require(label: str, text: str, fixtures: tuple[str, ...], purpose: str) -> None:
    missing = [fixture for fixture in fixtures if fixture not in text]
    if missing:
        errors.append(f"tdd/{label}: {purpose} lost fixtures: {missing}")


def _is_explicit_rejection(text: str, start: int) -> bool:
    """Allow prose that names a dogma only to reject it."""
    prefix = text[max(0, start - 96) : start]
    sentence_prefix = re.split(r"[.!?\n]", prefix)[-1]
    return bool(
        re.search(
            r"(?i)\b(?:do not|don't|never|avoid|reject|prohibit)\b"
            r"(?:[ \t]+[a-z-]+){0,7}[ \t]*$",
            sentence_prefix,
        )
    )


def validate_tdd_semantics(text: str, *, source: str = "tdd") -> None:
    """Reject rigid upstream rules that do not survive cross-stack use."""
    found: list[str] = []
    for pattern, label in FORBIDDEN_DOGMAS:
        if any(
            not _is_explicit_rejection(text, match.start())
            for match in pattern.finditer(text)
        ):
            found.append(label)
    if found:
        errors.append(f"{source}: stack-neutral TDD semantics regressed to rigid dogma: {found}")


def validate_tdd_contract(
    skill_dir: Path | None = None, *, readme_text: str | None = None
) -> None:
    """Keep TDD explicitly triggered, project-derived, evidence-led, and stack-neutral."""
    skill_dir = skill_dir or SKILLS_DIR / SKILL
    paths = {"SKILL.md": skill_dir / "SKILL.md", "NOTICE.md": skill_dir / "NOTICE.md"}
    paths.update({name: skill_dir / name for name in REFERENCE_FILES})
    missing_paths = [label for label, path in paths.items() if not path.is_file()]
    if missing_paths:
        errors.append(f"tdd: missing required skill payload files: {missing_paths}")
        return

    texts = {label: path.read_text(encoding="utf-8") for label, path in paths.items()}
    normalized = {label: _normalized(text) for label, text in texts.items()}

    if readme_text is None:
        readme_text = README.read_text(encoding="utf-8") if README.exists() else ""
    public_summary = readme_skill_rows(readme_text, SKILL)
    public_text = f"{texts['SKILL.md']}\n{public_summary}"
    combined_text = "\n".join((*texts.values(), public_summary))
    frontmatter = _normalized(_frontmatter_text(texts["SKILL.md"]))

    _require(
        "SKILL.md frontmatter",
        frontmatter,
        (
            "name: tdd",
            "Use when the user explicitly requests test-driven or test-first implementation",
            "a failing regression test before a bug fix",
            "Applies across languages, frameworks, services, CLIs, libraries, data "
            "systems, infrastructure, and embedded targets",
            "Do not use merely because a change should include tests",
            "coverage-only work",
            "exploratory prototypes whose behavior has not stabilized",
        ),
        "explicit trigger and non-trigger boundary",
    )

    _require(
        "README.md",
        _normalized(public_summary),
        (
            "Apply explicitly requested test-first implementation across stacks",
            "deriving seams, oracles, test levels, and commands from the target project",
            "RED-GREEN-REFACTOR evidence",
        ),
        "public stack-neutral catalog summary",
    )

    _require(
        "SKILL.md",
        normalized["SKILL.md"],
        (
            "Do not activate merely because a change should have tests.",
            "This skill does not own requirements discovery, task orchestration, commits, "
            "code review, release",
            "Do not invent a framework, command, working directory, or test layout.",
            "A test-like target name is not proof of safety.",
            "Before editing, state the behavior, observation seam, independent oracle, test "
            "level, and expected RED reason.",
            "Do not ask for ritual seam confirmation.",
            "A RED result is valid only when the failure directly demonstrates the missing "
            "behavior.",
            "Use one vertical behavior slice per cycle.",
            "GREEN is the smallest production change that satisfies the current behavior",
            "REFACTOR only while green.",
            "Never weaken, delete, skip, quarantine, or silently regenerate a legitimate "
            "failing test",
            "Report skipped or unavailable checks and any residual risk; never imply they passed.",
            "references/test-design.md",
            "references/test-doubles-and-effects.md",
            "references/cross-stack-execution.md",
            "references/legacy-and-hard-cases.md",
        ),
        "resident trigger, ownership, cycle, and evidence contract",
    )

    _require(
        "references/test-design.md",
        normalized["references/test-design.md"],
        (
            "A public seam is contractually observable",
            "Prefer the cheapest stable seam",
            "Do not ask the user to approve an obvious existing seam.",
            "No level is universally superior",
            "Build an independent oracle",
            "Several assertions are appropriate when they jointly prove one behavior",
            "Direct database, filesystem, queue, or wire inspection can be correct",
            "Snapshots and golden files are useful when the artifact is itself the contract",
            "Coverage is a diagnostic for unexercised paths, not the behavior or the stopping "
            "rule.",
        ),
        "risk-selected seam, oracle, assertion, and artifact guidance",
    )

    _require(
        "references/test-doubles-and-effects.md",
        normalized["references/test-doubles-and-effects.md"],
        (
            "Replace an uncontrolled boundary",
            "Do not mock an owned collaborator merely because mocking is convenient",
            "**Stub:**",
            "**Fake:**",
            "do not turn sleeps and generous timeouts into correctness proof",
            "Do not contact production.",
            "Run contract tests against both a fake and the real adapter or provider sandbox",
            "simulator success as physical-device evidence",
        ),
        "purpose-driven doubles and real-effect safety guidance",
    )

    cross_stack = normalized["references/cross-stack-execution.md"]
    _require(
        "references/cross-stack-execution.md",
        cross_stack,
        (
            "Use this authority order",
            "Do not infer a command solely from a file extension",
            "A target named `test` is not proof of safety.",
            "Do not deploy, publish, flash devices, migrate shared state, mutate production data",
            "Project-owned commands always win.",
            "Do not make npm, Jest, Vitest, pytest, Cargo, Gradle, Maven, dotnet, CMake",
            "Runtime behavior",
            "Compile/type/link behavior",
            "Schema/plan/policy behavior",
            "Packaging/configuration behavior",
            "Target behavior",
            "When a command runs zero tests",
            "Verification ladder",
            "Test and change the source, generator, schema, template, or build rule",
        ),
        "project-derived command and RED interpretation guidance",
    )
    missing_stacks = [marker for marker in CROSS_STACK_MARKERS if marker not in cross_stack]
    if missing_stacks:
        errors.append(
            "tdd/references/cross-stack-execution.md: cross-ecosystem discovery coverage "
            f"lost markers: {missing_stacks}"
        )

    _require(
        "references/legacy-and-hard-cases.md",
        normalized["references/legacy-and-hard-cases.md"],
        (
            "Reproduce the defect through the narrowest stable affected seam",
            "Use a characterization test",
            "smallest behavior-preserving preparatory refactor",
            "Do not manufacture a low-value test solely to claim TDD.",
            "Do not use retries to turn a flaky RED into GREEN",
            "Compatibility, protocols, schemas, and migrations",
            "Security and privacy",
            "Performance and resource behavior",
            "Property-, model-, and fuzz-driven slices",
            "Data and ML systems",
            "host-only GREEN is not target GREEN",
        ),
        "legacy, regression, nondeterminism, compatibility, and target guidance",
    )

    _require(
        "NOTICE.md",
        normalized["NOTICE.md"],
        (
            "mattpocock/skills",
            "skills/engineering/tdd/",
            "MIT License",
            "Copyright (c) 2026 Matt Pocock",
            "The above copyright notice and this permission notice shall be included",
        ),
        "upstream provenance and MIT notice",
    )

    sibling_coupling = (
        "call the Skill tool",
        "`codebase-design`",
        "`code-review` skill",
        "read `CONTEXT.md`",
    )
    lower_combined = combined_text.casefold()
    found_coupling = [
        fixture for fixture in sibling_coupling if fixture.casefold() in lower_combined
    ]
    if found_coupling:
        errors.append(
            "tdd: retained external sibling-skill or filename coupling: "
            f"{found_coupling}"
        )

    stack_assumptions = sorted(
        {
            match.group(0)
            for pattern in PUBLIC_STACK_ASSUMPTIONS
            for match in pattern.finditer(public_text)
        }
    )
    if stack_assumptions:
        errors.append(
            "tdd: resident/public contract must stay stack-neutral; route ecosystem clues to the "
            f"cross-stack reference instead: {stack_assumptions}"
        )

    validate_tdd_semantics(combined_text)


def validate(*, readme_text: str | None = None) -> None:
    """Entry point for the `tdd` contract."""
    validate_tdd_contract(readme_text=readme_text)
