---
mode: handoff
---
# 実装カード A: 成約しやすさの計算・分析の入口・テスト用データの作り方

親: [design.md](./design.md)（第11版）§2〜§6・§9

この文書は何か: リードの項目と返信の速さで「成約しやすさ」を計算する仕組み（標準ライブラリだけ）と、その読み取りの入口、答えを仕込んだテスト用データを作る道具、本番に流す SQL・消す SQL を作るための作業指示です。

- 状態: カード作成済み・カード自己審査済み（§9）・PO 実装承認 済（2026-11-01「PRマージ、デプロイまで完走させてくれ」）・クラウドの Sonnet へ実装依頼
- 担当: Sonnet（クラウドで実装〜push まで）。PR は Opus が手元で shingo-cc 名義で起票。審査・マージ判断は Opus。
- 画面（frontend）はカード B が別の枝で作る。応答の形（§3）は両方のカードで同じものを使う。変えない。
- 本番の DB には触らない。本番への書き込みは Opus が後で行う（§7 の道具を使う）。

## 読んだ節と照合（Opus、2026-11-01）

- docs/handoff/design-partner-card-ops/guards/00-common.md: プレースホルダを残さない（パス・名前・値はすべて実名）・報告は数だけ・報告に無い出力を成功と扱わない。○
- docs/handoff/design-partner-card-ops/guards/03-file.md・docs/handoff/design-partner-card-ops/guards/05-pr.md: 触るファイルを §1 で全部挙げた。PR は手元で shingo-cc 名義（Sonnet は push まで）。○
- docs/handoff/design-partner-card-ops/guards/10-executor.md: 散文で組み立てを頼まない（§2〜§7 で形・値・期待値を書いた）。○
- 第10版の設計審査の補足2・3と、Fable の評価の追加注意9件（どちらも Opus の手元の記録。リポジトリには無い）を §2〜§8 に写した（§9 に対応表）。
- 受領確認: 着手前に、報告の1行目へ「受領確認: card-a-backend を読んだ」と書く。

## 0. 本番の事実（Opus が 2026-11-01 08:03〜08:04 JST に読み取りの道で確かめた）

- tenant_001 の tenant_id は 1（tenant_001__leads の tenant_id は 1 だけ。public__tenants の id 1 は tenant_code test-corp）。
- tenant_001__leads は 2件（id 4・6）。lead_code が `TLR-` で始まる行は 0件。
- tenant_001__tenant_sales_form_options は 0件。
- tenant_001__close_reasons: type lost が 8件（id 8〜15、sort_order 1〜7 と 99）、type won が 7件。
- tenant_001__deal_close_reasons は 0件（表はある）。
- tenant_001__channel_masters の platform: messenger・instagram・discord・phone・in_person・whatsapp（すべて有効）。
- tenant_001__meta_messages は 4件（lead_id 4、platform discord）。direction 列の値は inbound / outbound。

## 1. 作るもの・触らないもの

作る・変える（これ以外は触らない）:

1. `backend/app/services/lead_conversion_factors.py`（新規）: 特徴を作る関数と、ロジスティック回帰（標準ライブラリだけ）。本番の入口と本番の外の確かめ（K3）の両方がこれだけを使う。
2. `backend/app/schemas/lead_conversion_factors.py`（新規）: 応答の型（§3）。
3. `backend/app/routers/analytics.py`（追記）: 入口 GET `/analytics/lead-conversion-factors` を1つ。
4. `scripts/lead_regression/generate.py`（新規）: テスト用データの作り方の正本（§4）。行のデータ（Python の辞書の並び）を返す関数と、本番に流す SQL を書き出す道具。
5. `scripts/lead_regression/k3_run.py`（新規）: 本番の外の確かめ K3a〜K3c と、K3d の比べる側の値を出す道具（§6）。
6. `scripts/lead_regression/check_sql.py`（新規）: 書き込みの SQL の機械の点検 K5①(a)（§5-3）。
7. `scripts/lead_regression/README.md`（新規）: 流し方（§4〜§7 のコマンド）だけ。
8. `docs/handoff/lead-regression/sql/delete_tenant_001.sql`（新規）: 消す SQL（§5-4）。
9. 試験（新規）: `backend/tests/test_lead_conversion_factors.py`（計算と特徴の試験）、`backend/tests/test_lead_regression_generate.py`（作り方・SQL の点検の試験。`scripts/lead_regression/` を import する）。CI の pytest で毎回流れる場所に置く。

