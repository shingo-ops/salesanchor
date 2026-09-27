# Discord リアクション絵文字ピッカー修正 — Design

> 対象 ADR: ADR-009（Discord Gateway）, ADR-091（Bot Scope）
> Recon: docs/handoff/discord-reaction-fix/recon.md

## KGI

本番環境の受信箱でリアクション追加ボタンをクリックしたとき、壊れた画像アイコンが表示されず、16種の絵文字グリッドが表示される。

## KPI

| 基準 | 検証方法 |
|------|---------|
| 壊れた画像（`<img>` タグのネットワークエラー）がゼロ | ブラウザ DevTools Network タブで CDN リクエストが発生しないこと |
| 絵文字グリッドに16種が表示される | 受信箱でリアクションボタンをクリックして目視確認 |
| 絵文字クリック → Discord チャンネルにリアクション反映 | 実際のチャンネルで確認 |

## 設計

### 変更前（問題）

```tsx
import EmojiPicker from "emoji-picker-react";
// CDN から絵文字画像を取得 → 本番環境で失敗
```

### 変更後（解決）

```tsx
// Unicode 絵文字を直接ボタンとして並べるプリセットグリッド
const PRESET_EMOJIS = ["❤️", "👍", "👎", "😊", "😂", "🎉", "✅", "🙏", "👀", "🔥", "💯", "⭐", "😍", "🤔", "👏", "💪"];
```

### 影響範囲

- `frontend/src/pages/inbox/EmojiPickerWrapper.tsx` — 実装置換（呼び出し元の interface は変更なし）
- `frontend/src/pages/inbox/InboxPage.css` — プリセットグリッド用スタイル追加
- `frontend/package.json` — `emoji-picker-react` 削除
- `frontend/package-lock.json` — 自動更新

### 戻し方

```bash
git revert ac649821a
```

### 外部事例

- Unicode 絵文字をボタンとして並べるシンプルなプリセットピッカーは、Slack・GitHub など主要サービスで標準的なアプローチ
- CDN 依存のライブラリ（twemoji 等）はネットワーク環境により画像が欠落するリスクがあることが広く知られている

## 守り手（維持の仕組み）

- `emoji-picker-react` が再追加されないよう package.json に含めない
- EmojiPickerWrapper の interface（`onEmojiClick` props）は維持されており、将来のピッカー差し替えが容易
