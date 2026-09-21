# Tool Path Migrations

Find the consumers of an affected command: callers, agent instructions, skills, service units, build/install/package definitions, runbooks, and an adopted inventory. Reconcile them with the move, rename, or deletion. Recheck the command's own root and sibling-path resolution after relocation.

An installed or service-bound path is an external contract. Coordinate with its owner before changing it. When consumers cannot move together, choose an authorized transition that preserves required compatibility and makes the eventual cutover clear.

Identify external references, such as wikis or issue trackers, that still need coordination rather than claiming they changed with the repository.
