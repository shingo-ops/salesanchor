# design — distui-01 配信先管理 UI（CC_TASK_DISTUI-01）

参照: `docs/handoff/distui-01/recon.md`
対象: ADR-154（TCG PARITY-02 配信機能）

## KGI / 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `/super-admin/tcg-distribution` にアクセスできる | ブラウザで URL 直打ち → 403 表示なし |
| 配信先一覧に既存レコードが表示される | 「納品テスト」1件が表示されること |
| プレビューカードに配信候補件数が表示される | `GET /tcg/distribution/preview` の `output_count` が表示されること |
| 新規登録: SA 未共有シートは保存できない | アクセスできないシートIDを入力 → エラーメッセージと共有手順が表示されること |
| 無効化: ボタンで `is_active=false` になる | 無効化後、行がグレーアウトされ配信ボタンが消えること |
| 個別配信: 確認ダイアログ後に実行できる | 配信実行後、行の「最終結果」列に結果が表示されること |

## 実装方針

`frontend/src/features/tcg-distribution/` 以下に機能を集約し、
`frontend/src/pages/super-admin/TcgDistributionPage.tsx` からコンポーズする。

- `DistributionPreview.tsx` — `GET /tcg/distribution/preview` で件数を表示
- `DistributionTargetList.tsx` — 一覧テーブル・無効化・個別配信
- `DistributionTargetForm.tsx` — 登録/編集ドロワー（保存前 verify-access チェック）
- `distributionApi.ts` — API 型定義・呼び出し関数
- `distribution.css` — ADR-067 デザイントークン準拠スタイル

## 外部・過去事例の参照と我々への応用

`TcgSupplierQualityPage.tsx` が同じ super-admin パターンを実装済み。
`useSuperAdmin()` フック・`PageLayout` の使い方を踏襲することで
認証まわりの実装を再発明しない。

保存前の Google Sheets アクセス確認については、gspread の
`_verify_spreadsheet_id()` ヘルパーが既に存在するため、
新規 verify-access エンドポイントはこれを呼び出すだけで実装できる。

## 影響範囲

- 変更ファイル: `backend/app/routers/tcg_distribution.py`（`verify-access` 追加のみ）
- 変更ファイル: `backend/app/services/tcg_distribution_svc.py`（`verify_spreadsheet_access()` 追加のみ）
- 新規ファイル: `frontend/src/features/tcg-distribution/` 以下 5 ファイル
- 新規ファイル: `frontend/src/pages/super-admin/TcgDistributionPage.tsx`
- 既存ファイル: `frontend/src/App.tsx`（1ルート追加のみ）
- 既存ファイル: `frontend/src/locales/ja.json` + `en.json`（キー追加のみ）
- 既存ファイル: `frontend/src/index.css`（`--color-error-bg-subtle` トークン追加のみ）

## 戻し方

```bash
git revert <マージSHA>
```

## 維持の仕組み

守り手: 人手で守る（super-admin 専用画面・PR review が守り手。CSSTトークン ADR-067 はフック強制）

- ADR-067 CSS チェックフック（pre-commit）が distribution.css の設計トークン違反を検出する
- ADR-027 i18n チェックが `t("key")` 漏れを検出する
- `useSuperAdmin()` フックが `is_super_admin` 認証を強制する（バイパス手段なし）
