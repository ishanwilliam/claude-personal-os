---
description: Mine new sessions and propose evidence-backed changes to your Personal OS
argument-hint: "[--since YYYY-MM-DD]"
---

Update the user's Personal OS from sessions since the last applied update. Nothing changes until the user approves it.

The plugin root is `${CLAUDE_PLUGIN_ROOT}`. If that text appears unexpanded, find it with `find ~/.claude/plugins -path '*claude-personal-os/scripts/pos.py'`. Below, `POS` means `python3 "<plugin root>/scripts/pos.py"`.

Read `<plugin root>/templates/method.md` and `<plugin root>/templates/skill-structure.md` first.

## 1. Find the starting point

Run `POS status` and `POS paths`.

- If `skill_installed` is false, tell the user to run `/claude-personal-os:build` instead, and stop.
- If `last_extracted_through` is empty (the skill was made by hand or before this plugin), read the provenance in `SKILL.md`, propose the last date it covers as `--since`, and ask the user to confirm it.
- If the user passed `--since`, use it.

## 2. Extract the new sessions

Run `POS extract` (with `--since <date>` when step 1 set one). If `prompts` is 0, say there is nothing new and stop.

## 3. Map

Same as the build: one general-purpose subagent per chunk, in parallel batches of up to five, each writing `<work dir>/obs-NNN.md` per the map step in `method.md`.

## 4. Compare against the current skill

Read the current `SKILL.md`, every file in `references/`, `<work dir>/index.md`, and `<state dir>/rejected.md` if it exists. Turn the new observations into proposed changes. Each change is one of:

- **Add:** a new rule or pattern, with its tag.
- **Strengthen / weaken:** change a tag because new evidence supports or contradicts it.
- **Stale:** the user's behavior changed, so the text no longer describes them.
- **Conflict:** new evidence contradicts an existing rule; the user arbitrates.
- **Remove:** the user said to drop it, or new evidence clearly contradicts it.

Rules:

- Silence is not evidence. A rule Claude now follows stops showing up in corrections, so never weaken or remove a rule only because the new sessions do not mention it.
- Never propose removing a non-negotiable unless the user's own words reverse it.
- Never re-propose anything in `rejected.md` unless there is clearly new evidence, and say so if you do.
- Run the interpretation pass from the method. Propose at most two candidates per update, as Adds tagged `[inferred]`, each listing the observations it connects.
- Before proposing an Add, check it does not contradict an existing rule; if it does, propose it as a Conflict instead.
- A one-off moment is not a change. Most updates should be a handful of changes, not dozens.

## 5. Review with the user

List the changes with letters (A, B, C, ...), most important first. Each gets: type, the before and after text (one or two lines each), its tag, and one evidence quote with date. Keep the whole list short enough to read in a minute. Ask the user which to apply; they may answer like "apply A-D, skip E".

## 6. Apply

Only for the approved changes:

1. Copy the current skill to `<history dir>/<UTC timestamp>-before-update/`.
2. Edit `SKILL.md` and `references/` in place. Keep numbering continuous and rules in their groups.
3. Append the update sentence to the provenance (format in `skill-structure.md`).
4. Append the rejected changes, with the date and one line each, to `<state dir>/rejected.md`.
5. Run `POS mark --kind update --through <last> --sessions <sessions> --prompts <prompts> --changes <number applied>`.
6. Report in two lines: what was applied, where the backup is, and the full path of the updated skill (`<skill_dir>/SKILL.md`), which new sessions load.
