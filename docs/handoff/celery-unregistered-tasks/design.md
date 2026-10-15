---
mode: handoff
---
<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# 設計 — celery-unregistered-tasks

> この文書は何か：一度も動いていない 2 つの定期作業（写しシートの書き出しと、毎朝の件数の突き合わせ）を動くように直し、成果のない 15 分ごとのまとめ翻訳を外すための設計です。あわせて、買取価格の取得が後片付けをしないせいで別の作業を失敗させる問題を直し、同じ登録漏れが二度と起きないように検査を足します。

**状態**: 設計案作成済み・設計審査済み（Opus 自己審査。独立した第二者レビューではない）・PO 実装承認待ち
**recon**: [recon.md](recon.md)
**出どころ**: `docs/handoff/ai-ops-247/stage1-design.md` §7 の U11・U13

---

## 1. PO の決定（原文）

- まとめ翻訳：「15 分ごとのまとめ翻訳が、この 7 日間で 1 件も翻訳していません。→この機能は外す」（2026-10-15）
- 写しシート：「写しシートは、いま誰か（PO や社員の方）が見ていますか？」に「y」（2026-10-15）→ 直す
- 毎朝の突き合わせ：「この毎朝の突き合わせも、同じように直しますか」に「y」（2026-10-15）→ 直す
- 二重保存の確認：「確認」→ recon §6 で確認済み。後始末はしない

## 2. KGI（PO が○×で判定できる形）

1. 反映の翌朝、写しシートの「READ ME」タブの「最終更新」が、その日の日付になっている。
2. 反映の翌朝 8 時台に、管理用の Discord へ「[SA-02 並走監視]」の知らせが 1 通届く。
3. 反映後、受信メッセージの即時翻訳が、反映前と同じように付く（件数の比較で判定。K4）。

## 3. 変更前 → 変更後

| # | 対象 | 変更前 | 変更後 |
|---|---|---|---|
| C1 | `backend/app/tasks/tcg_mirror.py:295` | デコレータなし。worker が毎日「unregistered」で捨てる | `@shared_task(name="app.tasks.tcg_mirror.run_tcg_mirror_write")` を付け、本体を `try:`／`finally: asyncio.run(engine.dispose())` で包む |
| C2 | `backend/app/tasks/sa02_recon_monitor.py:136` | デコレータなし | `@shared_task(name="app.tasks.sa02_recon_monitor.run_sa02_daily_recon")` を付け、同じく `finally` で `engine.dispose()` |
| C3 | `backend/app/celery_app.py:117`（beat の translate-pending-messages の 4 行） | 15 分ごとに起動 | 削除 |
| C4 | `backend/app/tasks/translation.py:20`〜21、`:123`〜149、`:151`〜257 | まとめ翻訳のタスク・本体・件数上限 | 削除。即時翻訳（`:24`〜60）と健全性チェック（`:260`〜274）は残す |
| C5 | `backend/app/services/message_translator.py:154`、`:195` | まとめ翻訳だけが呼ぶ 2 関数 | 実装時に「tests 以外の呼び出しが 0」を `git grep` で再確認し、0 なら削除。テストも合わせて削除。1 つでもあれば残し、カードの分岐 B に従う |
| C6 | `backend/tests/test_translation_task_context.py:18` ほか、まとめ翻訳を参照するテスト | まとめ翻訳を検査 | 該当テストを削除（即時翻訳のテストは残す） |
| C7 | `backend/app/tasks/buyback_scraper.py:41` | `asyncio.run` を 3 回呼ぶが、共用 engine を片付けない | 関数の本体を `try:`／`finally: asyncio.run(engine.dispose())`（`from app.database import engine`）で包む。自前で作る engine には触らない |
| C8 | 新規 backend/tests/test_celery_beat_registered.py（便2 で新規作成） | beat の名前が登録済みかを見る検査がない | include の全モジュールを読み込んだあと、beat_schedule の全 task 名が `celery_app.tasks` にあることを確かめるテストを足す |
| C9 | `docs/runbooks/alerts.md:192` | 「毎日 2〜3 回失敗・原因未調査」 | 「まとめ翻訳は 2026-10 に廃止。原因は買取価格の取得の後片付け漏れ（C7 で修正）」へ書き換え |

