# Contributing to NeuralStrike

Thanks for helping keep this list current! There are two ways to contribute.

## 1. Open an issue (easiest)

Use **New issue → Add an AI hacking agent** and fill in the form (name, link, date,
short note). Use **Fix or update an entry** for broken links, archived repos, wrong
dates or new benchmark scores.

## 2. Open a pull request

1. Add a row to the right table in `README.md`:
   - **Open Source** — public repos, sorted by creation / publication date
   - **Tencent Challenge**, **DARPA AIxCC**, **Enterprise/Closed Source**, **Papers**
2. Agent table rows have 8 columns:

   ```
   | # | Name | URL | Source | Created / Published | Notes | CodeWiki | DeepWiki |
   ```

   - `#` — renumber so rows stay `1..N` in order
   - `Source` — `GitHub`, `arXiv` or `arXiv, GitHub`
   - `Created / Published` — `YYYY-MM-DD` (or `YYYY-MM` if the day is unknown)
   - `CodeWiki` — `https://codewiki.google/github.com/<owner>/<repo>` (lower-case), or empty if pending
   - `DeepWiki` — `https://deepwiki.com/<owner>/<repo>`, or empty if pending
3. Check and regenerate the CSV:

   ```bash
   python3 tools/agents.py check   # validates columns, dates, links, duplicates, numbering
   python3 tools/agents.py fmt     # optional: tidy table spacing
   python3 tools/agents.py csv     # updates data/agents.csv
   ```

CI runs the same check on every pull request, plus a link checker.

## Scope

Only tools for **authorised** security testing, research, CTFs and education. Entries
that are clearly malware, or that are built to attack systems without permission,
will not be added.
