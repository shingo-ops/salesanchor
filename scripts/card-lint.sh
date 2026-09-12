#!/bin/bash
# card-lint.sh — 設計パートナーが出すカードを、実行役に渡す前に検査する
# 使い方: bash scripts/card-lint.sh <カードのテキストファイル>
# exit 0=違反なし / 1=違反あり(一覧を出力) / 2=使い方の誤り
# 設計: docs/handoff/design-partner-card-ops/card-lint-design.md
# 実測: docs/handoff/design-partner-card-ops/card-lint-recon.md
#   grep -P は使えない（BSD grep）。否定先読みは「抜いてから除く」の2段階で書く。
set -u

CARD="${1:-}"
if [ -z "${CARD}" ]; then
  echo "使い方: bash scripts/card-lint.sh <カードのテキストファイル>" >&2
  exit 2
fi
if [ ! -f "${CARD}" ]; then
  echo "ファイルが見つかりません: ${CARD}" >&2
  exit 2
fi

VIOLATIONS=0

# 違反を1件報告する。第1引数=検査番号、第2引数=検査名、第3引数=該当箇所
report() {
  echo "$1 $2 $3"
  VIOLATIONS=$((VIOLATIONS + 1))
}

# 手順のコマンド行だけを抜く。
# 「手順」で始まる行の次から、空行・見出し行・期待する出力の説明を除いた行。
# 見出しは行頭の「手順N」。字下げされた行だけをコマンド候補とする。
# 句点を含む行は散文として除く（禁止事項や説明文を拾わないため）。
extract_commands() {
  awk '
    /^手順[0-9]/ { in_step = 1; next }
    /^[^ \t]/ { in_step = 0 }
    in_step && /^[[:space:]]*$/ { next }
    in_step && /。/ { next }
    in_step && /^[[:space:]]*期待する出力/ { next }
    in_step && /^[[:space:]]*#/ { next }
    in_step { print }
  ' "${CARD}"
}

CMDFILE="$(mktemp)"
trap 'rm -f "${CMDFILE}"' EXIT
extract_commands > "${CMDFILE}"
CMDS="$(cat "${CMDFILE}")"

# ── L01: 手順のコマンド行が cd で始まらない ────────────────────────────────
# 2段階: コマンド行を抜き、cd で始まる行を除いた残りがあれば違反
L01_HITS="$(printf '%s\n' "${CMDS}" | grep -v '^[[:space:]]*cd ' | grep -v '^[[:space:]]*$' || true)"
if [ -n "${L01_HITS}" ]; then
  report "L01" "cd接頭辞なし" "$(printf '%s\n' "${L01_HITS}" | head -3)"
fi

# ── L02: プレースホルダ（山括弧に挟まれた日本語） ──────────────────────────
if grep -q '<[^>]*[^ -~][^>]*>' "${CARD}"; then
  L02_N="$(grep -c '<[^>]*[^ -~][^>]*>' "${CARD}")"
  report "L02" "プレースホルダ" "${L02_N}件"
fi

# ── L03: 終端合図がない ────────────────────────────────────────────────────
if ! grep -q 'END OF CARD' "${CARD}"; then
  report "L03" "終端合図なし" "END OF CARD が0件"
fi

# ── L04: 受領確認がない ────────────────────────────────────────────────────
if ! grep -q '受領確認' "${CARD}"; then
  report "L04" "受領確認なし" "受領確認 が0件"
fi

# ── L05: 出力先が列挙対象と同じディレクトリ ────────────────────────────────
# CC報告ファイル 以外への > リダイレクトと、同じ語での ls が両方あれば疑う
if grep -q '> */tmp/[^C]' "${CMDFILE}" && grep -q 'ls */tmp/' "${CMDFILE}"; then
  report "L05" "自己参照の疑い" "出力先と列挙対象が同じ /tmp 配下"
fi

# ── L06: psql の誤検知パターン ─────────────────────────────────────────────
if grep 'psql' "${CMDFILE}" | grep -q -e '<<' -e '-f ' -e '| *psql'; then
  report "L06" "psqlガードに当たる形" "ヒアドキュメント・-f・パイプ"
fi

# ── L07: psql があるのに読み取り専用の指定がない ───────────────────────────
if grep -q 'psql' "${CMDFILE}" && ! grep -q 'default_transaction_read_only' "${CARD}"; then
  report "L07" "読み取り専用の指定なし" "PGOPTIONS が無い"
fi

# ── L08: gh pr create を直接呼ぶ ───────────────────────────────────────────
if grep -q 'gh pr create' "${CMDFILE}"; then
  report "L08" "PR作成が直接呼び" "gh-pr-create-safe.sh を使う"
fi

# ── L09: gh-pr-merge-safe.sh に番号を渡す ──────────────────────────────────
if grep -q 'gh-pr-merge-safe.sh [0-9]' "${CMDFILE}"; then
  report "L09" "マージに番号を渡している" "番号は .pr-number から読まれる"
fi

# ── L10: --body-file の値が山括弧 ──────────────────────────────────────────
if grep -q '\-\-body-file *<' "${CMDFILE}"; then
  report "L10" "本文ファイルが未確定" "実在パスを書く"
fi

# ── L11: rm を含む ─────────────────────────────────────────────────────────
if grep -q '[^a-zA-Z]rm ' "${CMDFILE}"; then
  report "L11" "削除コマンド" "Codex 環境では拒否される"
