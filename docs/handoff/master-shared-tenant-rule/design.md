<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 選択肢の表（マスタ）の「全社共用／会社独自」2層

**対象ADR**: ADR-1061（案・`docs/adr/ADR-1061-master-shared-and-tenant-values.md`）  
**recon**: `docs/handoff/master-shared-tenant-rule/recon.md`  
**日付**: 2026-11-05  
**担当**: Planner（Claude Opus）  
**状態**: 設計案作成済み。設計審査はまだ。PO の実装承認はまだ。実装は始めていない。

---

## 0. 目的（PO の言葉）

PO 要件（2026-11-05 チャット原文。recon §冒頭）:

- 全社共用の値は、運営側の管理画面で足す。各社から見ると初期値。
- 会社独自の値は、各社の画面（管理センター）で社長が足す。その会社の中でだけ表示され、使われる。
- LINE 解析から登録した値は、運営側の値として扱う。管理センターから登録した値は、会社独自の値として扱う。
- 各社は、全社共用の値を見られるが、編集できない。
- 会社独自の値は、LINE 解析では使わない。
- 範囲は選択肢の表だけ。商談・リード・注文などの業務データは、各社のまま。

利用者に見える変化:

- 社長が管理センターの単位・ステータス・商品区分・仕入元を開くと、全社共用の値が「共用」の印つき・編集不可で一緒に並ぶ。自社で足した値は編集できる。
- 社長が自社で足した値が、他社の画面と LINE 解析に出なくなる。
- リードに「流入元」の欄ができる。選べる値は共用の 7 つと、自社で足した値。「紹介」を選ぶと、紹介者を自社のリードから選べる。
- 連絡ツールの選択肢が、共用の 5 つ（Messenger・Instagram・WhatsApp・Discord・メール）と自社で足した値になる。電話・対面は初期値から外れる。

---

## 1. 設計の型（全部の選択肢の表に同じ型を使う）

前例は ADR-145（products）、ADR-SA-17（translation_glossary）、suppliers（`migrations/20261016_020000_add_suppliers_rls.sql:1-37`）。recon §1・§3。

| 決め事 | 中身 |
|---|---|
| 置き場所 | public の表 1 つ。会社の区画に写しを作らない（データを分散させない）。 |
| 持ち主の列 | `tenant_id`。空（NULL）は全社共用、数字は会社独自。 |
| 書ける人 | 共用の行は、運営の印（`app.is_operator='true'`）があるときだけ。会社の行は、その会社の接続（`app.tenant_id`）のときだけ。表の守り（FORCE ROW LEVEL SECURITY）の 4 つの決まりで、DB が強制する。決まりの文は suppliers と同じ文にする。 |
| 見える範囲 | 共用の行と、自社の行。他社の行は見えない（表の守りの SELECT の決まり）。 |
| 運営の印を立てる場所 | `backend/app/auth/dependencies.py:429` の `set_operator_context` だけ。commit の後に `reset_operator_context`（`:446`）で必ず戻す。 |
| LINE 解析が読む範囲 | 共用の行だけ。読む文に `tenant_id IS NULL` を必ず書く（表の守りに頼らない二重の守り。解析が会社の接続の中で動いた場合でも会社の行を拾わないため）。 |
| LINE 解析が書く値 | 共用の行（運営の印を立てて書く）。 |
| 管理センターが書く値 | 会社の行だけ（`tenant_id` = その会社）。共用の行を直す・消す要求は 403 で断る。 |
| 業務データが持つもの | 選択肢のコード（または行の番号）だけ。表示名を写さない。 |

---

## 2. 対象と対象外

### 2-1. 対象（今ある選択肢の表）

recon §2〜§5 の食い違い D1〜D8 を、この型に揃える。

| 表 | 今の守り | 会社側の一覧に共用が出るか | 会社側の書き込みの権限 | 解析が会社の行を読むか |
|---|---|---|---|---|
| line_conditions（状態ルール） | なし | 別枠で出る | conditions.* | 読む（D1） |
| line_units（単位） | なし | 出ない（D2） | suppliers.view だけ（D4） | 読む（D1） |
| tcg_note_master（備考） | なし | 出る | suppliers.view だけ（D4） | 読む（D1） |
| tcg_product_categories（商品区分） | なし | 出ない（D2） | product_categories.* | 読む（D1） |
| tcg_status_master（ステータス） | なし | 出ない（D2） | suppliers.view だけ（D4） | 読む（D1） |
| payment_fee_settings（決済手数料） | なし | 出る | suppliers.view だけ（D4） | 解析は読まない |
| suppliers（仕入元） | あり | 一覧は出ない（D2） | suppliers.* | 点検する |
| products（商品） | あり | 出る | products.* | 守りで共用＋接続中の会社 |
| 連絡ツール | 会社の区画に写し（D5） | 共用が無い | 管理センター | 解析は読まない |
| 流入元 | 表が無い（新設） | — | — | 解析は読まない |

