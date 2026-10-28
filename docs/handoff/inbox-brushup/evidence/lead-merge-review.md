# リード統合（lead merge）の独立評価 — Fable 5.1

- 評価日時: 2026-10-28 22:50〜23:20 JST
- 評価者: Claude Fable 5.1（読み取り専用。ファイル変更・commit・push・PR・本番書き込みは行っていない）
- 根拠の読み方: コードは `origin/main`（commit 5b3162403964d8333a3dcb99dfde3c5d564bd84f）を `git archive` で写した `scratchpad/inbox-sample/main-src/` の行番号。本番 DB は reader 鍵の道（`ai_ro.*` ビュー・SELECT のみ）。個人情報は取らず、件数と id のみ
- 生出力: `/private/tmp/claude-501/-Users-tanizawashingo-salesanchor/6188646d-799b-417a-9c66-665f20bd0080/scratchpad/inbox-sample/lead-merge-fable-raw.txt`（末尾に scan1〜6・db1〜3・外部文書抜粋を連結）
- ラベル: 【事実】= 根拠あり（ファイル:行、SQL と件数、URL）／【推測】= 根拠から導いた見立て／【未確認】= 確かめられていない

---

## 0. 判定（要約）

**判定: 一部修正で妥当**

- 方式（手動で master/loser を選ぶ・自動の同一人物判定を組まない・副テーブルを付け替えて loser を消す）は ADR-098/095/119 と整合している【事実: §3】
- ただし実装は **lead_id を持つ 13 表のうち 4 表しか付け替えておらず**、特に `conversation_logs`（FK ON DELETE RESTRICT）を付け替えないため、**受信メッセージが 1 件でもあるリードを loser にすると DELETE が FK で止まり 500 になる**【事実: §1, §2-3】。本機能の中心用途（文言 `reasonPlaceholder`: 「Discord の新規受信を既存顧客に紐づけ」= 受信で自動作成された新リードを既存リードへ吸収）がまさにこのケースに当たる
- 本番では統合は **0 回**しか行われていない（`audit_logs` の `merge%` 0 件【事実: E10】）ので、今直せば被害は無い

---

## 1. lead_id を持つ全テーブル・ビュー・キャッシュと、merge 時の結果

### 1-1. 走査の範囲【事実】

- migrations 全文 grep + `backend/app/services/tenant.py` grep（raw: scan1, 374 行）
- 本番 tenant_004 の `pg_attribute`（lead_id 列を持つ relation。D2）、`pg_constraint`（leads を参照する FK の `confdeltype`。D5 = 全 5 テナント同一）、`pg_views`（D4）
- `confdeltype` の意味: a = NO ACTION, r = RESTRICT, c = CASCADE, n = SET NULL（PostgreSQL 16 `pg_constraint` 定義: https://www.postgresql.org/docs/16/catalog-pg-constraint.html）

### 1-2. 表【事実】（本番 tenant_004・2026-10-28 22:54 JST 時点の件数）

