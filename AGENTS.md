# Rules for AI coding tools

These rules apply to every AI tool used in this repository (Claude Code, Codex, and others). `CLAUDE.md` points here.

## H3 files: do not read

Team decision 2026-11-20 (`reviews/change_requests.md`). The H3 question set and answer key must stay unseen by the agent code and by the tools that write it.

- Do not open, print, search, or summarise these files, in any branch or commit:
  - `tests/h3_questions.csv`, `tests/h3_answer_key*.csv`
  - `results/h3_*` (grading results and router runs)
  - the H3 folder outside the repository (the default folder of `scripts/grade_h3.py`)
- Do not run `git show`, `git log -p`, or `git grep` on those paths.
- `reviews/h3_questions_sha256.txt` holds only hashes. Reading it is allowed.
- `tests/sample_questions.csv` and `tests/sample_answer_key.csv` are samples. Reading them is allowed.
- If a task needs the content of an H3 file, stop and ask a question author (data or evaluation member).

## Results

- Do not edit files in `results/` by hand. Build them with `python -m src.run_all` on the reference machine.
- Change a result file only in the same commit as the code that builds it.

## Frozen plan

- `plan/plan_v0.6.md` §1 (H1, H2, H3 criteria) is frozen at tag `plan-v0.6`. Do not change it.
- H3 is graded with the agent at tag `agent-v1`. Do not move that tag.
