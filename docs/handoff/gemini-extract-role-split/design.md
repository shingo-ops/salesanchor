# design: Gemini＝書き写し専任／システム＝判定 への役割分離（LINE解析）

- recon: `docs/handoff/gemini-extract-role-split/recon.md`（起点 origin/main `ae783c7f583e2d5628c19d999ed7ce6c7944e9b8`）
- 状態: 設計案（PO合意事項を反映）／Architect 審査は本文末尾／実装未着手
- 関連ADR: ADR-085（supplier_prompts）、ADR-093（発送日ルール判定）、ADR-158（is_current）、ADR-1001（public.products 統合）、ADR-027/067/144（UI）、ADR-135/136（危険PRとGO）
- 置き換える対象: `docs/handoff/use-gemini-product-code/design.md`（`pid_basis='GEMINI'` 採用）と、ADR-158 のうち Gemini の商品コードを第一候補にする Gate 部分（recon §A・§D）

## 1. KGI（PO合意 2026-09-28）

優先順位は 1. 誤判定ゼロ、2. 使うほど精度が上がる、3. コスト削減。人による確認が増えることは許容する。

| 基準 | 検証方法 |
|---|---|
| Gemini は判定しない（v7出力に RESOLVED_* 列が無い） | `backend/tests/test_tcg_gemini_extraction.py` の v7 パーサテストで、列一覧に RESOLVED_WORK_ID と RESOLVED_PRODUCT_CODE が無いことを assert |
| 状態・発送日に空欄が0件（無ければ `none`） | v7 パーサテスト：空欄の行は parse_errors に入る。本番では試運転表の state_raw / ship_raw の空欄件数が0 |
| システムの自動確定に誤りが0件 | 試運転期間に自動で確定した行から抽出して人が確認し、誤りが0件（件数は試運転で1日の件数が分かってから PO が決める） |
| 確認待ちの全件に「項目・候補・理由」が付く | 試運転表の `needs_review=TRUE` の行で、`review_items` が空のものが0件（SQL） |
| 人が登録したワードで同じ文が自動で確定する | 結合テスト：ワード追加 → 同じ明細を再判定 → matched |
| 詰まりが見える | 仕入元別・項目別の確認待ち件数が画面に出る（Evaluator が Playwright で確認） |
| 試運転は配信に影響しない | 試運転を有効にする前後で、配信クエリ（`tcg_distribution_svc.py:255,326,368`）の対象件数が同じ。試運転表は配信クエリから参照されない（grep で0件） |
| コスト90%以上削減（切り替え後） | `extraction_attempts.input_bytes` とトークン列の、切り替え前7日間と切り替え後7日間の比較 |

## 2. 役割（PO合意）

- **Gemini（書き写し係）**：商品のまとまりごとに次を原文どおり書き写す。商品名／価格／単位／数量／状態（無ければ `none`）／発送日（無ければ `none`）／ブロックの行範囲／見出しの行範囲。値が2つ以上あれば全部書いて `MULTI` の印を付ける。推測は禁止。作品名・備考・判定列は出さない。渡すのは、共通の指示・その仕入元のルール・原文だけで、マスタは渡さない。
- **システム（判定係）**：提供者・作品・商品名・状態・価格・数量・発送日・備考を決める。1つに決まれば確定、決まらなければ「どの項目で止まったか」を付けて確認待ちにする。
- **人（先生）**：確認待ちを見て正解を選び、検索ワードや除外ワードを自由に入力して登録する。

## 3. データの置き場所（PO決定）