触らないもの: `frontend/`・`migrations/`・`.github/`・`backend/requirements*.txt`（statsmodels・numpy を足さない）・既存の入口 `/analytics/conversion-by-attribute`（design §10 の食い違いは直さない）・ほかのすべてのファイル。DB への書き込みはしない。

## 2. 計算の決まり（`backend/app/services/lead_conversion_factors.py`）

### 2-1. 入力の形（本番の入口も K3 も同じ形に揃えてから渡す）

- `LeadRow`: `id`(int)・`status`(str)・`initiative`(str|None)・`channel_type`(str|None)・`country`(str|None)・`temperature`(str|None)・`estimated_scale`(str|None)・`customer_type`(str|None)・`competitor_check`(bool)・`sales_form_values`(list[str]。そのリードが選んだ店舗の形の value。選択が無ければ空)
- `MessageRow`: `lead_id`(int)・`id`(int)・`direction`("inbound" / "outbound")・`ts`(timezone 付き datetime)
- 値の綴りは `backend/app/schemas/lead.py` の列挙から取る（LeadStatus 31行・LeadTemperature 47行・LeadScale 53行・LeadCustomerType 59行）。文字を新しく直書きしない（Fable 注意2）。channel_type は channel_masters の platform の値（messenger・instagram・whatsapp）。

### 2-2. どのメッセージを読むか（design §4-1）

- channel_type が instagram・messenger のリード: そのテナントの meta_messages の `lead_id` が一致し `deleted_at IS NULL` の行。時刻は `created_at`。
- channel_type が whatsapp のリード: conversation_logs の `lead_id` が一致し `deleted_at IS NULL` の行。時刻は `occurred_at`。受信・送信の列の名前と値は migrations の conversation_logs の定義から読んで合わせる（推測で決めない。合わなければ `BLOCKED: 会話の記録の向きの列が分からない`）。
- 並び: 時刻の昇順、同じ時刻は id の昇順（design §4-4 の3）。

### 2-3. 1つのリードの値

- こちらの最初の返信までの時間: 最初の inbound の時刻から、それより後ろ（並びで後ろ）の最初の outbound の時刻までの秒数。こちらから営業したリードも同じ決まり（PO 2026-11-01 ②）。
- 相手の返信までの時間の平均: 並びで「すぐ前の行が outbound である inbound」それぞれについて、その outbound からの秒数を出し、算術平均する。
- やり取りの回数: 読んだ行の数（inbound と outbound の合計）。
- 2値にする区切り: 「早い最初の返信」は 3600秒以下（≦）、「早い相手の返信」は 21600秒以下（≦）（design §4-4 の3）。

### 2-4. 外す決まりと外した件数（応答の `excluded`。上から順に当て、最初に当たった1つだけに数える）

1. `by_status`: status が existing_customer・lost のどちらでもない。
2. `other_values`: channel_type が messenger・instagram・whatsapp 以外、または country が US・GB・AU 以外か空、または temperature が空、または initiative が inbound・outbound 以外か空（第11版で足した決まり。本物の値の扱いは design §9 の表で本物に切り替える前に決め直す）。
3. `no_inbound`: inbound が 0行（送信だけ）。
4. `no_outbound`: outbound が 0行（受信だけ）。
5. `no_reply_pair`: inbound も outbound もあるが、最初の返信か相手の返信の平均のどちらかが計算できない。
6. `no_sales_form`: `sales_form_values` が空。
7. `missing_scale_or_type`: estimated_scale か customer_type が空。

- 店舗の形: `sales_form_values` に `wholesale` を含めば卸（PO 2026-11-01 ⑤。other_text は読まない）。
- 相見積もりは空を許さない列なので外す決まりは無い。

### 2-5. 15項目（この順・この名前で固定。カード B も同じ）

| key | 1 になる条件（基準は 0） |
|---|---|
| initiative_inbound | initiative が inbound（基準 outbound） |
| sales_form_wholesale | 店舗の形が卸（基準 卸以外） |
| first_reply_within_1h | 最初の返信が 3600秒以下 |
| partner_reply_within_6h | 相手の返信の平均が 21600秒以下 |
| channel_whatsapp | channel_type whatsapp（基準 messenger） |
| channel_instagram | channel_type instagram（基準 messenger） |
| country_gb | country GB（基準 US） |
| country_au | country AU（基準 US） |
| temperature_hot | Hot（基準 Cold） |
| temperature_warm | Warm（基準 Cold） |
| message_count | やり取りの回数そのもの（整数。1 増えるごとの強さ） |
| scale_large | Large（基準 Small） |
| scale_medium | Medium（基準 Small） |
| customer_type_trust | 信頼重視（基準 価格重視） |
| competitor_found | competitor_check が true（基準 false） |

