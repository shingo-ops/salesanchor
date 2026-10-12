# Discord リアクション ハート方式 UI — design

> 設計: Opus（PO 承認済み・第2便）。実装: Sonnet。
> recon: docs/handoff/discord-reaction-heart-ui/recon.md
> 承認済みKGI: docs/specs/discord-reaction/kgi.md
> 対象 ADR: ADR-144, ADR-067, ADR-091

## 目的

絵文字ピッカー方式を廃止し、ハートだけを押せる UI にする。ハート以外の顧客リアクションは表示だけ残す。トグル操作の再利用部品として金型「アイコン切替ボタン」を登録する。

## PO 決定（原文）

- ハート以外の顧客リアクション =「表示だけ残す (推奨)」
- 新金型「アイコンの切替ボタン」=「登録してよい (推奨)」
- ハート表示 =「マウスを乗せた時だけ (推奨)」
- 位置 =「設計者が決める (推奨)」

## 変更前後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| 追加操作 | 吹き出し内の絵文字ボタン→ピッカー（16種） | 白抜きハートを吹き出しの外側（受信=右隣、送信=左隣）に hover / フォーカスで表示。クリックで ❤️ 送信 |
| タッチ端末 | 同上 | 吹き出し長押し 500ms でハート表示（長押し成立時のみコンテキストメニュー抑止） |
| 表示位置 | 吹き出しの内側 | 吹き出し下端（受信=左寄せ、送信=右寄せ） |
| ❤️ の表示 | ピル | 金型 IconToggleButton（自分が押したら塗りハート・件数つき）。再クリックで取消 |
| ❤️ 以外 | ピル（押すと送信/取消） | 非ボタンの表示専用バッジ（絵文字＋件数）。人名は Tooltip 金型 |
| 部品 | EmojiPickerWrapper・ピッカー CSS・状態 | 削除。アイコンは icons.tsx に HeartIcon outline/solid を登録 |

## 設計判断と代替案

- 新金型 frontend/src/components/IconToggleButton.tsx: 汎用（pressed / iconOff / iconOn / aria-label 必須 / size / disabled / 任意 count）。業務の意味を持たせず Meta 等でも再利用できる。押下時色は var(--icon-action-danger)、通常は var(--icon-action)、hover は var(--icon-action-hover)。件数は金型内の任意表示にした（バッジで使うため。外に出す案は呼び出し側の重複が増えるため不採用）。
- 位置は設計者判断: ハート型枠は吹き出しの外側、結果表示は吹き出し下端。吹き出し内に置く案は本文と混ざるため不採用。
- 自分が既にハート済みのときはホバーのハートを出さない（下端の押下済みハートが取消手段）。
- 長押しの状態管理は useLongPressReveal.ts、ハート抽出は純関数 reactionHeart.ts に分け、単体テストする。定数 LONG_PRESS_MS=500 と HEART_REACTION_EMOJI（U+2764 U+FE0F）は名前付き定数。

## 触らない範囲

backend/、migrations/、deploy.yml、scripts/、Discord 権限設定、カスタム絵文字のピッカー再導入（廃止）。

## 受入条件

| 基準 | 検証方法 |
|---|---|
| IconToggleButton が aria-pressed とアイコンを切替え、クリックを通し、disabled で通さず、count を任意表示する | frontend/src/components/IconToggleButton.test.tsx（vitest） |
| ❤️ グループとその他の分離・人名の整形 | frontend/src/pages/inbox/reactionHeart.test.ts（vitest） |
| 金型に stories があり Storybook がビルドできる | `npm run check:stories` と `npm run build-storybook` |
| 色直値・生 px・新規 i18n キーなし・未使用キー削除（ja/en 同数） | `npm run check:all`（lint / css-colors / i18n-missing-keys / stylelint 等） |
| 型・ビルドが通る | `npm run build` |
| CI 必須チェック全緑 | `gh pr checks` |
| 本番: hover でハート表示→クリックで塗りハート→再クリックで取消。他絵文字が表示のみ | PO が tenant_001 で実施（本 PR の外） |

## 外部・過去事例の参照と我々への応用

- Messenger: hover→React、リアクションはメッセージの下に表示 https://www.messenger.com/help/messenger-app/1602676269761759 。応用: ホバーで型枠、結果は下端。
- Instagram Web: hover→絵文字アイコン https://www.facebook.com/help/instagram/561290520611666 。応用: 同上。
- Business Suite Inbox: メッセージに hover して React を押す https://www.facebook.com/business/help/27148728838061242 。応用: 業務受信箱でも hover 起点。
- WhatsApp: メッセージ下に表示・自分の絵文字の再選択で取消・モバイルは長押し https://faq.whatsapp.com/424198503229937/ 。応用: 再クリックで取消・長押しでタッチ対応。
- 調査本文: /tmp/CC報告ファイル/reaction-ux-research.md と reaction-ux-research-2.md（リポジトリ外）。

## 影響範囲

- EmojiPickerWrapper の importer は InboxMessageThread.tsx のみ。REACTION_EMOJI_PRESETS の参照も同ファイル群のみ（削除後 `grep -rn` で 0 件を確認）。
- INBOX_ACTION_ICONS に heart / heartFilled を追加（既存キーは不変）。
- .msg-bubble の最大幅は .msg-stack（70%、モバイル 85%）へ移した。バブルは stack 内で 100%。

## 戻し方

マージコミットを revert する（backend・DB・設定の変更なし）。

## 維持の仕組み

- 守り手: frontend/src/components/IconToggleButton.test.tsx と frontend/src/pages/inbox/reactionHeart.test.ts が CI の vitest で常時実行される。金型の stories 欠落は check:stories が、色直値・生 px は ADR-067 / ADR-144 の CI ゲートが止める。
- 対象: 本 UI の金型・ハート抽出・長押し定数。
- 関所なしの場合: 該当なし。
