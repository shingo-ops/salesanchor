# design: review@salesanchor.jp locale 強制 en 解除

## recon 参照

`docs/handoff/remove-review-locale-en/recon.md`

## 対象 ADR

ADR-027 (`docs/adr/ADR-027-ui-internationalization.md`)

## 変更内容

`migrations/053_add_users_locale.sql` から撮影用の `UPDATE ... SET locale = 'en'` 行を削除する。撮影時は UI の言語切り替えで対応する。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| review@salesanchor.jp でログインすると日本語 UI が維持される | ログイン後 `/staff/me` の locale が `ja` を返すことを確認 |
| 次のデプロイ後も locale が en に戻らない | デプロイ後 DB で `SELECT locale FROM public.users WHERE email = 'review@salesanchor.jp'` が `ja` を返すことを確認 |

## 外部・過去事例の参照と我々への応用

該当なし。migration ファイルのデータ行削除のみ（スキーマ変更なし）。過去事例・外部事例を参照する必要はない。
