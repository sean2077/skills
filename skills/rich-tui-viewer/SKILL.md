---
name: rich-tui-viewer
description: Build interactive TUI data viewers with Rich + Textual. Use when the user asks to create a CLI tool for browsing data (logs, conversations, records, API responses) with a table overview and detail view, or asks for a "human-friendly" terminal interface.
allowed-tools: Read, Write, Bash, Glob, Grep
argument-hint: [description of what to browse]
---

# Rich + Textual TUI Data Viewer

Build an interactive terminal data viewer with two modes:
- **TUI mode** (default): Full-screen app with mouse-clickable table, detail screen, ESC to go back
- **CLI mode** (`-s` flag): Direct rich output for pipes, scripts, and SSH sessions

## Architecture

```
App (holds data)
├── DataTable (cursor_type="row")
│   └── on_data_table_row_selected → push_screen(DetailScreen)
└── Footer (shows key bindings)

DetailScreen (Screen)
├── VerticalScroll
│   └── Static(Group(...))   ← embed any Rich renderable
├── Binding("escape") → app.pop_screen()
└── Footer
```

## Implementation Rules

### 1. Dependencies

**Option A — PEP 723 inline metadata** (single-file scripts, no extra files):

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich>=13.0", "textual>=3.0"]
# ///
```

**Option B — pyproject.toml** (multi-file projects):

```toml
[project]
dependencies = ["rich>=13.0", "textual>=3.0"]
```

Both work with `uv run`.

### 2. Dual-Mode Entry Point

```python
def main():
    if args.select:
        cli_show(data)       # Rich Console output
    else:
        ViewerApp(data).run()  # Textual TUI
```

### 3. Screen Navigation (NOT widget toggling)

Use `push_screen()` / `pop_screen()` for list→detail navigation:
- Each Screen has independent Bindings and state
- Returning to the list preserves scroll position and selected row
- Code stays decoupled across classes

### 4. ESC Binding

**Wrong** — bare `pop_screen` is not a Screen-level action:
```python
BINDINGS = [Binding("escape", "pop_screen", "Back")]
```

**Correct** — use the namespaced `app.pop_screen` action:
```python
BINDINGS = [Binding("escape", "app.pop_screen", "Back")]
```

**Alternative** — custom action (when you need extra logic before popping):
```python
BINDINGS = [Binding("escape", "go_back", "Back", priority=True)]

def action_go_back(self) -> None:
    # ... cleanup, save state, etc.
    self.app.pop_screen()
```

Set `priority=True` if child widgets (e.g. `VerticalScroll`) consume the key before it reaches the Screen.

### 5. Embedding Rich Renderables in Textual

Use `Static(renderable)` to bridge Rich into Textual:

```python
from rich.console import Group
from rich.text import Text
from rich.panel import Panel

# Compose multi-line message as a single widget
parts = [header_text, *content_lines]
container.mount(Static(Group(*parts)))

# Or a panel
container.mount(Static(Panel(info, border_style="cyan")))
```

### 6. DataTable Setup

```python
table = DataTable(cursor_type="row")  # Row selection, not cell
table.add_columns("#", "Name", "Count", "Last Active")
table.add_row("1", "Channel A", "42", "03-15 08:00")
```

### 7. Lint Suppressions

Textual class attributes trigger RUF012 (mutable class defaults). Suppress with:
```python
BINDINGS = [...]  # noqa: RUF012
```

## Reference Example

A complete working example is in `example.py` alongside this SKILL.md. Read it for the full pattern including:
- Data model with `@dataclass`
- Overview table with icons and stats
- Detail screen with styled message rendering
- CLI fallback mode with `argparse`