| # | 表／ビュー | lead_id NOT NULL | FK → leads の ON DELETE | merge が付け替えるか（leads.py 行） | loser を DELETE したときの結果 | 本番行数（tenant_004） |
|---|---|---|---|---|---|---|
| 1 | companies | NN（tenant.py:203） | a NO ACTION（tenant.py:448） | 付け替える（3073-3076） | master へ移る | 51 |
| 2 | contacts | NULL 可（tenant.py:241） | a NO ACTION（tenant.py:457） | 付け替える（3078-3081） | master へ移る | 0（lead_id 非 NULL） |
| 3 | meta_messages | NULL 可 | n SET NULL（tenant.py:1025 / migration 012） | 付け替える（3084-3087） | master へ移る | 24（非 NULL）/1（NULL） |
| 4 | lead_channels | NN | c CASCADE（tenant.py:1047 / 20260607_120000） | 重複は先に削除して付け替える（3093-3119） | master へ移る（同一窓口は master 側が残る） | 4 |
| 5 | **conversation_logs** | NN（20260703_020000） | **r RESTRICT**（20260715_100000:19-22） | **付け替えない** | **DELETE が FK 違反で失敗 → SQLAlchemyError → 500「データベースエラーが発生しました。」（main.py:796-803）。commit（3157）に達しないので全体が巻き戻り、監査ログも残らない** | 6（4 リード） |
| 6 | quotes | NN（tenant.py:798） | a NO ACTION | 付け替えない | 行があれば FK 違反で失敗（同上 500） | 0 |
| 7 | deal_close_reasons | NN（tenant.py:835） | a NO ACTION | 付け替えない | 行があれば FK 違反で失敗（同上 500） | 0 |
| 8 | lead_attachments | NN（20260902） | c CASCADE | 付け替えない | **黙って連鎖削除**（ディスク上の file_path は残り孤立） | 0 |
| 9 | lead_sales_form_selections | NN（20260614） | c CASCADE | 付け替えない | **黙って連鎖削除**（loser の販売形態の選択が消える） | 0 |
| 10 | message_labels | NULL 可（20260604_180000） | FK なし | 付け替えない | **孤児化**（存在しない lead_id を指す） | 0 |
| 11 | customer_scores | NN・UNIQUE(lead_id)（20260604_180000） | FK なし | 付け替えない | **孤児化** | 0 |
| 12 | outbound_translation_drafts | NULL 可（20260604_220000） | FK なし | 付け替えない | **孤児化** | 0 |
| 13 | public.registration_tokens | NN（20260604_080000） | FK なし（D6: tenant FK のみ） | 付け替えない | **孤児化**。verify 時 `SELECT name FROM companies WHERE lead_id=:lead_id`（registration_tokens.py:300-301）が空になり会社名が出ない | 5（tenant 4） |
| V | v_company_stats（ビュー） | — | — | — | `LEFT JOIN leads ON l.id = c.lead_id`（20260612_120000）。companies が付け替わるので追従する | — |
| C | ダッシュボードキャッシュ | — | — | `invalidate_dashboard_cache`（3158） | 無効化される | — |
| S | 即時反映（SSE） | — | — | `publish_leads_update` は呼ばれない（leads.py の呼び出しは 482/711/790 のみ。topics.py は `/leads/{master_id}/merge` を `_PENDING` に分類） | 開いている他の画面は更新されない | — |

- 現時点の孤児件数は 4 表とも 0【事実: E12】。これは統合が 0 回だから（E10）であり、仕組みで守られているからではない
- `delete_lead`（leads.py:760-790）も同じ FK 露出を持つ（単純 DELETE）。本評価の対象外だが同じ直し方が効く【事実】

### 1-3. ADR-119 との差分【事実】

- ADR-119 の手順（docs/adr/ADR-119:81-86）は guard = `loser.converted_deal_id IS NOT NULL`、付け替え = companies / contacts / deals / meta_messages / lead_channels。実装は guard = `status != 'lead'`（leads.py:3064）、deals は表ごと廃止済み（migrations 20260729）。ADR-119 は 2026-06-07 付で、`conversation_logs` の FK（2026-07-15）より前に書かれており、以後改訂されていない（Status「Accepted（実装中）」のまま、1 行目〜3 行目）
- ADR-119:57「lead 新規作成時は同一トランザクション内で `lead_channels` にも INSERT する」に対し、`create_lead`（leads.py:401-490）は `lead_channels` に書かない【事実】

---

## 2. 52 リードに lead_channels が無い理由

### 2-1. 事実【事実】（tenant_004）

- leads 56 件、全部 status=lead（E1）。lead_channels 4 行／4 リード（discord 2・instagram 1・messenger 1。E2）。2 窓口以上のリードは 0（E3）
- lead_channels の無い 52 件は全部 channel_type='unknown'（E4）
- 作成時刻の分布（E20・UTC）: 2026-06-08 04:02 に 1 件、2026-06-08 06:17 に 1 件、**2026-07-02 17:18 に 49 件**、2026-07-03 04:15 に 1 件
- 52 件中 51 件に companies が紐づき、**49 件の notes に「便1a」の印**がある（E19）。leads の email/phone/country は全 56 件で空（E15）
- 52 件中 discord_user_id を持つものは 0（E5）。meta_messages を持つのは 1 件（id=38）だけで、その platform は 'phone'（手入力）、同じ送り主が lead_channels に別リードで居ることも無い（E18）

