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
| A | 判定の関数（照合・候補・推測チェック・発送日の呼び出し）＋単体テスト。DB・配線なし | 新規 `backend/app/services/extraction_judgement_svc.py`、新規 `backend/tests/test_extraction_judgement_svc.py` | 低 |
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

- 判定の関数は `backend/tests/test_extraction_judgement_svc.py` の単体テストで守る（CI の必須チェック `pytest (SQLite + PostgreSQL RLS)`）。
- 試運転の結果と確認待ちの件数は、PR-D の集計画面で週ごとに PO が見る。
- 仕入元ルール・検索ワード・除外ワードは SSOT の表だけに置き、ほかに置き場所を作らない（§3）。
- 守り手: CI 必須チェック pytest (SQLite + PostgreSQL RLS) と PO の週次確認（design.md §9-2）

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
