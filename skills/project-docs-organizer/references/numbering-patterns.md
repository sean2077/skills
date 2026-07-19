# Local Documentation Numbering

Read this after semantic boundaries are stable and the project needs a decision about numeric
ordering. Numbers are presentation, never a classification method.

## Decide whether numbering applies

Keep numbering disabled by default. Enable it only when the IA decision record identifies a
stable sibling display or reading order that materially improves an observed reader route and
the navigation benefit exceeds path/link churn. The absence of a coherent established convention
is permission to choose, not evidence for numbering. Keep numbering disabled when:

- the user explicitly declines it;
- a coherent established convention already routes readers effectively;
- a documentation generator owns ordering or navigation; or
- no observed reader route requires stable sibling ordering; or
- renaming stable public paths would cost more than the evidenced ordering problem.

README-only projects have no directory layer to number. If an established convention is itself
the retrieval failure, present the migration cost and let the maintainer reconsider it.

## Use sibling-local ordering tokens

- Name semantic groups first, then prefix only the siblings whose display order should remain
  predictable.
- Use two-digit tokens with insertion gaps by default: `10-`, `20-`, `30-`, and so on.
- Use `00-` only for real first-stop content. Do not create an entry page or directory merely
  to consume the token.
- Treat each number as sibling-local position, not category meaning. Numeric ranges carry no
  cross-project or cross-subtree semantics.
- Add prefixes inside a group only when readers must follow a genuine reading or execution order.
- Renumber existing paths only when the navigation benefit justifies link churn and the
  migration contract covers every active route.

The result may use numbered directories, numbered files, both, or neither. The decision follows
reader navigation and project convention; it never follows project size alone.
