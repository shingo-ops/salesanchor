# design: 全体の地図と関所（部署制の前提整備） / cross-dept-integrity-foundation

- 状態: 設計案（Opus作成・自己審査済み、判定は末尾）。
  - 2026-10-02、POは「便A → C → D → E の方向で進める」に「y」と回答した（この会話で）。
  - 新規ADRの採否（§6）と、既存テーマ（db-ssot・design-system）との範囲調整は未決。
  - 実装は未着手。
- 正本の参照:
  - KGI: `docs/handoff/cross-dept-integrity-foundation/kgi.md`（PO承認 2026-10-02）
  - 現状: `docs/handoff/cross-dept-integrity-foundation/recon.md`（origin/main `2ac19f708aae252098631da5274bd1b28162f9e0` 基準）
- 関連ADR:
  - ADR-027（i18n）、ADR-067（デザイントークン）、ADR-072（tenant lint）、ADR-121（process-artifacts gate）、ADR-135（相乗り防止・gate を main で必須化）、ADR-136（GO手順）、ADR-144（UIガバナンス）、ADR-155（商品マスタSSOT）、ADR-1003（GO委任）
  - 新規ADR案: 「配線台帳の自動生成とAPI型契約」（後述 §6）

## 1. 目的（PO定義より）
部署を分けても、データ・参照・画面部品が全体でずれない状態を、人の注意ではなく機械の検査で保証する。PO定義の原文は kgi.md にある。

## 2. 設計の原則（全便に共通）
1. **新しい正本を作らない。** 台帳は手書きにせず、コードから自動生成する。正本はコード（ルート定義、API呼び出し、FastAPIのルート）のまま残し、生成物との差分をCIで検査する。手で写した台帳は必ず古くなり、データが分散するため禁止する。
2. **既存テーマに寄せる。** 範囲が重なる部分は、既存テーマの正本を更新して扱う。
   - K2 のうちテーブル側は db-ssot（`docs/specs/db-ssot/kgi.md:8-14` の K2「正本の所在が設計書に明記」）に寄せる。
   - K4 は design-system の KGI⑤「関所」（`docs/specs/design-system/kgi.md:11-16`）に寄せる。
   - 本テーマは、各テーマの関所を main の必須チェックにつなぐ「配線役」を担う。
3. **1便＝1テーマ。** 便ごとに基準値を取り、反映後に測ってから次の便に進む。
4. **関所は二段階で入れる。** 最初は「増やさない（ラチェット）」で入れ、必須にする。既存の違反は別の便で減らし、0件になったら「絶対検査」へ切り替える。

## 3. 便の構成（変更前 → 変更後）

### 便A：K1-a　process-artifacts gate を main の必須チェックに戻す（ADR-135 に合わせる）
- 変更前: main の ruleset 15777895 の必須チェック13本に `process-artifacts gate` が無い（recon R1-2）。一方、`docs/adr/ADR-135-release-stowaway-prevention.md:48-51` には「登録済み」と書かれている。
- 変更後: 必須チェックを14本にする。
- 方法: `gh api` で ruleset を更新する。不可逆操作の一覧に入っているため、PO本人の `bash scripts/permit-danger.sh` が必要。
- 戻し方: ruleset から該当行を外す。
- コード変更: なし。
- 事前に確かめること（未確認の項目を潰す）:
  - 外れた時期と理由。ruleset の履歴を `gh api repos/.../rulesets/15777895/history` で確認する。読み取りのみ。
  - 意図して外したものなら、POに確認して止まる。

### 便B：削除（2026-10-02 PO判断）
Playwright E2E は休眠のままにし、K1 からも外す。
- 理由（recon R1-3、`e2e.yml:8-11`）: このE2EはAPIをmockしているため、部署間のずれを検出できない。1PRあたり約2分の増加にも見合わない。
- 部署間のずれは便Cで止める。

### 便C：K3　フロントとバックの型を自動で照合する
- 変更前: フロントの型はすべて手書き（export 258件・94ファイル、recon R3）。型生成の仕組みもCIの照合も無い。
- 変更後:
  1. backend に `scripts/export_openapi.py` を足す。サーバーは起動せず、`app.openapi()` で `frontend/src/api/schema.json` を出力する。FastAPI の `openapi()` は、起動しなくてもスキーマの dict を返す（Context7 /websites/fastapi_tiangolo で確認済み）。
  2. frontend の devDependency に `openapi-typescript` を足し、`frontend/src/api/schema.d.ts` を生成する（`npx openapi-typescript schema.json -o schema.d.ts`。Context7 /websites/openapi-ts_dev で確認済み）。
  3. 新しい workflow を作る。schema.json を作り直して差分を見るのと、`openapi-typescript --check` の2つで、生成物が古ければ赤にする（`--check` の動作は Context7 の CLI 文書で確認済み）。
  4. 手書きの型から生成型への置き換えは、部署ごとの別便で行う。置き換えが済んだ画面は、API の形が変わると `tsc` が赤になる。
