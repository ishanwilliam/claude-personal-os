---
description: Build your Personal OS skill from your Claude Code session history
argument-hint: "[--since YYYY-MM-DD]"
---

Build the user's Personal OS: a user-level skill that teaches Claude how this user works, extracted from their own Claude Code sessions.

The plugin root is `${CLAUDE_PLUGIN_ROOT}`. If that text appears unexpanded, find it with `find ~/.claude/plugins -path '*claude-personal-os/scripts/pos.py'`. Below, `POS` means `python3 "<plugin root>/scripts/pos.py"`.

Read `<plugin root>/templates/method.md` and `<plugin root>/templates/skill-structure.md` first and follow them exactly.

## 1. Check the starting point

Run `POS status` and `POS paths`.

- If `skill_installed` is true, a Personal OS already exists. Recommend `/claude-personal-os:update`, which keeps it and proposes changes. If the user still wants a build, it merges: rules in the existing skill are carried over unless new evidence contradicts them (step 4). Ask which they want before going further.
- Run `POS index --all` (or `--since <date>` if the user passed one) and report in two lines: sessions, prompts (and how many sessions came from prompt history), date range, top projects.
- Ask whether any of the listed projects should be left out (client or confidential work). Add the ones they name to `exclude_projects` in `<state dir>/state.json`, keeping its other keys, and rerun the index.
- If there are fewer than 20 sessions, say the result will be thin and mostly `[inferred]`, and ask whether to continue.
- If `cleanup_period_days` is below 90, say that Claude Code deletes transcripts after that many days and that expired sessions keep only the user's prompts, not Claude's replies. Offer to set `"cleanupPeriodDays": 180` in `~/.claude/settings.json`. Change it only if the user says yes, keeping every other setting.

## 2. Extract

Run `POS extract --all` (or with `--since`). Note `chunks`, `first`, `last`, `sessions` and `prompts` from its output.

## 3. Map

For every `chunk-NNN.md` in the work dir, launch one general-purpose subagent, in parallel batches of up to five. Give each one:

- the absolute path of its chunk and of `templates/method.md`
- the instruction to follow the map step and write observations to `<work dir>/obs-NNN.md`
- the instruction to return only a one-line count of observations written

## 4. Synthesize

Read every `obs-NNN.md` and `index.md`. Merge, count and tag them per the method. If a skill already exists, read it too: carry over every rule the new evidence does not contradict, marked `(carried over)`, and turn contradicted ones into tensions for step 5. Run the interpretation pass from the method and keep its candidates out of the draft until step 5. Then write the full skill to `<work dir>/draft/personal-os/` following `skill-structure.md`. Fill the provenance with the numbers from step 2.

## 5. Review with the user

Show a short summary: the five most important rules, the non-negotiables, and any tensions you found. Ask, in one batch, about tensions, the interpretation candidates (each with the observations it connects; confirm, edit or reject), how the skill should refer to them (name and pronouns, default they/them), and anything you were unsure of. Apply their answers to the draft.

## 6. Install

Only after the user approves:

1. If a skill already exists at `skill_dir`, copy it to `<history dir>/<UTC timestamp>-before-build/` first and say so.
2. Copy the draft to `skill_dir`.
3. Append any interpretation candidates the user rejected, with the date and one line each, to `<state dir>/rejected.md`.
4. Run `POS mark --kind build --through <last> --sessions <sessions> --prompts <prompts>`.
5. Tell the user the full path of the finished skill (`<skill_dir>/SKILL.md` is the file to open), that it loads in new sessions, and that a one-line reminder will appear at session start when an update is due.