### 2-2. 対象外（理由つき）

- 業務データ（リード・商談・注文・顧客）: PO「1」で各社のまま。
- 会社の列を持たない運営専用の表（product_formats・product_kinds・product_lines・quantity_units・weight_classes・line_unit_ignore_phrases・supplier_aliases・condition_definitions・link_templates）: 読み取りの道に会社の列つきで出ていない（AUDIT ts=2026-11-05T04:31:08Z sha=1e3a9d4cc0c0 rows=30 に含まれない）。管理センターに画面が無い。LINE 解析専用で、会社の値は解析で使わない要件のため、会社の層は作らない。共用だけのまま。
- 失注・成約理由（D6）: 管理する画面が無く、本番の件数も未確認（recon §7）。今回は型を当てはめず、残件にする（§9）。
- 会社の画面からの商品追加（D7）: 画面がメニューに無い（`frontend/src/App.tsx:230-232`）。今回は直さず残件にする（§9）。
- 発送地域・送料: 選択肢の表に入れるか未決（recon §7）。残件。
- 状態ルールの検索の名前違い（D8）: 別の作業で記録済み。今回は触らない。

---

## 3. 変更前と変更後

### 3-1. LINE 解析の読み取り（D1）

- 前: `backend/app/services/tcg_analyzer_svc.py:66-78` などで、条件を付けずに表を全部読む（recon §5。3 ファイルに `tenant_id` の文字 0 件）。
- 後: 解析が選択肢の表を読む文すべてに `tenant_id IS NULL` を付ける。対象は recon §5 の行と、scratch に残した 128 行の残り。実装の前に 1 行ずつ点検し、読む表と行番号の一覧を実装カードに載せる（§7 の S1）。
- 今の影響: 会社の行は 0 行（suppliers の 1 行を除く。recon §2）。だから解析結果は変わらない。受け入れ基準 K2 で、前後の解析結果が同じことを測る。

### 3-2. 表の守り（D3）

- 前: 6 つの表（line_conditions・line_units・tcg_note_master・tcg_product_categories・tcg_status_master・payment_fee_settings）に表の守りが無い（recon §3）。
- 後: 6 つの表に、suppliers と同じ文の 4 つの決まりを付ける。移行は 1 表 1 ファイル、冪等（`DROP POLICY IF EXISTS` → `CREATE POLICY`）。
- 同時に直さないと壊れる所: 運営画面の窓口 6 本（`backend/app/routers/super_admin_units.py`・`backend/app/routers/super_admin_conditions.py`・`backend/app/routers/super_admin_note_master.py`・`backend/app/routers/super_admin_status_master.py`・`backend/app/routers/super_admin_product_categories.py`・`backend/app/routers/super_admin_payment_fee_settings.py`）は、どれも運営の印を立てていない（`set_operator_context` の文字 0 件。scratch opctx・other_masters）。守りを付けると共用の行を書けなくなる。だから窓口 6 本に、書く前の `set_operator_context` と commit 後の `reset_operator_context` を、守りの移行と同じ便で入れる。
- 移行の文で共用の行を入れる場合は、`SET LOCAL app.is_operator = 'true'` を同じ取引の中で書く（前例: `migrations/20260914_140000_unify_tcg_products_to_public.sql`）。

### 3-3. 会社側の書き込みの権限（D4）

- 前: 単位・ステータス・備考・決済手数料の書き込みは、仕入元を見る権限（suppliers.view）だけで通る（recon §4）。この 4 つの表に専用の権限の名前は無い（scratch permkeys で 0 件）。
- 後: product_categories と同じ形で、専用の権限を足す。`units.view/edit/delete`・`status_master.view/edit/delete`・`note_master.view/edit/delete`・`payment_fee_settings.view/edit/delete`。社長（owner）は全部の権限を持ち、管理者（admin）は system.manage 以外を持つので、2 つの役は自動で持つ。ほかの役に配るかは、権限の作業（別の worktree の release-permission-keys-po-answers）の決め方に合わせる。

### 3-4. 会社側の一覧（D2）