| 区分 | 置き場所 | 根拠 |
|---|---|---|
| 仕入元ルール（SSOT） | `public.suppliers.extraction_*`（7列）＋新しい列 `extraction_ship_format` | 実際に Gemini へ届いている唯一の経路：`backend/app/tasks/tcg_extraction.py:229-249`、`backend/app/services/gemini_extraction_svc.py:236-317` |
| supplier_prompts | **削除**（PO決定 2026-09-28：不要）。表・CRUD API（`backend/app/routers/super_admin_suppliers.py:600-644`）・画面をまとめて消す。中身は移さない。DROP TABLE は不可逆なので、PO の「GO #PR番号」が必要 | 抽出経路からは読まれていない：recon §C |
| 知識ルール（仕入元ごとに紐付いている区切り方・読み飛ばす行・状態の言葉＝`block_delimiter`/`skip_condition`/`status_keyword`） | **仕入元マスタの抽出ルール欄に寄せる**（PO決定 2026-09-28）。列を足してデータを移し、`supplier_knowledge_links` 経由でプロンプトに入れるのはやめる。全仕入元に共通の除外（`message_exclude*`、`tcg_extraction.py:164-`）は、そのまま残す | recon §V4 |
| 商品の検索ワード・除外ワード（SSOT） | 既存の `public.product_search_keywords` / `product_exclude_keywords` | recon §G |
| 作品 | `public.products.work_id`（商品に作品が登録済み。作品用のワード表は作らない） | `backend/app/services/tcg_analyzer_svc.py:1227-1230` |
| 状態・ステータス・備考の各マスタ | 既存の `public.conditions` / `public.tcg_status_master` / `public.tcg_note_master` | `tcg_analyzer_svc.py:646-725, 989-997, 1093` |
| **試運転（A/B）の結果** | **新しい表 `public.extraction_shadow_results`**（本番の `analysis_results` とは分ける） | PO決定。`analysis_results` は `UNIQUE(extraction_item_id)`：recon §E |

## 4. 商品の判定（PO合意）

1. 対象は `public.products` の有効な全件（解析用の別マスタは作らない）。
2. 照合するのは、Gemini が示したブロックの行範囲にある**原文そのもの**。Gemini が書き写した値ではなく、元の文を見る。
3. 原文に品番が書いてあり、`products.product_code` か `mark` と一致すれば、その商品を候補にする（いまの Gate1 と同じ考え方：`backend/app/services/tcg_analyzer_svc.py:1217-1224`）。
4. 検索ワードをスペースで区切り、各語が**すべて**原文に含まれる商品を候補にする。比べる前に、両方を NFKC・小文字・カタカナ→ひらがな・空白削除・記号削除でそろえる。
5. 除外ワードを含む商品は候補から外す。
6. 単品か箱かの見分け（`backend/app/services/tcg_product_guards.py`）は、原文を入力にして使う。
7. 候補が1件なら確定。0件または2件以上なら確認待ち（候補・当たった語・外した語を記録）。
8. 作品は、確定した商品の `work_id` から決める。

## 5. その他の項目

- 状態：いまの `resolve_condition_v2()`（`backend/app/services/tcg_analyzer_svc.py:787-882`）に、Gemini が書き写した状態を渡す。`none` は「記載なし」として扱う。
- 数量・価格：いまの `_parse_numeric()`（`:896-923`）を使う。
- 備考：いまの `build_note_ja()`（`:1033-1071`）に、Gemini の備考列の代わりに**ブロックの原文**を渡す。
- 発送日：`backend/app/services/inventory_parser.py` にある発送日のルール判定（`:240-252, 518-541`）を関数として呼んで使う（コピーしない）。
- 推測チェック：Gemini が書き写した各値が、示した行範囲の原文に（そろえた上で）含まれるかを確かめる。最初は**記録だけ**して止めない。止める設定にするのは PO が数字を見て決めてから。

## 6. 試運転（A/B）

- 環境変数 `EXTRACTION_SHADOW_ENABLED`（初期値は無効）で切り替える。
- 有効にすると、本番の処理（いまの Gemini 呼び出しと解析）が終わったあと、同じ原文で v7 の Gemini 呼び出しとシステム判定を行い、結果を `extraction_shadow_results` に書く。本番の表には書かない。
- 費用：Gemini の呼び出しは1回増える。ただし v7 はマスタを送らないので、1回あたりの量は小さい見込み（数値は実測前なので未確認）。
- **注意（PO判断が必要）**：確認待ちで人がワードを登録すると、ワードの表は本番と共通（SSOT）なので、本番のキーワード照合（`match_pid_with_work` のフォールバック）にもすぐ効く。登録前に「過去の結果が何件変わるか」を出すプレビューで、影響を確かめてから登録する。

