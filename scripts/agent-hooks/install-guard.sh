#!/bin/bash
# 設計: docs/handoff/guard-add-by-ai/design.md §5-0・§5-5・§6・§13-8（ADR-1072）
# 使い方: bash ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh <name>
# 出力の最後の1行: INSTALL_OK(0) / INSTALL_OK_RECORD_INCOMPLETE(3) / INSTALL_FAILED: <理由>(1)
# 足すだけの台本。外す・並べ替える・欄を変える処理は持たない。
set -eu

python3 -I -B - "$@" <<'PY'
import copy
import datetime
import hashlib
import importlib.util
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile


class Fail(Exception):
    pass


def out(s):
    print(s)
    sys.stdout.flush()


def git(T, args, timeout=60):
    try:
        p = subprocess.run(["git", "-C", T] + list(args), capture_output=True, timeout=timeout,
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    except Exception as e:
        raise Fail("git が動きません (%s)" % type(e).__name__)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def git_ok(T, args, what):
    rc, o = git(T, args)
    if rc != 0:
        raise Fail("%s に失敗しました" % what)
    return o


def sha8_bytes(b):
    return hashlib.sha256(b).hexdigest()[:8]


def read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


def run():
    args = sys.argv[1:]
    # 1. 引数
    if len(args) != 1 or re.fullmatch(r"[a-z0-9-]+", args[0]) is None:
        raise Fail("引数は名前1つ（^[a-z0-9-]+$）だけです")
    name = args[0]
    # 2. 場所は固定
    H = os.environ.get("HOME", "")
    if not H or not os.path.isabs(H):
        raise Fail("HOME が決まっていません")
    DEST_ROOT = os.path.join(H, ".claude")
    T = os.path.join(H, ".salesanchor-tools")
    # 3. 正本の写しの確かめ
    if not os.path.isdir(T):
        raise Fail("正本の写しがありません")
    if git_ok(T, ["status", "--porcelain", "--untracked-files=all"], "git status").strip() != "":
        raise Fail("正本の写しに変更または追跡外のファイルがあります")
    if git_ok(T, ["rev-parse", "--is-shallow-repository"], "shallow の確認").strip() != "false":
        raise Fail("正本の写しが浅い取得です")
    head = git_ok(T, ["rev-parse", "HEAD"], "HEAD の確認").strip()
    remote = git_ok(T, ["ls-remote", "origin", "refs/heads/main"], "ls-remote").split()
    if not remote or remote[0] != head:
        raise Fail("正本の写しの HEAD が GitHub の main と違います")
    folder = os.path.join(T, "scripts", "agent-hooks", name)
    if os.path.islink(folder) or not os.path.isdir(folder):
        raise Fail("見張りのフォルダがありません")
    # 4. 版と PR 番号
    rel = "scripts/agent-hooks/%s/" % name
    mc = git_ok(T, ["log", "--first-parent", "HEAD", "-1", "--format=%H", "--", rel], "版の確認").strip()
    if not mc:
        raise Fail("見張りのフォルダの版が見つかりません")
    subj = git_ok(T, ["log", "-1", "--format=%s", mc], "件名の確認").strip()
    m = re.match(r"^Merge pull request #([0-9]+) from ", subj)
    if not m:
        raise Fail("PR のマージの版ではないため、記録できません")
    pr = m.group(1)
    # 5. 札（点検と同じ規則を読み込んで使う）
    ca_path = os.path.join(T, "scripts", "dev", "consent-audit.py")
    try:
        spec = importlib.util.spec_from_file_location("consent_audit_for_install", ca_path)
        ca = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ca)
        manifest_fn, words_fn, form_fn, hash_fn = ca._ga_manifest, ca._ga_words_ok, ca._ga_hook_form, ca.item_sha8
    except Exception as e:
        raise Fail("consent-audit.py を読み込めません (%s)" % type(e).__name__)
    text = git_ok(T, ["show", "%s:%s" % (mc, rel + "guard-manifest.json")], "札の読み出し")
    man = manifest_fn(text, name)
    if man is None:
        raise Fail("札が規則に合いません")
    if not man["hooks"]:
        raise Fail("札の hooks が空です")
    files, hooks, tests = man["files"], man["hooks"], man["tests"]
    # 6. 語の検査
    for fn in files:
        if not words_fn(git_ok(T, ["show", "%s:%s" % (mc, rel + fn)], "本体の読み出し")):
            raise Fail("本体に確認を飛ばす語があります (%s)" % fn)
    # 7. 置き場で試す
    stage = tempfile.mkdtemp(prefix="install-guard-")
    try:
        for fn in files:
            src = os.path.join(folder, fn)
            if os.path.islink(src):
                raise Fail("正本がシンボリックリンクです (%s)" % fn)
            if not os.path.isfile(src):
                raise Fail("正本が普通のファイルではありません (%s)" % fn)
            dst = os.path.join(stage, fn)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
        target = os.path.join(stage, hooks[0]["file"])
        for t in tests:
            tp = os.path.join(folder, t)
            if t.endswith(".py"):
                cmd = ["python3", "-I", "-B", tp, target]
            elif t.endswith(".sh"):
                cmd = ["bash", tp, target]
            else:
                raise Fail("試験の種類が分かりません (%s)" % t)
            try:
                r = subprocess.run(cmd, cwd=T, capture_output=True, timeout=300,
                                   env={"HOME": H, "PATH": os.environ.get("PATH", "")})
            except Exception as e:
                raise Fail("試験が動きません (%s: %s)" % (t, type(e).__name__))
            if r.returncode != 0:
                raise Fail("試験が落ちました (%s)" % t)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    # 8. settings.json の新しい形（まだ書かない）
    lock = os.path.join(DEST_ROOT, ".install-guard.lock")
    try:
        os.mkdir(lock)
    except OSError:
        raise Fail("別の実行中か、lock が残っています")
    try:
        return locked_part(T, H, DEST_ROOT, name, pr, files, hooks, folder, form_fn, hash_fn)
    finally:
        try:
            os.rmdir(lock)
        except OSError:
            pass