- 新しい依存の追加になるため、新規ADRが必要（§6）。
- 戻し方: workflow を削除し、devDependency を外す。
- リスク: backend の Pydantic 定義が緩いと、生成型も緩くなる（例: `dict`）。これは置き換えの便の中で、1APIずつ詰める。
- 【未確認】本番で `/openapi.json` が外部に公開されているか。`backend/app/main.py:190-191` は docs/redoc だけを本番で無効にしており、`openapi_url` は指定していない。FastAPI の既定では `/openapi.json` は有効のまま（Context7 で確認済み）。本便では変更しないが、API の一覧が外部から見えてよいかは、セキュリティの判断として別に起票する（§8）。

### 便D：K2　配線台帳を自動生成し、ずれたら赤にする
- 変更前: 画面 → API → テーブルの台帳は無い（recon R2-5）。ルートは125個（ページは114）、backend の include_router は113件。
- 変更後:
  1. `scripts/generate-wiring-ledger.js` を作る。ADR索引の生成（`scripts/generate-adr-index.js`）と同じ型にする。
     - `frontend/src/App.tsx` のルートと、ページから辿る import のグラフを読む。
     - その先にある `api.<method>(` のパスを集め、便Cの schema.json（API一覧）と照合する。
     - 結果を `docs/specs/wiring/ledger.md` に出力する。
  2. CI に「wiring ledger is up to date」を足す（`--check`、ADR index と同じ方式）。あわせて、次の2つを赤にする。
     - 台帳に無いAPIを画面が呼んでいる（存在しないAPIへの呼び出し）。
     - schema に無いパスへの呼び出し。
  3. API → テーブルの部分は db-ssot テーマの K2（正本の所在）に渡す。本便では「画面 → API」までを機械で保証する。
- 【未確認】ルーター関数から触るテーブルを静的に取れるかは調べていない。段階を分けるのはこのため。
- 前提: 便Cが先に終わっていること（API一覧の正本が schema.json になるため）。
- 戻し方: workflow と生成物を削除する。

### 便E：K4　デザインの関所を必須にし、既存の違反を減らす
- 変更前（recon R4、関所の数え方）:
  - 生select 60件・生input 216件・自作タブ31件。
  - hex 56件（index.css を除く）。
  - 番号の無い ui-allow が2件。
  - hexラチェット（`design-token-guard.yml`）は必須ではない。
  - ESLint はインラインスタイルの hex しか見ない（`frontend/eslint.config.js:40-48`）。
  - 日本語の直書きは CI では warn（`frontend/eslint.config.js:31`）。
- 変更後（この順に、1つずつ便を分ける）:
  - E1: 番号の無い ui-allow 2件（`ConditionsPage.tsx:501`、`UnitMasterPanel.tsx:361`）に課題番号を付ける。対象の部品を金型に置き換えられるなら置き換える。
  - E2: hexラチェットを main の必須チェックに加える。ruleset の変更なので permit-danger が要る。
  - E3: UIガバナンスの対象を `frontend/src/features/`・`frontend/src/components/` に広げる。今は対象が pages/ だけ（`scripts/check-ui-governance.js:36`）。
  - E4: 既存の違反を部署（ページ群）ごとに置き換える。金型は `Select`／`SelectControl`、`TextField`、`Tabs`（recon R4-2）。
    - ADR-144 が推奨する `OverflowTabs`・`SearchBar` は、`components/` にまだ無い（recon R4-2）。先に design-system テーマで金型として登録してから置き換える。
  - E5: すべて0件になったら、「増やさない」検査から「絶対検査」に切り替える。日本語直書きの検査も warn から error に上げる。
- 数え方の食い違い（ADR-144 の記載では input 16・select 118、design-system kgi では hex 36）は、E4 の便の冒頭で数え方を一本化し、正本（design-system の kgi.md）を更新する。

## 4. 実施の順番
A → C → D → E1 → E2 → E3 → E4（部署ごとに繰り返す）→ E5。
すべて終わって K1〜K4 が○になったら、K5 として部署制（③商品・在庫部）の試行に入る。

## 5. 受入基準
| 基準 | 検証方法 |
|---|---|
| K1: main の必須チェックに process-artifacts gate がある | `gh api repos/shingo-ops/salesanchor/rulesets/15777895 --jq '..|.context? // empty'` の出力にその名前がある |
| K2: 全ページ（114）が台帳に載り、漏れが0件 | `node scripts/generate-wiring-ledger.js --check` が exit 0 で、台帳のページ数＝App.tsx のページルート数 |
| K3: 型のずれでCIが赤になる | 検証用PRで backend のレスポンスのフィールド名を1つ変え、型照合の job が赤になることを確認したら PR を閉じる |
| K4: 生select・生input・自作タブ・hex・不正 ui-allow が0件で、検査が必須に入っている | `scripts/check-ui-governance.js` の全数モードと hex の数え方で0件。ruleset に hexラチェットがある |
| 各便: 基準値と反映後の値を記録した | `docs/handoff/cross-dept-integrity-foundation/track-record.md` に便ごとの before/after がある |

