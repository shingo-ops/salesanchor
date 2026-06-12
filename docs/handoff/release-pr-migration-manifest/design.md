# Phase 3 設計 — release-pr-migration-manifest

**対象ADR**: ADR-135  
**recon**: docs/handoff/release-pr-migration-manifest/recon.md  
**日付**: 2026-06-12  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- GitHub Actions で PR 本文を動的生成するパターンは公式ドキュメントおよびコミュニティで広く使用されている。今回は `gh pr create --body` に migration ファイルリストを埋め込む形で採用。
- 過去事例（#1981）: PO GO 前 migration（change_billing）が deploy.yml 修正リリースに相乗りし手動確認で発覚。今回の manifest バナーは「このリリースに migration が乗っている」を PO に視覚的に明示し、見落とし防止を機械化する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| develop→main PR に migration がある場合 ⚠️ バナーとファイルリストが表示される | CI: auto-release-pr.yml 実行後 PR 本文を目視確認 |
| develop→main PR に migration がない場合 ✅ 「migration なし」確認が表示される | CI: auto-release-pr.yml 実行後 PR 本文を目視確認 |
| 既存の PR 本文フォーマット（Summary・Test plan）が崩れない | PR 本文全体のレイアウト確認 |

---

## 技術 How・KPI

- KPI: リリースPRで migration の見落とし 0件（PO が目視確認できる）
- 技術選択: `git diff origin/main..HEAD --name-only -- 'migrations/**'` で検出。run: インライン変数で複数行を安全に扱う

---

## 弊害・トレードオフ

- `scripts/migrate_*.py` も対象に含めているため Python migration も検出される → 意図通り（より安全側）
- PR 本文が長くなる → 許容範囲

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | auto-release-pr.yml に migration 検出ステップ追加 | Generator |
| 2 | PR 本文に ⚠️/✅ バナーを動的挿入 | Generator |

---

## 継続

- 完了後の監視: 次回 develop→main PR で migration バナーが正しく表示されることを PO が確認
- 次フェーズへの引き継ぎ: migration 件数が多い場合のフォーマット調整は別タスク
