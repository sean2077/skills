# People and work

Read this only when the request involves contacts/user resolution, ordinary tasks and lists,
approval definitions/instances/tasks, attendance records, OKR objectives/key results/alignment, or
assignments and stand-up summaries.

## Fast-path contract and call budget

Do not preflight `contact`, `task`, `approval`, `attendance`, or `okr` service help for the documented
paths below.

- Known `ou_`/bot ID: use it directly; zero resolver calls.
- Person name/email: one `contact +search-user`; bot name: one `contact +search-bot`.
- List pending tasks assigned to the current user: one `task +get-my-tasks --complete=false`.
- Known task GUID/AppLink: one task action command.
- Task title then action: one task list/search call plus one action; no help calls.
- Simple task create with explicit fields/IDs: one `task +create`.
- Approval/attendance/OKR paths not documented here use exact shortcut/resource discovery only,
  never broad help first.

Require a unique, verified recipient/person result. Carry the typed ID unchanged and show the
resolved human-readable identity before assigning work, adding members, or taking an approval action.

## Contact fast paths

```bash
# Search people by name, email, or other visible keyword
lark-cli contact +search-user --query '<name-or-email>' --as user

# Search applications/bots by name
lark-cli contact +search-bot --query '<bot-name>' --as user

# Current logged-in user's profile/open_id when the task truly needs “me” as an explicit assignee
lark-cli contact +get-user --as user
```

Do not call contact merely to validate a supplied `ou_` ID. User identity can search visible people
and bots; bot identity often needs a known ID. Duplicate display names require disambiguation rather
than guessing.

## Keep approvals separate from tasks

- Approval forms, instances, approval to-dos/done items, approve/reject/transfer/return/withdraw/
  urge/add-approver/copy actions belong to `approval`.
- Ordinary to-do items, subtasks, lists, collaborators, attachments, task agents, and task records
  belong to `task`.
- “待办” alone is ambiguous; route by the underlying object. A Minutes/妙记 todo remains in
  `minutes`, not Task.

## Task read fast paths

```bash
# Pending tasks assigned to the current user; best for stand-up/daily summaries
lark-cli task +get-my-tasks --complete=false --as user

# Match a task title among the current user's tasks
lark-cli task +get-my-tasks --query '<task-title>' --as user

# General keyword/filter search
lark-cli task +search --query '<keyword>' --completed=false --as user

# Search incomplete tasks assigned to known people
lark-cli task +search --assignee 'ou_aaa,ou_bbb' --completed=false --as user

# Due-date window
lark-cli task +search --query '<keyword>' --due '-1d,+7d' --as user
```

Do not pass `--complete` when the user asked for all tasks. For pending/stand-up scenarios, always
pass `--complete=false`; otherwise completed tasks are mixed into the result. Do not add `--page-all`
unless the requested scope requires more than the shortcut's normal bounded pagination.

## Task create and complete fast paths

```bash
# Simple task
lark-cli task +create --summary '<title>' --as user

# Detailed task; IDs are already known
lark-cli task +create \
  --summary '<title>' \
  --description '<description>' \
  --assignee 'ou_xxx' \
  --due '2026-08-20' \
  --tasklist-id '<tasklist-guid-or-applink>' \
  --idempotency-key '<stable-key-for-this-logical-create>' \
  --as user

# Complete by real GUID or AppLink
lark-cli task +complete --task-id '<task-guid-or-applink>' --as user
```

A display ID such as `t104121` is not the task GUID. If only a title is supplied, first run
`+get-my-tasks --query` (or `+search` when broader filtering is requested), require a unique match,
then run the action. Do not inspect help between those calls.

For “create a task for me,” resolve the logged-in user's `open_id` once with `contact +get-user`, then
pass it as `--assignee`; do not run both `auth status` and contact lookup. Use `--data` only for a
requested field lacking a documented named flag; in that case inspect `lark-cli schema task.tasks.create`
once for the exact body field and cache it. Do not run schema for the common flags above.

The create response's `data.guid`/URL is sufficient. The complete response's `status`,
`completed_at`, and `already_completed` are sufficient; do not routinely call task get afterward.
Reconfirm deletion, bulk completion/reassignment, external assignees, or agent registration changes.

## Approval workflow

Approval is normally a human action, so use `--as user`. Reads may execute directly when the exact
shortcut/registered command and identifiers are already known. Before creating an approval, inspect
the real definition/form once because form field shape is workflow-specific. Before approve, reject,
transfer, return, withdraw, or add-approver actions, present the instance, current node, action,
comment, and target and require direct authorization.

Do not repeatedly reload the same definition or instance between dependent steps. Cache it for the
current task. Use the action response as the result when it reports the new status; only issue one
focused status read when the response is ambiguous or the user asks for verification.

## Attendance

Attendance queries cover records visible to the authorized user. For the common “my punch records”
path, follow the exact installed command but auto-fill fixed transport fields `employee_type` as
`employee_no` and `user_ids` as an empty array instead of asking the user for them. Supply the
requested date range/timezone once. Missing records are not proof of absence or misconduct.

Because attendance command surfaces are lower-frequency and may vary, inspect only the exact
shortcut/resource needed if it is not already cached; do not begin with `attendance --help`.

## OKR

Use `okr` for cycles, objectives, key results, alignment, metrics, and progress; do not route OKR work
to Tasks. A known objective/KR ID should go directly to its read/update operation. When IDs are not
known, perform one bounded cycle/objective lookup, then act on the selected object. Preserve alignment
IDs and metric units; preview edits and verify progress/relationship changes only when the write
response does not establish the result.

## Read-only work summary

A daily/weekly work summary typically costs one `calendar +agenda` plus one
`task +get-my-tasks --complete=false`, optionally one approval/OKR read when explicitly requested.
Use **Calendar and meetings** for agenda semantics, reusing it when its relevant rules are already in
active context. Collect first and summarize with source IDs and time ranges; never complete tasks,
answer approvals, or edit OKRs because the report suggests an action.

## Drift fallback

For a documented task/contact shortcut, exact help is allowed only after an unknown option/command.
For approval/attendance/OKR operations absent from this reference, discover the narrowest exact
shortcut or registered resource, cache the result, then execute. Never invent a `+<verb>` or repeat
identical help/schema calls.

**Official coverage:** `lark-approval`, `lark-attendance`, `lark-contact`, `lark-okr`, `lark-task`.
