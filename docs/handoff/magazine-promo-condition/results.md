# results: プロモパック系の状態「雑誌付き」（CN0025）の本番適用

設計は [design.md](./design.md)、調べは [recon.md](./recon.md)。仕入元名・原文・生出力は社外秘の保管場所（~/CC報告ファイル-keep/accuracy-gold-20261020/kw-apply/magazine3/）に置き、ここには件数と判定だけを書く。
実行は PO（manual-only 鍵を使うため `!` で実行）。出力の読み取りと判定は Opus（2026-10-21）。

## 手順と結果

| 段 | 何をしたか | 結果 |
|---|---|---|
| precheck | 01_precheck.sql | PRECHECK_OK 5件。群 promo_pack は3行。CN0025 は未使用。単位 17=Booklet |
| 状態の追加 dryrun | 02_apply.sql を ROLLBACK で流す | CHECK_OK 4件（群4行・CN0025 1件・既存3行は不変・canonical は群で重複なし）。最後は ROLLBACK |
| 状態の追加 commit | 02_apply.sql を COMMIT で流す | 同じ CHECK_OK 4件のあと COMMIT。CN0025 は id=68 |
| verify | 03_verify.sql | VERIFY_OK 5件。K2_OK（id60/61/62 の全列が precheck の控えと一致） |
| 3行の再解析 pre | 読み取りだけ | COND_PRE_OK |
| 3行の再解析 dryrun（1回目） | 3 job を1取引で再判定し ROLLBACK | 不合格（書き込み0）。理由は下の「1回目の不合格」 |
| 3行の再解析 dryrun（2回目） | 台本の点検を直して流し直す | 合格 job 3/3。期待行3/3。期待外の変化0。is_current 違反の増減0 |
| 3行の再解析 commit | 試走と同じ組でだけ COMMIT | 合格 job 3/3。書き込み3。COMMIT 後の読み戻しは試走と一致。事前の控えを回収済み |
| 3行の再解析 post | 読み取りだけ | 3行とも 雑誌付き・id68・R2・unit 17 Booklet・商品 424590・要確認なし。ほかの63行の指紋は pre と一致 |

## 受入条件

| 基準 | 判定 | 根拠 |
|---|---|---|
| K1 群 promo_pack が4行・CN0025 の値 | ○ | 03_verify の VERIFY_OK（promo_pack_rows 4・CN0025 1・unit_Booklet 1） |
| K2 id60/61/62 の全列が不変 | ○ | K2_OK（全列の md5 が precheck の控えと一致） |
| K3 正規表現が当たる件数 | ○ | 適用前に確認済み（424590 の15件、ほかの商品は0件） |
| K4 実コードでの試算 | ○ | 適用前に確認済み（origin/main 67e5ea6b9） |
| K5 3行が「雑誌付き・Booklet・R2」・ほかの行は不変 | ○ | 再解析の commit と post（期待3/3・期待外0・指紋一致） |
| K6 在庫表と GAS 在庫一覧の目視 | 今は観測できない | 下の「K6 について」 |
| K7 04_rollback の DRY-RUN | ○ | cond.sh rollback-dryrun（2026-10-21）。CN0025 を無効化1件、既存3行は不変（ROLLBACK_CHECK_OK）、参照3件のため削除はしない、最後は ROLLBACK |

## 1回目の不合格（設計の入れ忘れ）

1. 変えてよい列の範囲が狭すぎた。
   - 3行の再解析前の状態は「未開封」ではなく Error（condition 28）だった。単位は空、要確認は付いていた。
   - そのため単位（unit_id・unit_canonical・unit_resolved）と要確認（needs_review・review_reasons）も変わる。
   - 点検で変えてよいとしていたのは状態の3列だけだった。単位と要確認の5列を足し、変わった後の値まで点検するように直した。
2. is_current の点検が ADR-1032 の復活止めを知らなかった。
   - 新しい組 [424590,68] の最新の投稿は 09-30 のもの。同じ仕入元は、それより後の投稿にも同じ商品の行を持っている。
   - そのため本番の _merge_supplier_products（backend/app/services/tcg_analyzer_svc.py:2102-2121、revival_guard=True）では FALSE になる。これが仕様どおりの動き。
   - 点検に同じ規則を入れた。merge への prior_current_pairs の渡し方も、本番（backend/app/services/line_analysis_v102_svc.py:1503-1505・1520-1522。行番号は origin/main 67e5ea6b9 のもの。9c7275ea では :1506・:1508・:1523-1524 で中身は同じ）と同じにした。
   - 前からあると記録していた違反 [424590,28] result 463e51be も、同じ規則で説明がつく。規則を入れた後の点検では違反0件。

post の [4] は n_match=0 と出た。これは数え方の条件に is_current=TRUE が入っていたためで、上の 2 と同じ入れ忘れ。ほかの条件は [2] の一覧で3行とも満たしている。

## K6 について

- 3行は 09-26〜09-30 の古い投稿で、上の 2 のとおり is_current は FALSE。
- 在庫表と GAS 在庫一覧は現行の行だけを出すので、この3行は画面に出ない。
- 画面で「雑誌付き」を確かめられるのは、同じ商品の「雑誌付き」の新しい投稿が解析された後になる。

## 戻し方

- 状態: `bash cond.sh rollback-dryrun` → `bash cond.sh rollback-commit`。CN0025 を無効にするだけで、行は消さない。
  - 解析結果が状態 id を外部キーで参照しているため（01_precheck の FK 行）。
- 3行: 再解析 commit の前に取った before_snapshot.json から戻す。
