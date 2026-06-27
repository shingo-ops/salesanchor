# design.md — 検証用フィーチャーデモ一式削除

## 参照

- recon: `docs/handoff/cleanup-feature-demo/recon.md`
- ADR-027: `docs/adr/ADR-027-ui-internationalization.md`（i18n キー削除の根拠）
- ADR-143: `docs/adr/ADR-143-send-guard.md`（Phase B cherry-pick: dangling-route gate 解消のため取り込み）
- 機能スイッチ実装 PR: #2631（スイッチ本体は残す）

## 目的

テナント機能スイッチ MVP（#2631）の KGI 検証完了に伴い、検証専用コードを削除する。
スイッチ本体（tenant_features テーブル・require_feature・useFeatures・FeatureGate）は残し、
将来の実機能（inventory_v2 等）への転用に備える。

## 変更内容

| # | 対象 | 操作 |
|---|---|---|
| ① | `frontend/src/pages/dashboard/DashboardPage.tsx:34,461-465` | FeatureGate バナーブロック + import 削除 |
| ② | `backend/app/routers/feature_demo.py` | ファイルごと削除 |
| ③ | `backend/app/main.py:51,381-385` | import 行 + include_router ブロック削除 |
| ④ | `frontend/src/locales/ja.json:3060-3062` / `en.json:3060-3062` | featureDemo キー削除 |

## migration

なし（コード削除のみ）。

## 外部・過去事例の参照と我々への応用

検証用コードは KGI 確認後に速やかに削除するのが定石（"Clean as you go" 原則）。
今回の削除により、フィーチャーフラグ基盤（FeatureGate・require_feature）は
本番コードとして残り、実機能への差し替えを最小変更で行える状態になる。

## 検証基準

| 基準 | 検証方法 |
|---|---|
| B1 DashboardPage に FeatureGate バナーが非表示 | CI フロントエンド lint + ビルド通過 |
| B2 GET /api/v1/feature-demo/ping が 404 | 既存テスト通過（エンドポイント削除のみ） |
| B3 featureDemo i18n キーが存在しない | i18n キー整合性チェック通過 |
