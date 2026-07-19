# Tooling Verification

Read this when choosing the minimal syntax, help, dry-run, inventory, and real-target checks.

## Verification — minimal set

```bash
bash -n <script.sh>                 # shell syntax
python -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_bytes(), sys.argv[1], "exec")' path/to/script.py  # python syntax, no bytecode file
<script> --help                     # exit 0 + usage
<script> --dry-run ...              # dangerous scripts: prove the no-op path
bash <skill-dir>/scripts/inventory-check.sh <inventory> # reconcile structural inventory vs disk
rg -n '<old-path>' <docs> <skills> <units>   # after a move: no stale active references
# plus any domain test the project already has
```

Scripts whose effect can't be fully verified on a dev host (anything that drives real hardware, a device GUI, or a flashing/loader path) still need a real-target smoke before they're trusted.
