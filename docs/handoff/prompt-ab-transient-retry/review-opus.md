# Opus 審査記録: prompt_ab 一時的な失敗のやり直し

## 設計審査（reviewer, model opus）
- 1回目: REVISE（R1〜R9: v7 を対象にするか・transient_retries の意味・引数検査・main 配線試験・回数上限・試験の作り方・反映確認の方法）
- 2回目: APPROVE（§9 で全件反映。前回の指摘で残っているものなし）

## コード審査（reviewer, model opus）2026-10-27
- 対象: origin/release/prompt-ab-transient-retry HEAD db0459bcd9117d9ee3a97902974b537ebeb80726
- 判定: APPROVE。直すべき点なし
- 確認内容: design.md §3・§9 と一致（引数2つ・判定関数・やり直しは v7/v8 の if/else だけ・calls 不変・待ち 30→60→120・上限 5・p.error 検査）。K1〜K5 の試験あり・既存試験の削除 0 行。backend/app で prompt_ab を import するのは試験道具 prompt_ab_recompute.py だけ。危険パスなし
- 軽い指摘（直さない）: ログ書式 `%.0fs` は 1 秒未満の待ちを「0s」と表示する（表示のみ）
- 未確認: 試験・ruff は審査役は流していない（実行役の報告と recon.md が根拠。CI で確かめる）
