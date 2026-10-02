# recon: Discord 連携設定ページ再設計

この文書は「Discord 連携設定ページを分かりやすく作り直す前に、いまの画面がどうなっているかを実コードで確かめた記録」です。

親（管理センター仕様）: [docs/specs/management-center/ideal-state.md](../../specs/management-center/ideal-state.md)

## PO 原文（2026-10-03）

「文字が冗長に書かれていてUI/UXに考慮できていない素人くさいページになっている。非エンジニアでも直感的にわかりやすくて見やすいページデザインを作ってほしい。またPCサイズなのに下部にタブバーが入っているので削除してくれ」
承認済み設計: 「この案で作る (推奨)」

## 既存 ADR 検索結果

`git grep -i discord docs/adr/FEATURE-INDEX.md` で ADR-091（Discord Bot）・ADR-159 を確認。UI 部品規約は ADR-144、トークンは ADR-067、SubMenu のリンク型は ADR-149、i18n は ADR-027。本件はいずれの決定も変更しない（適用のみ）。

## 現在地（origin/main 76378b929 時点・事実）

| # | 事実 | 根拠 |
|---|---|---|
| 1 | 設定ページは 1 画面に 4 ブロック（Guild ID / 自動セットアップ / チケット設定 / ボタン設置）が縦に並び、チケット設定だけで入力 8 個 + 説明文が各 1〜2 行 | origin/main:frontend/src/pages/admin/DiscordConfigPage.tsx:258-529 |
| 2 | 生の `<input>` / `<textarea>` と Tailwind 風クラス（`space-y-*`, `text-token-*`）を使用。TextField / Textarea / Card / Badge の金型を未使用 | origin/main:frontend/src/pages/admin/DiscordConfigPage.tsx:263, :269, :452, :259 |
| 3 | 自動セットアップ後、`created` のステップだけを入力欄に反映（`skipped`/`updated` は反映されない） | origin/main:frontend/src/pages/admin/DiscordConfigPage.tsx:215-222 |
| 4 | 自動セットアップ結果は 1 行ごとに「ステップ名 + 色付き文字」のフラット一覧。種類のまとまりなし | origin/main:frontend/src/pages/admin/DiscordConfigPage.tsx:339-362 |
| 5 | 入力 2 項目に `estimated_scale` という内部用語を含む説明文 | frontend/src/locales/ja.json（変更前 discordTicketConfig.smallChannelIdHint 等） |
| 6 | 管理ハブ `/admin/*` は下部タブバーを常時表示（PC でも表示） | origin/main:frontend/src/pages/admin/AdminHubPage.tsx:63-76、frontend/src/pages/admin/admin-hub.css:9-69 |
| 7 | `useIsMobile`（≤767px）は既存フック。シェル切替で使用済み | frontend/src/hooks/useIsMobile.ts:15、frontend/src/App.tsx:133 |
| 8 | 管理センター左メニューに Discord連携 / Discordアナウンス / テナントポリシー / チャネル管理が無く、PC ではタブバー以外に入口なし | frontend/src/pages/management-center/ManagementCenterPage.tsx:36-80 |
| 9 | 4 ページのルートは実在 | frontend/src/App.tsx:365-380（`/admin` 配下 tenant-policy / discord-config / discord-announce / channel-masters） |
| 10 | SubMenu は `to` 指定でリンク型（ADR-149） | frontend/src/components/SubMenu.tsx:21-25 |
| 11 | 使える金型: Card / Badge / TextField / Textarea / Button / ButtonLink / PageLayout | frontend/src/components/（各 .tsx の存在を ls で確認） |

## 設計仕様書（あるべき姿）

該当する理想形の仕様は管理センター領域: docs/specs/management-center/ideal-state.md（読了・本件は入口追加のみで理想形と矛盾しない）。

## 未確認

- 本番画面の実機目視（本 PR は CI とユニットテストまで。PO の画面確認が必要）
- `/admin/channel-masters` を操作できる権限の正確な名称（バックエンドは `get_current_user` のみ。メニュー表示は `tenant.profile.edit` としたが、PO 判断で変更可）
