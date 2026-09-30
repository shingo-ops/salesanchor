# 追補3：過去の原文に新方式（v7）だけを一括で流す（正答率の測定用）

状態：**設計確定（PO 合意 2026-10-01）／Opus 自己審査済み／実装は未着手**
- 親
  - `docs/handoff/gemini-extract-role-split/price-qty-resolver-design.md`
  - `docs/handoff/gemini-extract-role-split/design.md`
- 根拠
  - `docs/handoff/gemini-extract-role-split/recon.md`
  - 本書 §2 に挙げる本番の実測値

## 1. PO の決定（原文・2026-10-01）
「新方式の抽出だけをまず実行してほしい、現状の新システムが出せる正答率を確認したいので」

- 新方式の抽出だけを行う。旧方式の抽出結果は変えない。
- 測る対象は「今の」新システムである。既知の誤り（年号の数字を数量と読む）も、直さずにそのまま測る。

## 2. 事実（2026-10-01 本番の読み取り、origin/main のコード）
| # | 事実 | 根拠 |
|---|---|---|
| F1 | 新方式の結果は、試運転の23ジョブ分だけが残っている | `extraction_shadow_runs` の count=23 |
| F2 | 過去のジョブに新方式だけをもう一度流す仕組みは、コードに無い。既存の再実行（retry_extraction、recovery）は、旧方式の抽出を消してやり直す | `backend/app/tasks/tcg_extraction.py:524-540`、`backend/app/services/tcg_diagnostics_svc.py:146` |
| F3 | UNIQUE `(extraction_job_id, engine_version)` がある。同じジョブを2回流すと、Gemini を呼んだあとに INSERT で失敗し、費用だけがかかる | `migrations/20260928_110000_create_extraction_shadow_tables.sql:34` |
| F4 | 仕入元ルールのある115社の原文は1,547件あり、そのうち旧方式の抽出が完了しているのは1,488件 | 本番の読み取り |
| F5 | 同じ投稿を空行の違いだけで2回取り込んだ重複が、141組ある | `price-qty-resolver-design.md` の根拠 |
| F6 | 旧方式の1回あたりの費用は、平均 0.0228 USD（記録のある290件） | `extraction_attempts` |
| F7 | 新方式の23回分の費用は、記録されていない | llm_usage_events の line_extraction_shadow が0件 |

## 3. 作るもの
### 3-1. 一括実行の道具（新規：`backend/app/tools/shadow_backfill.py`）
- 起動方法：`python -m app.tools.shadow_backfill --limit N --max-cost-usd X [--dry-run]`
- 対象にするジョブ（SELECT を1本だけ使う）
  - extraction_jobs.status が `done` であること
  - 仕入元に `has_required_supplier_rule` を満たすルールがあること
  - `extraction_shadow_runs` にまだ run が無いこと。これで UNIQUE の衝突を避ける（F3）
  - 重複を除くこと。`(supplier_channel_id, line_posted_at, regexp_replace(raw_text,'\s','','g'))` ごとに1件だけを選び、created_at が最新のものを採る
  - 並べ方：古い投稿から
- 1件ごとの処理
  1. 本番と同じ関数で、raw_text・supplier_context・knowledge_links を読む（`tcg_extraction.py` の既存の読み込みを関数に切り出して使い回し、クエリを複製しない）
  2. `run_shadow_for_job` を呼ぶ
  3. 費用の台帳（`llm_usage_events`、purpose=`line_extraction_shadow`）について、実行を始めてからの累計を読む。`--max-cost-usd` を超えたら、そこで止める
- `--dry-run` のときは、対象の件数と先頭10件のジョブ ID を表示するだけにする。Gemini も呼ばず、DB にも書かない。
- 終わったら、処理件数・成功件数・失敗件数・費用の累計を表示する。
- 書き込み先は、`extraction_shadow_runs`、`extraction_shadow_results`、`llm_usage_events` だけ。旧方式の表（extraction_items、extraction_attempts、extraction_jobs）には書かない。

### 3-2. 変える既存コード
- `backend/app/tasks/tcg_extraction.py`：ジョブの原文・仕入元ルール・knowledge_links を読む部分を、関数 `load_extraction_context(session, extraction_job_id)` として切り出す。本番の動きは変えない（試験で確かめる）。

### 3-3. 触らないもの
- migration、deploy.yml、本番の scripts/、旧方式の経路、判定ロジック、画面

## 4. 実行の手順（本番。PO の GO が要る）
1. `--dry-run` で対象の件数を確かめる（読み取りだけ）
2. 最初の20件を流す（`--limit 20 --max-cost-usd 2`）→ 台帳で実際の費用を測り、見積もりを PO に報告する
3. PO の合意を得てから、残りを流す（`--max-cost-usd` は PO が決めた上限）

## 5. 測り方（流したあと）
1. 全項目の正答率
   - 無作為（seed 固定）に選んだ300まとまりについて、Opus が原文と商品マスタを見て判定する。
   - 判定する項目：区切り・商品・状態・単位・価格・数量・発送・完売
   - 項目ごとに「正解／誤り／確認待ち」を数える。
2. 新旧の比較：同じジョブについて、旧方式の extraction_items と、新方式の shadow_results を機械で突き合わせる。食い違ったものは、原文で判定する。

## 6. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| 対象の選び方が §3-1 のとおり | 単体試験（重複を除く・試運転済みを飛ばす・ルールのない仕入元を除く） |
| 費用の上限で止まる | 単体試験（台帳の累計が上限を超えたら止まり、Gemini を呼ばない） |
| dry-run は書き込まない | 単体試験（Gemini を呼ぶ関数と INSERT が呼ばれない） |
| 本番の抽出の動きが変わらない | 既存の tcg_extraction の試験がすべて緑 |

## 外部・過去事例の参照と我々への応用
- 過去事例（社内）：試運転の23回（2026-09-29〜30）は、本番の処理と同じ関数で動いた。今回もその関数（run_shadow_for_job）を使い回すので、新しい解析の経路は作らない。
- 外部事例：社内のデータで直接測れる作業のため、使わない。

## 維持の仕組み
- 守り手: 設計担当（Opus）が対象の選び方と上限を決める。Sonnet が試験を維持する。道具は一括測定の専用で、定期実行はしない。
