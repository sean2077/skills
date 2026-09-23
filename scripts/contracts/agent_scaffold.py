"""Distribution checks for agent-scaffold; execution tests own its behavior."""
from __future__ import annotations

from pathlib import Path

from catalog_core import SKILLS_DIR, errors

SKILL = 'agent-scaffold'
REQUIRED_PATHS = ('SKILL.md', 'NOTICE.md', 'references/testing-conventions.md', 'references/specification-conventions.md', 'references/delivery-conventions.md', 'references/onboarding-selection.md', 'references/project-conventions.md', 'agent-scaffold.sh', 'scripts/harness-core.py', 'scripts/managed-assets.json', 'assets/scaffold/AGENTS.harness.md', 'assets/runtime/hooks/hook-paths.py')
# The adapted testing guidance carries upstream MIT attribution. Generic validation
# only routes a shipped NOTICE.md; hold its provenance and license text here, as the
# retired testing and terminology skills did for their original notices.
NOTICE_MARKERS = (
    "mattpocock/skills",
    "skills/engineering/tdd/",
    "skills/engineering/domain-modeling/",
    "MIT License",
    "Copyright (c) 2026 Matt Pocock",
    "The above copyright notice and this permission notice shall be included",
)


MIT_LICENSE_TEXT = 'Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.'

def validate_agent_scaffold_contract(skill_dir: Path | None = None) -> None:
    root = skill_dir or SKILLS_DIR / SKILL
    missing = [path for path in REQUIRED_PATHS if not (root / path).is_file()]
    if missing:
        errors.append(f"{SKILL}: missing required payload: {missing}")
        return
    notice = " ".join((root / "NOTICE.md").read_text(encoding="utf-8").split())
    missing_notice = [marker for marker in NOTICE_MARKERS if marker not in notice]
    if MIT_LICENSE_TEXT not in notice:
        missing_notice.append("the complete MIT license text")
    if missing_notice:
        errors.append(
            f"{SKILL}/NOTICE.md: upstream provenance and MIT notice missing: {missing_notice}"
        )


def validate(*, readme_text: str | None = None) -> None:
    validate_agent_scaffold_contract()