def record_rows(T, rows, po_ref, name):
    """rows: [(target, op, item_hash, extra_args)]。返り値: (書けた数, 書けなかった数)"""
    okn, bad = 0, 0
    for target, op, ih, extra in rows:
        cmd = ["python3", "-I", "-B", os.path.join(T, "scripts", "dev", "perm-change.py"), "record",
               "--target", target, "--op", op, "--item-hash", ih, "--po-ref", po_ref,
               "--intent", "install-guard %s" % name, "--reason", "ADR-1072 install-guard"] + extra
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=60)
            rc, err = r.returncode, r.stderr.decode("utf-8", "replace").strip()
        except Exception as e:
            rc, err = 1, type(e).__name__
        if rc == 0:
            okn += 1
        else:
            bad += 1
            out("RECORD_FAILED: %s %s %s" % (target, op, ih))
            if err:
                print(err, file=sys.stderr)
    return okn, bad


def file_rows(changed):
    rows = []
    for fn, before, after in changed:
        if before != "-":
            rows.append(("hook-files", "remove", before, []))
        rows.append(("hook-files", "add", after, []))
    return rows


def locked_part(T, H, DEST_ROOT, name, pr, files, hooks, folder, form_fn, hash_fn):
    po_ref = "PR#%s" % pr
    settings = os.path.join(DEST_ROOT, "settings.json")
    try:
        with open(settings, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        raise Fail("settings.json を読めません")
    if not isinstance(old, dict):
        raise Fail("settings.json が object ではありません")
    d = copy.deepcopy(old)
    changed_groups = {}  # (event, index) -> 前の組か None
    if hooks:
        hs = d.get("hooks")
        if hs is None:
            hs = d["hooks"] = {}
        if not isinstance(hs, dict):
            raise Fail("settings.json の hooks が object ではありません")
    for hk in hooks:
        new = form_fn(H, name, hk)
        event, matcher = hk["event"], hk.get("matcher", "")
        lst = hs.get(event)
        if lst is None:
            lst = hs[event] = []
        if not isinstance(lst, list):
            raise Fail("settings.json の hooks.%s が配列ではありません" % event)
        old_lst = old.get("hooks", {}).get(event) if isinstance(old.get("hooks"), dict) else None
        old_n = len(old_lst) if isinstance(old_lst, list) else 0
        cands = []
        for gi, g in enumerate(lst):
            if not isinstance(g, dict):
                continue
            if g.get("matcher", "") != matcher:
                continue
            if not isinstance(g.get("hooks", []), list):
                raise Fail("settings.json の組の hooks が配列ではありません")
            cands.append(gi)
        if any(isinstance(h, dict) and h.get("command") == new["command"]
               for gi in cands for h in lst[gi].get("hooks", [])):
            continue
        placed = None
        after = hk.get("after")
        if after:
            for gi in cands:
                for hi, h in enumerate(lst[gi].get("hooks", [])):
                    c = h.get("command") if isinstance(h, dict) else None
                    words = c.split() if isinstance(c, str) else []
                    last = words[-1] if words else ""
                    if last == after or last.endswith("/" + after):
                        lst[gi]["hooks"].insert(hi + 1, new)
                        placed = gi
                        break
                if placed is not None:
                    break
        if placed is None and cands:
            gi = cands[0]
            if "hooks" not in lst[gi]:
                lst[gi]["hooks"] = []
            lst[gi]["hooks"].append(new)
            placed = gi
        if placed is None:
            g = {"matcher": matcher, "hooks": [new]} if "matcher" in hk else {"hooks": [new]}
            lst.append(g)
            placed = len(lst) - 1
        key = (event, placed)
        if key not in changed_groups:
            changed_groups[key] = copy.deepcopy(old_lst[placed]) if placed < old_n else None
    # 9. 本体を写す
    changed = []  # (file, 前8桁か-, 後8桁)
    try:
        for fn in files:
            src = os.path.join(folder, fn)
            dst = os.path.join(DEST_ROOT, "scripts", name, fn)
            srcb = read_bytes(src)
            want = hashlib.sha256(srcb).hexdigest()
            before = "-"
            if os.path.lexists(dst):
                if os.path.islink(dst) or not os.path.isfile(dst):
                    raise Fail("入れ先が普通のファイルではありません (%s)" % fn)
                before = sha8_bytes(read_bytes(dst))
                if hashlib.sha256(read_bytes(dst)).hexdigest() == want:
                    continue
                os.chmod(dst, 0o644)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o555)
            if hashlib.sha256(read_bytes(dst)).hexdigest() != want:
                raise Fail("写した本体が正本と違います (%s)" % fn)
            changed.append((fn, before, want[:8]))
        # 10. settings.json を書く
        if d != old:
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            bak = "%s.bak-install-guard-%s-%s" % (settings, name, stamp)
            tmp = "%s.tmp-install-guard-%s" % (settings, name)
            try:
                shutil.copyfile(settings, bak)
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(d, f, ensure_ascii=False, indent=2)
                    f.write("\n")
                with open(tmp, encoding="utf-8") as f:
                    chk = json.load(f)
                if not isinstance(chk, dict):
                    raise Fail("書いた settings.json が object ではありません")
                os.chmod(tmp, stat.S_IMODE(os.stat(settings).st_mode))
                os.replace(tmp, settings)
            except Fail:
                raise
            except Exception as e:
                raise Fail("settings.json を書けません (%s)" % type(e).__name__)
            finally:
                if os.path.lexists(tmp):
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass
    except Fail as e:
        if changed:
            record_rows(T, file_rows(changed), po_ref, name)
        raise
    # 11. 記録
    out("PR=#%s" % pr)
    for fn, b, a in changed:
        out("FILE %s/%s %s %s" % (name, fn, b, a))
    rows = file_rows(changed)
    batch = "batch:" + secrets.token_hex(8)
    for (event, gi), before in changed_groups.items():
        after = d["hooks"][event][gi]
        matcher = after.get("matcher", "")
        ah = hash_fn(after)
        bh = hash_fn(before) if before is not None else "-"
        out("GROUP %s|%s %s %s" % (event, matcher, bh, ah))
        rows.append(("user-hooks", "add", ah, ["--batch", batch]))
        if before is not None:
            rows.append(("user-hooks", "remove", bh,
                         ["--replaced-by", ah, "--batch", batch,
                          "--old-json", json.dumps(before, ensure_ascii=False)]))
    if not changed and not changed_groups:
        out("NO_CHANGE")
    okn, bad = record_rows(T, rows, po_ref, name)
    out("RECORDED=%d" % okn)
    if bad:
        return "INSTALL_OK_RECORD_INCOMPLETE", 3
    return "INSTALL_OK", 0


try:
    last, code = run()
except Fail as e:
    out("INSTALL_FAILED: %s" % e)
    sys.exit(1)
except Exception as e:
    out("INSTALL_FAILED: 想定外の止まり方 (%s)" % type(e).__name__)
    sys.exit(1)
out(last)
sys.exit(code)
PY
