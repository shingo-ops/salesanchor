# Phase 3 設計 — discord-pdca-sa-link

**対象ADR**: ADR-1039, ADR-114
**recon**: docs/handoff/discord-pdca-sa-link/recon.md
**日付**: 2026-10-26
**担当**: 設計者（Opus）の指示書 docs/handoff/discord-pdca/bin2b2-sa-link-card.md を実装

## 外部・過去事例の参照と我々への応用

- git 公式の説明（gitattributes の filter の節、gitrepository-layout の commondir、git-worktree の gitdir）への参照は正本の指示書 docs/handoff/discord-pdca/bin2b2-sa-link-card.md の :126-127 に書いてある。応用：worktree の繋がりが元のリポジトリと一致することと、元のリポジトリに commondir が無いことを確かめ、偽の設定を読む道を塞ぐ。実測（git 2.39.3）も同 :127 のとおり

## 受け入れ基準

正本は指示書 docs/handoff/discord-pdca/bin2b2-sa-link-card.md の「完了の確認」（:98 以降）と試験の節（:86-92）。下の表はその要約。

| 基準 | 検証方法 |
|---|---|
| 偽の commondir・gitdir の部屋を reaper が消さず印ファイルが出ない | scripts/tests/test-reaper-safety.sh の G4〜G9（指示書 :81-88） |
| 偽の繋がりの部屋・一覧外のリポジトリの部屋を janitor が残す | scripts/tests/test-disk-janitor.sh の J3〜J5（指示書 :90-92） |
| 確かめを外すと試験が落ちる | docs/handoff/disk-janitor/evidence/link-check-mutation.txt |
| 前後で消す・残すの顔ぶれが同じ | docs/handoff/disk-janitor/evidence/link-check-dryrun-diff.txt |

## 技術 How・KPI

- KPI: 本店の部屋の dry-run で消す・残すの差 0 件、新たに「合わない」へ入る部屋 0 件
- 技術選択: git_safe_link_ok で .git・commondir・gitdir・config を確かめ、合わない部屋は残す

## 弊害・トレードオフ

- 受け入れる弱さ（取り直しでは解消しない）：人や AI が本店で bash scripts/new-worktree.sh を動かすと、今後も本店の写しの自動回収が動く。指示書 docs/handoff/discord-pdca/bin2b2-sa-link-card.md の :44 のとおり。本店の写しを最新に保つのは別の話でこの便では扱わない

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
