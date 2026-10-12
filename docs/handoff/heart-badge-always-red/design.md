# design.md — ハートバッジ常時赤表示

> 作成: 2026-10-01 | recon: `docs/handoff/heart-badge-always-red/recon.md`
> 対象ADR: ADR-144, ADR-067

## 変更前 / 変更後

| 状態 | 変更前 | 変更後 |
|------|--------|--------|
| お客様のみ（is_mine=false） | 白抜きグレー＋件数 | 赤の塗りハート＋件数（枠なし） |
| 自分も付けた（is_mine=true） | 赤の塗りハート＋件数 | 赤の塗りハート＋件数＋枠（`--accent`）＋背景（`--link-active-bg`） |
| クリック | is_mine ? 取消 : 送信 | 変更なし |
| ホバーハート（自分未リアクション・吹き出し外） | 白抜きトグル | 変更なし |
| ❤️以外のバッジ | 表示専用 | 変更なし |

## 技術 How

- `IconToggleButton` に `variant?: 'default' | 'badge'`（既定 `default`）を追加。
  - `badge`: 常に `iconOn`、色は `var(--icon-action-danger)`。`pressed` は `.comp-icon-toggle--badge.comp-icon-toggle--pressed` の `border-color: var(--accent)` / `background: var(--link-active-bg)` で表現。
  - `default`: 挙動不変（後方互換）。
- `frontend/src/pages/inbox/MessageReactionBadges.tsx` は `variant="badge"` を指定するのみ。aria-pressed=is_mine、aria-label（add/remove）は現行どおり。
- 新トークン・直値なし。

## 外部・過去事例の参照と我々への応用

| 事例 | 概要 | 本プロジェクトへの応用 |
|-----|------|---------------------|
| Discord / WhatsApp のリアクション表示 | 誰かが付けた反応は常に同じ見た目で表示し、自分の反応のみ枠・背景で強調する | 赤の塗りハート＋件数を常時表示し、自分分は `--accent` 枠＋`--link-active-bg` 背景で区別 |

## 受入条件

| 基準 | 検証方法 |
|------|----------|
| お客様のみのハートが塗り・赤で表示され aria-pressed=false、枠なし | `frontend/src/pages/inbox/MessageReactionBadges.test.tsx` / `frontend/src/components/IconToggleButton.test.tsx` |
| 自分のハートありで aria-pressed=true かつ枠クラス付与 | 同上 |
| クリックで `onToggleHeart(messageId, is_mine)` が呼ばれる | `frontend/src/pages/inbox/MessageReactionBadges.test.tsx` |
| `default` variant が従来どおり（badge クラスなし・押下で切替） | `frontend/src/components/IconToggleButton.test.tsx` |
| 新状態が Storybook カタログに載る | `BadgeOthersOnly` / `BadgeMine` ストーリー、`build-storybook` 成功 |
| 色直値・新トークンなし | `npm run check:all` |

## 維持の仕組み

- 金型側に variant として実装し、Storybook ストーリーとユニットテストで状態を固定（CI の test:unit / build-storybook が守り手）。
- 色は既存トークン参照のみ。
- 守り手: CI（test:unit / build-storybook / check:all のトークン検査）

## 戻し方 / 測り方

- 戻し方: `frontend/src/pages/inbox/MessageReactionBadges.tsx` の `variant="badge"` 1行を削除すれば従来表示に戻る。
- 測り方: 本番でお客様のみのハートが赤塗りで表示されること、自分が付けると枠が付くことを PO が目視。
