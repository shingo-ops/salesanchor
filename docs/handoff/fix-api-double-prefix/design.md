# design: API 呼び出しの /api/v1 二重の修正

対象ADR: ADR-152（docs/adr/ADR-152-frontend-api-path-no-prefix.md）
参照: docs/handoff/fix-api-double-prefix/recon.md

## 変更
- 6か所の path 先頭の `/api/v1` を外す（frontend/src/pages/admin/ChannelMastersPage.tsx、frontend/src/pages/inbox/ManualRecordSection.tsx、frontend/src/pages/company-detail/CompanyConvLogsTab.tsx）。
- 再発防止: frontend/src/lib/api.no-double-prefix.test.ts を追加（api クライアント呼び出しの第1引数が /api/v1 で始まるものが0件）。
- 触らない: frontend/src/lib/api.ts、backend、nginx、文言、CSS、i18n。

## 受入条件
|基準|検証方法|
|---|---|
|6か所の二重がなくなる|追加テスト（main で赤・修正後で緑）と git grep|
|既存の挙動が壊れない|vitest 全体、lint、tsc を main と比較|
|本番で `/api/v1/api/v1/` が0件|デプロイ後に Opus が本番 nginx ログで数える|
|再発を検出できる|追加テスト（CI の Frontend テスト）|

## 外部・過去事例の参照と我々への応用
- 過去事例: ADR-152（PR #3181 の TcgParallelReportPage.tsx が /api/v1 を付けて本番 404）。同一パターンの再発。
- 応用: ADR-152 が推奨しながら未実装だった機械検出を vitest で実装し、CI で毎回検出する。
- 外部事例: 不要（リポジトリ内の api クライアント規約 frontend/src/lib/api.ts:29 に合わせる局所修正のため）。

## 維持の仕組み
守り手: 追加テスト（CI）。frontend/src/lib/api.no-double-prefix.test.ts が CI の Frontend テストで毎回走る。
