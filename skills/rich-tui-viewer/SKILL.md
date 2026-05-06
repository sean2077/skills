---
name: rich-tui-viewer
description: Build interactive TUI data viewers with Rich + Textual + Typer. Use when the user asks to create a CLI tool for browsing data (logs, conversations, records, API responses) with a table overview and detail view, or asks for a "human-friendly" terminal interface.
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Rich + Textual TUI Data Viewer

Build an interactive terminal data viewer with two modes:
- **TUI mode** (default): Full-screen app with mouse-clickable table, detail screen, ESC to go back
- **CLI mode** (`-s` flag): Direct rich output for pipes, scripts, and SSH sessions

## Architecture

```
cli (typer.Typer)
├── --select → cli_show()       ← Rich Console output (pipes, scripts)
└── (default) → ViewerApp.run() ← Textual TUI below

ViewerApp (App)
├── DataTable (cursor_type="row")
│   └── on_data_table_row_selected → push_screen(DetailScreen)
└── Footer

DetailScreen (Screen)
├── VerticalScroll
│   └── Static(Group(...))   ← embed any Rich renderable
├── Binding("escape") → app.pop_screen()
└── Footer

Shared: render_*() helpers return Rich objects → used by both cli_show() and DetailScreen
```

## Implementation Rules

### 1. Dependencies

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich>=13.0", "textual>=3.0", "typer>=0.15"]
# ///
```

For multi-file projects, put the same deps in `pyproject.toml`. Both work with `uv run`.

### 2. Dual-Mode Entry Point (Typer)

Use `Annotated` + `str | None` syntax (Python 3.11+), `rich_markup_mode="rich"` for styled `--help`, and name the Typer instance `cli` (not `app`) to avoid confusion with Textual's `App`:

```python
from typing import Annotated
import typer

cli = typer.Typer(rich_markup_mode="rich")

@cli.command()
def main(
    select: Annotated[str | None, typer.Option("-s", "--select", help="View a specific item")] = None,
    lines: Annotated[int | None, typer.Option("-n", "--lines", help="Show only last N entries")] = None,
) -> None:
    data = load_data()
    if select:
        item = find_item(data, select)  # raise typer.BadParameter(...) on miss
        cli_show(item, n=lines)         # Rich Console output
    else:
        ViewerApp(data).run()           # Textual TUI

if __name__ == "__main__":
    cli()
```

**Typer gotchas:**
- **Do NOT use `from __future__ import annotations`** — typer inspects types at runtime; PEP 563 deferred annotations break this and produce cryptic errors
- Use `typer.BadParameter("msg")` for validation errors (auto-formats with usage hint)
- Use `typer.Exit(code)` instead of `sys.exit()` (testable, no traceback)
- `rich_markup_mode="rich"` enables `[bold]`, `[green]` etc. in help strings

### 3. Screen Navigation & ESC Binding

Use `push_screen()` / `pop_screen()` for list→detail navigation (NOT widget toggling):
- Each Screen has independent Bindings and state
- Returning to the list preserves scroll position and selected row

**ESC must use the namespaced action** — bare `pop_screen` silently fails:
```python
# Wrong:  Binding("escape", "pop_screen", "Back")
# Correct:
BINDINGS = [Binding("escape", "app.pop_screen", "Back")]
```

Set `priority=True` if child widgets (e.g. `VerticalScroll`) consume ESC before it reaches the Screen.

### 4. Embedding Rich Renderables in Textual

Use `Static(renderable)` to bridge Rich into Textual. Extract render functions that return Rich objects — reuse them in both CLI (`console.print`) and TUI (`Static(...)`) modes:

```python
from rich.console import Group
from rich.text import Text
from rich.panel import Panel

def render_item(item: Item) -> list[Text]:
    """Shared renderer — returns Rich objects usable in both modes."""
    return [header_text, *(Text(line) for line in item.lines)]

# TUI: wrap in Static + Group
container.mount(Static(Group(*render_item(item))))

# CLI: iterate and print
for part in render_item(item):
    console.print(part)
```

### 5. DataTable Setup

```python
table = DataTable(cursor_type="row")  # Row selection, not cell
table.add_columns("#", "Name", "Count", "Last Active")
table.add_row("1", "Channel A", "42", "03-15 08:00")
```

### 6. Lint Suppressions

Textual class attributes trigger RUF012 (mutable class defaults). Suppress with:
```python
BINDINGS = [...]  # noqa: RUF012
```

## Reference Example

A complete working example is in `example.py` alongside this SKILL.md. Read it for the full pattern including:
- Data model with `@dataclass`
- Overview table with icons and stats
- Shared rendering helpers (DRY across CLI/TUI)
- Detail screen with styled message rendering
- Typer CLI with `Annotated` options, `BadParameter`, and `rich_markup_mode`
