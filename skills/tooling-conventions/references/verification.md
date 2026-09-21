# Tooling Verification

Select checks supported by the affected command and its consumers:

```bash
bash -n <script.sh>
python -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_bytes(), sys.argv[1], "exec")' path/to/script.py
bash <skill-dir>/scripts/inventory-check.sh <inventory>
rg -n -F '<old-path>' <docs> <skills> <units>
```

Use the project's Python 3.8+ launcher. The compile check does not execute the script or create bytecode. The inventory command applies to an adopted structural inventory, and the path search helps reconcile migrations.

Exercise help, preview, and other CLI interfaces that the command actually provides. Verify that a claimed dry run suppresses the relevant effects. Use focused behavior checks and required project gates alongside syntax validation.

Hardware, device GUI, flashing, and loader behavior needs appropriate target evidence. Report host-only checks separately from real-target validation and identify unavailable checks.
