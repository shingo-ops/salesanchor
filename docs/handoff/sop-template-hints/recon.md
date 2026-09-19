<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — sop-template-hints

**仕事名**: sop-template-hints  
**日付**: 2026-09-05  
**対象ADR**: ADR-121  
**担当**: shingo-cc

---

## 既存ADR検索結果

- `docs/adr/ADR-121-sop-process-artifacts-gate.md` — 既存: process-artifacts gate の設計根拠

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/PULL_REQUEST_TEMPLATE.md:29-34` | 標準ワークフロー確認セクション。HTMLコメントで注意書きを付与する対象欄 |
| `scripts/check-process-artifacts.js:214` | `.replace(/<!--[\s\S]*?-->/g, '')` — HTMLコメント除去後にパース。コメント追記は検査に影響しない |
| `scripts/check-process-artifacts.js:222` | 削除するファイル欄も同様にHTMLコメント除去後パース |
| `docs/handoff/_templates/recon.md:1` | ひな型 recon — バッククォートパス注意コメントを冒頭に追記する対象 |
| `docs/handoff/_templates/design.md:1` | ひな型 design — 同上 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | HTMLコメントがパーサーに影響するか | `scripts/check-process-artifacts.js:214,222` 確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 変更対象は HTMLコメント（注意書き）のみ。欄の追加・削除・並び替えは行わない
- `_templates/` ファイルへのコメント追記はゲートに影響しない（ひな型はパース対象外）
- `sop-pr-template-hint/` （前便の成果物）は削除対象外・本PRの許可ファイル外のため触らない
