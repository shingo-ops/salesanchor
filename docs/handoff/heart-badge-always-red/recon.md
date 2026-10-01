# recon.md — ハートバッジ常時赤表示

> 作成: 2026-10-01 | STANDARD-WORKFLOW Phase ② | 担当: 実装役（Sonnet）／設計: Opus
> 対象ADR: ADR-144（UIガバナンス）, ADR-067（デザイントークン）

## PO決定（原文）

Q「お客様が付けたハートの表示はどうしますか？（現在＝自分が付けた時だけ赤、お客様だけなら白抜き）」
A「常に赤、自分分は枠で区別 (推奨)」
選択肢文: 「Discordや WhatsAppと同じく、誰かがハートを付けていれば赤い❤＋件数。自分が付けている時はバッジに色付きの枠（Discordの自分の反応と同じ見せ方）。押せば自分のハートを付け外し。既存の色トークンのみ使用。」

## 現在地（origin/main b3235f5f8 時点）

- `frontend/src/components/IconToggleButton.tsx`: `pressed` が true のとき iconOn（塗り）、false のとき iconOff（白抜き）。
- `frontend/src/components/IconToggleButton.css`: `.comp-icon-toggle--pressed` のみ `color: var(--icon-action-danger)`。未押下は `var(--icon-action)`（グレー系）。枠は `1px solid transparent`。
- `frontend/src/pages/inbox/MessageReactionBadges.tsx`: ❤️ グループを `IconToggleButton pressed={heart.is_mine}` で描画。お客様のみ（is_mine=false）だと白抜きグレーになる。
- 呼び出し元: `frontend/src/pages/inbox/InboxMessageThread.tsx`（MessageReactionBadges の唯一の使用箇所。grep 結果で確認）。
- IconToggleButton の使用箇所は MessageReactionBadges と stories/test のみ。
- 使用可能な既存トークン（`frontend/src/index.css`）: `--accent`（ライト #1e3a8a / ダーク #5b8dd9）、`--link-active-bg`（ライト #ebeff8 / ダーク #1e3a8a）。ライト・ダーク両方に定義済みのため新トークン不要。

## 既存ADR検索

ADR-144（UI部品は金型を先確認・拡張）、ADR-067（色直値禁止）に従い、新コンポーネントは作らず IconToggleButton を後方互換で拡張する。
