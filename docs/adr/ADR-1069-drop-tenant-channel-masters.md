# ADR-1069: 古い会社ごとの連絡手段の名簿（tenant_NNN.channel_masters）を消す

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（PO 本人の「GO #PR番号」でマージし、本番で K1＝会社ごとの表0 を反映2回またいで確かめたら採用に上げる） |
| 備考 | 設計 `docs/handoff/channel-master-shared/design.md` §6 の4（PR-C）は PO 実装承認 2026-11-06「1」の範囲。PO 2026-11-07「1,2を順番に」（2＝PR-C）。表を消すので ADR-1003 の例外にあたり、委任 GO では出さない |
| 起案日 | 2026-11-07 |
| 方針の決定者 | Shingo（PO）。細部は PO の委任に基づき Opus が設計 |
| 関連 | ADR-1007（migration は形だけ・会社の作成は完全に）、ADR-135・ADR-136（migrations を含む PR の GO）、ADR-1003（委任 GO と例外）、ADR-1024（読み取り専用の窓 ai_ro）、ADR-145（public 共用表の FORCE RLS の型） |
| 設計・根拠 | `docs/handoff/channel-master-shared/design.md`、`docs/handoff/channel-master-shared/recon.md`、`docs/handoff/channel-master-shared/card-pr-c.md`、`docs/handoff/channel-master-shared/review-pr-c-card.md` |

---

## What（何を決めたか）

1. 会社ごとの連絡手段の名簿 `tenant_NNN.channel_masters`（と連番 `channel_masters_id_seq`）を、新しい migration で全社分消す。`DROP TABLE IF EXISTS` で、CASCADE は付けない。
2. 毎回の反映で全 migration を流し直す台本 `scripts/run_all_migrations.sh` から、古い表を作る `20260611_100000_create_channel_masters.sql` の行を外す。古い migration のファイル自体は過去の記録として残す。
3. 試験の足場（`backend/tests/rls_bootstrap.py` ほか）と、読み取り専用の窓の列の分類（`migrations/20261024_100300_create_ai_cloud_views.sql` の tenant_* channel_masters 3行）を同じ PR で外す。
4. 消す前に、5社の表の中身を読み取り専用の鍵で（`ai_ro` のビューから）控え（SELECT の出力と sha256）として残す。反映の全体の控えは deploy の `scripts/backup.sh` に任せる。
5. マージは次の3つが揃ってから: PR-B 反映後に検索 K1 が0件／PR-B 反映から7日間エラー0（最短 2026-11-14）／PO 本人の「GO #PR番号」。

## Why（なぜ）

- 名簿の正本は `public.channel_masters`（全社1つ）に移った（PR-A・PR-B）。会社ごとの表を残すと、同じ事実が2か所にあり、どちらが正しいか分からなくなる（DB の正本1か所の決まり）。
- アプリはもう会社ごとの表を読まない（検索 K1 0件）。本番の5社の表の中身はどれも public と同じ6行で、会社独自の行は無い（2026-11-07 読み取り専用の鍵で確認）。だから消しても失う情報は無い。
- 台本から作る行を外さないと、次の反映で空の表が作り直され、消しても元に戻ってしまう。
- CASCADE を付けないのは、想定外の依存があれば反映が止まる側に倒すため。窓のビューは台本の先頭で外れ、最後に実在の表から作り直されるので、表が消えても作り直しは失敗しない。
- `backend/AGENTS.md` の「テーブル削除は PO 確認のうえ ADR を起案」に従い、この ADR で残す。

## 戻し方

- この PR を revert して反映すると、20260611 が流れて空の表ができる。中身は控えから戻す。revert の PR も migrations を含むので PO の GO が要る。
- 表が無い間も、アプリは public の名簿だけを読むので画面と解析は動く。

## 確かめ方

| 基準 | 検証方法 |
|---|---|
| 会社ごとの表が0 | 読み取り専用の鍵で `pg_class` と `pg_namespace` から `channel_masters`・`channel_masters_id_seq` を schema ごとに並べ、public の2行だけ。反映を2回またいで変わらない（`information_schema.tables` は reader の権限で絞られるので使わない） |
| 冪等で連番も消える | CI の使い捨て PostgreSQL の試験 `backend/tests/test_drop_tenant_channel_masters_pg.py` が pass |
| 作り直されない | `scripts/run_all_migrations.sh` に 20260611 の行が無い |
