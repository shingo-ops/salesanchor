# 設計 — migration-timestamp-dup-guard

**対象ADR**: ADR-082
**recon**: docs/handoff/migration-timestamp-dup-guard/recon.md
**日付**: 2026-06-24
**担当**: shingo-cc

---

## 外部・過去事例の参照と我々への応用

- 該当なし：本変更は migration-guard.yml への step 追記のみ（CI 検査の強化）。本番スキーマ・デプロイ挙動への影響ゼロ。外部事例参照が不要な理由は「新規設計要素なし・既存ガードの延長線上」という性質による。社内前例として PR #1277（migration 083 未登録）・PR #1345（{schema} リテラルによる本番1.5h停止）が同じパターン（CI ガード追加で再発防止）の適用例。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 既存刻印と重複した新規ファイルを含む PR で fail する | 検収1: `migrations/20260622_020000_planted_dup_test.sql` を追加した別ブランチ PR の CI run が赤 |
| PR 内で同一刻印の2本を追加した PR で fail する | 検収2: `20270101_000000_planted_a.sql` + `b.sql` を同一PR に含めた CI run が赤 |
| 本 PR 自体（migration 追加なし）が pass する | 本 PR の CI run の本 step が `✅ skip` で通過 |
| main 既存重複6組が誤検知されない | 本 PR の CI run で本 step が pass（既存ファイルは --diff-filter=A 対象外） |
| 差分が migration-guard.yml 1ファイルのみ | `gh pr diff <PR> --name-only` の出力が 1 行 |

---

## 技術 How・KPI

- KPI: CI チェック5 追加により、タイムスタンプ重複 migration が PR 段階でブロックされる
- 技術選択: `git ls-tree "$BASE" migrations/` で base 時点の刻印集合を取得。`--diff-filter=A` と組み合わせることで既存重複を誤検知しない設計
- 実装対象: `.github/workflows/migration-guard.yml` 末尾に step 1つ追記のみ

---

## 弊害・トレードオフ

- 既存重複6組のリネームは**しない**（run_all_migrations.sh の手書き順序が崩れるリスク > 刻印重複の弊害）
- 新 step は「追記のみ」のため、既存チェック1〜4への影響ゼロ

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | migration-guard.yml 末尾に チェック5 step を追記 | shingo-cc |
| 2 | SOP artifacts (recon.md / design.md) を commit | shingo-cc |
| 3 | Draft PR 起票（base=main） | shingo-cc |
| 4 | 検収1・2（planted violation）で CI 赤を確認 | shingo-cc |
| 5 | planted ファイル削除・検収3（pass）確認 | shingo-cc |
| 6 | GO記録受領・un-draft → PO マージ | Shingo（PO） |

---

## 継続

- 完了後の監視: 次回 migration 追加 PR で チェック5 が自動起動することを確認
- 次フェーズ: 既存重複6組のリネームは別タスク・別 GO で検討（本 PR スコープ外）