### 2-2. 発生経路【事実】

1. **49 件 = migration `20260703_010000_txn_backbone_ben1a.sql`** が作った。lead_id の無い company 1 社につき lead を 1 件作り（raw4 の全文 24-29 行: `INSERT INTO %I.leads (tenant_id, customer_name, company_name, status, notes) ... '[便1a] 遡及作成: ...'`）、`lead_channels` には何も書かない。作成時刻が 1 分内に 49 件そろっていること・notes の印 49 件・companies 紐づき 51 件がこれに一致する
2. **2026-06 の 2 件**: `create_lead`（POST /leads、leads.py:401-490）は leads にしか INSERT せず lead_channels を書かない。Meta webhook（webhook.py:583-700）と Discord（dm_writer.py:48-170、ticket_channel_creator.py:113-130）は必ず lead_channels を書く（`_ensure_lead_channel` / `INSERT ... ON CONFLICT DO NOTHING`）ので、この 2 件は webhook/Discord 経路では作られていない。id=38 は 'phone' の手入力メッセージ（E18）と会話ログ 1 件（E22）を持つ
3. **2026-07-03 04:15 の 1 件**（印なし・会社あり）: 作成経路は【未確認】（audit_logs の create 行を引けば分かるが、個人情報列を避けるため今回は引いていない）
4. **埋め戻しは 1 回だけ**: `20260613_030000_funnel_leads_initiative_channel.sql:55-65` が `leads.source` の `instagram:<id>` / `messenger:<id>` 形式から lead_channels を作って source を DROP した。それ以外に lead_channels を埋める migration は無い（scan1 grep）。便1a 由来の 49 件は外部 ID を持たないので、埋め戻し対象になり得ない

### 2-3. 受信時の自動寄せがこの 52 件にどう効くか【事実】

- Meta 受信: `_persist_meta_message`（webhook.py:583-700）は **lead_channels だけ**で既存リードを探し（Stage 1）、無ければ新規 lead + lead_channels を INSERT する（667, 691-696）。名前や leads の列での照合（Stage 2）は無い
- Discord 受信: dm_writer.py:105-167 も lead_channels を一次権威にし、無ければ新規 lead を作って lead_channels を書く（Stage 2 は「lead_channels 表が無い」ときだけの保険 124-126）
- したがって **52 件は今後も受信で自動的には結び付かない**。同じ人から届けば必ず新しいリードが 1 件増え、人が「統合」で寄せる以外に道が無い
- さらに受信時は **inbound を conversation_logs にも書く**（Meta: webhook.py:875-885 `write_conversation_log` / Discord: dm_writer.py:231-243）。よって受信で生まれた新リード（= 統合で消したい側）は原則 conversation_logs を 1 件以上持ち、§1 の RESTRICT で統合が 500 になる
- 【未確認】本番で meta_messages 24 件に対し conversation_logs が 6 件しか無い理由（Stage 1 配線前のメッセージか、書き込み失敗が warning で握りつぶされたか。webhook.py の try/except は warning のみ）
- 【推測】52 件の実害: 便1a 由来 49 件は「会社の出自リード」として作られた箱で、連絡窓口 ID を元々持たない。これらに窓口を足す手段は、今は「受信で生まれた新リードを master=この 49 件のどれかに統合する」だけであり、その統合が §1 で止まる

---

## 3. 今の方式は ADR と SSOT に照らして妥当か