- 前: 単位・ステータス・商品区分・仕入元の会社側の一覧は、自社の行だけ（recon §4）。
- 後: 4 つとも「共用の行＋自社の行」を返す。返事の各行に `is_shared`（tenant_id が空なら真）を付ける。画面は `is_shared` が真の行に「共用」の印を付け、編集・削除のボタンを出さない。備考・状態ルールも同じ印に揃える。
- 共用の行を直す・消す要求は、窓口が 403 で断る（今は自社の行だけを探すので 404。これを「共用は直せません」の 403 に揃える）。
- 画面の部品は既存の金型だけを使う（ADR-144）。文字は `t("key")`（ADR-027）。新しい印の部品が要るかは、実装カードで frontend/src/components を確かめて決める。

### 3-5. 流入元の表（新設）

- 前: 流入元の表も、リードの列も無い（recon §6）。商談に自由入力の列を足す変更がある（`migrations/096_add_deal_lead_source.sql`）が、どこからも読まれていない。本番に列があるかは未確認。
- 後:
  - 表 `public.lead_sources`（列: id・tenant_id・code・label_ja・label_en・sort_order・is_active・created_at・updated_at）。code は tenant_id ごとに重ならない（共用と会社で 2 つの一意の索引）。表の守りは §1 の型。
  - 共用の初期値 7 つ: Messenger・Instagram・WhatsApp・Discord・自社サイト・メール・紹介。コードは messenger・instagram・whatsapp・discord・website・email・referral。
  - リードの表に 2 列を足す: `lead_source_code`（流入元のコード）、`referrer_lead_id`（紹介者のリードの番号）。
  - 紹介者は、`lead_source_code='referral'` のときだけ入れられる。同じ会社のリードだけ選べる（リードは会社の区画の表なので、区画の中の外部キーにする）。自分自身は選べない。
  - 保存時の点検は、今の連絡ツールの点検（`backend/app/routers/leads.py:190-220`）と同じ形。「共用＋自社」の有効な値にだけ通す。
  - 商談の `lead_source`（自由入力）は使わない。本番に列があるかを確かめてから、消すか残すかを残件で決める（§9）。
- 運営側の追加画面: 運営の管理画面に、流入元と連絡ツールの共用の値を足す枠を作る（既存の運営画面の金型に合わせる）。
- 管理センターの画面: 流入元と連絡ツールの会社の値を足す枠。共用は印つき・編集不可。

### 3-6. 連絡ツールの共用化（D5）

- 前: 会社の区画ごとに表（`backend/app/services/tenant.py:1086`）があり、会社を作るときに初期値 6 つを写す（`backend/app/services/tenant.py:1584`、`backend/app/services/channel_masters.py:10-17`）。本番は 5 社×6 行＝30 行（recon §6）。
- 後:
  - 表 `public.channel_masters`（§1 の型）を新設する。共用の初期値 5 つ: messenger・instagram・whatsapp・discord・email（表示は Messenger・Instagram・WhatsApp・Discord・メール）。
  - 本番の 30 行の写しは、すべて今の初期値と同じ 6 行（recon §6）。会社が足した行は無い。だから会社の行として移す行は 0 行。phone・in_person を使うリードは 0 件。
  - 読む所・書く所（`backend/app/routers/conv_logs.py:190`・`:493-553`、`backend/app/routers/leads.py:190-220`、`frontend/src/components/ChannelTypeCombobox.tsx:44`）を新しい表に向ける。
  - 会社を作るときの写し（`backend/app/services/tenant.py:1584`）をやめる。
  - 会社の区画の古い表は、新しい表に切り替えて動きを確かめた後の便で消す（消すのは PO の GO が要る）。
  - `ACTIVE_CHANNEL_PLATFORMS`（`backend/app/services/channel_masters.py:19`）は、コードの初期値から作られている。これを使う所を実装の前に全部数え、新しい表を読む形に替える（§7 の S1）。
  - メールの `connection_type`（自動か手動か）の扱いは、今の表の列の意味を実装カードで確かめて決める（未確認）。

### 3-7. 古い値の整理（PO 回答どおり）

| 会社 | 今の値 | 直した後 | 根拠 |
|---|---|---|---|
| 001・006 | email 9 件 | 連絡ツール=email（メール） | PO「テナント001とテナント006は…整理して良い」 |
| 006 | referral 2 件 | 連絡ツール=空、流入元=referral、紹介者=空 | 同上 |
| 006 | sns 3 件 | 連絡ツール=空 | 同上 |
| 001・006 | unknown 43 件 | 連絡ツール=空 | 同上 |
| 004（HIGH LIFE JPN） | unknown 54 件 | 連絡ツール=空 | PO「1」（2026-11-05） |

