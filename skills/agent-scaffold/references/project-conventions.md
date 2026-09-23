# Project conventions: adopt, fill, and maintain

Use this reference when initializing or upgrading the project harness, including a read-only
preview of that work. The Agent owns semantic adaptation; the installer owns deterministic
assets. An authorized full setup includes writing useful missing guidance, not only listing
recommendations. Routine docs cleanup, research, and scripting do not trigger scaffold.

## Accepted coverage

Apply [one-time selection](onboarding-selection.md) before full setup: all domains are offered
by default; the user can exclude any in one question. A recorded choice is reused, not asked
again on updates. The rows below are coverage areas for selected domains, not a requirement to
create one file per area. Do not maintain excluded domains or delete their existing guidance.
Core safety, permissions and source/projection ownership always apply.

## Discover the actual project

Resolve the authorized checkout and its applicable instructions first. Read existing entry
points, relevant build/docs configuration, and actual callers. Prefer explicit user choices
and applicable project conventions, then executable configuration and usage, then content;
use directory names only as clues. Where sources disagree, distinguish stale prose, intended
future behavior, and active contracts before changing anything.

Expand inspection only to answer material questions. Do not scan dependency caches, vendor
code, generated output, historical archives, or secret contents merely to inventory the repo.
A configured command is not evidence it has run; even `--help`/`--dry-run` needs an effects
check before invoking an unfamiliar wrapper. No dependency install, daemon start, network
publication, device access, or global-config change follows from discovery alone.

Adopt responsibility by purpose **and scope**, not one globally selected docs/tools root:

| Observed project | Adopt rather than normalize |
|---|---|
| `doc/`, `docs/`, `handbook/`, translated pages, or a docs-site source | Follow current navigation/configuration and preserve language, filenames, numbering, and frontmatter. |
| `docs/` contains generated API output, handwritten source lives elsewhere | Route edits to the generator/source; a familiar directory name does not make it writable guidance. |
| `tools/` contains standalone commands, `scripts/` build internals | Preserve both purposes, installed interfaces, and external consumers. Do not move them into `.agents/tools/`. |
| Make/Just/Task/package scripts already expose the needed jobs | Document those entries; do not add a tools directory or wrappers to standardize their names. |
| Modules have local guides, commands, and owners | Keep local differences local; root guidance routes to them rather than flattening them. |
| A workspace contains independent repos/submodules | Initialize only the authorized repository/checkout; do not recurse or assume shared ownership. |
| A Wiki, external docs repo, or symlinked location owns material | Keep the known route and owner; do not copy or write through it without authority. Unavailable content remains unverified. |
| A small/new repo has no established structure | Use concise project-owned prose in an existing entry point, or the smallest useful new page. Do not seed empty directories or a template catalog. |

## Fill real gaps, not a list of files

Use existing homes and equivalent guidance before adding content. A complete mature project
may need only links, or no changes. A new project may need one short section, not one file per
row below. Prefer facts that a new Agent cannot infer reliably over generic advice: the generic
daily rules for each selected domain already ship as `.agents/conventions/<domain>.md` (release:
`.agents/tools/release/README.md`), routed from the managed block. This table covers the
project facts those guides defer to.

