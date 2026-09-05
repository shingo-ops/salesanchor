<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: 人手で守る（reaper の日次出力を目視） -->
# 設計 — ops-tmp-report-flow

**対象ADR**: ADR-114  
**recon**: `docs/handoff/ops-tmp-report-flow/recon.md`  
**日付**: 2026-09-06  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：本件は 2026-09-05 の実測インシデント（/tmp 45GB・ENOSPC 2 回）を起点とした
  運用ルール整備のため、外部事例の参照は不要と判断。ゴースト検出（PR #3316）の
  「警告のみ」設計方針をそのまま踏襲する。

---

## 設計方針（本 PR は警告のみ）

- **自動削除はしない**。PO がブラウザに貼り終えた後に人手で削除する
  （貼る前に自動削除されると調査が無駄になるため）。
- ゴースト検出（PR #3316）と同じ「警告のみ」の設計方針にそろえる。
- reaper は 2026-09-05 から毎日 3 時に実行される（plist 更新済み）。
  日次出力を目視することで 100MB 超ファイルを早期に発見できる。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| /tmp 直下と /tmp/*/ のファイルを走査し 100MB 超を警告する | `bash scripts/reaper-worktree.sh --execute 2>&1 \| tail -30` で TMP セクションが出力される |
| 該当なし時は「TMP: 0件」と出力される | 上記コマンドで `TMP: 0件` が含まれることを目視確認 |
| 削除処理を一切含まない | reaper スクリプトの /tmp 検査ブロックに `rm` / `rmdir` / `git worktree remove` が存在しないことをコードレビューで確認 |
| executor-preamble.md に「調査結果のファイル出力」節が新設されている | `docs/ai-agents/executor-preamble.md:33` に節が存在することを確認 |

---

## 技術 How・KPI

- KPI: reaper 日次実行で /tmp 100MB 超ファイルが翌朝 3 時までに検出・警告される
- 技術選択: `find /private/tmp -maxdepth 2 -type f -print0`（macOS /tmp は /private/tmp へのシンボリックリンクのため直接指定）＋ `du -sk` でサイズ取得

---

## 弊害・トレードオフ

- `find /private/tmp -maxdepth 2` は `/tmp/*/*/` より深いファイルを検査しない。
  → 運用上のレポートファイルは `/tmp/<カード名>/` の 1 階層に置く慣行であり許容範囲。
- reaper 実行中に /tmp ファイルが急増しても検査は次回実行まで反映されない。
  → 同日 2 回発生した場合に備え、executor-preamble.md に 10MB 上限のリアルタイム停止ルールを明記して補完する。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `scripts/reaper-worktree.sh` にゴースト検出直後の /tmp 検査ブロック追加 | Generator |
| 2 | `docs/ai-agents/executor-preamble.md` に「調査結果のファイル出力」節を新設 | Generator |
| 3 | `docs/handoff/ops-tmp-report-flow/recon.md` / `design.md` 作成 | Generator |
| 4 | `bash scripts/reaper-worktree.sh --execute 2>&1 \| tail -30` で出力形式確認 | Generator |
| 5 | PR 作成 | Generator |

---

## 継続

- 完了後の監視: reaper 日次実行ログ（LaunchAgent plist、毎朝 3 時）を目視。TMP 警告が出た場合 PO が `/tmp` を確認し不要ファイルを削除する。
- 次フェーズへの引き継ぎ: 将来的に自動削除が必要になった場合は別 PR で設計する（本 PR では禁止）。
