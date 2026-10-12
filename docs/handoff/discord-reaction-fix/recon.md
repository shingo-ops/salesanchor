# Discord リアクション絵文字ピッカー修正 — Recon（現在地把握）

> この文書は、emoji-picker-react CDN 依存問題の修正前調査結果です。
> 親作業: PR #3805（Discord リアクション送受信機能）のデプロイ後バグ修正

## 既存 ADR 検索結果

| キーワード | 検索コマンド | 該当 ADR |
|-----------|-------------|----------|
| emoji-picker | `git grep -i "emoji-picker" docs/adr/` | 該当なし |
| discord | `git grep -i "discord" docs/adr/` | ADR-009（Gateway Worker）, ADR-091（Bot Scope） |
| cdn | `git grep -i "cdn" docs/adr/` | 該当なし |

## 問題の現在地

### 発生事象

- PR #3805（Discord リアクション機能）デプロイ後、本番環境で絵文字ピッカーが壊れた画像アイコンを表示
- `emoji-picker-react` ライブラリが外部 CDN（`cdn.jsdelivr.net`）から絵文字画像データを取得する仕組み
- 本番環境で CDN への接続が失敗すると壊れたアイコンが表示される

### 問題ファイル

- `frontend/src/pages/inbox/EmojiPickerWrapper.tsx:1-80` — emoji-picker-react を使用していた実装
- `frontend/package.json:83` — `emoji-picker-react` 依存が存在

### 修正方針

- CDN 依存のフルピッカーを廃止
- Unicode 絵文字（❤️ 👍 👎 😊 😂 🎉 ✅ 🙏 👀 🔥 💯 ⭐ 😍 🤔 👏 💪）をボタンとして並べるプリセットグリッドに置換
- 外部 CDN・画像リソース不要のため本番環境での読み込み失敗が発生しない