| Coverage to establish | Useful project-specific content |
|---|---|
| Document entry and ownership | Where current development/design/operations material lives, what each location owns, and where a new document belongs. Preserve unique content and update actual readers/callers when material moves. |
| Specifications (`specs`) | Adopt semantic preservation, current/target status and observable acceptance using [specification conventions](specification-conventions.md). Do not invent product decisions. |
| Terminology (`terminology`) | Establish the actual glossary owner and project-wide incremental maintenance using [terminology](terminology.md), not a mandatory context-map template. |
| Git and releases (`git`, `release`) | Establish the selected project commit/delivery and release policy using [delivery conventions](delivery-conventions.md); retain real tools rather than replacing them with prose. |
| Status and evidence | How this project distinguishes drafts, current decisions, implemented behavior, and history. Approval and recent edits are not proof of implementation. Preserve established conventions; optional flat `status`/`updated` are hints, not a mandatory schema. Formats owning their frontmatter keep it. |
| Task commands | Real build/test/diagnostic/generation entries, cwd, necessary environment, and consequential effects. Keep internal helpers private and established CLI/installed/service-bound interfaces stable. |
| Test quality and policy | Adopt test locations, discovery/runner configuration, fixtures, coverage gates, and scoped test-first choices. Fill useful design/oracle, dependency and failure-evidence guidance using [testing conventions](testing-conventions.md), without imposing a framework or TDD. |
| Verification and delivery | Which checks cover the change, what is mock/offline versus real integration, unavailable environments, and the project's commit/PR/MR/release boundary. Link CI rather than duplicate its entire inventory. |
| Source and generated ownership | Important generator/source/output relations, vendor boundaries, attribution, and how to regenerate. Never patch a projection as a durable fix. |
| Environment and collaboration | Existing package manager/lockfile/setup, credential-free examples, shared-resource limits, exact checkout/review revision, and worktree lifecycle owner. No new lease/state controller. |
| Non-obvious external contracts | Relevant primary sources and applicable date/version next to the owning fact, when needed. Do not create a general research workflow or claim a fresh review from an editorial edit. |

For example, record that `make check` omits hardware tests, or that a dev command stops an
installed service, when supported by this project. Do not invent those effects or commands.
Do not settle unknown product architecture, test policy, or approval status while filling a
document. Report material unresolved choices and complete independent safe parts. Selected domains default to useful coverage, not forced frameworks or policies; an inapplicable domain can state its supported boundary briefly.

## Author within the granted scope

For a full authorized initialization, fill missing content and connect its readers after
asset installation. Discussion, preview, `plan`, `doctor`, and `verify` do not authorize writes.
An explicitly runtime-only update remains runtime-only. A layout migration, new toolchain,
changed permission model, or destructive cleanup is a separate scope decision, not an
implicit part of installation. Preserve unrelated dirty/staged work and local overrides.

Keep the managed AGENTS block unchanged by project customization; it already routes each
selected domain to its installed generic guide. Put high-frequency project entries and
non-obvious local limits in project-owned prose outside it; link deeper guidance from there. The
new Agent must not need this installed skill or the onboarding conversation to find project
instructions. Do not copy these principles or the installed guides into project docs; add only
the project-specific facts they defer to.

## Upgrade by current ownership and coverage

The installer refreshes managed assets and preserves the accepted domain list; the Agent maintains project-owned guidance with the
project's existing editing authority. Initial authorship does not grant permanent template
ownership. Do not add a mandatory layout registry, recurring approval gate, or side database.

On later runs, rediscover current authoritative entry points and inspect only relevant drift.
Use narrow Git history or current navigation when needed to distinguish missing information
from deliberate consolidation/removal. A missing old filename is not sufficient reason to
restore it. If intent cannot be established, preserve the ambiguous part and report it.

| Change since initialization | Correct maintenance |
|---|---|
| User renamed `docs/` to `doc/` or changed language/numbering | Adopt the new location/style and fix stale routes; do not restore the old layout. |
| An initial guide was merged into CONTRIBUTING or removed deliberately | Use its current successor; do not recreate the former template. |
| A project expresses an upstream recommendation differently | Preserve equivalent meaning instead of inserting another copy. |
| A new scaffold release adds a useful convention | Check applicability and existing coverage; fill only the gap in its current home. |
| Guidance contradicts active commands, source ownership, or safety boundaries | Correct confirmed drift within scope; do not merely preserve a broken instruction because the file exists. |
| Nothing relevant changed | No duplicate sections, timestamp-only updates, default-directory creation, or unrelated reformatting. |

## Completion evidence

Run installer `verify` for assets, then inspect the actual project reader routes and affected
commands. A new Agent should find valid current docs, command cwd/effects, source ownership,
test-quality guidance, verification coverage, and the delivery boundary using the resulting
entry points alone.
Do not treat a count of files, an inventory entry, or fixed English headings as acceptance.

Distinguish observed checks from inspected commands and from unknown external/host behavior.
A runtime `ok` means only its reported asset checks passed; it neither certifies semantic
coverage nor authenticates a live host. Preserve failed or unavailable evidence and report
what remains. Repetition should converge by meaning and ownership, not template equality.