fi

# ── L12: git worktree add を直接呼ぶ ───────────────────────────────────────
if grep 'git worktree add' "${CMDFILE}" | grep -q -v 'new-worktree.sh'; then
  report "L12" "worktreeを直接作成" "scripts/new-worktree.sh を使う"
fi

# ── L13: ブランチ名が release/ hotfix/ 以外 ────────────────────────────────
# 2段階: -b を含む行を抜き、release/ hotfix/ に当たる行を除いた残りがあれば違反
L13_HITS="$(grep -e '-b ' "${CMDFILE}" | grep -v -e '-b release/' -e '-b hotfix/' || true)"
if [ -n "${L13_HITS}" ]; then
  report "L13" "ブランチ名が規約外" "$(printf '%s\n' "${L13_HITS}" | head -1)"
fi

# ── L14: 下書きPR ──────────────────────────────────────────────────────────
if grep -q '\-\-draft' "${CMDFILE}"; then
  report "L14" "下書きPR" "下書きは禁止"
fi

# ── L15: 停止時の報告経路がない ────────────────────────────────────────────
if ! grep -q '停止' "${CARD}"; then
  report "L15" "停止時の報告経路なし" "停止 の語が0件"
fi

# ── L16: timeout を使う ────────────────────────────────────────────────────
if grep -q '[^a-zA-Z]timeout ' "${CMDFILE}"; then
  report "L16" "timeoutコマンド" "macOS には無い"
fi

# ── L17: git show $SHA: を引用符なしで使う ─────────────────────────────────
if grep -q 'git show \$SHA:' "${CMDFILE}"; then
  report "L17" "変数展開が壊れる形" '"${SHA}:パス" と囲む'
fi

# ── L18: --admin / --auto ──────────────────────────────────────────────────
if grep -q -e '\-\-admin' -e '\-\-auto' "${CMDFILE}"; then
  report "L18" "関所の素通り" "--admin と --auto は禁止"
fi

# ── L19: 上限のない一覧系 ──────────────────────────────────────────────────
# 2段階: 一覧系を含む行を抜き、上限指定のある行を除いた残りがあれば違反
L19_HITS="$(grep -e 'gh run list' -e 'git branch -r' -e 'gh pr list' "${CMDFILE}" | grep -v -e 'head' -e '--limit' -e 'grep -c' || true)"
if [ -n "${L19_HITS}" ]; then
  report "L19" "出力上限なし" "$(printf '%s\n' "${L19_HITS}" | head -1)"
fi

# ── L21: gh run view / gh run watch ────────────────────────────────────────
if grep -q -e 'gh run view' -e 'gh run watch' "${CMDFILE}"; then
  report "L21" "gh-scope-guard が拒否" "gh pr checks を使う"
fi

# ── L22: permits への直接アクセス ──────────────────────────────────────────
if grep -q '.claude/permits' "${CMDFILE}"; then
  report "L22" "許可の自己発行" "permit-danger.sh 経由にする"
fi

# ── L23: 危険語を含む ──────────────────────────────────────────────────────
# 検査式そのものが危険語に当たらないよう、変数に組み立ててから使う
D1="DELETE"; D2="FROM"; D3="TRUNC"; D4="ATE"
if grep -q -e "${D1} ${D2}" -e "${D3}${D4}" "${CMDFILE}"; then
  report "L23" "危険語を含む" "その語を使わずに済む方法を探す"
fi

# ── L24: 1行が長すぎる（暫定・警告のみ・止めない） ─────────────────────────
L24_N="$(awk 'length($0) > 200 { n++ } END { print n + 0 }' "${CARD}")"
if [ "${L24_N}" -gt 0 ]; then
  echo "L24 警告 1行200字超が ${L24_N}件（閾値は暫定・止めない）"
fi

# ── L25: ダブルクォートの中にバッククォート ────────────────────────────────
if grep -q '"[^"]*`[^"]*"' "${CMDFILE}"; then
  report "L25" "バッククォートを含む文字列" "コマンド置換と解釈される"
fi

# ── L29: カード冒頭に「読んだ節」の書き出しが無い ─────────────────────────
if ! grep -q "guards/" "${CARD}"; then
  report "L29" "読んだ節の書き出しなし" "guards のどれを引いたかを冒頭に書く"
fi

# ── L30: commit と push があるのに確認が無い ───────────────────────────────
if grep -q "git commit" "${CMDFILE}"; then
  if grep -q -e "git push" -e "gh-pr-create-safe.sh" "${CMDFILE}"; then
    if ! grep -q "git log" "${CMDFILE}"; then
      report "L30" "commit の実在を確かめていない" "git log で確認する手順を入れる"
    fi
  fi
fi

# ── L31: マージの出力を報告に残していない ─────────────────────────────────
if grep -q "gh-pr-merge-safe.sh" "${CMDFILE}"; then
  if ! grep "gh-pr-merge-safe.sh" "${CMDFILE}" | grep -q ">>"; then
    report "L31" "マージの出力を残していない" "報告ファイルへリダイレクトする"
  fi
fi

# ── 判定 ───────────────────────────────────────────────────────────────────
if [ "${VIOLATIONS}" -gt 0 ]; then
  echo "違反 ${VIOLATIONS} 件。このカードは投入しない。"
  exit 1
fi
exit 0
