<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — drop-column-guard

**対象ADR**: ADR-1002
**recon**: docs/handoff/drop-column-guard/recon.md
**日付**: 2026-09-16
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

該当なし：本変更は既存 migration-guard.yml の5チェックと同一パターンの6番目追加であり、外部事例は不要と判断。既存チェック1〜5が本プロジェクト内の実績として機能している。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| ADR 参照なしの破壊的 migration が CI でブロックされる | PR に ADR-NNN なしで破壊的 SQL を含めた場合に CI 赤になることを確認（人手で守る） |
| ADR 参照ありの破壊的 migration が CI を通過する | PR 本文に ADR-NNN を記載した場合にチェック6が pass することを確認（人手で守る） |
| 既存チェック1〜5が影響を受けない | CI 全チェックが pass（`.github/workflows/migration-guard.yml:1` の既存 step に変更なし） |

---

## 技術 How・KPI

- KPI: 今後 ADR なしの破壊的 migration が main にマージされる件数 = 0
- 技術選択: 既存 migration-guard.yml の step 追加（理由: 新 workflow 不要、既存パターンと統一）

---

## 弊害・トレードオフ

- PR 本文のどこかに ADR-NNN と書くだけで通過する → 対策: ADR の承認状態は人間が確認する旨を警告メッセージに表示
- _down.sql（ロールバック用）も検知対象になる → 対策: _down.sql を含む PR は対応する ADR を本文に書けば通過する（通常、up migration と同じ PR・同じ ADR）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | migration-guard.yml にチェック6を追加 | Generator（実施済み） |
| 2 | PR 作成・CI 確認 | Generator（実施済み） |
| 3 | PO GO → マージ | PO |

---

## 継続

- 完了後の監視: 今後の migration PR で チェック6 が正しく動作しているか CI ログで確認
- 守り手: `.github/workflows/migration-guard.yml:343`（チェック6 の step 定義）
