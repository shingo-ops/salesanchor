# recon: 生成型の初採用（便C-2、TcgSoldOutPage）

- 基準: origin/main `1690f48f3`（BASE_OK）
- 親テーマ: cross-dept-integrity-foundation（PR #3942）。根拠: ADR-1005。前提の便C-1（PR #3971）は本番反映済み。
- 調査: Sonnet（読み取りとローカル実行）。判断: Opus

## 事実
- tsc が走る場所:
  - `frontend/package.json:8`（`tsc && vite build`）
  - `.github/workflows/frontend-check.yml:37-39`（`npx tsc --noEmit`）
  - `frontend/Dockerfile:22`（`RUN npm run build`）。本番イメージは `.github/workflows/deploy.yml:360` でビルドされる。
- 生成される型ファイル（frontend/src/api/generated/schema.d.ts）は gitignore されている。生成しないまま import すると、上の3か所で tsc が失敗する。
- `frontend/Dockerfile` には `NODE_ENV=production` も `--omit=dev` も無く、`npm install` で devDependencies が入る。`frontend/.dockerignore` は api-contract/ を除外していない。`COPY . .` のあとに `npm run build` を実行すると、prebuild で生成が先に走る。
- 対象画面の API は1件だけ（`frontend/src/features/tcg-sold-out/soldOutApi.ts:34` の GET /tcg/sold-out-results）。backend 側は `backend/app/routers/tcg_analysis_review.py:188` で、response_model が付いている。
- 手書き型と生成型を照合した結果、違いは2つだった。
  - `supplier_id` と `product_id`: 手書きは `string | null`、backend の実際の形は `number | null`。
  - どちらも画面（`frontend/src/pages/super-admin/TcgSoldOutPage.tsx`）では使っていない。
  - それ以外の17フィールドと、レスポンスの5フィールドは一致した。
- SourceScope に当たる名前付きの列挙は生成型に無い。operation の query パラメータに `"all" | "active" | "history"` がある。