- 成約（目的の値 1）は status が existing_customer。lost は 0。
- 説明の行列は 定数1 の列 ＋ 上の 15 列。行の順は lead の id の昇順（K3d のため）。

### 2-6. ロジスティック回帰（標準ライブラリだけ）

- 方法: ニュートン法（IRLS と同じ）。初期値は全係数 0。
- 1回の更新: 勾配 g = Xᵀ(y − p)、ヘッセ H = Xᵀ W X（W = p(1−p)）、β ← β + H⁻¹ g。逆行列は部分ピボット付きのガウス・ジョルダン法（自前、`fractions` 不要・float で）。
- 収束: 更新の大きさの最大の絶対値が 1e-10 以下。上限 100 回。
- 計算できない（design §4-4 の7）: 上限まで収束しない、ヘッセの逆行列が作れない（ピボットの絶対値が 1e-12 以下）、どれかの |β| が 20 を超える、のどれか。このとき例外で落とさず、全項目を `computable: false`・値を null で返す。
- 標準誤差: 収束した β で作った H⁻¹ の対角の平方根。
- 強さ（オッズ比）＝ exp(β)、95%の幅 ＝ exp(β ± 1.959963984540054 × 標準誤差)（statsmodels の conf_int と同じ正規分布の 0.975 点）。
- 差があると言えるか: 幅が 1 を含まない（ci_low > 1 または ci_high < 1）。
- 丸めない: 入口は float をそのまま返す（Fable 注意5）。丸めは画面だけで行う。

### 2-7. 件数の決まり

- 回帰に使えたリード（§2-4 で外れなかった）で、min(成約, 失注) ÷ 15 ≧ 10 なら計算する。満たさなければ `status: "insufficient"`・`items: []`。

## 3. 入口と応答の形（カード B と共有。変えない）

- `GET /analytics/lead-conversion-factors`、権限は `dependencies=[Depends(require_permission("dashboard.view"))]`（`backend/app/routers/analytics.py:1108`〜1111 の conversion-by-attribute と同じ書き方。db・tenant_id の受け取りも同じ形）。読むだけ。書き込みはしない。
- 読む表は、そのテナントの leads・lead_sales_form_selections（tenant_sales_form_options と結んで value を得る）・meta_messages・conversation_logs だけ。テナントの切り替えは既存の入口と同じ仕組みに任せ、表の名前にスキーマを直書きしない。
- 応答（`backend/app/schemas/lead_conversion_factors.py`）:

```json
{
  "status": "ok",
  "included_count": 470,
  "won_count": 150,
  "lost_count": 320,
  "required_per_item": 10,
  "item_count": 15,
  "excluded": {
    "by_status": 2, "other_values": 0, "no_inbound": 0, "no_outbound": 0,
    "no_reply_pair": 0, "no_sales_form": 0, "missing_scale_or_type": 0
  },
  "items": [
    {"key": "initiative_inbound", "odds_ratio": 2.03, "ci_low": 1.31, "ci_high": 3.14,
     "significant": true, "computable": true}
  ]
}
```

- `status` は `"ok"` / `"insufficient"` / `"not_computable"`（§2-6 の計算できない）。`"ok"` のとき items は §2-5 の順で 15個。それ以外は `[]`。
- 試験: 権限が無いと 403、テナントにリードが無いと `insufficient` と件数 0、作り物の DB データで値が §2 の関数を直接呼んだ値と完全に同じ。既存の analytics の試験（`backend/tests/test_analytics.py`・`backend/tests/test_analytics_conversion_by_attribute_rls.py`）の作り方に合わせる。

## 4. テスト用データの作り方（`scripts/lead_regression/generate.py`。作り方の正本はここ1か所。design §4-4 の5）