## 7. PR 分割（1PR1テーマ）

| PR | 内容 | 触るファイル（予定） | 危険 |
|---|---|---|---|
| A | 判定の関数（照合・候補・推測チェック・発送日の呼び出し）＋単体テスト。DB・配線なし | 新規 backend/app/services/extraction_judgement_svc.py、新規 backend/tests/test_extraction_judgement_svc.py | 低 |
| B | migration：`extraction_shadow_results` の新設、`suppliers.extraction_ship_format` の追加、supplier_prompts→extraction_notes のデータ移行 | migrations/2026xxxx_*.sql、`.github/workflows/deploy.yml`（CI の必須チェックに従う） | **高：GO #PR番号が必要** |
| C | v7 の指示とパーサ、試運転の実行部分（初期値は無効） | `backend/app/services/gemini_extraction_svc.py:443-453`、`backend/app/services/tcg_work_reference.py:13-14`、`backend/app/tasks/tcg_extraction.py`、`extraction_prompt_config`（v7 の行は PR 内の migration で入れる→危険扱い） | **高** |
| D | 画面：試運転の確認待ち一覧（既存 NeedsReviewListPage に金型 `DataTable` でタブを追加）、ワード登録（除外ワード1件追加 API を新設）、影響プレビュー、詰まりの集計、仕入元ルール画面に発送日欄、supplier_prompts 画面の撤去 | `frontend/src/pages/super-admin/NeedsReviewListPage.tsx`、`backend/app/routers/tcg_product_master.py`、ja/en.json 他 | 中 |
| E | 切り替え（264件そろってから） | 配信と解析の入口 | **高：PO GO** |

## 8. 戻し方

- 試運転：`EXTRACTION_SHADOW_ENABLED` を無効にする（本番には影響しない）。
- 切り替え後：指示文を v6 に戻す（`extraction_prompt_config` の is_active）。あわせて、コード側の版の分岐（`backend/app/services/tcg_work_reference.py:14`）も戻す。
- supplier_prompts：表を消さずに残すので、データは元に戻せる。

## 9. 外部・過去事例の参照と我々への応用

- 該当なし。この設計の正しさは、外部事例ではなく試運転（A/B）の自社実測で確かめる（§1）。

## 9-2. 維持の仕組み

- 判定の関数は backend/tests/test_extraction_judgement_svc.py の単体テストで守る（CI の必須チェック `pytest (SQLite + PostgreSQL RLS)`）。
- 試運転の結果と確認待ちの件数は、PR-D の集計画面で週ごとに PO が見る。
- 仕入元ルール・検索ワード・除外ワードは SSOT の表だけに置き、ほかに置き場所を作らない（§3）。
- 守り手: `backend/tests/test_extraction_judgement_svc.py` と `backend/tests/test_extraction_shadow_svc.py`（CI 必須チェック pytest (SQLite + PostgreSQL RLS) で実行）、および PO の週次確認（design.md §9-2）

## 10. 本番DBの実測（2026-09-28、PO が読み取り専用で実行。生データは recon の db-survey.txt）

| 項目 | 値 |
|---|---|
| 1日の抽出明細数（直近14日） | 31〜2,463件（平日はおよそ2,000件） |
| 有効な商品数／そのうち work_id が NULL | 1,336件／0件 |
| 仕入元数／抽出ルール欄の記入数 | 265件／price・qty・order が14件、state が7件、example が3件、default_unit が258件、notes が13件 |
| supplier_prompts | 32件（全件に記入あり） |
| knowledge_rules（種類ごと） | block_delimiter 18件、skip_condition 13件、status_keyword 4件、message_exclude 9件、message_exclude_no_digit 1件 |
| 指示文の長さ | base_extraction 1,079文字、work_id_extraction 1,385文字 |
| Gemini 呼び出し（直近7日） | 1,046回、1回あたり入力 平均655,910バイト（中央値638,608バイト）→ 入力の大部分はマスタ |
| 完売・サーチ済みの skip_condition | id 21〜26（PO が削除を承認 2026-09-28） |

## 11. 未確認・未決定

