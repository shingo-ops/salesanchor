#!/usr/bin/env python3
"""Extract PR body from a `gh pr create` / `gh pr edit` command.

Supports:
  --body "..."      / --body '...'   / --body "$(cat <<EOF ... EOF)"
  --body-file <path> (quoted or not, absolute or relative to argv[1] cwd)

Only the --body/--body-file that belongs to a `gh pr create` or
`gh pr edit` invocation is used. A --body on an unrelated command in the
same compound command (e.g. `gh pr comment --body "..."`) is ignored, so
that a chain like:
    gh pr edit 1 --body-file f.md && gh pr comment 1 --body "GO: ..."
is judged only on f.md.

Usage: extract-pr-body.py [cwd]
  stdin: the shell command string
  argv[1] (optional): effective cwd, used to resolve a relative
    --body-file path (defaults to os.getcwd())

Exit codes:
  0: body extracted (stdout has it) or no --body/--body-file directive
     belonging to create/edit was found (stdout is empty; caller skips
     validation -- fail-open, unchanged from before).
  3: a create/edit --body-file directive WAS found but the file could not
     be read (missing/unreadable). Fail-closed: caller must block, not
     skip, since we cannot verify an unreadable body.
"""
import sys
import re
import os
import shlex

cmd = sys.stdin.read()
cwd = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else os.getcwd()


class BodyFileUnreadable(Exception):
    def __init__(self, path):
        super().__init__(path)
        self.path = path


def owning_subcommand(pos):
    """Return the gh-pr subcommand ('create'/'edit'/'comment'/...) that
    owns the --body/--body-file occurrence starting at `pos`, i.e. the
    nearest preceding `gh pr <subcommand>` invocation in the command
    string. Returns None if no such invocation precedes it."""
    owner = None
    owner_start = -1
    for m in re.finditer(r'\bgh\s+pr\s+(\w+)\b', cmd):
        if m.start() <= pos and m.start() > owner_start:
            owner_start = m.start()
            owner = m.group(1)
    return owner


def is_body_owner_valid(pos):
    return owning_subcommand(pos) in ('create', 'edit')


def try_heredoc():
    for m in re.finditer(
        r'--body\s+"?\$\(cat\s+<<[\'"]?(\w+)[\'"]?\s*\n([\s\S]*?)\n\1\s*\n\)"?',
        cmd,
    ):
        if is_body_owner_valid(m.start()):
            return m.group(2)
    return None


def try_body_dq():
    for m in re.finditer(r'--body\s+"((?:[^"\\]|\\.)*)"', cmd):
        if is_body_owner_valid(m.start()):
            return m.group(1).replace('\\n', '\n').replace('\\"', '"')
    return None


def try_body_sq():
    for m in re.finditer(r"--body\s+'((?:[^'\\]|\\.)*)'", cmd):
        if is_body_owner_valid(m.start()):
            return m.group(1)
    return None


def try_body_file():
    # --body-file "path" / --body-file 'path' / --body-file path
    for m in re.finditer(
        r'--body-file\s+("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|\S+)',
        cmd,
    ):
        if not is_body_owner_valid(m.start()):
            continue
        raw = m.group(1)
        try:
            path = shlex.split(raw)[0]
        except (ValueError, IndexError):
            path = raw.strip('"\'')
        path = os.path.expanduser(path)
        if not os.path.isabs(path):
            path = os.path.join(cwd, path)
        try:
            with open(path, encoding='utf-8') as f:
                return f.read()
        except OSError:
            # --body-file was explicitly given for create/edit but the
            # file can't be read: fail-closed, do NOT silently skip.
            raise BodyFileUnreadable(path)
    return None


try:
    for extractor in (try_heredoc, try_body_dq, try_body_sq, try_body_file):
        result = extractor()
        if result is not None:
            print(result)
            sys.exit(0)
except BodyFileUnreadable as e:
    print(f"--body-file が読み込めません（未存在・読み取り不可）: {e.path}", file=sys.stderr)
    sys.exit(3)

# 抽出できなかった場合（--body/--body-file が create/edit に付いていない）は空文字
print("")
