#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich>=13.0", "textual>=3.0"]
# ///
"""Rich + Textual TUI data viewer pattern: minimal working example.

Two modes:
  - TUI (default): clickable table → detail screen → ESC to go back
  - CLI (-s flag): direct rich output for pipes and scripts

Usage:
  uv run example.py          # TUI interactive mode
  uv run example.py -s 1     # CLI output for item #1
  uv run example.py -s 1 -n 5  # Last 5 messages only
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

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
            Message("Alice", "API docs have been updated", "09:01"),
            Message("Bot", "Synced to wiki", "09:02"),
            Message("Bob", "Perf test results are in", "09:15"),
            Message("Bot", "P99 latency dropped from 120ms to 45ms — 62% improvement", "09:16"),
            Message("Alice", "Nice! Ready to ship", "09:30"),
            Message("Charlie", "Rollout plan decided?", "09:45"),
            Message("Alice", "10% canary for one day first", "09:46"),
            Message("Bot", "Canary deploy created, ETA 10:00", "09:50"),
        ]),
        Channel("Alerts", "🔔", [
            Message("Monitor", "CPU usage above 80%: node-03", "08:30"),
            Message("Bot", "Auto-scaled 2 nodes", "08:31"),
            Message("Monitor", "node-03 CPU back to normal (45%)", "08:45"),
            Message("Monitor", "Disk usage alert: db-primary (92%)", "14:00"),
            Message("Bot", "Triggered log cleanup job", "14:01"),
        ]),
        Channel("DM · Dave", "👤", [
            Message("Dave", "Did you fix that bug?", "10:00"),
            Message("Bot", "PR #142 submitted, awaiting review", "10:01"),
            Message("Dave", "Let me check", "10:05"),
            Message("Dave", "LGTM, merged", "10:20"),
        ]),
        Channel("Weekly Reports", "📊", [
            Message("Bot", "This week: 5 features, 3 bugfixes", "17:00"),
            Message("Bot", "Pending: 2 P1 issues", "17:00"),
            Message("Eve", "What's the focus next week?", "17:15"),
            Message("Bot", "1. Data migration  2. Perf optimization launch  3. Docs", "17:16"),
        ]),
    ]


# -- CLI output mode -----------------------------------------------------------


def cli_show(channel: Channel, n: int | None = None) -> None:
    """Direct rich output to terminal (pipe/script friendly)."""
    console = Console()
    msgs = channel.messages[-n:] if n else channel.messages

    info = Text()
    info.append(f"  {channel.icon} {channel.name}", style="bold")
    info.append(f"   {channel.msg_count} messages", style="cyan")
    console.print()
    console.print(Panel(info, box=box.ROUNDED, border_style="cyan", padding=(0, 1)))
    console.print()

    for msg in msgs:
        header = Text()
        header.append(f" {msg.time} ", style="dim")
        if msg.sender == "Bot":
            header.append(" Bot ", style="bold white on dark_green")
            console.print(header)
            for line in msg.text.split("\n"):
                console.print(Text(f"   {line}", style="green"))
        else:
            header.append(f" {msg.sender} ", style="bold white on blue")
            console.print(header)
            for line in msg.text.split("\n"):
                console.print(Text(f"   {line}"))
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

        info = Text()
        info.append(f"  {ch.icon} {ch.name}", style="bold")
        info.append(f"   {ch.msg_count} messages", style="cyan")
        container.mount(Static(Panel(info, border_style="cyan", padding=(0, 1))))
        container.mount(Static(Rule(style="bright_black")))

        for msg in ch.messages:
            parts: list[Text] = []
            header = Text()
            header.append(f" {msg.time} ", style="dim")

            if msg.sender == "Bot":
                header.append(" Bot ", style="bold white on dark_green")
                parts.append(header)
                for line in msg.text.split("\n"):
                    parts.append(Text(f"   {line}", style="green"))
            else:
                header.append(f" {msg.sender} ", style="bold white on blue")
                parts.append(header)
                for line in msg.text.split("\n"):
                    parts.append(Text(f"   {line}"))

            container.mount(Static(Group(*parts)))


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Channel viewer (Rich + Textual example)")
    parser.add_argument("-s", "--select", help="View a specific channel (number or name keyword)")
    parser.add_argument("-n", "--lines", type=int, help="Show only the last N messages")
    args = parser.parse_args()

    channels = load_sample_data()

    if args.select:
        target = None
        try:
            idx = int(args.select) - 1
            if 0 <= idx < len(channels):
                target = channels[idx]
        except ValueError:
            for ch in channels:
                if args.select.lower() in ch.name.lower():
                    target = ch
                    break
        if target is None:
            Console().print(f"[red]Not found: {args.select}[/red]")
            sys.exit(1)
        cli_show(target, n=args.lines)
    else:
        ViewerApp(channels).run()


if __name__ == "__main__":
    main()
