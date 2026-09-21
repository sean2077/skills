# People and work

## Select and resolve the work item

Use known typed IDs directly. Resolve people through `contact +search-user` and bots through `contact +search-bot`. Require a unique, verified person and show the resolved identity before assigning work, adding members, or taking approval actions.

Use `task +get-my-tasks --complete=false` for pending tasks. A known task GUID/AppLink can be used in its action command; a title needs list/search resolution first. Discover unfamiliar approval, attendance, and OKR operations through the installed help/schema.

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
then run the action using the resolved GUID.

For “create a task for me,” resolve the logged-in user's `open_id` once with `contact +get-user`, then
pass it as `--assignee`; do not run both `auth status` and contact lookup. Use `--data` only for a
requested field lacking a documented named flag; in that case inspect `lark-cli schema task.tasks.create`
for the missing body field and retain the applicable result.

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

Consult the installed attendance help/schema to resolve unfamiliar commands or uncertain parameters.

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

## Command discovery

Use installed help/schema for an unfamiliar option or changed command. For identity, permissions, confirmation, and uncertain outcomes, follow [setup and safety](setup-auth-and-safety.md).

**Official coverage:** `lark-approval`, `lark-attendance`, `lark-contact`, `lark-okr`, `lark-task`.
