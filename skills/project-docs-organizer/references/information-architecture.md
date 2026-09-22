# Documentation Information Architecture

## Structure from retrieval needs

Preserve the user's chosen location and a coherent existing documentation or site-generator structure. A focused README can serve a small project; add a dedicated tree when durable topics or reader journeys need it.

Identify the readers, recurring tasks, search terms, ownership, lifecycle, and generator constraints relevant to the change. Compare viable groupings using [classification methods](classification-methods.md) when the choice remains unresolved.

Prefer boundaries that make a document's home predictable, preserve cohesive ownership, survive ordinary project changes, and reduce duplication. Different subtrees may use different groupings. Provide secondary reader routes with links or generated navigation to the same canonical source.

## Test the proposed organization

Try representative affected documents and common reader tasks. Check whether readers can find the needed material, whether ownership is clear, and whether future changes would cause unrelated moves. Revise a grouping that creates ambiguity or excessive nesting.

For a material reorganization, weigh retrieval benefits against migration cost and preserve consequential rationale in the project's existing decision process. For a bounded move or merge, concentrate on the destination, useful content, and affected links.

## Entry points and ordering

A root README should explain the project and offer a useful start. A documentation landing page should expose the available routes and distinguish guidance from proposals, generated copies, and history. Link to authoritative setup, architecture, command, and operational pages.

Use [local numbering](numbering-patterns.md) where display order helps readers; preserve established ordering and generator-owned navigation unless changing them solves the actual problem. Complete moves through [migration and links](migration-and-links.md).

## Cold-reader example

After moving installation and authentication pages, ask a fresh reader: “Starting at README, how do I authenticate, and which page owns that requirement?” Give only the resulting documents and links. A correct answer should cite the owning page; guessing from common practice does not establish discoverability. Repair the route or missing explanation, preserving project-specific facts. This is an optional retrieval check, not a fixed reviewer count or new document lifecycle.
