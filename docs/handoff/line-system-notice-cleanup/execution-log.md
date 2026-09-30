# 実行記録: LINE のお知らせ34件と幽霊仕入元9件の片付け

- 対象PR: #3874
- 設計: `docs/handoff/line-system-notice-cleanup/design.md`
- 実行SQL: `docs/handoff/line-system-notice-cleanup/cleanup.sql`（DRY-RUN→COMMIT）
- 戻しSQL: `docs/handoff/line-system-notice-cleanup/rollback.sql`（未実行）
- **実行者: PO（Shingo）**。実行担当（Claude）は本番書き込み権限を持たないため、自動の安全判定に従い実行を PO に委任した。事後確認・記録（本ファイル）は実行担当が担当。
- GO: `GO #3874`（2026-09-30、本番データ実行より前に受領）

## 1. 実行前の基準値（このセッションで再取得・確認）

### 1-1. 配信の基準値（dist_before.txt、937行→944行、冪等）
scratchpad: `.../scratchpad/cleanup-exec/dist_before.txt`（本セッションで再実行し直近値に更新。全944行、`run_dist_before.py` と同じSQL・同じ48h窓）

### 1-2. 対象行の実行前状態（pre_state.txt）
```
      section
-------------------
 A_source_messages
(1 row)

                  id                  | is_active | superseded_by
--------------------------------------+-----------+---------------
 0794fff7-9e23-4ff6-a17a-6390238ca23f | t         |
 3334568b-31e8-4f5b-b03e-7901eff1458c | t         |
 37e6a8a4-f8dd-42a3-8428-f7baa98397ed | t         |
 38238ca9-dd56-4914-8058-ff25af55bddd | t         |
 440ba83c-b4f0-4b19-bc1d-e779f9f33c25 | t         |
 7e977356-b278-4152-ae16-55acc179b9c9 | t         |
 84970895-156c-4ddd-bb14-53422c2e5af0 | t         |
 892f9890-985b-4788-a8c6-425018e15bf2 | t         |
 c5967c53-c33a-46bd-93f1-6fe4b75b679a | t         |
 cc885f49-8ad1-41bb-81ae-a3c0f566629a | t         |
 efdd8af2-09dc-4902-b33c-5b9ac36eb854 | t         |
 f1596367-3d82-4879-86d1-87507e2eb3db | t         |
(12 rows)

      section
-------------------
 B_source_messages
(1 row)

                  id                  | is_active |            superseded_by
--------------------------------------+-----------+--------------------------------------
 1668b957-96a2-47e6-9e87-d352d4a15c0d | f         | efdd8af2-09dc-4902-b33c-5b9ac36eb854
 2731976c-3b13-4847-94b8-e2d7a1990793 | f         | e3b52b4a-f676-4520-89fd-97f355ffa9b8
 d18c5fa4-6985-4a63-b109-16ec6365dcb8 | f         | eef0d3dc-f8c9-44b9-bad0-701db87fa090
(3 rows)

   section
-------------
 C_suppliers
(1 row)

  id   |               name               | is_active
-------+----------------------------------+-----------
 25593 | 鈴木（板谷STAFFアカウント）      | t
 25595 | Evedat板谷                       | t
 25602 | イベダットースタッフアカウント） | t
 25608 | LF                               | t
 25624 | maarii☆                          | t
 25633 | ｍ                               | t
 25637 | 一真                             | t
 25650 | 伊藤晴彦                         | t
 25658 | GL スタッフ                      | t
(9 rows)

       section
---------------------
 D_supplier_channels
(1 row)

                  id                  | is_active
--------------------------------------+-----------
 164fc276-7a9f-42f9-8d92-a2f63b18f30c | t
 27651604-e3e4-43bf-8feb-cdcf43e74930 | t
 749fe03b-a0f2-4bc7-b44c-8539eaa1c070 | t
 a76ddd41-01fa-4de2-9945-50ff6f2c2c2d | t
 bce3fadc-a5d4-493d-9cad-aeeab7b3fd96 | t
 ce3e3b0b-d049-432b-9b82-7ad884c9db57 | t
 d06dfbae-a8ac-4fec-9308-ac0fec91f86d | t
 e37c407b-894a-4342-8672-c510f50564fb | t
 ee12c2c8-65ec-485f-89b1-f9cfb31145dc | t
(9 rows)

          section
----------------------------
 E_supplier_knowledge_links
(1 row)

 id  | is_active
-----+-----------
 290 | t
(1 row)
```
（生ファイル: `.../scratchpad/cleanup-exec/pre_state.txt`。想定どおり: A=12件有効／B=3件無効／C=9件有効・（旧）無し／D=9件有効／E=有効）

## 2. 本番実行（PO が SSH で手動実行）

PO からの報告（端末出力の要約。実行担当はこのセッションで SSH 端末には同席しておらず、以下は PO からの報告をそのまま転記したものであり、実行担当自身が取得した生ログではない）:

> BEGIN / DO / 3チャネルの active_rows がそれぞれ1 / 9仕入元が（旧）・is_active=f / COMMIT

