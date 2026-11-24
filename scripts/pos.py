#!/usr/bin/env python3
"""Reads Claude Code transcripts and tracks Personal OS state. Standard library only."""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
PROJECTS_DIR = CLAUDE_DIR / "projects"
# Prompt history outlives transcripts (no cleanup), so it fills gaps for expired sessions.
HISTORY_FILE = CLAUDE_DIR / "history.jsonl"
STATE_DIR = Path(os.environ.get("PERSONAL_OS_HOME", CLAUDE_DIR / "personal-os"))
STATE_FILE = STATE_DIR / "state.json"
SKILL_DIR = Path(os.environ.get("PERSONAL_OS_SKILL_DIR", CLAUDE_DIR / "skills" / "personal-os"))

# Claude Code deletes transcripts after cleanupPeriodDays (30 by default), so nudge well before that.
DEFAULTS = {"nudge_after_sessions": 15, "nudge_after_days": 21, "chunk_chars": 60000}

SYSTEM_TAGS = re.compile(
    r"<(system-reminder|ide_selection|ide_opened_file|local-command-stdout|local-command-stderr|"
    r"local-command-caveat|command-message|bash-stdout|bash-stderr)>.*?</\1>",
    re.S,
)
COMMAND = re.compile(r"<command-name>(.*?)</command-name>", re.S)
ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)
PASTE = re.compile(r"<pasted_content[^>]*>(.*?)</pasted_content[^>]*>", re.S)
# Clients inject new context tags over time (e.g. browser_instruction); their names have _ or -, HTML tags rarely do.
INJECTED = re.compile(r"\A\s*<([a-z]+[_-][a-z_-]+)\b[^>]*>.*?</\1>", re.S)
SKIP_PREFIXES = ("[Request interrupted", "<task-notification", "Caveat:", "This session is being continued")
PASTE_LIMIT = 1500
CONTEXT_LIMIT = 300


