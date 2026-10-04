# ADR-1005: API型契約（OpenAPI→TypeScript）と配線台帳の自動生成

- 状態: Accepted
- 起案日: 2026-10-04
- 起案: Claude Opus（設計担当）
- 決定者: Shingo（PO）
- 承認: 2026-10-04。ccopusgo セッションのチャットで「ADR-1005 を承認するか（y/n）」に対し、PO本人が「ｙ」と回答した。
- 関連: ADR-027, ADR-067, ADR-072, ADR-135, ADR-144
- 設計: docs/handoff/cross-dept-integrity-foundation/design.md（便C・便D）
- 現状調査: docs/handoff/cross-dept-integrity-foundation/recon.md

## Context（事実。origin/main 基準）
- フロントのAPIレスポンス型はすべて手書きで、export 宣言が258件・94ファイルある。型を生成する道具もCIでの照合も無い（recon R3）。
- backend のエンドポイント612件の内訳（`backend/app/routers/*.py` 114ファイルを ast で数えた。2026-10-04）:
  - `response_model=` あり: 377件（61.6%）
  - `response_model` は無いが戻り値の型注釈あり: 80件
  - どちらも無し: 155件（25.3%）。ファイル単位では `backend/app/routers/tcg_distribution.py` の11件がすべて型無し。
  - 型ありの457件（74.7%）は「スキーマが役に立つ形で出る」件数の上限である。`-> dict` のような注釈も数に含めている。
- FastAPI は、サーバーを起動しなくても `app.openapi()` でスキーマを生成できる（Context7 /websites/fastapi_tiangolo で確認）。openapi-typescript は CLI でスキーマから型を生成でき、`--check` オプションで生成物が古いかどうかを確かめられる（Context7 /websites/openapi-ts_dev で確認）。
- 本番の API パス /openapi.json と /docs は、外部からのアクセスにどちらも 404 を返す（2026-10-04 に curl で確認）。スキーマは外部に公開されていない。
- 画面 → API → テーブルの台帳は存在しない（recon R2-5）。テーブル参照は `tenant_table_ref(db, tenant_id, "<テーブル名>")` の文字列リテラルで書かれており（例: `backend/app/routers/leads.py:200,255,963`）、テーブル名を機械的に抜き出せる可能性がある。ただし全件では未確認。
- 部署（業務領域）ごとに作業を分けると、ある部署の API の形の変更が別部署の画面を壊しても、今の必須チェックでは検出できない。配線を見ているのは、削除されたルートを検出する dangling-route gate だけである（recon R1-1）。

## Decision（案）
1. FastAPI のスキーマを API の形の正本とする。手書きの型や手書きの台帳は新しく作らない（SSOT）。
2. CI でスキーマと TypeScript 型を生成し、コミット済みの生成物と差があれば赤にする。
3. 手書きの型から生成型への置き換えは、業務領域（部署）ごとの別便で行う。型の無いエンドポイント155件には、置き換えの便の中で `response_model` を付ける。
4. 画面 → API の台帳をコードから自動で生成し（ADR索引と同じ「生成して差分を見る」方式）、台帳とスキーマに無いAPIを呼ぶ画面があれば赤にする。API → テーブルの部分は db-ssot テーマの K2 に寄せる。
5. 新しい依存として、frontend の devDependency に openapi-typescript を1つ加える。実行時の依存は加えない。

## 代替案と不採用の理由
- 契約テスト（Pact など）: 消費側と提供側を別々に運用する前提の道具で、1つのリポジトリに両方がある今の構成には重い。
- 手書きの台帳や手書きの型を続ける: 必ず古くなり、データが分散する（PO定義 2026-10-02 に反する）。
- E2E（Playwright）で代用する: 今の E2E は API を mock にしているため、API の形のずれを検出できない（`.github/workflows/e2e.yml:8-11`）。

## Consequences
- 良くなること: 型を付けたエンドポイントは、形が変わると、それを使う画面のビルド（`tsc`）が赤になる。部署をまたぐずれが、マージの前に止まる。
- 限界: 型の無い155件（25.3%）は、`response_model` を付けるまで保護されない。最初は保護される範囲が全体の最大74.7%になる。
- 費用: CI に生成と照合の job が1つ増える。所要時間は導入時に測る。
- 戻し方: workflow を削除し、devDependency を外す。生成物は残しても、実行には影響しない。

## 受入条件
| 基準 | 検証方法 |
|---|---|
| スキーマと型が生成物と一致していないとCIが赤になる | 検証用PRで backend のレスポンスのフィールド名を1つ変え、照合の job が赤になることを確認する |
| 型の無いエンドポイントの件数が、置き換えの便ごとに減る | `scratchpad` の count.py と同じ ast 集計を repo のスクリプトにして、便ごとに before/after を track-record に記録する |
| 台帳の漏れが0件 | 台帳のページ数と、App.tsx のページルート数（2026-10-02 時点で114）が一致する |