1. 残りの skip_condition 7件の扱い（Gemini に判断させない方針なので、システム側へ移すか削除するか）→ PO に聞く
2. §6 の注意：確認待ちで登録したワードが、本番の照合にもすぐ効くこと → PO に聞く
3. skip_condition がどの仕入元に紐付いているか（`supplier_knowledge_links.knowledge_rule_id` を使って数える）
4. ADR-136 のファイルが2つある件と、ADR-158 の状態欄が「Proposed」のままの件（別件として報告）

## 12. Architect 審査（Opus が自分で審査。独立した第二者によるレビューではない、2026-09-28）

- **PR-A（判定の関数とテスト）：APPROVE。** 入力として使う関数が、原文を渡せる純粋な関数であることを確認した（`backend/app/services/tcg_product_guards.py`、`backend/app/services/inventory_parser.py:518`）。work_id が NULL の商品は0件（§10）。DB にも配線にも触れない。
- **削除 PR（skip_condition id 21〜26）：APPROVE。** 対象の6件と、代わりに処理する解析ルール（conditions CN0007/CN0010、tcg_status_master ST0011〜13）が本番に実在することを確認した（§10）。migration による DELETE なので危険 PR 扱いとし、GO #PR番号 が必要。
- **PR-B〜E：REVISE。** §11 の1と2が決まってから、実装カードを作る。

# design 追補：PR-B1 / PR-C / PR-D / PR-CLEAN（2026-09-28、Opus）

- 根拠となる調査：recon2.md（origin/main `4bad43a4dca6368ffa7370792a3c912e90bba52`）。以下 `backend/app/routers/super_admin_suppliers.py` などはすべてリポジトリ相対パスで引く。
- Architect 審査：本文末尾（§Z）。

## A/B 期間中の SSOT の扱い（重要な決定）

- **block_delimiter（区切り記号）**
  - 切り替え（PR-E）までは、v6 と v7 の両方が同じ `knowledge_rules` と `supplier_knowledge_links` を読む。
  - A/B 期間中は区切り記号を仕入元の欄へ**移さない**。移すと置き場所が一時的に2つになり、SSOT に反するため。移すのは PR-E で行う。
- **status_keyword（ステータス判定語）**
  - v7 の Gemini には渡さない。判定にあたるので、システム側の `public.tcg_status_master` に任せる。
- **発送日の書き方**
  - `public.suppliers.extraction_ship_format` を新しく設ける（PR-B1）。
  - 画面での編集は PR-D、v7 への注入は PR-C で行う。
- **v7 の指示文**
  - `public.extraction_prompt_config` に、新しいキー `raw_copy_extraction` として置く（SSOT は DB）。
  - 最初の文面は PR-B1 の migration で `INSERT ... ON CONFLICT (prompt_key) DO NOTHING` として入れる。こうすれば再現でき、かつ管理画面での編集を上書きしない。
  - その後の編集は、既存の管理 API（`backend/app/routers/super_admin_suppliers.py:1196-1224` の PUT /super-admin/extraction-prompts/{key}）で行う。

## PR-B1：試運転用の表と発送日の欄（migration のみ・危険 PR・GO #番号が必要）

