---
mode: handoff
---
# 実装カード 便C-2: 生成型の初採用（TcgSoldOutPage）と生成の配線

- 根拠: ADR-1005（Accepted）、design.md 便C、便C-1（PR #3971、本番反映済み）
- 現状調査: 2026-10-06 Sonnet 調査（origin/main `a77cfb1c0`）。詳細は scratchpad の rep.txt。要点は下のとおり
- この便の目的:
  - 画面のコードで、生成型を初めて使う。
  - 「API の形が変わると画面のビルド（tsc）が赤になる」状態を、1画面で実際に成立させる。
  - それを支える生成の配線（ビルド前・CI の型検査前）を整える。

## 調査で分かった事実（設計の前提）
- 生成物の型ファイル（frontend/src/api/generated/schema.d.ts）は gitignore されている。生成しない環境で import すると、tsc が失敗する。
- tsc が走る場所は次の3つ。
  1. `frontend/package.json:8` の `"build": "tsc && vite build"`
  2. `.github/workflows/frontend-check.yml:37-39` の `npx tsc --noEmit`（その前の `npm ci` は :25-27）
  3. `frontend/Dockerfile:22` の `RUN npm run build`。本番イメージは `.github/workflows/deploy.yml:360` の `docker compose build` で作られる。**生成の配線をしないまま import を入れると、本番のビルドが止まる。**
- `frontend/package.json:50-51` は `predev` / `prebuild` = `npm run generate:icon-sizes`。
- 最初の対象を TcgSoldOutPage にした理由:
  - API 呼び出しは1件だけ（`frontend/src/features/tcg-sold-out/soldOutApi.ts:34` の `GET /tcg/sold-out-results`）。
  - backend の `backend/app/routers/tcg_analysis_review.py:188` には `response_model` がある。
  - openapi.json のスキーマは具体的（`SoldOutResultsResponse`）。
  - 手書き型は3つで、すべて同じファイルにある（`soldOutApi.ts:3,4,25`）。
- 生成型の参照方法は `components["schemas"]["SoldOutResultsResponse"]` と `components["schemas"]["SoldOutResultItem"]`。export されているのは paths / webhooks / components / $defs / operations の5つで、frontend/src の既存の名前と衝突しない。

## 変更（変更前 → 変更後）

### 1. frontend/package.json
- `"predev": "npm run generate:icon-sizes"` → `"predev": "npm run generate:icon-sizes && npm run generate:api-types"`
- `"prebuild": "npm run generate:icon-sizes"` → `"prebuild": "npm run generate:icon-sizes && npm run generate:api-types"`
- 他は変えない。

### 2. .github/workflows/frontend-check.yml
- `npm ci`（:25-27）の直後、`npx tsc --noEmit`（:37）より前に、step を1つ足す。中身は `run: npm run generate:api-types`（working-directory は frontend）。
- 他は変えない。

### 3. frontend/src/features/tcg-sold-out/soldOutApi.ts
- 手書きの `SoldOutItem` と `SoldOutResponse` を、生成型の別名に置き換える。
  ```ts
  import type { components } from "../../api/generated/schema";
  export type SoldOutItem = components["schemas"]["SoldOutResultItem"];
  export type SoldOutResponse = components["schemas"]["SoldOutResultsResponse"];
  ```
- `SourceScope` の扱いは、生成型に同じ値の列挙（enum / union）があるかどうかで決める。
  - ある場合は別名にする。
  - 無い場合は手書きのまま残し、理由をコメントに1行書く。
- 画面側（`frontend/src/pages/super-admin/TcgSoldOutPage.tsx:11` の import）は、名前を変えないので触らない。

## 着手前の実物点検（分岐ごとの対処。違っていたら止まる）
1. **本番のビルドで生成できるかを確かめる。**
   - `frontend/Dockerfile` を全文読み、次の2点を確認する。
     - `npm install` の時点で devDependencies が入るか（`NODE_ENV=production` や `--omit=dev` が無いか）
     - `frontend/.dockerignore` が `api-contract/` を除外していないか
   - devDependencies が入らない場合、または `api-contract/` が除外されている場合は、止まって報告する。Dockerfile を変えるかどうかは設計者が判断する。
2. **型の中身を照合する。**
   - 手書きの `SoldOutItem` / `SoldOutResponse` と、生成型 `SoldOutResultItem` / `SoldOutResultsResponse` のフィールドを1つずつ比べ、表にして貼る。比べる項目は、名前・型・null を許すか・省略できるか。
   - 違いがあれば、次の2つに分けて書く。
     - 画面が使っていて、型が変わると tsc が赤になるもの
     - 画面が使っていないもの
   - 違いの修正は、画面側を生成型（＝backend の実際の形）に合わせる方向だけにする。backend は変えない。修正が `TcgSoldOutPage.tsx` の表示ロジックに及ぶ場合は、止まって報告する。

## 検証（実装役が実行し、生出力を貼る）
| 基準 | 検証方法 |
|---|---|
| 生成物が無い状態からビルドできる | `frontend/src/api/generated/schema.d.ts` を消してから `npm run build` を実行し、成功する。消すときは rm を使わず、`git clean -n` で対象を確認してから `git clean -fX frontend/src/api/generated/` を使う。ignore されたファイルなので、このコマンドで消える |
| CI の型検査が通る | PR で `Frontend lint & custom checks` と `frontend-check` の tsc が pass |
| API の形のずれで画面のビルドが赤になる | 一時的に backend の `SoldOutResultItem` のフィールド名を1つ変え、export と生成をし直すと、`npx tsc --noEmit` が赤になる。確認したら戻す。commit はしない |
| 既存の検査が壊れていない | `npm run lint`（0 errors、警告は main と同じ数）、`npm run check:all`、`npm run test:unit`（関係するものがあれば） |
| 本番 | マージ後に deploy run が success、`https://app.salesanchor.jp/` が 200、PO が実機で /super-admin/tcg-sold-out の表示を確認する（人の動作確認） |

## 触らない範囲
- backend 全体
- ほかの画面
- `frontend/Dockerfile`（点検1で問題があれば止まる）
- ruleset
- `scripts/` の下
- `deploy.yml`、`workflow-lint.yml`

## GO
- frontend/src を変更するので、process-artifacts gate が GO 記録を必要とする。PO 本人の「GO #<番号>」をもらってから転記する。

## 戻し方
- PR を revert する。prebuild の行を戻せば、生成の配線も元に戻る。