- 直す前の値は、変更の記録（会社の区画の data_change 系の記録か、移行の前に取る写しの表）に、リードの番号と前の値で残す。どちらに残すかは実装カードで既存の記録の表を確かめて決める。
- 集計画面は空を unknown として数える（`backend/app/routers/analytics.py:992`・`:1746`・`:1767`）。だから集計の見え方は変わらない作り（コード読み。画面では未確認。K8 で測る）。
- 本番のデータを直すので、PO の `! bash scripts/permit-danger.sh "psql write"` と GO が要る。

---

## 4. 代替案と選んだ理由

| 案 | 中身 | 選ばない理由／選ぶ理由 |
|---|---|---|
| A（選ぶ） | public の表 1 つ＋持ち主の列＋表の守り | 前例 3 つ（products・suppliers・translation_glossary）と同じ。値が 1 か所。DB が守るので、窓口の書き忘れでも他社に漏れない。 |
| B | 会社の区画ごとに写しを持つ（今の連絡ツールの形） | 共用の値を直すと全社の写しを直す必要がある。値が分散する。PO の SSOT の条件に反する。 |
| C | 共用の表と会社の表を分ける | 読むたびに 2 つの表を合わせる必要がある。前例と違う形が増える。 |
| D | 窓口のコードだけで守る（表の守りなし） | 書き忘れ 1 か所で他社の値が見える。今の D1 がその例。 |

---

## 5. リスクと対処

| リスク | 対処 |
|---|---|
| 表の守りを付けた瞬間、運営画面 6 本が共用の行を書けなくなる | 守りの移行と、窓口 6 本の運営の印を同じ便に入れる。便の受け入れ基準 K4 で、運営画面から 1 行足して消すまでを本番で確かめる。 |
| 表の守りを付けた瞬間、運営の印なしで共用の行を書く処理（定期作業・スクリプト・移行）が止まる | 6 つの表へ書く処理を全部数えてから便を出す（§7 の S1）。今回、書く処理を数える検索は見張りに止められ、まだ数えていない（§8）。 |
| 運営の印が接続に残り、次の会社の要求が共用の行を書ける | 前例どおり commit の後に `reset_operator_context` を必ず呼ぶ。試験で「印を戻した後は書けない」を確かめる。 |
| 解析の読む文の付け忘れ | 解析の 3 ファイルで、選択肢の表を読む文に `tenant_id IS NULL` が無いものを数える点検を CI に足す（§10）。 |
| 連絡ツールの切り替えで、リードの保存が 422 で止まる | 新しい表に 5 つの共用の値が入ってから、読む所を切り替える順にする。古い値 email は新しい共用の値にあるので通る。 |
| 移行のロック待ち | ADR-1037 の 1 秒のロック待ちを守る。 |

---

## 6. 外部・過去事例の参照と我々への応用

- 過去事例 1: ADR-145（public.products の FORCE RLS）→ 我々への応用: 共用の行は運営の印だけが書ける、という同じ決まりの文を 6 つの表に使う。
- 過去事例 2: suppliers の表の守り（`migrations/20261016_020000_add_suppliers_rls.sql`、ADR-1018 の S1 段階②b）→ 我々への応用: 1 表 1 ファイル・冪等の移行の形をそのまま使う。
- 過去事例 3: ADR-SA-17（translation_glossary）→ 我々への応用: 運営の印を立てる道を `set_operator_context` の 1 か所にする。
- 外部事例: 該当なし。理由: 社内に同じ型の本番での前例が 3 つあり、本番で動いている（recon §3 の AUDIT）。外部の事例より直接の根拠になるため。数値の外部事例は使わない。

---

## 7. 便（届ける単位）と計画

1 便 1 テーマ。migration を含む便は PO の「GO #PR番号」が要る（ADR-135・ADR-136）。

| 便 | 中身 | migration | 担当 |
|---|---|---|---|
| S1 | 調べ物だけ: 6 つの表と流入元・連絡ツールに書く処理・読む処理を全部数える。`ACTIVE_CHANNEL_PLATFORMS` を使う所を数える。結果を recon に足す。 | なし | クラウドの Sonnet（調査） |
| 便1 | 決まりの記録（ADR-1061）を採用にする。LINE 解析の読む文に `tenant_id IS NULL` を付ける。CI の点検を足す。 | なし | クラウドの Sonnet（実装） |
| 便2 | 6 つの表に表の守り。運営画面 6 本に運営の印。会社側の 4 つの窓口の権限（§3-3）。 | あり | 同上 |
| 便3 | 会社側の一覧に共用の行を印つき・編集不可で出す（§3-4）。共用を直す要求は 403。 | なし | 同上 |
| 便4 | 流入元の表・初期値 7 つ・リードの 2 列・紹介者・運営と管理センターの枠（§3-5）。 | あり | 同上 |
| 便5 | 連絡ツールの共用の表・初期値 5 つ・読む所の切り替え・会社作成時の写しをやめる（§3-6）。古い値の整理（§3-7）。 | あり（＋本番データの変更） | 同上 |
| 便6 | 会社の区画の古い連絡ツールの表を消す。 | あり（表を消す） | 同上。PO の GO 必須 |