## 6. 新規ADR案（便Cの前に起票。POの承認が必要）
- 題名（案）: ADR-NNNN 配線台帳の自動生成とAPI型契約（OpenAPI→TypeScript）
- What: FastAPI のスキーマを正本にして、フロントの型と画面→APIの台帳を生成する。ずれはCIで止める。
- Why: 部署ごとに作業しても、API の形の変更が他部署の画面を壊さないようにするため（PO定義・R4）。手書きの型と手書きの台帳はSSOTに反し、データの分散を生む。
- 代替案と不採用の理由:
  - 契約テスト（Pact）: 消費側と提供側を別々に管理する仕組みで、1つの repo に同居する構成には重い。
  - 手書きの台帳: 必ず古くなる。

## 7. 外部・過去事例の参照と我々への応用
- Anthropic「How we built our multi-agent research system」（2025-06-13）:
  - 事例の内容: エージェント同士の依存が多い作業は、マルチエージェントに不向き。
  - 我々への応用: 部署を分けるなら、部署の間の依存（API・データ）を機械で固定しておく必要がある。これが本設計の根拠。
  - 適用の限界: 調査タスクでの結果で、Sales Anchor で測った値ではない。
- 社内の過去事例（ADR索引の自動生成）:
  - 事例の内容: `scripts/generate-adr-index.js --check` が必須チェック「ADR index is up to date」として機能している（recon R1-1 #9）。
  - 我々への応用: 便Dの台帳は、同じ「生成して差分を見る」方式にする。実績のある型なので、新しく覚えることが少ない。
- 社内の過去事例（E2E停止）:
  - 事例の内容: CI時間の都合で必須の検査を止め、そのまま4か月放置された（recon R1-3）。
  - 我々への応用: 関所を止めるときは、再開の条件と期限を書く。§9 の守り手で監視する。

## 8. 対象外
- 製品機能の変更。
- 本番データの変更。
- 本番で `/openapi.json` が公開されている件の是非（セキュリティ判断として別に起票する）。
- API → テーブルの対応付け（db-ssot テーマで扱う）。
- 部署定義ファイルの作成（K5 で扱う）。

## 9. 維持の仕組み
- 守り手: `.github/workflows/adr-index-check.yml`（便Dで同じ型の台帳検査を足す見本）
- 守り手: `scripts/check-ui-governance.js`（便Eで対象範囲を広げる）
- 守り手: `scripts/check-design-token-ratchet.sh`（便E2で必須にする）
- 守り手: `scripts/check-process-artifacts.js`（便Aで main の必須に戻す）
- 停止した関所の監視: 関所を `if: false` などで止めるときは、PR本文に再開の期限を書く。期限切れを検出する仕組みの追加は、process-hardening テーマへ渡す。

## 10. リスクと戻し方
| リスク | 起きること | 対処・戻し方 |
|---|---|---|
| 必須チェックを足したことで、無関係なPRが止まる | 開発が止まる | 便ごとに、必須にする前に「必須ではない」状態で1週間動かし、失敗率を確認する。戻すときは ruleset から外す |
| 生成型への置き換えで画面が壊れる | 表示崩れ・型エラー | 部署ごとに別の便で行い、`tsc` と人の動作確認で確かめる |
| 台帳の静的解析が漏れる | 載らない画面が出る | `--check` でページ数と照合する。漏れは赤にして、解析の方を直す |
| 数え方の不一致 | 件数を誤って報告する | E4 の冒頭で数え方を一本化し、正本の kgi を更新する |

---

## 自己審査（Architect役・同一AIによる。第三者のレビューではない）
| 観点 | 判定 | 根拠・指摘 |
|---|---|---|
| 既存仕様・ADRとの整合 | OK | 便Aは ADR-135 に実機を寄せる（CLAUDE.md の最上位原則）。K2・K4 は既存テーマに寄せ、正本の重複を作らない |
| 根拠の十分さ | 条件付き | 件数・設定は origin/main 基準で、ファイル:行が付いている。未確認が3点ある（ruleset から外れた経緯、ルーター→テーブルの静的抽出が可能か、CIでの hex 件数＝ugrep と GNU grep の差）。いずれも、該当する便の着手前に潰す手順を書いた |
| 受入条件の検証可能性 | OK | §5 は全項目をコマンド1本、または検証PRで○×判定できる |
| 実装範囲の明確さ | 条件付き | 便A〜E1 は実装カードにできる粒度。C・D・E3 は新規ADRの承認後に、変更前後のコードまで書いたカードを作る |
| PO判断事項 | あり | ①新規ADR（OpenAPI型契約）の採否 ②範囲が重なる既存テーマ（db-ssot・design-system）を本テーマから動かしてよいか。（便Bの判断は 2026-10-02 に削除で決着） |

**判定: REVISE（条件付き）**
- 設計の方向性と便A・E1 は、実装カードを作れる状態にある。
- 便C・D は新規ADRの承認が前提で、POの判断が済むまで実装可能とはしない。
