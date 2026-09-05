# design: reaper-ghost-detect

設計日: 2026-09-05
担当: Hikky-dev (REAPER-02)

---

## KGI

`~/worktrees/salesanchor/` 内の git 未登録ディレクトリ（ゴースト）を
reaper 実行時に検出し、人が確認できる状態にする。

| 基準 | 検証方法 |
|---|---|
| ゴーストが 0件のとき「GHOST: 0件」と出力される | 実行テスト（本PR内で確認済み） |
| ゴーストが存在するとき件数・サイズ・パスが表示される | ダミーディレクトリで実行テスト（本PR内で確認済み） |
| ゴーストは削除されない（警告のみ） | コードレビュー: `rm`・`git worktree remove` の不在 |
| 既存の判定ロジック（チェック1〜3）を変更しない | コードレビュー: 挿入箇所は既存フローの外 |

---

## 修正: ゴースト検出ブロックの追加

### 挿入位置

`scripts/reaper-worktree.sh` のサマリ表示（`=== reaper 結果 ===`）の後、
`if [ "${#WILL_DELETE[@]}" -eq 0 ]` の前。

この位置を選んだ理由:
- 全分類処理が完了した後
- `exit 0` より前なので、削除対象がゼロのときも必ず実行される
- dry-run でも実行される（サマリ出力の一部として機能）

### 親ディレクトリの導出

```bash
_GHOST_SCAN_DIR="${HOME}/worktrees/$(basename "${MAIN_REPO_ROOT}")"
```

`MAIN_REPO_ROOT` は既存変数（:40-45）。ハードコードなし。

### 判定ロジック

```bash
# git worktree list --porcelain から登録済みパス一覧を収集
_REGISTERED_WT_PATHS=()
while IFS= read -r _LINE; do
  case "${_LINE}" in
    worktree\ *) _REGISTERED_WT_PATHS+=("${_LINE#worktree }") ;;
  esac
done < <(git -C "${MAIN_REPO_ROOT}" worktree list --porcelain 2>/dev/null)

# ~/worktrees/<repo>/*/ を走査
for _GDIR in "${_GHOST_SCAN_DIR}"/*/; do
  _GDIR_PATH="${_GDIR%/}"
  _IS_REG=0
  for _REGP in "${_REGISTERED_WT_PATHS[@]}"; do
    [ "${_GDIR_PATH}" = "${_REGP}" ] && { _IS_REG=1; break; }
  done
  if [ "${_IS_REG}" -eq 0 ]; then
    # パスとサイズを表示（削除しない）
  fi
done
```

### 出力フォーマット

ゴーストなし:
```
=== ゴースト検出 ===
   走査: /Users/tanizawashingo/worktrees/salesanchor

👻 GHOST: 0件
```

ゴーストあり:
```
=== ゴースト検出 ===
   走査: /Users/tanizawashingo/worktrees/salesanchor

   👻 GHOST: /Users/tanizawashingo/worktrees/salesanchor/orphaned-dir (12.3 MB)

⚠️  GHOST 合計: 1 件 / 12.3 MB（手動確認してください）
```

---

## 外部事例

本修正は「ファイルシステムと git の登録状態の二重チェック」パターン。
`git worktree list` は git 管理外のディレクトリを知らない、という既知の設計上の制約への対処。

---

## 守り手

- reaper が日次（03:00）または起動時に自動実行されるため、ゴーストが翌朝には可視化される
- 守り手ファイル: `~/Library/LaunchAgents/jp.salesanchor.reaper-onlogin.plist`
  （StartCalendarInterval Hour=3 Minute=0、2026-09-05 追加）
- 削除はしないため、誤検出があっても被害ゼロ