各便の実装カードは、便を出す前に Opus が書き、ADR-113 のカードの点検を通す。

---

## 8. 未確認（このままでは実装可にしない）

- 6 つの表に書く処理の全数。書く命令の文字を含む検索が見張りに止められ、まだ数えていない（2026-11-05）。S1 で数える。
- LINE 解析が会社の接続（`app.tenant_id`）の中で動くか。動かない場合、表の守りだけで共用の行だけになる。どちらでも §3-1 の二重の守りで足りる。
- 運営の窓口のうち、public.products を書く窓口（super_admin_aliases・super_admin_product_formats・super_admin_product_lines・super_admin_quantity_units・super_admin_weight_classes）が、今の products の守りで止まっていないか。読むだけか書くかは未確認。今回の範囲外だが S1 で一緒に数える。
- 本番の deals に lead_source の列があるか。
- 連絡ツールの `connection_type` の意味。
- 失注・成約理由の本番の件数。

---

## 9. 残件（今回の便に入れない）

- 失注・成約理由（D6）を同じ型にするか。
- 会社の画面からの商品追加（D7）を会社の行にするか。画面を出すかから PO が決める。
- 発送地域・送料を選択肢の表に入れるか。
- 商談の自由入力の流入元の列の扱い。

---

## 10. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K1: 6 つの表すべてで、表の守りと強制がオン、決まりが 4 つ | 本番の読み取りの道で pg_class.relrowsecurity・relforcerowsecurity と pg_policies の数を読む（AUDIT 行を残す）。期待: 6 行とも真・真・4 |
| K2: LINE 解析の結果が便1 の前後で同じ | 同じ投稿を前後で解析し、結果の行の数と値を比べる（正答率の測り方 ADR の手順）。期待: 差 0 件 |
| K3: 会社 001 で足した単位が、会社 006 の画面と LINE 解析に出ない | pytest（会社 2 つで足して読む）＋ テナント 001 の画面で Evaluator（Playwright） |
| K4: 運営画面から共用の単位を 1 行足して消せる。会社の接続からは共用の行を直せず 403 | pytest（運営の印あり・なしの両方）＋ 本番で運営画面から 1 行足して消す |
| K5: 管理センターの単位・ステータス・商品区分・仕入元に、共用の行が「共用」の印つきで出て、編集・削除のボタンが無い | Evaluator（Playwright、テナント 001） |
| K6: suppliers.view だけの人は、単位・ステータス・備考・決済手数料を書けない（403） | pytest |
| K7: リードの流入元の選択肢が共用 7 つ＋自社の値。紹介のときだけ紹介者を選べ、他社のリードは選べない | pytest ＋ Evaluator（Playwright、テナント 001） |
| K8: 連絡ツールの選択肢が共用 5 つ＋自社の値。電話・対面が出ない。集計画面の数が整理の前後で同じ | Evaluator（Playwright、テナント 001）＋ 集計の窓口の返事を前後で比べる |
| K9: 整理の後、リードの連絡ツールに一覧に無い値が 0 件。前の値が記録に 97+9+2+3 件残る | 本番の読み取りの道で値ごとの件数を数える（AUDIT 行を残す） |
| K10: 解析の 3 ファイルに、選択肢の表を `tenant_id IS NULL` なしで読む文が 0 件 | CI の点検（便1 で足す） |

---

## 11. 維持の仕組み

- 守り手: 表の守り（DB が強制）。窓口の書き忘れでも他社の値は見えない・共用は直せない。
- 守り手: CI の点検（便1 で足す。解析の読む文の `tenant_id IS NULL`）。ファイルの名前は便1 の実装カードで決める。
- 守り手: ADR-1061。新しい選択肢の表を作るときは、§1 の型に合わせることを ADR の What に書く。
- 守り手: 人手で守る（新しい選択肢の表の設計審査で、§1 の型に合っているかを審査役が確かめる）。

---

## 12. 設計審査（Architect）

- 状態: まだ。クラウドで審査を動かし、APPROVE／REVISE／REJECT と根拠をこの節に書く。