- 型の根拠：`@shared_task(name=...)` は `backend/app/tasks/fx_rate_updater.py:42` と `backend/app/tasks/buyback_scraper.py:41` の既存の書き方。`finally: asyncio.run(engine.dispose())` は `backend/app/tasks/translation.py:144` の既存の書き方。新しい書き方は持ち込まない。
- 触らない範囲：即時翻訳の経路（`backend/app/services/inbound_translation.py:19`、`backend/app/tasks/translation.py:24`）、予算の判定（`backend/app/services/message_translator.py:529`）、`message_translations` テーブル、健全性チェック、写しシートの書く中身と書き込み先、突き合わせの中身と送り先、買取価格の取得の処理内容、migration、監視ルール、deploy。
- 配線と DB の正本：新しいテーブル・列・設定・データの置き場は作らない。写しシートは DB を正本とする見るだけの写しのまま（`backend/app/tasks/tcg_mirror.py:30` の固定 ID）。

## 4. 代替案と選んだ理由

| 案 | 内容 | 採否 | 理由 |
|---|---|---|---|
| A | デコレータを足し、既存の後片付けの型をそろえる（本案） | 採用 | 既存の型 2 つの組み合わせだけで直る。新しい仕組みがない |
| B | beat の起動を `celery_app.task` で包む専用の登録ファイルを作る | 不採用 | 登録の置き場が 2 か所に分かれ、正本が増える |
| C | まとめ翻訳を残して予算を直す | 不採用 | PO が「外す」と決めた |
| D | 買取価格の後片付けは別のテーマで直す | 不採用 | C1・C2 で登録する 2 つの作業が、同じ失敗に巻き込まれうる（recon §4）。同時に直さないと KGI 1・2 の判定がぶれる |

## 5. 弊害・リスクと対処

| リスク | 影響 | 対処 |
|---|---|---|
| 写しシートの [MIRROR] タブ 5 つと READ ME が、毎晩全部上書きされる | 人がそのタブに書き込んでいた場合、消える | タブ名に [MIRROR] が付いた、機械で書いたタブだけが対象。ほかのタブには触らない（`backend/app/tasks/tcg_mirror.py:270`）。PO に事前に周知する（PR 本文） |
| 本番に鍵の設定がないと、写しシートは「スキップ」で終わる | KGI 1 が×になる | K2 でログを見て判定。×なら PO に鍵の確認を依頼する（secrets は変えない） |
| 突き合わせの知らせが毎朝 1 通増える | 管理用 Discord の通知が増える | PO 了承済み（y）。並走が終わったら外す（SA-02-design §10 の手順のまま） |
| まとめ翻訳を外すと、即時翻訳に失敗した行を後から拾う定期経路がなくなる | 未翻訳の行が残りうる | 今も 7 日間 0 件で、実質的には拾えていない。画面を開いたときの都度翻訳は残る（recon §3）。健全性チェック（毎時）が未翻訳を検知して知らせる |
| 反映の時点で、旧名前のまとめ翻訳がキューに残っている | 1 回だけ「unregistered」が出る | 一過性。K1 の数え方からは除く（反映後 1 時間以内の 1 件は許容） |
| C7 の `engine.dispose()` が、同時に動く別の作業の接続まで捨てる | 同時実行中の作業が接続を張り直す | 既存の 3 タスク（`backend/app/tasks/translation.py:60`・`:148`・`:274`）が同じことをすでに毎回している。新しい影響ではない |

## 6. 外部・過去事例

