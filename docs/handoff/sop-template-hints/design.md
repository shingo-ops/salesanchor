<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# 設計 — sop-template-hints

**対象ADR**: ADR-121  
**recon**: docs/handoff/sop-template-hints/recon.md  
**日付**: 2026-09-05  
**担当**: shingo-cc

---

## 外部・過去事例の参照と我々への応用

- docs/handoff/sop-pr-format/design.md — process-artifacts gate の書式規則を preamble に文書化した先行事例。今回はゲートに影響しない HTMLコメントの追記なので、同様のアプローチで「書式ミスの発生源（テンプレート）に直接注意書きを埋める」方針を採用。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `標準ワークフロー確認` の欄数・順序が変わらない | `git diff` でセクション行数の増減が HTMLコメント内のみであることを目視確認 |
| `触るファイル:` コメントに「カンマ区切り」「改行・箇条書き不可」「例付き」が含まれる | テンプレート当該行を目視確認 |
| `削除するファイル:` コメントに「1行でも変更・削除した行があるファイルを全列挙」が含まれる | テンプレート当該行を目視確認 |
| `対象ADR:` コメントに「ls docs/adr/ で実在確認」が含まれる | テンプレート当該行を目視確認 |
| `_templates/recon.md` と `_templates/design.md` 冒頭にバッククォートパス注意コメントが追記される | `git diff` 確認 |
| CI `process-artifacts gate` が PASS する | `gh pr checks` 全緑 |

---

## 技術 How・KPI

- KPI: CI process-artifacts gate が PASS（コメント除去後の構造に変化なし）
- 技術選択: HTMLコメント追記のみ。`check-process-artifacts.js:214,222` の `.replace(/<!--[\s\S]*?-->/g, '')` によりパーサーには影響しない

---

## 弊害・トレードオフ

- なし。HTMLコメントはパーサーに無視される設計であることを実装で確認済み

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `.github/PULL_REQUEST_TEMPLATE.md` の5欄のHTMLコメントを更新 | Generator |
| 2 | `docs/handoff/_templates/recon.md` と `design.md` 冒頭にコメント追記 | Generator |
| 3 | `docs/handoff/sop-template-hints/recon.md` と `design.md` 作成 | Generator |
| 4 | commit → push → PR更新 | Generator |

---

## 継続

- 完了後の監視: CI pass を確認して終了
- 次フェーズへの引き継ぎ: なし

## 維持の仕組み

守り手: 人手で守る（`_templates/` への変更は PR＋レビュー経由のみ。CI は process-artifacts gate で保護）
