# 状態「雑誌付き」(CN0025) 記録 SQL（本番未適用）

プロモパック系（群 promo_pack）に状態「雑誌付き」を 1 行足す。設計は [../design.md](../design.md)（PO 承認済み 2026-10-21）、現状は [../recon.md](../recon.md)。
本番に流すのは PO の `!`（担当 Sonnet は流さない）。manual-only の鍵を使うため。原文・仕入元名はここに書かない。

## 流すタイミング

- 93 行の再解析は 2026-10-20 に本番反映済み。順番の前提（93 行の再解析の COMMIT と post の後に入れる）は満たしているので、もう流してよい。
- 流し終えたあと、保留の 3 行だけを再解析する（台本は `CC報告ファイル-keep/accuracy-gold-20261020/kw-apply/magazine3/`。dryrun → commit → post の順）。

## 接続のしかた

前例（bin2 の README）には接続の書き方が無い。再解析の台本（kw-apply/reanalyze4.sh）と同じ経路を使う。SQL は標準入力で渡し、`-v end=...` で終わり方を指定する。

```
ssh -i ~/.ssh/manual-only/id_ed25519 -o BatchMode=yes ubuntu@49.212.137.46 \
  "cd /home/ubuntu/salesanchor && docker compose exec -T postgres psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -v end=ROLLBACK" < 02_apply.sql
```

`01_precheck.sql`・`03_verify.sql` は `-v end` なしで同じ形（読み取り専用の設定が先頭に入っている）。`!` で流すときは、この 1 行を台本ファイルにしておく。

## 順番

| 順 | 作業 | 期待 |
|---|---|---|
| 1 | `01_precheck.sql` | PRECHECK_OK が 5 行（promo_pack 3・code_CN0025_unused・canonical_absent_in_promo_pack・unit 17=Booklet・check_allows_promo_pack）。ROW・ROWFULL・CONSTRAINT・FK は情報として出る。ROWFULL の md5 と FK の行を保存しておく |
| 2 | `02_apply.sql` を `-v end=ROLLBACK` で DRY-RUN | BEFORE_OK 1・INSERTED conditions 1・CHECK_OK 4 行（promo_pack_rows 4・CN0025・existing_rows_unchanged 3・canonical_unique_in_group）。最後に ROLLBACK |
| 3 | `02_apply.sql` を `-v end=COMMIT` | 手順 2 と同じ件数、COMMIT |
| 4 | `03_verify.sql` | VERIFY_OK が 5 行。ROWFULL の md5 を 01 の控えと突き合わせ、id60/61/62 が同じであること（K2）を確かめる |
| 5 | 保留 3 行の再解析 | 設計 K5。台本の dryrun → commit → post |

## 戻し

`04_rollback.sql` を `-v end=ROLLBACK` で DRY-RUN（K7）→ `-v end=COMMIT` で CN0025 を無効にする。そのあと保留 3 行を再解析して未開封へ戻す。

- 行ごと消すのは `-v del=1` を足したときだけ。line_conditions を指す参照（外部キーの表）が全部 0 件のときに限り消す。1 件でもあれば 1/0 で止まり、無効のまま残る。
- 01 の FK の行で、解析結果の表が外部キーかどうかが分かる。外部キーでない場合も、再解析の前に消すと古い結果が存在しない id を指すので、まず無効化だけにする。

## 注意

- code は固定の CN0025。最大値からの採番はしない（CN+14桁の日時の値が混ざるため）。
- 足すのは 1 行だけ。既存の id60/61/62 は変えない（02 の中で適用前後の全列を取引内で比べ、違えば 1/0 で止まる）。
- value_rank は 4（群の末尾）。並びを変えたいときは value_rank だけを直す。
