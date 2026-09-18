#!/usr/bin/env bash
# validate-pr-body.sh
# PR本文を stdin から受け取り、プロセス成果物の必須項目を検査する。
# 合格: exit 0 (stdout に ✅ メッセージ)
# 不合格: exit 1 (stderr に ❌ エラーを全列挙)
# バイパス: PR_BODY_VALIDATE_SKIP=1 で即 exit 0
set -euo pipefail

if [[ "${PR_BODY_VALIDATE_SKIP:-}" == "1" ]]; then
  echo "✅ PR本文検証スキップ（PR_BODY_VALIDATE_SKIP=1）"
  exit 0
fi

# リポジトリルートを取得
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
if [[ -z "$REPO_ROOT" ]]; then
  echo "⚠️  git リポジトリルートが取得できません。ファイル実在確認をスキップします" >&2
fi

# PR本文を stdin から読み込む
PR_BODY="$(cat)"

# python3 でパース（grep -E は多バイト文字パターンの信頼性が低いため）
# PR_BODY は cat で消費済みのため、環境変数経由で python3 に渡す
PARSE_RESULT="$(PR_BODY_TEXT="$PR_BODY" python3 - "$REPO_ROOT" <<'PYEOF'
import sys
import re
import os

pr_body = os.environ.get('PR_BODY_TEXT', '')
repo_root = sys.argv[1] if len(sys.argv) > 1 else ""

errors = []

# ──────────────────────────────────────────────────────────────────────────────
# 検査1: ### 標準ワークフロー確認 セクションが存在するか
# ──────────────────────────────────────────────────────────────────────────────
if not re.search(r'###\s*標準ワークフロー確認', pr_body):
    errors.append('❌ PR本文に「### 標準ワークフロー確認」セクションがありません')
    errors.append('   → PRテンプレートの「標準ワークフロー確認」セクションに記入してください')

# ──────────────────────────────────────────────────────────────────────────────
# 検査2: 対象ADR: 行に ADR-\d[\w-]* 形式の値があるか（ADR-____ はNG）
# CIスクリプトと同じ正規表現: 対象ADR:\s*([^\n]+) → その中から ADR-\d[\w-]* を抽出
# ──────────────────────────────────────────────────────────────────────────────
adr_line_match = re.search(r'対象ADR:\s*([^\n]+)', pr_body)
if not adr_line_match:
    errors.append('❌ 対象ADR: 行が見つかりません（ADR-NNN の形式で記入）')
else:
    adr_values = re.findall(r'ADR-\d[\w-]*', adr_line_match.group(1))
    if not adr_values:
        errors.append('❌ 対象ADRが記入されていません（ADR-NNN の形式で記入。ADR-____ はNG）')

# ──────────────────────────────────────────────────────────────────────────────
# 検査3: recon: 行にパスがあり、ファイルが実在するか
# CIスクリプトと同じ正規表現: recon:\s*(docs\/handoff\/[^\s\n]+\.md)
# ──────────────────────────────────────────────────────────────────────────────
recon_match = re.search(r'recon:\s*(docs/handoff/[^\s\n]+\.md)', pr_body)
if not recon_match:
    errors.append('❌ recon パスが記入されていません（docs/handoff/<仕事名>/recon.md 形式で記入）')
    errors.append('   ※ <仕事名> を含むテンプレ値はNG')
else:
    recon_path = recon_match.group(1).strip()
    if re.search(r'<[^>]+>', recon_path):
        errors.append(f'❌ recon パスにテンプレート値（<仕事名> 等）が残っています: {recon_path}')
    elif repo_root:
        full_path = os.path.join(repo_root, recon_path)
        if not os.path.isfile(full_path):
            errors.append(f'❌ recon.md が存在しません: {recon_path}')

# ──────────────────────────────────────────────────────────────────────────────
# 検査4: 設計: 行にパスがあり、ファイルが実在するか（____ はNG）
# CIスクリプトと同じ正規表現: 設計:\s*([^\n（]+)
# ──────────────────────────────────────────────────────────────────────────────
design_match = re.search(r'設計:\s*([^\n（]+)', pr_body)
if not design_match:
    errors.append('❌ 設計: 行が見つかりません')
else:
    design_raw = design_match.group(1).strip()
    if not design_raw or re.match(r'^_+$', design_raw):
        errors.append('❌ 設計docのパスが記入されていません（____ はNG）')
    elif re.search(r'<[^>]+>', design_raw):
        errors.append(f'❌ 設計パスにテンプレート値（<仕事名> 等）が残っています: {design_raw}')
    elif repo_root:
        full_path = os.path.join(repo_root, design_raw)
        if not os.path.isfile(full_path):
            errors.append(f'❌ 設計docが存在しません: {design_raw}')

# ──────────────────────────────────────────────────────────────────────────────
# 検査5: 触るファイル: と 削除するファイル: が記入されているか
# ──────────────────────────────────────────────────────────────────────────────
touch_match = re.search(r'触るファイル:\s*', pr_body)
if not touch_match:
    errors.append('❌ 「触るファイル:」の宣言がありません（必須）')