- 関数 `generate(seed: int, base_date: datetime.date) -> Dataset`。`random.Random(seed)` 1つだけを使い、同じ seed・base_date なら同じ結果。Dataset は §2-1 の LeadRow・MessageRow の並びに、SQL に要る列（lead_code・時刻・本文・失注理由の順番 等）を足したもの。
- 件数 470。項目は互いに無関係に、それぞれ別々に割り振る。割り振りは「決まった数の値を並べた表を rng.shuffle する」形で、端数の配り先は rng で決める:
  - initiative: inbound 235・outbound 235
  - 店舗の形（value）: wholesale 141、physical_store・ec_site・live_streaming・other の4つで残り 329 を 82・82・82・83 に（どれが 83 かは rng）
  - 最初の返信: 3600秒以下 235・遅い 235／相手の返信: 21600秒以下 235・遅い 235／顧客タイプ: 235・235／相見積もり true 235・false 235
  - channel_type・country・temperature・estimated_scale: 3つの値を 157・157・156（どれが 156 かは rng）
  - やり取りの回数: 4〜20 から rng.randint で1件ずつ
- 仕込む強さ（log をとって足す。design §3-2 の表）: #1 2.0、#2 2.5、#3 1.8、#4 1.6、#5 1.5、#6〜#11 1.0、#12 1.7、#13 1.0、#14 1.8、#15 0.6。この表は generate.py の定数1か所だけに置く（画面にも入口にも書かない。design §4-3）。
- 成約をちょうど 150件にする（design §3-2）: 基準の高さ b0 を二分法で求め、確率の合計が 150 になるようにする（誤差 1e-9）。各リードの成約を rng.random() < p で決め、合計が 150 でなければ成約の乱数だけを引き直す（項目はそのまま）。引き直しの回数を Dataset に記録する。
- メッセージ: 相手から来たリードは inbound から、こちらから営業したリードは outbound から始め、受信と送信を交互に、やり取りの回数だけ作る。最初の時刻は base_date の 180日前〜70日前（00:00 UTC 起点の秒で一様）。間の取り方は design §3-2 の2つ目と3つ目の点のとおり（最初の返信は 60〜3540秒か 3660〜172800秒、相手の返信は 300〜21600秒か 21660〜259200秒、それ以外のこちらの送信は 300〜86400秒）。秒は整数。最後のメッセージが base_date の 2日前より前にあることを assert する。
- 本文: 実在の人名・会社名・仕入元を含まない英語の定型文（例 `Hello, I am interested in your products.`）を、受信と送信で数個ずつ用意して順に使う。
- 目印（Fable 注意9）: lead_code `TLR-00001`〜`TLR-00470`、customer_name も同じ文字。lead_channels.external_id `tlr-psid-00001`、meta_messages.message_id と conversation_logs.external_message_id は `tlr-s` ＋種の数＋ `-m` ＋6桁の連番（本番の種なら `tlr-s20261101-m000001`）（seed を含めて、種を変えたデータどうしでも重ならない）。
- 失注の理由: 失注のリードに id 順で、type lost の 8個を sort_order の順に繰り返し割り当てる（40件ずつ。design §3-2 第11版）。
- 本番の値: seed 20261101・base_date 2026-11-01・tenant_id 1。

### 4-1. SQL の書き出し

- `python3 scripts/lead_regression/generate.py --seed 20261101 --base-date 2026-11-01 --tenant-id 1 --mode dryrun|commit --out "$SCRATCH/lead_insert.sql"`。出力先がリポジトリの中なら `STOP:` で終了コード2。
- 書く表と列は design §3 の表のとおり（本物との違いの欄も全部守る）。書く表は tenant_001 の tenant_sales_form_options・leads・lead_sales_form_selections・deal_close_reasons・lead_channels・meta_messages・conversation_logs だけ。
- tenant_id 列はすべての INSERT で `1` を明示する（conversation_logs・tenant_sales_form_options は既定が無い。Fable 注意1）。読んだ値は引数で受け、DB の public の表を SQL の中で読まない。
- 失注理由の id・店舗の形の選択肢の id は直書きしない。失注理由は `tenant_001.close_reasons` を `type = 'lost'` と sort_order で引く（Fable 注意8）。選択肢は同じ SQL の中で入れたものを value で引く。リードの id は INSERT … RETURNING で受ける（一時表 `pg_temp` に lead_code と id を入れてよい）。
- 1つのトランザクション。最初に前提の点検（DO ブロック。合わなければ RAISE EXCEPTION）: tenant_001.leads に `TLR-` が 0件、tenant_001.tenant_sales_form_options が 0件、tenant_001.close_reasons の type lost が 8件、tenant_001.deal_close_reasons の表がある（Fable 注意3）。
- 最後に件数の点検（DO ブロック）: `TLR-` のリード 470・成約 150・失注 320、lead_sales_form_selections 470、deal_close_reasons 320、lead_channels（instagram・messenger の数）、meta_messages・conversation_logs（`tlr-s20261101-` の数）が Dataset と一致。合わなければ RAISE EXCEPTION。
- `--mode dryrun` は最後を `ROLLBACK;`、`commit` は `COMMIT;`。それ以外は1バイトも同じ（試験で確かめる）。
- 最初の行に `SET statement_timeout`・`lock_timeout` を入れてよいが、search_path は切り替えない。

