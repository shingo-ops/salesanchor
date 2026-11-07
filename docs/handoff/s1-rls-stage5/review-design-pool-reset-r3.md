# 審査 3 回目 — design-pool-reset.md（差分 a0368b43c → b44d1c740）

- 役割: 設計の再審査役（Architect）。読むだけ。製品コード・本番・secret には触っていない。設計書と ADR は直していない。
- 対象: `git diff a0368b43c b44d1c740`（3 ファイル: docs/handoff/s1-rls-stage5/design-pool-reset.md・docs/handoff/s1-rls-stage5/k-baseline.sh・docs/handoff/s1-rls-stage5/review-design-pool-reset-r2.md）の差分だけ。
- 前回: docs/handoff/s1-rls-stage5/review-design-pool-reset-r2.md（REVISE・必須 N1、推奨 N2〜N5）。
- SQLAlchemy: 上流タグ rel_2_0_38 の lib/sqlalchemy/pool/base.py（1515 行）・lib/sqlalchemy/engine/create.py・lib/sqlalchemy/pool/impl.py を raw.githubusercontent.com から取って読んだ。以下「sqla base.py」等はこのファイル。backend/requirements.txt:4 は `sqlalchemy==2.0.38` で版は一致。
- 下の「設計」は /root/worktrees/salesanchor/release-s1-rls-pool-reset-review3/docs/handoff/s1-rls-stage5/design-pool-reset.md（b44d1c740）の行番号。
- 試験そのものは流していない（コードはまだ無い）。下の判断は上流のソースを読んだ結果。

## 1. 前回の指摘ごとの照合表

| ID | 重さ | 結果 | 根拠 |
|---|---|---|---|
| N1 T1 の `_reset_on_return is None` | 必須 | 直った | 設計:171 が `from sqlalchemy.pool.base import reset_none` の上で `d.engine.sync_engine.pool._reset_on_return is reset_none` に変わり、`is None` は使わないと明記。上流で確かめた: ① import できる — sqla base.py:95-100 `class ResetStyle(Enum)`（`reset_none = 2`）、:107 `reset_rollback, reset_commit, reset_none = list(ResetStyle)` はモジュールの最上位の代入なので `from sqlalchemy.pool.base import reset_none` で取れる。② Bx で True になる — 設計:52 の `pool_reset_on_return=None` は sqla create.py:868-877 の対応表（:874 `"reset_on_return": "pool_reset_on_return"`）と :657-660（`if tk in kwargs: pool_args[k] = pop_kwarg(tk)`、値が None でも `in` で渡る）で pool の `reset_on_return` に渡り、AsyncAdaptedQueuePool（sqla impl.py:261）は QueuePool（:45）を継ぎ :137 で `Pool.__init__` を呼ぶ。sqla base.py:287-295 の `util.parse_user_argument_for_enum` が `None` を `ResetStyle.reset_none`（:291 `["none", None, False]`）に変えて `self._reset_on_return` に入れる。:107 の `reset_none` は同じ列挙の要素なので `is` は True。sqlite 側を `event.contains` の False だけで判定する直しも前回の直し方どおり |
| N2 基準値の窓が約 15 分 | 推奨 | 直った（K2 について）。K3 ② は残り（新指摘 N6） | 設計:183 に「便1 の配備の直前に、コンテナがなるべく長く動いた状態で取り直し、それを便1 の基準値にする。0 でないマスは『1 時間あたりの件数が基準値から増えない』に置き換え、PR に書く。便2 も同じ」と入った。前回の直し方と一致。ただし K3 ② の上限 20／時（設計:189）は 15 分窓と 65 分の数えから作ったまま、取り直した基準値で見直す書き方が無い |
| N3 k-baseline.sh の「6 種」 | 推奨 | 直った | docs/handoff/s1-rls-stage5/k-baseline.sh:5 が「7 種の文字列」に。設計:181 の「7 種」と一致 |
| N4 T4 は Bx を見分けない | 推奨 | 直った | 設計:174 で目的を「回帰の確認（Bx の有無を見分ける試験ではない）」に書き直し、state の判定を外した。設計:190（K4）と :246（維持の仕組み）に「見分けるのは T1〜T3、T4 は回帰の確認」と入った |
| N5 K1 を流す機械 | 推奨 | 直った（設計）。ADR には入っていない（新指摘 N7） | 設計:182 に「基準値と事後値は同じ機械（PO の Mac）・同じ回線で取る」。docs/adr/ADR-1070-pool-reset-on-return.md:34 の「測り方」とdocs/handoff/s1-rls-stage5/k-baseline.sh:1-7 の注記には無い |