| 観点 | ADR の決まり（根拠） | 今の実装 | 評価 |
|---|---|---|---|
| 手動で寄せる | ADR-098:25「完全自動の同一人物判定は前提にしない（手動紐付け or 本人申告が現実解）」、同:61「名寄せに自動同一判定を組まない」 | 人が master/loser を選んで POST（MergeLeadModal.tsx:118） | **妥当** |
| 項目を写さない | ADR-095:25-30「同じ事実の保管庫は 1 か所」「コピー保存しない。参照（ID）で持つ」 | loser の属性は master に写さず、loser 行の全列を audit_logs.old_data に残す（leads.py:3151-3155） | **妥当**（スナップショットは二重持ちと別物。ADR-095:26-27）。ただし監査ログを見る画面は無い（raw4: GET /audit-logs 系 API なし・frontend に merged_into 参照なし）ので、写さなかった値は実務上「消えた」のと同じ |
| 物理削除 | ADR-096:35「顧客マスタ＝背骨①・永続」、20260715 migration:3「取引データ永久保存の方針・§11 ソフトデリート予約」 | loser を DELETE（leads.py:3123） | **一部不整合**。leads は companies/conversation_logs の背骨（companies.lead_id NOT NULL・conversation_logs.lead_id NOT NULL）であり、設計はソフトデリートを「予約」している。ただし §4 のとおり、副テーブルを全部付け替えた上での物理削除は Salesforce も採る形で、規模（統合 0 回・リード 56 件）では許容範囲 |
| loser は status=lead 限定 | ADR-119:66 は `converted_deal_id IS NOT NULL` → 400。deals 廃止後の等価が `status != 'lead'` | leads.py:3064 | **妥当だが ADR 未改訂**。negotiating/existing_customer を loser にできないのは安全側 |
| ライフサイクル | ADR-089:74「leads → companies → deals」、companies.lead_id NOT NULL（ben1a） | companies を master へ付け替える | **妥当** |
| 付け替えの網羅 | ADR-119:81-86（5 表） | 4 表のみ。conversation_logs ほか 9 表が漏れ | **不整合**（§1） |
| 受信 ID の SSOT | ADR-098:28「保存するのは ID のみ」、ADR-119:100「lead_channels が lookup 権威」 | 重複窓口は master 側を残す（3093-3119） | **妥当** |
| 試験 | — | backend/tests 375 ファイル中、リード/会社/担当者の統合を試す試験は 0（raw5: grep 結果は在庫系のみ） | **欠落** |

結論: 「手動・写さない・loser は lead 限定」は妥当。「物理削除」は付け替えを完全にすれば妥当。今は付け替えが不完全なので **一部修正で妥当**。

---

## 4. もっと良い方式があるか（Salesforce / HubSpot との比較）

### 4-1. 外部製品の事実

**HubSpot**【事実】（https://knowledge.hubspot.com/records/merge-records を 2026-10-28 23:05 JST に HTTP 200 で取得。抜粋は raw の docs-extract）
- 2 件ずつ統合。「once you've merged two records, it is not possible to unmerge them」
- 既定では「a new unique Record ID is created for the resulting merged record」。元 ID は「Merged [record] IDs」プロパティに残る。β「Primary ID Preservation」では primary の ID を保つ（「This prevents APIs and webhooks that rely on Record IDs from breaking」）
- 項目は「the primary record's property values are prioritized」「If the primary record does not have a value for a property (e.g., null, empty) the secondary record's value is used」。画面で項目ごとに選べる（「click the values you want to keep」）
- 「all timeline activities of both records ... will appear on the new record」「all associated records of both records ... will appear on the new record」
- 「the secondary contact's email address is permanently associated with the primary contact」（= 消した側の連絡先 ID を残す側に足す。本件の lead_channels 付け替えと同じ考え方）
- 「you cannot merge records if they've been included in a combined total of 250+ merges」
- 開発者向け: 2025-01-14 以降の統合では旧 ID でも統合後レコードが返る（changelog）【未確認: developers.hubspot.com/changelog/updated-merge-functionality-for-contacts-and-companies は 404、検索エンジンの抜粋のみ】