- 新規 migration を1本作る：migrations/20260928_1xxxxx_create_extraction_shadow_tables.sql。登録先は `scripts/run_all_migrations.sh` の末尾。
  1. `ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_ship_format TEXT;`
  2. `public.extraction_shadow_runs`（Gemini の呼び出し1回につき1行。A/B 専用）
     - `id uuid PK`（既定値の書き方は既存 migration に合わせる）
     - `extraction_job_id uuid NOT NULL REFERENCES public.extraction_jobs(id) ON DELETE CASCADE`
     - `prompt_key text NOT NULL`、`prompt_config_version int`、`engine_version text NOT NULL`、`requested_model text NOT NULL`
     - `input_bytes bigint`、`response_text text`
     - トークンと費用の列：`migrations/20260927_130000_add_extraction_token_cost_columns.sql` と同じ名前・同じ型にする
     - `status text NOT NULL CHECK (status IN ('completed','failed'))`、`error_code text`、`error_detail text`
     - `started_at timestamptz NOT NULL DEFAULT now()`、`finished_at timestamptz`
     - `UNIQUE (extraction_job_id, engine_version)`
  3. `public.extraction_shadow_results`（ブロック1つにつき1行）
     - `id uuid PK`、`run_id uuid NOT NULL REFERENCES public.extraction_shadow_runs(id) ON DELETE CASCADE`、`block_index int NOT NULL`
     - `line_start int`、`line_end int`、`heading_line_start int`、`heading_line_end int`
     - Gemini が書き写した値（すべて text）：`raw_product_name`、`raw_price`、`raw_unit`、`raw_quantity`、`raw_state`、`raw_ship`、`raw_multi`
     - システムの判定結果：`product_id int REFERENCES public.products(id)`、`work_id int`、`condition_id int`、`quantity_normalized numeric(14,2)`、`price_normalized numeric(14,2)`、`ship_offer_type text`、`ship_timing text`、`note_ja text`、`status varchar(50)`、`exclusion text`
     - `match_status text NOT NULL CHECK (match_status IN ('matched','ambiguous','unmatched'))`、`needs_review boolean NOT NULL`
     - `review_items jsonb NOT NULL DEFAULT '[]'`（`[{item, reason, candidates}]`）
     - `evidence jsonb NOT NULL DEFAULT '{}'`、`verify_failures jsonb NOT NULL DEFAULT '[]'`
     - `created_at timestamptz NOT NULL DEFAULT now()`
     - `UNIQUE (run_id, block_index)`
     - 索引：`(needs_review, created_at)`、`(run_id)`
  4. `INSERT INTO public.extraction_prompt_config (prompt_key, prompt_text, is_active) VALUES ('raw_copy_extraction', <下の文面>, TRUE) ON CONFLICT (prompt_key) DO NOTHING;`
     - 列名と必須の列は `migrations/20260926_080000_create_extraction_prompt_config.sql` を読んで合わせる。
- `analysis_results` と配信のクエリには一切触れない。
- テスト：使い捨ての postgres:16 で、関係する migration → 新しい migration を2回実行し、冪等であることを確かめる。

### v7 指示文（raw_copy_extraction の最初の文面）

```
あなたは書き写し担当です。判断・推測・補完・言い換え・翻訳はしません。
入力は LINE の投稿本文で、各行の先頭に行番号（例 L0001）が付いています。
商品のまとまり（ブロック）ごとに1行ずつ、次の9列を「｜」で区切って出力してください。1行目は次のヘッダーをそのまま出力します。
RAW_PRODUCT_NAME｜RAW_PRICE｜RAW_UNIT｜RAW_QUANTITY｜RAW_STATE｜RAW_SHIP｜RAW_MULTI｜RAW_SOURCE_LINE_SPAN｜RAW_HEADING_LINE_SPAN
- 値は原文の文字をそのまま書き写す。
- 原文に書かれていない値は none と書く。空欄にしない（特に RAW_STATE と RAW_SHIP）。
- 1つのブロックに同じ種類の値が2つ以上あるときは、すべてを「／」でつないで書き、RAW_MULTI にその列名を書く（複数あれば「／」でつなぐ）。なければ none。
- RAW_SOURCE_LINE_SPAN はブロックの行範囲（例 L0003-L0005）。RAW_HEADING_LINE_SPAN はそのブロックに掛かる見出し行の範囲。なければ none。
- 作品・商品・状態・在庫・完売などの判定はしない。書かれている文字を書き写すだけ。
- 後に続く「仕入元の書き方」は、この仕入元がどこに何を書くかの説明です。書き写す場所を見つける参考にだけ使ってください。
```

## PR-C：v7 の呼び出し・読み取りと試運転の実行（backend、初期値は無効）

- `backend/app/services/gemini_extraction_svc.py`
  - 新しい関数 `call_gemini_raw_copy(raw_text, supplier_context, knowledge_links)` を作る。
  - DB の `raw_copy_extraction` だけを使う（is_active）。無いときは例外にして、試運転側が failed として記録する。本番の経路は巻き込まない。
  - 仕入元の書き方として渡すもの：既存の `_build_supplier_context_note` と同じ書き方で、`extraction_*`（ship_format を含む）と block_delimiter だけ。skip_condition と status_keyword は渡さない。
  - 行番号の付け方とモデルの設定は、既存の `call_gemini_extraction` と同じにする。
