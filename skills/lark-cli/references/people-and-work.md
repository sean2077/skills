# People and work

Read this only when the request involves contacts/user resolution, ordinary tasks and lists,
approval definitions/instances/tasks, attendance records, OKR objectives/key results/alignment, or
assignments and stand-up work summaries.

## Resolve people and identity

Use `contact` to resolve names/emails to real open IDs or to inspect a known open ID. User and bot
identity expose different contact paths: user identity can search visible people/bots; bot identity
typically needs a known ID for profile lookup. Inspect current help, require a unique result, and
never guess a person from a duplicate display name.

Carry the resolved typed ID (`open_id`, department ID, chat ID, email, and so on) without changing
its type. Preview the resolved human-readable person before assigning work, adding members, or
performing an approval action.

## Keep approvals separate from tasks

- Approval forms, approval instances, approval to-dos/done items, approve/reject/transfer/return/
  withdraw/urge/add-approver/copy actions belong to `approval`.
- Ordinary to-do items, subtasks, lists, collaborators, attachments, task agents, and task records
  belong to `task`.
- The word “待办” alone is ambiguous; route by whether the underlying object is an approval document
  or a Task object. Never convert one into the other.

Approval is normally a human action, so use `--as user`. Before initiating an approval, inspect the
real definition/form/schema and show the material fields and process. Before approve/reject/
transfer/return or similar actions, show the instance, current node, action, comment, and target;
require direct authorization and verify the resulting status.

For Task, inspect `lark-cli task --help` and exact shortcut help before every unfamiliar operation;
do not invent `+<verb>` names. Resolve due dates/timezones, assignees, list membership, and parent
relationships before writing. Reconfirm deletes, bulk completion/reassignment, external assignees,
or agent registration changes.

## Attendance

Attendance queries are for the authorized user's visible records unless the installed API and
permissions explicitly support more. For the common “my punch records” path, follow the command
schema and auto-fill `employee_type` as `employee_no` and `user_ids` as an empty array rather than
asking the user for those fixed transport fields. Report the queried date range/timezone and do not
infer presence or misconduct from missing records alone.

## OKR

Use `okr` for cycles, objectives, key results, alignment, metrics, and progress records; do not route
OKR work to Tasks. Default to user identity for the current user's or visible hierarchy's OKRs.
Read the cycle/objective/KR structure first, preserve alignment IDs and metric units, preview edits,
and verify progress/relationship changes.

## Read-only work summary

A daily/weekly work summary may combine `calendar + task` and optionally approval/OKR data. Load
**Calendar and meetings** for agenda semantics. Collect first, preserve source IDs and time ranges,
then summarize; never mark tasks complete, answer approvals, or edit OKRs merely because the report
suggests an action.

**Official coverage:** `lark-approval`, `lark-attendance`, `lark-contact`, `lark-okr`, `lark-task`.