実行に使われた SQL は `docs/handoff/line-system-notice-cleanup/cleanup.sql`（DRY-RUN でROLLBACKに変えて確認後、COMMIT版で本実行）。この SQL は `DO $$ ... GET DIAGNOSTICS n = ROW_COUNT; IF n != <想定件数> THEN RAISE EXCEPTION` の件数ガード（A=12, B=3, C=9, D=9, E=1）を持ち、想定と異なれば例外で全体がロールバックされる構造。PO の報告どおり COMMIT に到達したことは、全ガードを通過したことを意味する。

## 3. 事後確認（このセッションで実施、2026-09-30）

### 3-1. お知らせ15文型で is_active=TRUE が0件か

本番 `source_messages` 全1671件を読み取り、現ブランチの `backend/app/services/tcg_line_system_events.py`（15パターン収録済み）の `match_system_event` を実際にimportして全件に適用（display_name の代理は suppliers.name、recon と同じ方式）。

```
total_rows_scanned: 1671
label_counts (all, active+inactive): {'announce': 5, 'invite_wait': 13, 'left': 4, 'note_created': 2, 'join': 1, 'line_works_join': 4, 'removed': 5, 'voice_call_start': 1, 'note_posted': 3, 'call_end': 1}
ACTIVE matches (should be 0): 0
```
→ **判定: 0件（基準を満たす）**。スクリプト: `.../scratchpad/cleanup-exec/post_check.py`、生出力: `.../scratchpad/cleanup-exec/post_check_raw.txt`

### 3-2. 本物3チャネル・幽霊仕入元9件・チャネル9件・リンク290

```
         supplier_channel_id          |                  id                  | is_active | superseded_by |                        left
--------------------------------------+--------------------------------------+-----------+---------------+-----------------------------------------------------
 06ed487c-210f-4506-80ad-452d76e362d3 | 1668b957-96a2-47e6-9e87-d352d4a15c0d | t         |               | お世話になっております！...
 593d4e81-03ee-4dbc-b720-362bb0f23f9c | d18c5fa4-6985-4a63-b109-16ec6365dcb8 | t         |               | ⭐️本日、ヲタクエストのアンナさんから、下記のWhatnot
 ab32c1a4-6370-4da0-b3c1-ff43681ac568 | 2731976c-3b13-4847-94b8-e2d7a1990793 | t         |               | みなさまお疲れ様です！...
(3 rows)

  id   |                  name                  | is_active
-------+----------------------------------------+-----------
 25593 | （旧）鈴木（板谷STAFFアカウント）      | f
 25595 | （旧）Evedat板谷                       | f
 25602 | （旧）イベダットースタッフアカウント） | f
 25608 | （旧）LF                               | f
 25624 | （旧）maarii☆                          | f
 25633 | （旧）ｍ                               | f
 25637 | （旧）一真                             | f
 25650 | （旧）伊藤晴彦                         | f
 25658 | （旧）GL スタッフ                      | f
(9 rows)

                  id                  | is_active
--------------------------------------+-----------
 164fc276-7a9f-42f9-8d92-a2f63b18f30c | f
 27651604-e3e4-43bf-8feb-cdcf43e74930 | f
 749fe03b-a0f2-4bc7-b44c-8539eaa1c070 | f
 a76ddd41-01fa-4de2-9945-50ff6f2c2c2d | f
 bce3fadc-a5d4-493d-9cad-aeeab7b3fd96 | f
 ce3e3b0b-d049-432b-9b82-7ad884c9db57 | f
 d06dfbae-a8ac-4fec-9308-ac0fec91f86d | f
 e37c407b-894a-4342-8672-c510f50564fb | f
 ee12c2c8-65ec-485f-89b1-f9cfb31145dc | f
(9 rows)

 id  | is_active
-----+-----------
 290 | f
(1 row)
```
→ 3チャネルとも有効な行がちょうど1つ、その ID は design.md §6「B」の3行と完全一致。9仕入元・9チャネル・リンク290はすべて想定どおり。生ファイル: `.../scratchpad/cleanup-exec/post_state.txt`

## 4. 配信の比較

`run_dist_before.py` と同じ方法（`fetch_output_rows_captured.sql`、48h窓、`-c` 引数直渡し、`SET default_transaction_read_only=on`、ファイルを本番に置かない）で `dist_after.txt`（944行）を取得し、`dist_before.txt`（このセッションで再取得した最新の実行前基準値、同じく944行）と比較した。

```
$ diff dist_before.txt dist_after.txt
（差分なし、0行）
```

**結論: 配信の結果は実行前後で完全一致（差分0）。片付けによる配信への影響なし。**48時間窓の外への新規取り込みも今回の比較時点では発生していない。

## 5. design.md の状態

「本番実行済み（2026-09-30、PO が手動実行）」に更新（design.md 冒頭の状態行）。

## 6. 未確認事項

- PO の端末出力は要約として口頭（チャットメッセージ経由）で受領したものであり、実行担当自身が psql セッションの生ログ全文を取得したわけではない（本番への SSH 書き込みは PO のみが実行、実行担当は読み取り専用アクセスのみ）。DRY-RUN 実行時の詳細な行カウント出力（`RAISE EXCEPTION` の有無を含む生の psql セッションログ）は、PO の端末画面上にのみ存在し、本ログには転記できていない。