- 新しいパーサ `parse_raw_copy_response(response_text, raw_text)`
  - 9列固定。ヘッダーが完全に一致しなければ ValueError。
  - RAW_STATE か RAW_SHIP が空の行は parse_errors に入れる。
  - 行範囲は既存の v6 と同じ規則で検証する。
- 版の定数：`backend/app/services/tcg_work_reference.py` に `RAW_COPY_PROMPT_VERSION = "raw-copy-v7-p1"` を足す。既存の frozenset には入れない（v6 の分岐に影響させないため）。
- 新しいサービス backend/app/services/extraction_shadow_svc.py に `run_shadow_for_job(session, extraction_job_id)` を作る。
  1. ジョブの原文・仕入元の情報・knowledge_links を、本番と同じクエリで読む（`backend/app/tasks/tcg_extraction.py:229-304` を関数として切り出すか、同じ SQL を使う。**複製が必要になる場合は止めて報告する**）。
  2. v7 を呼んで、`extraction_shadow_runs` に記録する。
  3. ブロックごとに、次の順で判定する。
     - `extraction_judgement_svc.block_text` / `match_product` / `verify_copied` / `ship_timing`（PR-A）
     - 状態・数量・価格・ステータス・備考は、既存の `resolve_condition_v2` / `_parse_numeric` / `resolve_status_v2` / `build_note_ja`（`backend/app/services/tcg_analyzer_svc.py`）を呼ぶ。備考の入力はブロックの原文。
     - **既存の関数の引数が Gemini 固有の構造を必要とする場合は、止めて報告する**。
  4. `review_items` を作る：1つに決まらなかった項目ごとに `{item, reason, candidates}` を入れる。
  5. `extraction_shadow_results` に保存する。同じ run の中では、DELETE してから INSERT し直す。
  6. 例外が起きても本番には伝えない。failed として記録して、ログに残す。
- 呼び出し元：`backend/app/tasks/tcg_extraction.py:484-500` の `if final_status == "done":` の中で、本番の解析が終わった後に `if os.environ.get("EXTRACTION_SHADOW_ENABLED", "").strip() == "1":` で `run_shadow_for_job` を呼ぶ。try/except で本番から切り離す。
- テスト
  - パーサ（正常／ヘッダー不一致／none／空欄での失敗）
  - run_shadow_for_job（Gemini をモックする。matched／ambiguous／unmatched／verify の失敗）
  - 無効のときは呼ばれないこと
  - 例外が本番に伝わらないこと

## PR-D：試運転の確認画面・ワード登録・影響プレビュー・詰まり集計・発送日の欄（frontend＋routers）

- 関連ADR: ADR-027, ADR-067, ADR-144（画面は i18n・デザイントークン・金型の決まりを守る）
- API（新しいルーター backend/app/routers/tcg_shadow_review.py、`require_super_admin`）
  - `GET /tcg/shadow-results?needs_review=&supplier_id=&offset=&limit=`：原文ブロック・止まった項目・候補（商品名付き）・理由を返す。
  - `GET /tcg/shadow-results/bottlenecks?days=7|30`：仕入元別・項目別の確認待ち件数と、自動で確定した割合。
  - `POST /tcg/shadow-results/keyword-preview`（入力：`{product_id, kind: search|exclude, keyword}`）
    - 直近30日の `extraction_shadow_results` のブロックを、ワードを追加した状態で `match_product` で判定し直す。
    - 結果が変わる件数（`unmatched→matched`、`ambiguous→matched`、`matched→ambiguous` など）を返す。
    - DB には書き込まない。
  - 除外ワードを1件追加する API：`POST /tcg/products/{product_id}/exclude-keywords`（`backend/app/routers/tcg_product_master.py`）
    - サービスは `add_exclude_keyword` とし、`backend/app/services/tcg_product_master_svc.py:474-530` の `add_search_keyword` を写した作りにする。
  - 仕入元の抽出ルール：`backend/app/routers/super_admin_suppliers.py:751-765` の `_EXTRACTION_RULE_COLS` と `_EXTRACTION_RULE_UPDATABLE`、`backend/app/schemas/central_masters.py:410-432` に `extraction_ship_format` を追加する。