def load_state():
    try:
        state = json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        state = {}
    return {**DEFAULTS, **state}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def parse_ts(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def clean_prompt(raw):
    """Returns the human-written part of a prompt, or None when it is not one."""
    text = SYSTEM_TAGS.sub("", raw)
    cmd = COMMAND.search(text)
    if cmd:
        args = ARGS.search(text)
        rest = ARGS.sub("", COMMAND.sub("", text)).strip()
        text = f"{cmd.group(1).strip()} {args.group(1).strip() if args else ''}".strip() + ("\n" + rest if rest else "")
    text = PASTE.sub(lambda m: "[pasted]\n" + m.group(1).strip()[:PASTE_LIMIT] + "\n[/pasted]", text).strip()
    while INJECTED.match(text):
        text = INJECTED.sub("", text, count=1).strip()
    if not text or text.startswith(SKIP_PREFIXES) or re.match(r"<[a-z]+[_-]", text):
        return None
    return text


def is_human(record):
    if record.get("type") != "user" or record.get("isMeta") or record.get("isSidechain"):
        return False
    origin = record.get("origin")
    if isinstance(origin, dict):
        return origin.get("kind") == "human"
    content = record.get("message", {}).get("content")
    if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return False
    return True


def tail(text, limit=CONTEXT_LIMIT):
    if len(text) <= limit:
        return text.strip()
    cut = text[-limit:]
    return "..." + cut[cut.find(" ") + 1:].strip()


def read_session(path, since=None):
    """Yields (timestamp, cwd, prompt, previous assistant text) for each human prompt after since."""
    last_assistant = ""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("type") == "assistant" and not rec.get("isSidechain"):
                said = text_of(rec.get("message", {}).get("content")).strip()
                if said:
                    last_assistant = said
            elif is_human(rec):
                prompt = clean_prompt(text_of(rec.get("message", {}).get("content")))
                ts = parse_ts(rec.get("timestamp"))
                if prompt and not (since and ts and ts <= since):
                    yield ts, rec.get("cwd") or "", prompt, last_assistant


def iter_sessions():
    if not PROJECTS_DIR.is_dir():
        return
    for path in sorted(PROJECTS_DIR.glob("*/*.jsonl")):
        yield path


def read_history(since=None):
    """Returns {session id: [(timestamp, project, prompt, "")]} from the prompt history file."""
    sessions = {}
    try:
        fh = open(HISTORY_FILE, encoding="utf-8", errors="replace")
    except OSError:
        return sessions
    with fh:
        for line in fh:
            try:
                rec = json.loads(line)
                ts = datetime.fromtimestamp(rec["timestamp"] / 1000, timezone.utc)
            except (ValueError, KeyError, TypeError):
                continue
            text = (rec.get("display") or "").strip()
            for paste in (rec.get("pastedContents") or {}).values():
                if isinstance(paste, dict) and paste.get("content"):
                    text += "\n[pasted]\n" + paste["content"].strip()[:PASTE_LIMIT] + "\n[/pasted]"
            if not text or (since and ts <= since):
                continue
            sid = rec.get("sessionId") or f"{rec.get('project', '')}:{ts.date()}"
            sessions.setdefault(sid, []).append((ts, rec.get("project") or "", text, ""))
    return sessions


def summarize(rows, sid, project, source, path=None):
    stamps = [r[0] for r in rows if r[0]]
    cwds = [r[1] for r in rows if r[1]]
    return {
        "id": sid,
        "path": str(path) if path else None,
        "source": source,
        "rows": None if path else rows,
        "project": cwds[0] if cwds else project,
        "start": min(stamps).isoformat() if stamps else None,
        "end": max(stamps).isoformat() if stamps else None,
        "prompts": len(rows),
    }


def session_prompts(session, since=None):
    if session["rows"] is not None:
        return session["rows"]
    return list(read_session(Path(session["path"]), since))


def select_sessions(since=None):
    """Transcripts first; history fills in sessions whose transcript is gone."""
    current = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    excluded = load_state().get("exclude_projects") or []
    out, seen = [], {current}
    for path in iter_sessions():
        if path.stem == current:
            continue
        seen.add(path.stem)
        rows = list(read_session(path, since))
        if rows:
            out.append(summarize(rows, path.stem, path.parent.name, "transcript", path))
    for sid, rows in read_history(since).items():
        if sid not in seen:
            out.append(summarize(sorted(rows, key=lambda r: r[0]), sid, "", "history"))
    out = [s for s in out if not any(x in s["project"] for x in excluded)]
    return sorted(out, key=lambda s: s["start"] or "")


def since_arg(args, state):
    if getattr(args, "all", False):
        return None
    if getattr(args, "since", None):
        return parse_ts(args.since if "T" in args.since else args.since + "T00:00:00+00:00")
    return parse_ts(state.get("last_extracted_through")) if state.get("last_extracted_through") else None


def report(sessions):
    return {
        "sessions": len(sessions),
        "prompts": sum(s["prompts"] for s in sessions),
        "from_history": sum(1 for s in sessions if s["source"] == "history"),
        "first": sessions[0]["start"] if sessions else None,
        "last": max((s["end"] for s in sessions if s["end"]), default=None),
    }


def project_index(sessions):
    """Per-folder counts and dates, so habits visible only in folder names (copies, renames) can be seen."""
    rows = {}
    for s in sessions:
        r = rows.setdefault(s["project"], {"sessions": 0, "prompts": 0, "first": s["start"], "last": s["end"]})
        r["sessions"] += 1
        r["prompts"] += s["prompts"]
        r["last"] = max(filter(None, (r["last"], s["end"])), default=None)
    return rows


def cmd_index(args):
    state = load_state()
    sessions = select_sessions(since_arg(args, state))
    projects = project_index(sessions)
    print(json.dumps({**report(sessions), "projects": {k: v["sessions"] for k, v in
                      sorted(projects.items(), key=lambda kv: -kv[1]["sessions"])}}, indent=2))


def cmd_extract(args):
    """Writes the human prompts, with the reply each one answered, into numbered chunk files plus index.md."""
    state = load_state()
    since = since_arg(args, state)
    sessions = select_sessions(since)
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    # Leftover observations or drafts from the last run would be read as new evidence.
    for old in [*out.glob("chunk-*.md"), *out.glob("obs-*.md")]:
        old.unlink()
    shutil.rmtree(out / "draft", ignore_errors=True)
    limit = args.chunk_chars or state["chunk_chars"]
    chunks, buf = [], []
    size = 0
    for s in sessions:
        note = " | source: prompt history, no Claude replies" if s["source"] == "history" else ""
        block = [f"\n## Session {s['id'][:8]} | project: {Path(s['project']).name} | {(s['start'] or '')[:10]}{note}\n"]
        for ts, _cwd, prompt, before in session_prompts(s, since):
            if before:
                block.append(f"> Claude (end of previous reply): {tail(before)}\n")
            block.append(f"USER [{ts.isoformat()[:16] if ts else '?'}]: {prompt}\n")
        text = "\n".join(block)
        if buf and size + len(text) > limit:
            chunks.append("".join(buf))
            buf, size = [], 0
        buf.append(text)
        size += len(text)
    if buf:
        chunks.append("".join(buf))
    for i, body in enumerate(chunks, 1):
        (out / f"chunk-{i:03d}.md").write_text(body)
    index = ["# Project folders\n", "| Folder | Sessions | Prompts | First | Last |", "|---|---|---|---|---|"]
    for folder, r in sorted(project_index(sessions).items(), key=lambda kv: kv[1]["first"] or ""):
        index.append(f"| {folder} | {r['sessions']} | {r['prompts']} | {(r['first'] or '')[:10]} | {(r['last'] or '')[:10]} |")
    (out / "index.md").write_text("\n".join(index) + "\n")
    print(json.dumps({"out": str(out), "chunks": len(chunks), **report(sessions)}, indent=2))


def cleanup_days():
    try:
        return json.loads((CLAUDE_DIR / "settings.json").read_text()).get("cleanupPeriodDays", 30)
    except (OSError, ValueError, AttributeError):
        return 30


def due(state, sessions_since):
    if not state.get("last_extracted_through"):
        return "no update recorded yet" if (SKILL_DIR / "SKILL.md").is_file() else "never built"
    last = parse_ts(state["last_extracted_through"])
    days = (datetime.now(timezone.utc) - last).days if last else 0
    if sessions_since >= state["nudge_after_sessions"]:
        return f"{sessions_since} new sessions"
    if sessions_since and days >= state["nudge_after_days"]:
        return f"{days} days since the last update"
    return None


def cmd_status(args):
    state = load_state()
    since = parse_ts(state.get("last_extracted_through")) if state.get("last_extracted_through") else None
    new = select_sessions(since)
    print(json.dumps({
        "skill_installed": (SKILL_DIR / "SKILL.md").is_file(),
        "skill_dir": str(SKILL_DIR),
        "last_extracted_through": state.get("last_extracted_through"),
        "updates": len(state.get("history", [])),
        "new_sessions": len(new),
        "new_prompts": sum(s["prompts"] for s in new),
        "due": due(state, len(new)),
        "cleanup_period_days": cleanup_days(),
        "nudge_after_sessions": state["nudge_after_sessions"],
        "nudge_after_days": state["nudge_after_days"],
    }, indent=2))


def cmd_nudge(_args):
    """Prints one line for the SessionStart hook when an update is due, at most once a day."""
    try:
        state = load_state()
        today = datetime.now(timezone.utc).date().isoformat()
        if state.get("last_nudged") == today:
            return
        since = parse_ts(state.get("last_extracted_through")) if state.get("last_extracted_through") else None
        if since is None and not (SKILL_DIR / "SKILL.md").is_file():
            reason, action = "never built", "/claude-personal-os:build"
        else:
            new = select_sessions(since)
            reason, action = due(state, len(new)), "/claude-personal-os:update"
        if not reason:
            return
        state["last_nudged"] = today
        save_state(state)
        print(f"Personal OS update is due ({reason}). Tell the user once, in one line, that they can run {action}.")
    except Exception:
        return


def cmd_mark(args):
    """Records an applied build or update so the next run starts after it."""
    state = load_state()
    through = args.through
    state["last_extracted_through"] = through
    state.setdefault("history", []).append({
        "applied_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": args.kind,
        "through": through,
        "sessions": args.sessions,
        "prompts": args.prompts,
        "changes": args.changes,
    })
    state.pop("last_nudged", None)
    save_state(state)
    print(json.dumps({"state": str(STATE_FILE), "last_extracted_through": through}, indent=2))


def cmd_paths(_args):
    print(json.dumps({
        "projects_dir": str(PROJECTS_DIR),
        "history_file": str(HISTORY_FILE),
        "state_dir": str(STATE_DIR),
        "skill_dir": str(SKILL_DIR),
        "work_dir": str(STATE_DIR / "work"),
        "history_dir": str(STATE_DIR / "history"),
    }, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(prog="pos", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, fn in (("index", cmd_index), ("extract", cmd_extract)):
        sp = sub.add_parser(name)
        sp.add_argument("--since", help="ISO date; default is the end of the last applied update")
        sp.add_argument("--all", action="store_true", help="ignore state and read every session")
        if name == "extract":
            sp.add_argument("--out", default=str(STATE_DIR / "work"))
            sp.add_argument("--chunk-chars", type=int)
        sp.set_defaults(fn=fn)

    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("nudge").set_defaults(fn=cmd_nudge)
    sub.add_parser("paths").set_defaults(fn=cmd_paths)

    sp = sub.add_parser("mark")
    sp.add_argument("--kind", choices=["build", "update"], required=True)
    sp.add_argument("--through", required=True, help="timestamp of the newest prompt that was read")
    sp.add_argument("--sessions", type=int, default=0)
    sp.add_argument("--prompts", type=int, default=0)
    sp.add_argument("--changes", type=int, default=0)
    sp.set_defaults(fn=cmd_mark)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
