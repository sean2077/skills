#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich>=13.0", "textual>=3.0", "typer>=0.15"]
# ///
"""Rich + Textual TUI data viewer pattern: minimal working example.

Two modes:
  - TUI (default): clickable table → detail screen → ESC to go back
  - CLI (-s flag): direct rich output for pipes and scripts

Usage:
  uv run example.py              # TUI interactive mode
  uv run example.py -s 1         # CLI output for item #1
  uv run example.py -s 1 -n 5    # Last 5 messages only
  uv run example.py --help        # Show help
"""

from dataclasses import dataclass
from typing import Annotated

import typer

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static


# -- Data layer (replace with your actual data source) -------------------------


@dataclass
class Message:
    sender: str
    text: str
    time: str


@dataclass
class Channel:
    name: str
    icon: str
    messages: list[Message]

    @property
    def msg_count(self) -> int:
        return len(self.messages)

    @property
    def last_time(self) -> str:
        return self.messages[-1].time if self.messages else "—"


def load_sample_data() -> list[Channel]:
    """Generate sample data. Replace with real data loading logic."""
    return [
        Channel("Tech Discussion", "👥", [
            Message("Alice", "API docs updated", "09:01"),
            Message("Bot", "P99 latency 120ms → 45ms (–62%)", "09:16"),
            Message("Alice", "Nice! Ship it", "09:30"),
        ]),
        Channel("Alerts", "🔔", [
            Message("Monitor", "CPU above 80%: node-03", "08:30"),
            Message("Bot", "Auto-scaled 2 nodes", "08:31"),
            Message("Monitor", "node-03 back to normal (45%)", "08:45"),
        ]),
        Channel("DM · Dave", "👤", [
            Message("Dave", "Did you fix that bug?", "10:00"),
            Message("Bot", "PR #142 submitted", "10:01"),
            Message("Dave", "LGTM, merged", "10:20"),
        ]),
    ]


def resolve_channel(channels: list[Channel], query: str) -> Channel:
    """Find a channel by 1-based index or name substring. Raises typer.BadParameter on miss."""
    try:
        idx = int(query) - 1
    except ValueError:
        pass  # not a number — fall through to name search
    else:
        if 0 <= idx < len(channels):
            return channels[idx]
        raise typer.BadParameter(f"Index {query} out of range (1–{len(channels)})")
    for ch in channels:
        if query.lower() in ch.name.lower():
            return ch
    raise typer.BadParameter(f"No channel matching '{query}'")


# -- Rendering helpers ---------------------------------------------------------


def render_channel_header(channel: Channel) -> Panel:
    """Rich panel with channel name, icon, and message count."""
    info = Text()
    info.append(f"  {channel.icon} {channel.name}", style="bold")
    info.append(f"   {channel.msg_count} messages", style="cyan")
    return Panel(info, box=box.ROUNDED, border_style="cyan", padding=(0, 1))


def render_message(msg: Message) -> list[Text]:
    """Render a single message as a list of Rich Text lines."""
    is_bot = msg.sender == "Bot"
    header = Text()
    header.append(f" {msg.time} ", style="dim")
    header.append(f" {msg.sender} ", style="bold white on dark_green" if is_bot else "bold white on blue")
    body_style = "green" if is_bot else "default"
    return [header, *(Text(f"   {line}", style=body_style) for line in msg.text.split("\n"))]


# -- CLI output mode -----------------------------------------------------------


def cli_show(channel: Channel, n: int | None = None) -> None:
    """Direct rich output to terminal (pipe/script friendly)."""
    console = Console()
    msgs = channel.messages[-n:] if n else channel.messages

    console.print()
    console.print(render_channel_header(channel))
    console.print()

    for msg in msgs:
        for line in render_message(msg):
            console.print(line)
        console.print()


# -- TUI interactive mode ------------------------------------------------------


class DetailScreen(Screen):
    """Detail view: scrollable message list, ESC to go back."""

    BINDINGS = [  # noqa: RUF012
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, channel: Channel) -> None:
        super().__init__()
        self._channel = channel

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="scroll")
        yield Footer()

    def on_mount(self) -> None:
        container = self.query_one("#scroll", VerticalScroll)
        ch = self._channel

        container.mount(Static(render_channel_header(ch)))
        container.mount(Static(Rule(style="bright_black")))

        for msg in ch.messages:
            container.mount(Static(Group(*render_message(msg))))


class ViewerApp(App):
    """Data viewer: table overview → click to enter detail."""

    TITLE = "Channel Viewer"

    CSS = """
    DataTable { height: 1fr; }
    DataTable > .datatable--cursor {
        background: $accent;
        color: $text;
    }
    #scroll { height: 1fr; }
    """

    BINDINGS = [  # noqa: RUF012
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, channels: list[Channel]) -> None:
        super().__init__()
        self._channels = channels

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield DataTable(id="overview", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("  #", "  Type", "  Channel", "  Messages", "  Last Active")
        for i, ch in enumerate(self._channels, 1):
            table.add_row(
                f"  {i}",
                f"  {ch.icon}",
                f"  {ch.name}",
                f"  {ch.msg_count}",
                f"  {ch.last_time}",
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        idx = event.cursor_row
        if 0 <= idx < len(self._channels):
            self.push_screen(DetailScreen(self._channels[idx]))


# -- Entry point ---------------------------------------------------------------


cli = typer.Typer(rich_markup_mode="rich")


@cli.command()
def main(
    select: Annotated[str | None, typer.Option("-s", "--select", help="View a specific channel (number or name keyword)")] = None,
    lines: Annotated[int | None, typer.Option("-n", "--lines", help="Show only the last N messages")] = None,
) -> None:
    """Interactive channel viewer with TUI and CLI modes."""
    channels = load_sample_data()

    if select:
        target = resolve_channel(channels, select)
        cli_show(target, n=lines)
    else:
        ViewerApp(channels).run()


if __name__ == "__main__":
    cli()