**Salesforce**【未確認（原文を直接閲覧できず）】
- 公式ページ https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/sforce_api_calls_merge.htm と https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_lead.htm は WebFetch・curl（ブラウザ UA）とも HTTP 403、help.salesforce.com は JS 読み込み画面のみ、web.archive.org は取得不可。以下は検索エンジンが同 URL から引いた抜粋であり、原文照合はできていない
- merge() は 1 回に最大 3 件（master 含む）、対象は Lead / Contact / Account、非 master（victim）は削除され、`queryAll()` で `isDeleted = true AND masterRecordId != null` として引ける（= 消した側に「統合先」を指す `MasterRecordId` が残る）
- 画面では master を選び項目ごとに残す値を選ぶ。消した側はごみ箱（Recycle Bin）から一定期間戻せる（第三者記事: 15 日。公式未確認）

### 4-2. 3 方式を今の規模（tenant_004 56 件・tenant_006 74 件・統合 0 回・lead_id を持つ表 13）に当てはめる

| 方式 | 利点 | 弊害 | 本件での評価 |
|---|---|---|---|
| A. 物理削除 + 全副テーブル付け替え + 監査に統合先を残す（今の方式の完成形。Salesforce の victim 削除 + MasterRecordId に近い） | leads を読む全クエリ・全画面を変えなくてよい。SSOT は 1 か所のまま。schema 変更なし | 戻すには監査ログから手で復元。消した id を開くと 404 | **適合**。変更は leads.py 1 関数 + 試験 + 文言。戻し方はコードの revert だけ |
| B. 論理削除（leads.merged_into_lead_id を足し、消さない） | 旧 id で統合先へ転送できる（HubSpot の旧 ID 解決と同じ）。取消が容易 | leads を読む全経路（一覧・受信箱・stats・v_company_stats・webhook の lookup・RLS 試験）に `merged_into IS NULL` の条件を足す必要があり、漏れれば幽霊リードが出る。companies.lead_id NOT NULL などの背骨は結局付け替えが要るので A の作業は減らない。status CHECK・ADR-109 の見直しも要る | 今の規模では **過剰**。将来 API/webhook が lead id に依存する外部連携が増えたら再検討 |
| C. 項目ごとに値を選ばせる（Salesforce/HubSpot の画面） | 人が見て選べる | 画面を新造（比較表 + 列ごとの Radio）。leads の列は 40 以上（_LEAD_COLUMNS leads.py:65-86）。本番 56 件は email/phone/country が全件空（E15）で、選ぶ値がほぼ無い | 今は **不要**。代わりに「master が空の項目だけ loser の値で埋める」（HubSpot の既定動作）をサーバー側で決定的に行えば、画面なしで同じ効用の大半が得られる |

---

## 5. 推奨案（1 つ）

**推奨: 方式 A。今の `merge_leads` を「lead_id を持つ 13 表を全部付け替えてから loser を消す」形に直し、試験を足し、ADR-119 を改訂する。schema 変更なし。画面は確認文言だけ直す**

### 5-1. 変更内容と根拠

1. `backend/app/routers/leads.py` `merge_leads`（2996-3168）
   - 付け替えを追加: conversation_logs（RESTRICT のため **DELETE 前に必須**）、quotes、deal_close_reasons、message_labels、outbound_translation_drafts、lead_attachments（CASCADE に任せず UPDATE）、`public.registration_tokens`（tenant_id = 当該テナントの行）
   - 一意制約のある表: lead_sales_form_selections は master に同じ選択があれば loser 側を捨ててから UPDATE（lead_channels と同じ手順 3093-3119）。customer_scores は UNIQUE(lead_id) なので master に行があれば loser 行を削除、無ければ UPDATE
   - 任意（PO 判断 §6-2）: master の列が NULL/空の項目だけ loser の値で埋める（HubSpot 既定。対象は `_UPDATABLE_COLUMNS` leads.py:88-99 の範囲、status/prospect_rank は除外）
   - 監査: `merge_summary` に各表の付け替え件数を追加（既存の形 3136-3144 に項目を足すだけ）
   - 同じ付け替え手順を `delete_lead`（760-790）でも使うかは本件の範囲外（§6）
