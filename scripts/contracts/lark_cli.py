"""Contract guards for the unified, context-cached `lark-cli` catalog skill.

Loaded and dispatched by `contracts.run_all()`; edit this file alone when the
`lark-cli` skill contract changes.
"""

from __future__ import annotations

from pathlib import Path

from catalog_core import SKILLS_DIR, errors

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
    """Keep one lean router, session reuse, fast paths, and every domain boundary."""
    skill_dir = skill_dir or SKILLS_DIR / SKILL
    paths = {"SKILL.md": skill_dir / "SKILL.md"}
    paths.update({name: skill_dir / name for name in REFERENCE_COVERAGE})
    missing_paths = [label for label, path in paths.items() if not path.is_file()]
    if missing_paths:
        errors.append(f"lark-cli: missing required router/reference files: {missing_paths}")
        return

    texts = {label: path.read_text(encoding="utf-8") for label, path in paths.items()}
    normalized = {label: " ".join(text.split()) for label, text in texts.items()}

    # Generic validation owns routing metadata, reference links and budgets.
    # Do not pin call-quota ceremony, but keep fail-closed resident safety:
    # identity continuity, confirmation, untrusted payloads, and path containment.
    frontmatter = texts["SKILL.md"].split("---", 2)[1] if texts["SKILL.md"].startswith("---") else texts["SKILL.md"]
    missing_triggers = [token for token in ("飞书", "Larksuite") if token not in frontmatter]
    if missing_triggers:
        errors.append(
            f"lark-cli/SKILL.md: routing description lost language/product triggers: {missing_triggers}"
        )
    resident_safety = (
        "never silently switch identity",
        "Never carry a prior `--yes`",
        "untrusted data",
        "contradictory signals",
        "confirmation_required",
        "must not self-supply `--yes`",
        "CLI file paths must be relative",
    )
    missing_safety = [value for value in resident_safety if value not in normalized["SKILL.md"]]
    if missing_safety:
        errors.append(f"lark-cli/SKILL.md: resident safety contract lost fixtures: {missing_safety}")

    overlay = "the resident identity, uncertainty, and verification exceptions still apply"
    for label in REFERENCE_COVERAGE:
        if label == "references/setup-auth-and-safety.md":
            continue
        if overlay not in normalized[label]:
            errors.append(
                f"lark-cli/{label}: domain fast path lost the resident identity/uncertainty exception"
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
            "Session context cache",
            "current live model context, including later related user turns",
            "If the host already injected `SKILL.md`, do not issue a second file read",
            "do not reopen it just to “refresh” it",
            "never carry `--yes`, mail `--confirm-send`, or an idempotency key",
            "Targeted drift fallback",
            "Cache the discovered contract for as long as it remains in the current live context",
            "Do not turn every request into an environment audit",
            "missing_scope",
            "Resource ACL",
            "ok == true",
            "confirmation_required",
            "relative to the current directory",
            "lark-cli config init --new",
            "lark-cli config bind --identity bot-only",
            "explicit approval of `bot-only` or `user-default`",
            "background-capable execution path",
            "--no-wait --json",
            "lark-cli auth qrcode",
            "A bot missing a scope",
            "error.hint",
            "_notice.update",
            "lark-cli update",
        ),
        "references/messaging.md": (
            "Known `chat_id` (`oc_...`) -> one IM command",
            "Known user/bot `open_id` (`ou_...`) -> one IM command with `--user-id`",
            "lark-cli im +messages-send",
            "--no-reactions",
            "unique, verified recipient",
            "untrusted external data",
            "response containing `ok == true`, `message_id`",
            "Do not issue a follow-up message read",
        ),
        "references/mail.md": (
            "Fast-path contract",
            "lark-cli mail +triage",
            "lark-cli mail +messages",
            "--html=false",
            "Every actual send requires a fresh explicit user confirmation",
            "--confirm-send",
            "Default to creating/updating a draft",
            "lark-cli mail user_mailbox.messages send_status",
            "run the documented delivery check exactly once",
            "For a scheduled send, do not poll immediately",
        ),
        "references/documents-and-files.md": (
            "Fast-path routing and call budget",
            "A clear URL path is enough to choose the service",
            "lark-cli docs +fetch",
            "lark-cli drive +download --url",
            "do not WebFetch a protected resource",
            "Never fabricate a block ID",
            "Do not refetch the whole resource",
            "--start-block-id",
            "--end-block-id",
            "lark-cli drive +add-comment",
            "lark-cli drive +list-comments",
            "--solved-status true",
            "--solved-status all",
            "lark-cli slides +update-slide",
            "@./",
        ),
        "references/tables-and-records.md": (
            "Fast-path contract",
            "lark-cli sheets +csv-get",
            "lark-cli sheets +cells-set",
            "lark-cli base +record-batch-create",
            "A BaseApp/AppMode",
            "lark-cli sheets +formula-verify",
            "Formula writes must run the known verifier directly",
            "one focused `+record-list`/`+record-search` acceptance read",
            "border_styles",
            "Borders belong inside each `cell_styles` item",
            "Do not reconstruct retired sheets resource commands",
        ),
        "references/calendar-and-meetings.md": (
            "Fast-path contract and call budget",
            "lark-cli calendar +agenda",
            "lark-cli calendar +suggestion",
            "lark-cli calendar +list-attendees",
            "does not include attendees",
            "lark-cli calendar +join-event",
            "Do not automatically issue a second `+get`/`+agenda` query",
            "reusing it when its relevant recipe is already in active context",
            "Future or scheduled event",
            "Ended meeting search",
            "lark-cli vc +meeting-list-active --as bot --user-id",
            "Identity is state across the whole chain",
            "lark-cli note +transcript",
            "note_display_type=unified",
            "explicit consent",
            "./notes/{note_id}/unified_transcript.md",
        ),
        "references/people-and-work.md": (
            "Fast-path contract and call budget",
            "lark-cli contact +search-user",
            "lark-cli task +get-my-tasks --complete=false",
            "lark-cli task +complete",
            "lark-cli schema task.tasks.create",
            "do not routinely call task get afterward",
            "reusing it when its relevant rules are already in active context",
            "Keep approvals separate from tasks",
            "employee_type",
            "user_ids",
        ),
        "references/apps-platform-and-workflows.md": (
            "Treat the commands below as the maintained command cache",
            "lark-cli apps +list --keyword",
            "lark-cli apps +create",
            "lark-cli apps +metric-list",
            "lark-cli apps +env-set",
            "lark-cli event consume",
            "--max-events 1 --timeout 30s",
            "do not run `event list`, `event schema`, or `event --help` first",
            "Maintaining the command cache",
            "reuse exact relevant content already in active context instead of reopening it",
            "raw OpenAPI",
            "one lean resident router",
            "query strings or fragments",
            "--params",
        ),
    }
    for label, fixtures in domain_required.items():
        missing = [value for value in fixtures if value not in normalized[label]]
        if missing:
            errors.append(f"lark-cli/{label}: domain fast path/boundary lost fixtures: {missing}")

    retired_reference_patterns = {
        "references/setup-auth-and-safety.md": (
            "Cache the discovered contract for the rest of the current task",
        ),
        "references/calendar-and-meetings.md": (
            "Also load **People and work**",
        ),
        "references/people-and-work.md": (
            "Load **Calendar and meetings** for agenda semantics",
        ),
        "references/apps-platform-and-workflows.md": (
            "Inspect `lark-cli apps --help` and the exact shortcut help",
            "inspect `lark-cli event --help` first",
            "Load every genuinely required domain reference",
        ),
    }
    for label, patterns in retired_reference_patterns.items():
        restored = [value for value in patterns if value in normalized[label]]
        if restored:
            errors.append(
                f"lark-cli/{label}: unconditional domain discovery was restored: {restored}"
            )

    if any("../lark-" in text for text in texts.values()):
        errors.append("lark-cli: unified skill must not depend on sibling official lark-* skills")



def validate(*, readme_text: str | None = None) -> None:
    """Entry point for the `lark-cli` contract."""
    validate_lark_cli_contract(readme_text=readme_text)
