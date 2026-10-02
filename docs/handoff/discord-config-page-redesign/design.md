# design: Discord 連携設定ページ再設計

この文書は「Discord 連携設定ページをどう作り直し、PC の下部タブバーをどう消すか」を決めた記録です。

親: [docs/specs/management-center/ideal-state.md](../../specs/management-center/ideal-state.md) ／ 子: [recon.md](./recon.md)

recon: docs/handoff/discord-config-page-redesign/recon.md

対象ADR: ADR-144, ADR-067, ADR-149（関連: ADR-027, ADR-091）

## PO 原文・承認

「文字が冗長に書かれていてUI/UXに考慮できていない素人くさいページになっている。非エンジニアでも直感的にわかりやすくて見やすいページデザインを作ってほしい。またPCサイズなのに下部にタブバーが入っているので削除してくれ」
「この案で作る (推奨)」

## Before / After

| 項目 | Before | After |
|---|---|---|
| 構成 | 4 ブロックが区切りなしで縦並び | カード 3 枚（①サーバー接続 ②自動セットアップ ③チケットの案内文）+ 折りたたみ「詳細設定」 |
| サーバー接続 | 常に入力欄 + 説明 | 状態バッジ（接続済み / 未接続）。接続済みは ID を文字表示 + [変更] |
| 自動セットアップ結果 | フラット 10 行・色付き文字 | ロール / カテゴリ / チャンネル / ボタンに分け、各行にバッジ（作成・更新・既存・投稿・失敗） |
| 入力欄 | 8 個を常時表示（`estimated_scale` 等の内部用語） | 通常は案内文 1 個のみ。ID 類は「詳細設定（通常は変更不要）」内に平易な名前で格納 |
| 自動セットアップ後 | `created` のみ入力欄に反映 | 完了・一部失敗のとき両 API を再取得して最新値を反映 |
| PC の下部タブ | 表示 | 非表示（モバイル ≤767px のみ表示・変更なし） |
| PC での入口 | タブバーのみ | 管理センター左メニューに 4 項目追加 |

## 変更範囲（触るファイルと触らない範囲）

触る: `frontend/src/pages/admin/DiscordConfigPage.tsx`（全面書き換え）、`frontend/src/pages/admin/discord-config.css`（新規・var() のみ）、`frontend/src/pages/admin/AdminHubPage.tsx`（`useIsMobile` で nav を条件描画）、`frontend/src/pages/management-center/ManagementCenterPage.tsx`（4 項目追加）、`frontend/src/locales/ja.json`・`frontend/src/locales/en.json`（discordConfig / discordTicketConfig / discordAutoSetup を短文化・不要キー削除・`discordConfig.syncStatus` は LeadsPage が使用中のため維持）、テスト 3 本（新規）。
触らない: backend、`admin-hub.css`、他の admin ページ、DesktopShell / MobileShell、API 仕様。

## 金型

Card / Badge / TextField / Textarea / Button / ButtonLink / PageLayout / SubMenu のみ。新規コンポーネントなし。生 input・生 textarea・色直値・`ui-allow` なし。通知枠の金型は無いため Badge(warning) + ButtonLink で表現。

## 外部・過去事例の参照と我々への応用

該当なし（理由: 既存デザインシステムの金型を組み合わせる内部 UI 整理で、新規概念・外部サービス導入なし）。

## 受入条件

| 基準 | 検証方法 |
|---|---|
| 未接続: 入力欄 + [接続する]、自動セットアップは無効で理由が出る | DiscordConfigPage.test.tsx「shows unconnected state…」 |
| 接続済み: ID が文字表示、[変更] で入力欄が出る | 同「shows connected state…」 |
| 結果が 4 種類に分かれ、各行に正しいバッジが付く | 同「groups auto setup results…」 |
| 自動セットアップ後に 2 API を再取得する | 同「re-fetches both configs…」 |
| 詳細設定は初期で閉じ、aria-expanded で開閉、7 項目が出る | 同「keeps advanced settings collapsed…」 |
| PC で下部タブが無い／モバイルで 6 タブ | AdminHubPage.test.tsx（useIsMobile をモック） |
| 管理センターに 4 項目、権限が無いと非表示 | ManagementCenterPage.test.tsx |
| ja/en キー一致・日本語ハードコードなし | `npm run check:all`（check:i18n-missing-keys, lint） |
| 色・余白は var() のみ | `npm run check:all`（check:css-colors, check:css-values, check:stylelint） |
| ビルド・全ユニット・Storybook が通る | `npm run build` / `test:unit` / `build-storybook` |

## 維持の仕組み

守り手: .github/workflows/frontend-check.yml（CI: lint・i18n・build・test）と frontend/scripts/check-i18n-missing-keys.js（ja/en 一致）、ESLint の UI ガバナンス規則（ADR-144: 生 input 禁止）、上記 3 本のユニットテスト
対象: 金型の使用・ja/en 一致・PC でタブバーが出ないこと・4 項目の入口が残ること
