# design: import-history-redesign

## 目的

アップロード履歴テーブルで「このアップロードがどうなったか」を一目で把握可能にする。

## recon/ADR相互参照

- recon.md: `docs/handoff/release-import-history-redesign/recon.md` — import_job_messages中間テーブル経由の結合確認済み
- ADR-027 (i18n強制): `docs/adr/ADR-027-ui-internationalization.md` — ja.json/en.json両ファイルへのi18nキー追加が必須。ハードコード日本語禁止
- ADR-144 (UIガバナンス): `docs/adr/ADR-144-ui-governance.md` — 既存コンポーネント金型を優先。生select/生input/色直値禁止

## 変更前後

### 変更前の列
ファイル名 | メッセージ数 | 仕入元数 | 未解決数 | アップロード者 | ステータス | 確認状態 | 日時

### 変更後の列
ファイル名 | 新規メッセージ | 解決 | 未解決 | アップロード者 | 日時 | 詳細ボタン

## 変更内容

| ファイル | 変更 |
|---------|------|
| backend/app/routers/tcg_line_import.py | 履歴SQLをJOINクエリに変更、レスポンスモデル更新 |
| frontend/src/pages/super-admin/TcgLineImportPage.tsx | テーブル列差替え、CTAボタン追加 |
| frontend/src/locales/ja.json | i18nキー追加 |
| frontend/src/locales/en.json | i18nキー追加 |

## 検証方法

| 基準 | 検証方法 |
|------|---------|
| 新規メッセージ数が正しい | import_job_messagesでrelation_kind='created'の件数と一致 |
| 解決数が正しい | extraction_jobsでstatus IN ('done','empty')の件数と一致 |
| 未解決数が正しい | extraction_jobsでstatus IN ('pending','running','error')の件数と一致 |
| 詳細ボタンが動作する | クリックでImportWorkflowPanelが表示される |
| 削除した列が表示されない | 仕入元数/ステータス/確認状態が非表示 |

## 外部・過去事例の参照と我々への応用

該当なし（内部管理画面改善・UI列の差替えのみ）

## 維持の仕組み

守り手: `frontend/src/pages/super-admin/TcgLineImportPage.tsx` — テーブル列定義を保持。既存のImportWorkflowPanelが詳細表示を担当。i18nキーは `frontend/src/locales/ja.json` / `en.json` で管理。
