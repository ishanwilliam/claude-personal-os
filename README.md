# claude-personal-os

A Claude Code plugin that builds a **Personal OS**: a skill that teaches Claude how *you* work, extracted from your own Claude Code sessions rather than from what you say about yourself. It then keeps that skill current with small, evidence-backed updates that you approve.

Every new session starts with Claude already knowing how you like questions asked, what you never want to see, how you approve work, which decisions are settled, and where you tend to lose time.

## What you get

A user-level skill at `~/.claude/skills/personal-os/`:

| File | Holds |
|---|---|
| `SKILL.md` | Who you are, numbered collaboration rules for Claude, your non-negotiables, and project-agnostic principles |
| `references/01` to `09` | Executive summary, core principles, decision framework, engineering and product philosophy, learning model, communication, blind spots, growth opportunities |

Every rule carries a confidence tag and is backed by quotes from your sessions:

- `[strong]`: seen in three or more sessions, stated by you as an absolute, or corrected in two or more sessions
- `[moderate]`: seen in two sessions, or stated once
- `[inferred]`: seen once as behavior and never stated, or read from indirect evidence

## Install

In Claude Code:

```
/plugin marketplace add ishanwilliam/claude-personal-os
/plugin install claude-personal-os@claude-personal-os
```

Requires `python3` (standard library only).

## Use

| Command | Does |
|---|---|
| `/claude-personal-os:build` | Reads all your sessions and writes the Personal OS. Shows you a summary and asks before installing. |
| `/claude-personal-os:update` | Reads only sessions since the last update and proposes lettered changes (add, strengthen, weaken, stale, conflict, remove), each with evidence. You pick which to apply. |
| `/claude-personal-os:status` | Says what the skill covers and whether an update is due. |

Your Personal OS is saved to `~/.claude/skills/personal-os/SKILL.md`, and each command tells you this path when it finishes.

Already have a Personal OS you wrote by hand? Run `update`, not `build`. It reads the date your skill covers up to and proposes changes on top of it. If you run `build` anyway, it merges: your existing rules are kept unless new evidence contradicts them.

**Cost.** `build` and `update` launch one subagent per chunk of about 60,000 characters of your prompts. A build over a few hundred sessions is typically four or five chunks and a few minutes; an update after 15 sessions is usually one chunk. This uses tokens from your plan like any other Claude Code work.

## Your files

| Path | Holds |
|---|---|
| `~/.claude/skills/personal-os/` | The skill itself: plain markdown you can read and edit; updates build on your edits |
| `~/.claude/personal-os/state.json` | How far history has been read, update log, thresholds, `exclude_projects` |
| `~/.claude/personal-os/work/` | Chunks, observations and drafts from the last run |
| `~/.claude/personal-os/history/` | A backup of the skill before every build or update |
| `~/.claude/personal-os/rejected.md` | Changes you declined |

Open the skill with `code ~/.claude/skills/personal-os` (`.claude` is hidden in Finder). Set `PERSONAL_OS_HOME` or `PERSONAL_OS_SKILL_DIR` to move these folders.

Claude Code sees the skill in every session and project, and Claude loads the full rules when relevant, usually early. To check, ask "is the personal-os skill loaded?". To load it every session without exception, add to `~/.claude/CLAUDE.md`:

```
At the start of every session, load the personal-os skill.
```

## How it stays current

- **Reminder, not autopilot.** After 15 new sessions, or 21 days with any new session, Claude mentions once a day that an update is due. The check is local and costs no tokens (thresholds: `nudge_after_sessions`, `nudge_after_days` in `state.json`).
- **You approve every change.** Nothing is rewritten silently, so a few unusual sessions cannot skew the rules.
- **Working rules are kept.** Missing evidence never weakens or removes a rule, because a rule Claude already follows stops showing up in your corrections.
- **Rejected changes are remembered** in `rejected.md` and not proposed again without new evidence.
- **Every update is reversible.** The previous version is backed up to `~/.claude/personal-os/history/`; ask Claude to restore it.

### Keep enough history

Claude Code deletes transcripts after `cleanupPeriodDays` (30 by default). Expired sessions fall back to `~/.claude/history.jsonl`, which keeps your prompts but not Claude's replies. `build` offers to raise the setting to 180, or set it yourself in `~/.claude/settings.json`:

```json
{ "cleanupPeriodDays": 180 }
```

## How it works

All of this runs in the chat after you type the command. You only answer Claude's questions, and nothing is written to this repo.

1. `scripts/pos.py extract` collects only what you typed, from transcripts and, for expired sessions, `~/.claude/history.jsonl`, plus a per-folder `index.md`.
2. One subagent per chunk records observations: a claim, verbatim quotes, and how many sessions show it.
3. Claude merges and tags them, drafts the skill, and proposes a few deeper patterns for you to confirm.
4. You review. Only then is it installed or applied, and the state file records how far history has been read.

The method is in [templates/method.md](templates/method.md) and the output contract in [templates/skill-structure.md](templates/skill-structure.md). Edit them to change what gets extracted.

## Privacy

- **What is read.** `build` reads your prompts from every project on this machine, including work or confidential ones. Extraction runs locally, but the prompts are then sent to Claude for analysis, like any file Claude reads for you. Nothing goes anywhere else.
- **Leaving projects out.** `build` asks which to exclude. You can also list paths (or part of one) under `exclude_projects` in `~/.claude/personal-os/state.json`, for example `"exclude_projects": ["/Users/me/client-work"]`. It applies to transcripts and prompt history alike.
- **What is written.** Your Personal OS quotes your prompts word for word, so it may contain client names, links or private details. It lives under `~/.claude/`, outside this repo, and `.gitignore` blocks generated output from being committed here. If you share it (a public repo, a teammate, a post), read it first and remove anything you would not want seen.

## Uninstall

`/plugin uninstall claude-personal-os@claude-personal-os` removes the commands and the reminder. Your Personal OS stays in `~/.claude/skills/personal-os/` and keeps loading in every session; delete that folder and `~/.claude/personal-os/` to remove it completely.

## Tests

```
python3 -m unittest discover -s tests
```

## License

MIT