## 5. 試験と点検

### 5-1. 計算の試験（`backend/tests/test_lead_conversion_factors.py`）

- 区切りちょうど: 3600秒・21600秒ちょうどの作り物で 1 になる（≦）。3601秒・21601秒で 0。
- 同じ時刻の受信と送信は id の順に並ぶ。
- deleted_at の入った行は読まない（入口の試験で1行入れる。design §4-4 の1）。
- 外す決まり §2-4 の7種それぞれ1件ずつの作り物で、その欄だけが 1 増える。
- 完全分離の作り物で例外にならず `not_computable`。
- statsmodels との突き合わせ: seed 1 の Dataset で、自前の計算の β・標準誤差・幅の下と上を、クラウドで statsmodels 0.15.0（`Logit(y, X).fit(method="newton", maxiter=100, tol=1e-10)`、conf_int(0.05)）で出した値と小数4桁まで一致させる。期待値は試験ファイルに定数で書き込み（どの環境で何を流して出したかを注記）、CI は statsmodels を入れずに定数と比べる。statsmodels が import できる環境では、その場で statsmodels と比べる試験も流す（できなければ skip）。

### 5-2. 作り方の試験（`backend/tests/test_lead_regression_generate.py`）

- 同じ seed で2回作ると、SQL の sha256 が一致。dryrun と commit の違いは最後の1文だけ。
- 件数: 470・成約 150・各項目の割り振りが §4 の数。
- 470件すべてで §2-3 の2つの値が計算でき、§2-4 で1件も外れない（K2 を本番の外で）。
- 最後のメッセージが base_date の 2日前より前。
- 値の綴りが `backend/app/schemas/lead.py` の列挙に入っている（Fable 注意2）。

### 5-3. 書き込みの SQL の点検（`scripts/lead_regression/check_sql.py`。試験から呼んで CI で毎回流す。design §4-4 の9）

- 本番の値（§4）で書き出した SQL について、次がすべて 0件なら合格:
  - INSERT・UPDATE・DELETE の書き込み先で `tenant_001.` で始まらないもの
  - FROM・JOIN で読む表のうち `tenant_001.` でも `pg_temp.` でもないもの（Fable 注意8）
  - `tenant_00` に続く 001 以外の数字、`public.`、`search_path`
- 違反を1つ入れた作り物の SQL で不合格になる試験も入れる。

### 5-4. 消す SQL（`docs/handoff/lead-regression/sql/delete_tenant_001.sql`。design §6-1。PO 本人が流す。今回は流さない）

- 1つのトランザクション。手順1 の点検を最初の DO ブロックにし、当たれば RAISE EXCEPTION で止まる（Fable の提案「手順1 を固い前置き」）。点検の中身は design §6-1 手順1 のとおり。手順0 で記録する値（元の行の id の一覧・書き込みを始めた時刻・テスト用リードの id）は、ファイルの先頭の一時表に入れる形にし、値の入れ場所を `-- 手順0 の記録をここに貼る` の注記で示す（その場所以外に空欄を残さない）。
- 手順2〜8 を design §6-1 の順で。手順9 の数え直しを最後の DO ブロックで行い、テスト用の行が残っていれば RAISE EXCEPTION。
- 書き込み先が tenant_001 だけであることを §5-3 と同じ点検で確かめる試験を入れる（読む側は手順1 の audit_logs も tenant_001 の表）。

## 6. 本番の外の確かめ K3（クラウドで1回流し、数を報告する）

