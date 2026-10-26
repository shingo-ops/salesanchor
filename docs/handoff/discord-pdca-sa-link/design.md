# Phase 3 設計 — discord-pdca-sa-link

**対象ADR**: ADR-1039, ADR-114
**recon**: docs/handoff/discord-pdca-sa-link/recon.md
**日付**: 2026-10-26
**担当**: 設計者（Opus）の指示書 docs/handoff/discord-pdca/bin2b2-sa-link-card.md を実装

## 外部・過去事例の参照と我々への応用

- 該当なし：前の便（ADR-1039 便2b-0）の git 守りの延長で、設計は指示書に固定済みのため外部事例の参照は不要と判断

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 偽の commondir・gitdir の部屋を reaper が消さず印ファイルが出ない | scripts/tests/test-reaper-safety.sh の G4〜G9 |
| 偽の繋がりの部屋・一覧外のリポジトリの部屋を janitor が残す | scripts/tests/test-disk-janitor.sh の J3〜J5 |
| 確かめを外すと試験が落ちる | docs/handoff/disk-janitor/evidence/link-check-mutation.txt |
| 前後で消す・残すの顔ぶれが同じ | docs/handoff/disk-janitor/evidence/link-check-dryrun-diff.txt |

## 技術 How・KPI

- KPI: 本店の部屋の dry-run で消す・残すの差 0 件、新たに「合わない」へ入る部屋 0 件
- 技術選択: git_safe_link_ok で .git・commondir・gitdir・config を確かめ、合わない部屋は残す

## 弊害・トレードオフ

- 本店の checkout で new-worktree.sh を動かすと本店の古い reaper の写しが動く → 対策: マージ後に設計者が道具の写しを取り直す

## 計画票

| ステップ | 内容 | 担当 |
|---|---|---|
| 1 | 実装と試験と証拠 | Generator |
| 2 | Draft PR と GO 待ち | 設計者 |

## 継続

- 完了後の監視: reaper-schedule.yml の初回 --execute の結果
- 次フェーズへの引き継ぎ: 起動設定の入れ替えと agent-console v0.46.3

## 維持の仕組み

- 試験 G4〜G9・J3〜J5 を scripts/tests/test-reaper-safety.sh と scripts/tests/test-disk-janitor.sh に置き、手元で回す（CI では回らない）。効かなくする確認の記録は docs/handoff/disk-janitor/evidence/link-check-mutation.txt
