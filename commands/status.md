---
description: Show whether your Personal OS exists and whether an update is due
---

The plugin root is `${CLAUDE_PLUGIN_ROOT}`. If that text appears unexpanded, find it with `find ~/.claude/plugins -path '*claude-personal-os/scripts/pos.py'`.

Run `python3 "<plugin root>/scripts/pos.py" status` and answer in at most three lines: whether the skill is installed, what it covers up to, how many new sessions and prompts there are since, and whether an update is due (and which command to run).