- `python3 -I scripts/lead_regression/k3_run.py --out-dir "$SCRATCH/k3"`（`$SCRATCH` はクラウドの作業用の場所。リポジトリの中なら `STOP:`）。
- 種は 1〜200 に前もって固定する（design §2-1 (1)。合格するまで変えない）。K3c の並べ替えは、種 s のデータの成約の印を `random.Random(1000000 + s)` で shuffle する。base_date は 2026-11-01。
- 出す数（項目ごと）:
  - K3a: 95%の幅が仕込んだ値を含む回数（180〜198 で ○）
  - K3b: 推定の幾何平均 ÷ 仕込んだ値（0.90〜1.11 で ○）と、その値そのもの
  - K3c: 並べ替えたデータで幅が 1 を含む回数（180 以上で ○。上の端は見ない。審査 v10 の補足3）
  - 「計算できない」が出た回数（外れに数える）、「差がある」と出た回数
  - 成約を 150 にするための引き直しの回数（種ごとの平均・最大）
- 本番の値（seed 20261101）の Dataset でも §2 の計算を流し、15項目の β・幅を小数6桁で出す（K3d の比べる側。Opus が本番の入口の値と小数4桁で突き合わせる）。
- × が出た場合（作りが正しくても 1〜2割の見込みで出る）: 流し直さない。design §2-1 (2) のとおり × の側の 200通りで statsmodels 0.15.0 と突き合わせ、(a)(b)(c) のどれかを、見込みの範囲の表（design §2-1）と比べて報告する。#6〜#11・#13 で 199回は (b) に入る（Fable 注意7）。(b) で計算の誤りが見つからなかったときも (c) と同じく報告して止める（Fable 注意6）。直してよいのは (a) の計算の誤りだけで、直したら同じ種で1回だけ流し直し、前後の両方を報告する。

## 7. 停止する条件（停止したら、その時点で報告して終わる）

- §0 や §1 の行番号・名前が実物と合わない（5行以上ずれる、列が無い）→ `BLOCKED:` に続けて合わなかった名前と行番号。
- design §3 の表の列が migrations の定義に無い → 推測で足さず `BLOCKED:`。
- K3 のどれかが × → §6 の切り分けまで行い `NEEDS_DECISION: K3 が ×` に続けて項目と数。push はしてよい。
- statsmodels と小数4桁で一致しない（計算の誤り）→ 直してから報告。直せなければ `BLOCKED:`。

## 8. 終わりの条件

- `backend` の pytest のうち §1 の新しい試験と `backend/tests/test_analytics.py` が通る（流したコマンドと結果の最後の行を報告に書く）。
- `git diff --name-only origin/main...HEAD` が §1 のファイルと、このカード・design の docs だけ。
- §6 の数が報告にある。本番の値の Dataset の SQL（commit 版）の sha256 と行数も報告にある。
- 枝 `release/lead-regression-backend` に push 済み。PR は作らない。
- 報告の最後の行は `DONE` / `BLOCKED:` ＋理由 / `NEEDS_DECISION:` ＋内容 のどれか。

## 9. カードの自己審査（2026-11-01 Opus。同じ AI による自己審査）

- 判定: APPROVE
- 設計との整合: K2（§5-2・§2-4 の内訳）、K3a〜K3c（§6）、K3d（§6 の比べる側・§2-6 丸めない）、K5①(a)（§5-3）、K6 の SQL（§5-4）、design §4-4 の 11件（1: §2-2・§5-1、2: §2-4、3: §2-3・§5-1、4: §4 本文、5: §4、6: カード B の注意書き、7: §2-6、8: §6 と Opus の報告書、9: §5-3、10: §2-4、11: design §9 を参照）。
- 審査 v10 の補足2（④⑤の追加分はカードで書き、実装の PR で設計審査役が確かめる）: ④は全テナントに出す・public へ書かない（§1 で public を触らない）、⑤は §2-4。補足3（K3c は下の端だけ）: §6。
- Fable の追加注意9件: 1 §4-1 tenant_id 明示、2 §2-1・§5-2、3 §4-1 前提の点検、4 §2-4・§5-2 の内訳で K2、5 §2-6、6 §6、7 §6、8 §4-1・§5-3、9 §4 目印に seed。
- 第11版で設計に足した決まり: 失注理由は lost の 8個（本番の事実 §0）、外す内訳に `other_values`・`no_reply_pair` を足した（本物の値で必要。テスト用データでは 0件になる）。
- 残る未確認: conversation_logs の向きの列の名前（§2-2 で実物から読ませ、合わなければ止める）。K3 の結果（作りが正しくても 1〜2割の見込みで ×）。

END OF CARD