- 外部事例：使わない。理由は、Celery の「タスクとして登録されていない関数を beat が呼ぶと、worker が unregistered で捨てる」という挙動と、asyncpg の接続がループに紐づく挙動は、本リポジトリのログ（28 件）と既存コメント（`backend/app/tasks/translation.py:144`）で直接確かめられているため。外部の数値を設計成功の証明には使わない。
- 過去事例（社内）：`docs/handoff/runtime-config-audit/recon.md:86` に、同じ「attached to a different loop」を `engine.dispose()` で直した記録がある。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K0 C8 のテストが、C1・C2 の前は×、後は○になる | 実装担当が C8 を先に書き、修正前の実行結果（失敗）と修正後の実行結果（成功）を両方保存する |
| K1 反映後 72 時間、worker のログに `unregistered task` が 0 件（反映後 1 時間以内の旧まとめ翻訳 1 件を除く） | prod1 の celery-worker のログを読み取りで数える |
| K2 反映の翌朝 02:30 JST の実行で `[tcg_mirror] 書き出し完了` が出る。PO がシートの READ ME の「最終更新」を見て当日の日付 | ログの読み取り＋PO の目視 |
| K3 反映の翌朝 08:00 JST に、管理用 Discord へ「[SA-02 並走監視]」が 1 通届く | PO の目視（またはログの送信記録） |
| K4 即時翻訳の件数：反映後 24 時間の `message_translations` 新規件数が、反映前 7 日の 1 日平均の 50% 以上 | 本番 DB の読み取り（反映前に基準値を取る）。0 件が続く場合は R3 として PO に報告 |
| K5 反映後 72 時間、買取価格の取得の直後に同じ worker で起きる「attached to a different loop」が 0 件（基準値：7 日で 18 件） | worker のログを読み取りで数える |
| K6 beat_schedule に translate-pending-messages が無い。worker のログにまとめ翻訳の実行行が 0 件 | `git grep` とログの読み取り |
| K7 CI がすべて緑（ruff・backend のテスト・ADR index・成果物ゲート） | PR の checks |

## 技術 How・KPI

- How：上の C1〜C9。すべて既存の型の再利用。
- KPI：unregistered の件数（基準 2 件/日 → 0 件/日）、買取価格の取得の直後の失敗（基準 18 件/7 日 → 0 件）、写しシートの最終更新日（基準：書かれたことなし → 毎日）。

## 計画票

| 便 | 内容 | 前提 |
|---|---|---|
| 1 | 文書だけの PR（この recon と design） | なし |
| 2 | 実装 PR（C1〜C9）。テストを先に書く（K0） | PO の実装承認と実装カード |
| 3 | 反映後の観測（K1〜K6）と、stage1-design §7 の U11・U13 の閉じ | 便2 の本番反映 |

- 便2 は `migrations/`・`.github/workflows/deploy.yml`・本番 `scripts/` を含まない。ADR-136 の危険 PR には当たらない（実装カードで変更ファイルを確定し、再確認する）。

## 継続

- 突き合わせ（sa02）は、SA-02 の並走が終わったら、`backend/app/celery_app.py:127` のコメントどおり beat ごと外す。その判断は SA-02 のテーマで行う。
- まとめ翻訳を外したあとに未翻訳の行が増えるかは、健全性チェック（毎時）の知らせで見る。

## 維持の仕組み

- 守り手: backend/tests/test_celery_beat_registered.py（便2 で新規作成） — beat に書いた名前が登録されていなければ CI が落ちる。今回の登録漏れ 2 件は、このテストがあれば追加時に止まっていた。
- 守り手: 人手で守る — 新しい作業で `asyncio.run` を使うときは `finally: asyncio.run(engine.dispose())` を付ける。今回はテストで強制しない（作業ごとに接続の作り方が違い、機械判定の誤検知が多いため）。

## 設計審査

- 記録: [review-opus.md](review-opus.md)