2. 試験 `backend/tests/test_lead_merge_pg.py`（新規）: 13 表それぞれに loser 行を 1 件置いて統合 → 200・各表の lead_id=master 件数・孤児 0・lead_attachments 行数不変・audit 2 行・自己統合 400・status≠lead 400・存在しない id 404
3. `docs/adr/ADR-119`: Status を Accepted に、guard を `status != 'lead'` に、付け替え表を 13 表に、「lead 新規作成時に lead_channels を書く」(57 行) は手入力リードには外部 ID が無い事実（E5/E15）に合わせて「窓口 ID を持つ経路のみ」に書き直す
4. 文言 `frontend/src/locales/ja.json:2343`（en.json も）: 「メッセージ・チャンネル情報」→「会話ログ・見積・添付・取引先など、このリードに結び付く情報すべて」

### 5-2. 影響範囲

- ファイル: `backend/app/routers/leads.py`、`backend/tests/test_lead_merge_pg.py`（新規）、`docs/adr/ADR-119-*.md`、`frontend/src/locales/ja.json`、`frontend/src/locales/en.json`。呼び出し元は `frontend/src/components/MergeLeadModal.tsx:118` の 1 か所のみ（grep: raw5）。API の入出力は変えない
- 表: §1-2 の 13 表（読み書きは UPDATE/DELETE のみ、列追加なし）。migration なし
- 画面: 新しい部品は不要。既存の Modal / Button / RadioControl / TextareaControl / LoadingBlock（MergeLeadModal.tsx:22-27）とトークン `var(--warning-bg)` 等（同:160-166、tokens.css:576-577）で足りる。項目選択画面（方式 C）を将来作る場合も RadioControl（frontend/src/components/RadioControl.tsx）と DataTable（同 DataTable.tsx）で組める

### 5-3. 戻し方

- schema 変更が無いので、PR の revert だけで前の挙動に戻る。統合済みデータは audit_logs の `merge_absorb` / `merge_delete`（old_data に loser 全列）から手で復元できる（現状と同じ）

### 5-4. 数で判定できる受入条件

1. 試験: 新規試験ファイルの全ケース（13 表 + 異常系 3）= **16 件が PASS**、CI 緑
2. 統合後、次の 4 表の孤児 lead_id が **0**（E12 と同じ SQL）: message_labels / customer_scores / outbound_translation_drafts / registration_tokens
3. conversation_logs を持つリードを loser にした統合が **200** を返し、`conversation_logs WHERE lead_id = master` の件数が「統合前 master 分 + loser 分」に一致
4. lead_attachments / lead_sales_form_selections の総行数が統合前後で **不変**（CASCADE が発火していない）
5. audit_logs の `merge_absorb` + `merge_delete` が統合 1 回につき **2 行**
6. 本番: 最初の実統合 1 回の後に 2〜5 を reader 鍵の道で測って全て合格

---

## 6. 確かめられなかった点・PO に決めてもらう点

### 6-1. 未確認【未確認】
- Salesforce 公式文書の原文（403 のため検索抜粋のみ。§4-1）
- 2026-07-03 04:15 作成の 1 件の作成経路（§2-2-3）
- meta_messages 24 件に対し conversation_logs が 6 件しか無い理由（§2-3）
- 500 時にセッションが rollback される経路の実装（commit に達しない事実から「残らない」とは言えるが、`get_db` の後始末は読んでいない）
- tenant_006（leads 74 件）の lead_channels の有無（今回は tenant_004 のみ集計）

### 6-2. PO に決めてもらう点
1. 推奨案（方式 A）で進めてよいか
2. 「master が空の項目だけ loser の値で埋める」を入れるか（入れないと写さない現状のまま）
3. FK の無い 4 表（message_labels / customer_scores / outbound_translation_drafts / public.registration_tokens）に将来 FK を足すか（migration と ADR が要る。今回の推奨案には含めない）
4. 便1a 由来の 49 件（窓口 ID なし）は、受信で生まれた新リードを人が統合するまで結び付かない。この運用でよいか、別途「窓口 ID を手で登録する画面」を作るか
5. `delete_lead` にも同じ付け替え／ブロックを入れるか（今は conversation_logs があるリードは削除も 500 になる）