## 2. 差分が新しい食い違いを生んでいないか

| # | 確かめたこと | 結果 |
|---|---|---|
| 1 | 設計:171 の上流の行 `:95-107・:287-291` | sqla base.py:95-107（ResetStyle と :107 の代入）、:287-295（変換。:291 が reset_none の行）。一致（:287-291 は呼び出しの頭から reset_none の行まで） |
| 2 | 設計:171 の T1 判定「postgresql: True・True。sqlite: `event.contains` が False」と設計:246「install_pool_reset の呼び出しを外すと T1 が赤」 | 一致。呼び出しを外すと `event.contains` が False で赤。`pool_reset_on_return=None` を外すと `is reset_none` が False（既定は :290 の reset_rollback）で赤 |
| 3 | sqlite のとき `d._reset_session_state` が存在するか（T1 の sqlite 側で `event.contains(..., d._reset_session_state)` を呼ぶため） | 設計:56 で `_reset_session_state` は if の外のモジュールの最上位に定義される。sqlite でも属性はある。一致 |
| 4 | 設計:174 T4 と :190 K4・:246 | 3 か所とも「T4 は回帰の確認」で揃っている |
| 5 | 設計:182-183 の箇条と :187 の K2 の表の「20 マスすべて 0 件」 | :183 が置き換えの条件を書いているので矛盾ではない。表の「基準」欄は置き換えに触れていないが、箇条が直前にあるので読み違いの余地は小さい（指摘にしない） |
| 6 | 設計:3 の状態の行 | 「N1〜N5 を反映。T1 の判定の行の確認待ち」。本審査で確認した |
| 7 | docs/adr/ADR-1070-pool-reset-on-return.md は差分に無い | ADR:16 の `install_pool_reset(engine)`・`pool_reset_on_return=None` の記述は設計 §2 と一致のまま。T1 の判定の書き方は ADR に無いので N1 の直しで ADR を直す必要は無い |

## 3. 新しい指摘

| ID | 重さ | 指摘 | 根拠 | 直し方 |
|---|---|---|---|---|
| N6 | 推奨 | K3 ② の上限 20／時は、約 15 分の窓（12.7／時）と別の数え方の 65 分（約 16.6／時）から作ったまま。N2 の直しで K2 は取り直した基準値に寄せたが、K3 ② は取り直しても固定の 20 のまま | 設計:183（K2 だけを置き換える）・設計:189（「20 は 2 回の実測の大きい方に 2 割足した上限」） | 設計:183 の箇条に「K3 ② の上限も、取り直した基準値の `close_exc_per_h` が 16.6 を超えたら、その値の 1.2 倍に置き換えて PR に書く」を足す（実装と並べてよい） |
| N7 | 推奨 | N5 の「同じ機械・同じ回線で取る」が設計 §6 にだけあり、ADR-1070 の「測り方」と物差しの台本の注記には無い。台本だけを見て流す人が別の機械で取る余地が残る | docs/adr/ADR-1070-pool-reset-on-return.md:34、docs/handoff/s1-rls-stage5/k-baseline.sh:1-7、設計:182 | k-baseline.sh の注記に 1 行（「基準値と事後値は同じ機械・同じ回線で流す。設計 §6」）を足す。ADR:34 にも同じ一文を足す（実装と並べてよい） |

必須の新しい指摘は無い。

## 4. 判定

**APPROVE**

前回の必須 N1 は直った（`from sqlalchemy.pool.base import reset_none` は sqla base.py:107 で import でき、`pool_reset_on_return=None` は create.py:874・:657-660 → impl.py:137 → base.py:287-291 で `reset_none` に変わるので、Bx が入っていれば T1 の 2 つ目は True）。推奨 N2〜N5 も直った（N2・N5 は残りを N6・N7 として推奨に回した）。N6・N7 は実装と並べて直してよい。