- 画面
  - `frontend/src/pages/super-admin/NeedsReviewListPage.tsx` に既存の金型 `Tabs` を入れる。
    - 「本番の確認待ち」は今の表示のまま。
    - 「試運転の確認待ち」は `DataTable` に、仕入元・原文の抜粋・止まった項目・候補・理由・日時を出す。
    - 行を選ぶと `Modal` を開き、次を出す。
      - 原文ブロックの全文
      - 候補の一覧
      - ワードの種類を選ぶ `Select`（検索／除外）
      - 入力欄 `TextField`（最初から原文のブロックが入っている）
      - 「影響を確認」ボタン → プレビューの件数を表示 →「登録」ボタン
  - 詰まりの集計：同じページの3つ目のタブ「詰まり」に、`Card` と `DataTable` で表示する。
  - `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx`：発送日の書き方の欄を、既存の `Textarea` 金型で足す。
  - i18n：ja/en に同じキーを足す。キーは既存の名前空間の決まりに合わせる。ハードコードの日本語、生の要素、色やピクセルの直接指定は禁止（ADR-027/067/144）。
- テスト：API の単体テストと PG テスト。画面は既存のテストの作法に合わせる。

## PR-CLEAN：古い仕入元ルールの経路を撤去（危険 PR・GO #番号が必要）

- supplier_prompts
  - 取り除くもの：API（`backend/app/routers/super_admin_suppliers.py:49-50, 600-667`）、スキーマ（`backend/app/schemas/central_masters.py:388-408`）、画面（`frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx` のプロンプト部分）、i18n（ja/en の `knowledge.prompt*`）
  - migration で `DROP TABLE IF EXISTS public.supplier_prompts;`（不可逆）
- skip_condition の登録経路
  - `backend/app/routers/super_admin_suppliers.py:968` の許可カテゴリから外す。
  - 画面の `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx`（143-152, 227, 306, 324, 632-636）と `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:44-45` から外す。
  - `backend/app/services/gemini_extraction_svc.py:298, 307-308` の描画処理を取り除く。

## §Z Architect 審査（Opus が自分で審査。独立した第二者によるレビューではない）

- **PR-B1：APPROVE**
  - 追加だけの変更で、既存の表・配信クエリには触れない。
  - 置き場所は PO の決定どおり（試運転の結果は分ける、ルールとマスタは SSOT）。
- **PR-C：APPROVE（条件付き）**
  - 切り替えスイッチの初期値は無効。例外は本番から切り離す。
  - 既存の関数の引数が合わない場合、またはクエリを複製することになる場合は、止めて報告することを条件にする。
- **PR-D：APPROVE**
  - 使うのはすべて既存の金型（Tabs、DataTable、Modal、Select、TextField、Card、Textarea）。recon2 §7 で存在を確認済み。
  - プレビューは DB に書き込まない。
- **PR-CLEAN：APPROVE**
  - PO の決定（supplier_prompts は削除、skip_condition は廃止）どおり。DROP は不可逆なので GO #番号 が必要。
- **残るリスク**
  - PR-C/D/CLEAN は backend/frontend を変えるため、PR を作る時点で GO記録が必要（`scripts/dev/validate-pr-body.sh:308-322`）。ブランチを push するところまでで止まる。

## 追記（2026-09-30）：試運転の一時停止
- PO 決定（2026-09-30）：「新しいシステムは停止しておいて、整備してから精度チェックしたいので未整備のまま動作させたくない」「試運転を止めることを許可する（前にご相談した「整備が終わるまで止める」）」
- docker-compose.yml の celery-worker の EXTRACTION_SHADOW_ENABLED の初期値を 1→0 に変更。再開は同じ値を 1 に戻す
- 停止前に記録された extraction_shadow_runs（2026-09-29〜30、整備前）は精度評価に使わない
- 関連 ADR：ADR-1003（GO の委任。この変更の GO は ADR-1003 に基づく Opus 発行）
