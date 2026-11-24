# Extraction method

Shared by `/claude-personal-os:build` and `/claude-personal-os:update`. The goal is an operating manual for working with this user, extracted from evidence, not from self-description.

## What the corpus is

Each chunk file holds the user's own prompts from Claude Code sessions, grouped by session and project. Before most prompts there is a line starting `> Claude (end of previous reply):`; it is only there so short replies ("yes", "go", "apply A-D") can be read in context. Never attribute Claude's words to the user. Sessions marked `source: prompt history` come from `~/.claude/history.jsonl` after their transcript expired and have no Claude lines, so read their short prompts in sequence.

`index.md` in the work dir lists every project folder with session counts and dates. It is read in the synthesis step.

## Map step (one subagent per chunk)

Read the whole chunk and write observations to the output file you were given. For each observation:

- **Claim:** one sentence about how the user works, decides, communicates, or what they want from Claude.
- **Category:** one of `before-executing`, `while-executing`, `after-executing`, `diagnosing`, `communication`, `writing-style`, `design-ux`, `engineering`, `product`, `decisions`, `learning`, `blind-spot`, `growth`, `environment`.
- **Evidence:** one to three verbatim quotes from USER lines, each with its session id, project and date.
- **Count:** how many distinct sessions and projects show it in this chunk.
- **Signal:** `explicit` (the user stated it as a rule or correction) or `behavioral` (inferred from what they did).

Look hardest for:

1. Corrections and frustration: repeated requests, CAPS, "again", "I told you", "why are you unable". Each one is a rule Claude broke.
2. Standing preferences stated as absolutes: "never", "always", "from now on", "don't ever".
3. Recurring rituals: the same kind of request across sessions (audits, "is X up to date", "are you sure").
4. Decisions the user made and does not want re-raised.
5. How the user approves, rejects, and asks questions, and what they want back (length, format, verdicts).
6. Patterns that cost the user time or quality (blind spots), stated plainly and kindly, with evidence.

Do not record: project facts that live in code, secrets or credentials, one-off task details, or traits with no quote behind them. If the chunk has nothing for a category, skip it.

## Confidence tags

- `[strong]`: seen in three or more sessions, or stated as an absolute ("never", "always", "from now on"), or corrected in two or more sessions.
- `[moderate]`: seen in two sessions (in one project or two), or stated explicitly once without an absolute.
- `[inferred]`: seen once as behavior and never stated, or read from indirect evidence. Use sparingly.

If most rules come out `[strong]`, the tags carry no signal: recheck the counts.

Tags are assigned in the synthesis step from the merged counts, not per chunk.

## Synthesis rules

- Merge duplicate observations across chunks and add up their counts before tagging.
- Read `index.md` for habits visible only in folder names and dates: parallel copies of one repo, work moving to a renamed copy, many short-lived folders. Cite the folder names as behavioral evidence.
- A rule the user no longer has to state may simply be working. Absence of new evidence never weakens or drops a rule from an existing skill.
- When two observations conflict, keep both in a short "tension" note and let the user arbitrate; never silently pick one.
- Prefer the user's own words in rules ("they ask for X" plus a short quote) over paraphrase.
- Refer to the user by name or as they/them unless the corpus shows the user stating their pronouns. Never infer pronouns from a name.
- Write in plain direct sentences. Follow every writing rule the corpus itself establishes (for example, if the user bans a punctuation mark or emojis, the generated files must not contain them).
- No flattery. The blind-spots file is honest and specific, or it is useless.

## Interpretation pass

After merging, look across the observations for three to five second-order patterns (an update proposes at most two) that no single quote states: a direction all their projects move in, a value that explains several unrelated rules, a risk their way of working keeps creating. Each one:

- names the observations it connects (at least three, from at least two sessions)
- is written as a candidate rule for Claude, tagged `[inferred]`
- goes to the user in the review step and enters the skill only if they confirm it; a confirmed one keeps `[inferred]` and adds `(confirmed <date>)`

Rejected candidates go to `rejected.md` like any other rejected change.
