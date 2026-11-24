# Output structure

The Personal OS is a user-level Claude Code skill, so it loads in every project.

```
personal-os/
  SKILL.md
  references/
    01-executive-summary.md
    02-core-principles.md
    03-decision-framework.md
    04-engineering-philosophy.md
    05-product-philosophy.md
    06-learning-model.md
    07-communication.md
    08-blind-spots.md
    09-growth-opportunities.md
```

## SKILL.md

Frontmatter:

```yaml
---
name: personal-os
description: <USER>'s Personal Operating System. Load at the start of any session, or whenever deciding how to communicate with them, how much to ask before executing, how to report results, or how to handle their files and UI work. Contains their collaboration rules and non-negotiables; deeper analysis lives in references/.
---
```

Body, in this order:

1. **Title:** `# Personal OS: working with <USER>`
2. **Provenance:** sessions, user prompts, date range, projects, and the tag legend. Add the line `Re-extraction should append to this provenance line, not erase it.` Each update appends one sentence: `Update <date>: +<n> sessions, <m> prompts, <first> to <last>; <k> changes applied.`
3. **Who they are:** three to five sentences: role, what they build, how they use Claude. Use their name or they/them throughout the skill unless they confirmed other pronouns in the review step.
4. **AI Collaboration Guide:** numbered direct instructions to Claude, grouped under `Before executing`, `While executing`, `After executing`, `Diagnosing and iterating`, `Challenging them`, `Supporting them`. Each rule ends with its confidence tag, which may be followed by `(carried over)` or `(confirmed <date>)`. Numbering is continuous across groups.
5. **Non-negotiable behaviors:** a short bullet list of the rules that were stated as absolutes or corrected in two or more sessions.
6. **Project-agnostic operating rules:** up to twelve principles that hold across every project.

Keep SKILL.md under about 300 lines; depth goes in `references/`.

## references/

Each file opens with `# <n>. <Title>`. `01-executive-summary.md` is the exception to the finding format: one page covering the corpus, the main patterns, where it goes wrong and open tensions. Every other file is a numbered list of findings, so updates can edit one finding without touching the rest:

```
## <n>.<k> <Finding as a short claim> [tag]

<One to three sentences of analysis.>

- "<verbatim quote>" (<session id>, <project>, <date>)

**For Claude:** <what to do about it, or the rule number it backs>
```

`08-blind-spots.md` orders findings by cost to the user and replaces `For Claude` with `**Fix:**`. `09-growth-opportunities.md` orders them by leverage. Tensions the user has not arbitrated go at the end of `03-decision-framework.md`.
