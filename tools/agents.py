#!/usr/bin/env python3
"""NeuralStrike README table tool.

    python3 tools/agents.py check            # validate the agent tables (CI runs this)
    python3 tools/agents.py fmt              # rewrite the tables with tidy, uniform cells
    python3 tools/agents.py csv              # write data/agents.csv (sortable, CI keeps it in sync)
    python3 tools/agents.py csv --stats      # write data/agents_stats.csv (+ stars, last push, archived)

--stats calls the GitHub API, so set GITHUB_TOKEN to avoid the 60-requests-per-hour
anonymous limit. It goes to a separate file because the numbers change daily.

Only the standard library is used, so it runs anywhere Python 3.9+ does.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
CSV_OUT = ROOT / "data" / "agents.csv"
STATS_OUT = ROOT / "data" / "agents_stats.csv"

# Sections whose tables use the 8-column agent layout.
AGENT_SECTIONS = ("## Open Source", "## Tencent Challenge")
HEADER = ["#", "Name", "URL", "Source", "Created / Published", "Notes",
          "CodeWiki (empty are pending)", "DeepWiki (empty are pending)"]
SOURCES = {"GitHub", "arXiv", "arXiv, GitHub"}
DATE_RE = re.compile(r"~?\d{4}-\d{2}(-\d{2})?")
GH_REPO_RE = re.compile(r"https://github\.com/([\w.-]+)/([\w.-]+)")


def read_lines() -> list[str]:
    # utf-8-sig drops a byte-order mark if an editor added one.
    return README.read_text(encoding="utf-8-sig").split("\n")


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_separator(line: str) -> bool:
    return line.startswith("|") and set(line.replace("|", "").strip()) <= set("-: ")


def agent_rows(lines: list[str]):
    """Yield (section, line_index, cells) for every data row of the agent tables."""
    section = ""
    for i, line in enumerate(lines):
        if line.startswith("## "):
            section = line.strip()
            continue
        if not section.startswith(AGENT_SECTIONS) or not line.startswith("|") or is_separator(line):
            continue
        cells = split_row(line)
        if cells and cells[0] == "#":
            continue
        yield section, i, cells


def check() -> int:
    lines = read_lines()
    errors: list[str] = []
    seen: dict[str, int] = {}
    numbers: dict[str, list[int]] = {}
    for section, i, cells in agent_rows(lines):
        where = f"README.md:{i + 1}"
        if len(cells) != len(HEADER):
            errors.append(f"{where}: expected {len(HEADER)} columns, found {len(cells)}")
            continue
        num, name, url, source, date, _notes, codewiki, deepwiki = cells
        numbers.setdefault(section, []).append(int(num) if num.isdigit() else -1)
        if not name:
            errors.append(f"{where}: empty name")
        if source and source not in SOURCES:
            errors.append(f"{where}: source {source!r} — use one of {sorted(SOURCES)}")
        if date and not DATE_RE.fullmatch(date):
            errors.append(f"{where}: date {date!r} — use YYYY-MM-DD or YYYY-MM")
        if codewiki and not codewiki.startswith("https://codewiki.google/"):
            errors.append(f"{where}: CodeWiki column holds {codewiki!r}")
        if deepwiki and not deepwiki.startswith("https://deepwiki.com/"):
            errors.append(f"{where}: DeepWiki column holds {deepwiki!r}")
        m = GH_REPO_RE.search(url)
        # A paper row may point at the same repo as its code row.
        if m and "arXiv" not in source:
            key = f"{m.group(1)}/{m.group(2)}".lower().rstrip(".")
            if key in seen:
                errors.append(f"{where}: {key} is already listed on line {seen[key]}")
            seen[key] = i + 1
    for section, nums in numbers.items():
        if nums != list(range(1, len(nums) + 1)):
            errors.append(f"{section}: rows are not numbered 1..{len(nums)} in order")
    for e in errors:
        print(e)
    total = sum(len(n) for n in numbers.values())
    print(f"{total} rows checked, {len(errors)} problem(s)")
    return 1 if errors else 0


def fmt() -> int:
    lines = read_lines()
    for _section, i, cells in agent_rows(lines):
        if len(cells) == len(HEADER):
            lines[i] = "| " + " | ".join(cells) + " |"
    # Normalise each agent table's header/separator too.
    section = ""
    for i, line in enumerate(lines):
        if line.startswith("## "):
            section = line.strip()
        elif section.startswith(AGENT_SECTIONS) and line.startswith("| #"):
            lines[i] = "| " + " | ".join(HEADER) + " |"
            if i + 1 < len(lines) and is_separator(lines[i + 1]):
                lines[i + 1] = "|" + "|".join(" --- " for _ in HEADER) + "|"
    README.write_text("\n".join(lines), encoding="utf-8")
    print("README.md tables formatted")
    return 0


def github_stats(owner: str, repo: str, token: str | None) -> dict[str, str]:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "neuralstrike-agents-csv",
                 **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
        return {"stars": str(d.get("stargazers_count", "")),
                "last_push": (d.get("pushed_at") or "")[:10],
                "archived": str(d.get("archived", "")).lower()}
    except urllib.error.HTTPError as e:
        return {"stars": "", "last_push": "", "archived": f"error {e.code}"}
    except (urllib.error.URLError, TimeoutError):
        return {"stars": "", "last_push": "", "archived": "error"}


def export_csv(with_stats: bool) -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if with_stats and not token:
        print("warning: GITHUB_TOKEN not set — the anonymous API limit is 60 requests/hour", file=sys.stderr)
    fields = ["section", "number", "name", "url", "source", "created", "notes", "codewiki", "deepwiki"]
    if with_stats:
        fields += ["stars", "last_push", "archived"]
    out = STATS_OUT if with_stats else CSV_OUT
    out.parent.mkdir(exist_ok=True)
    rows = 0
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for section, _i, cells in agent_rows(read_lines()):
            if len(cells) != len(HEADER):
                continue
            row = dict(zip(fields, [section.lstrip("# ").replace(" (WIP)", "")] + cells))
            if with_stats:
                m = GH_REPO_RE.search(cells[2])
                row.update(github_stats(m.group(1), m.group(2).rstrip("."), token) if m
                           else {"stars": "", "last_push": "", "archived": ""})
            w.writerow(row)
            rows += 1
    print(f"wrote {rows} rows to {out.relative_to(ROOT)}")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "check":
        return check()
    if cmd == "fmt":
        return fmt()
    if cmd == "csv":
        return export_csv("--stats" in argv)
    print(f"unknown command {cmd!r}\n{__doc__}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