else:
    # 直後（同一行 or 次行のリスト）に内容があるか
    after = pr_body[touch_match.end():]
    same_line = after.split('\n')[0].strip()
    if not same_line:
        next_lines = after.split('\n')[1:]
        has_list = any(re.match(r'\s*[-*]\s+\S', l) for l in next_lines[:5])
        if not has_list:
            errors.append('❌ 「触るファイル:」の内容が空です')

delete_match = re.search(r'削除するファイル:\s*', pr_body)
if not delete_match:
    errors.append('❌ 「削除するファイル:」の宣言がありません（必須）')

# ──────────────────────────────────────────────────────────────────────────────
# 検査6: 触るファイル宣言 vs git diff の照合
# CIスクリプト check-process-artifacts.js:760-826 と同じロジック
# ──────────────────────────────────────────────────────────────────────────────
if repo_root and touch_match:
    import subprocess

    # 除外パターン（CI と同一: check-process-artifacts.js:757-761）
    EXCLUDE_PATTERNS = [
        r'package-lock\.json$',
        r'-snapshots/.*\.png$',
        r'^\.claude-pipeline/active-work\.md$',
    ]

    try:
        # git fetch して最新の origin/main を取得
        subprocess.run(['git', 'fetch', 'origin', 'main', '--quiet'],
                       cwd=repo_root, capture_output=True, timeout=30)

        # git diff --numstat origin/main...HEAD
        result = subprocess.run(
            ['git', 'diff', '--numstat', 'origin/main...HEAD'],
            cwd=repo_root, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            # 変更ファイル一覧を取得
            diff_files = []
            delete_files = []
            for line in result.stdout.strip().split('\n'):
                parts = line.split('\t')
                if len(parts) == 3:
                    added, deleted, path = parts
                    if added == '-' and deleted == '-':
                        continue  # binary
                    # 除外パターン適用
                    if any(re.search(p, path) for p in EXCLUDE_PATTERNS):
                        continue
                    diff_files.append(path)
                    if int(deleted) > 0:
                        delete_files.append(path)

            # PR本文から「触るファイル」リストを抽出
            touch_section = pr_body[touch_match.end():]
            # セクション終了まで取得（次の非リスト行 or 末尾）
            touch_lines_raw = re.match(r'((?:[\s\S]*?)(?=\n[^\s\-*]|\n*$))', touch_section)
            declared_touch = set()
            if touch_lines_raw:
                for tl in touch_lines_raw.group(1).split('\n'):
                    tl = re.sub(r'^\s*[-*]\s*', '', tl).strip()
                    # カンマ区切り対応
                    for part in tl.split(','):
                        part = part.strip()
                        if part and part != 'なし':
                            declared_touch.add(part)
            # 同一行のカンマ区切りも対応
            same_line_touch = touch_section.split('\n')[0].strip()
            if same_line_touch:
                for part in same_line_touch.split(','):
                    part = part.strip()
                    if part and part != 'なし':
                        declared_touch.add(part)

            # 宣言外の変更ファイルを検出
            undeclared = [f for f in diff_files if f not in declared_touch]
            if undeclared:
                errors.append('❌ 宣言外のファイルを変更しています:')
                for uf in undeclared:
                    errors.append(f'   - {uf}')
                errors.append('   → 「触るファイル:」に追記してください')

            # PR本文から「削除するファイル」リストを抽出
            if delete_match and delete_files:
                del_section = pr_body[delete_match.end():]
                del_lines_raw = re.match(r'((?:[\s\S]*?)(?=\n[^\s\-*]|\n*$))', del_section)
                declared_delete = set()
                if del_lines_raw:
                    for dl in del_lines_raw.group(1).split('\n'):
                        dl = re.sub(r'^\s*[-*]\s*', '', dl).strip()
                        for part in dl.split(','):
                            part = part.strip()
                            if part and part != 'なし':
                                declared_delete.add(part)
                same_line_del = del_section.split('\n')[0].strip()
                if same_line_del and same_line_del != 'なし':
                    for part in same_line_del.split(','):
                        part = part.strip()
                        if part and part != 'なし':
                            declared_delete.add(part)

                undeclared_del = [f for f in delete_files if f not in declared_delete]
                if undeclared_del:
                    errors.append('❌ 宣言外のファイルから行を削除しています:')
                    for ud in undeclared_del:
                        errors.append(f'   - {ud}')
                    errors.append('   → 「削除するファイル:」に追記してください')

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass  # git が使えない環境ではスキップ

# 結果出力
for e in errors:
    print(e)
PYEOF
)"

if [[ -n "$PARSE_RESULT" ]]; then
  echo "$PARSE_RESULT" >&2
  exit 1
fi

echo "✅ PR本文検証OK"
exit 0
