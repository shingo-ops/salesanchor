# design — 受信箱 会話画面 A「見た目」（スマホの吹き出し・入力欄を WhatsApp 実測へ）

状態: 設計審査済み（§12）。§4 は PO 決定済み（2026-11-01「1」＝案1）。段A-1 は実装カード card-a1.md（同じフォルダ）で実装へ。段0 の測り足しは 2026-11-01 に済み（measure-a2.md）。段A-2 は実装カード card-a2.md（PO の実装承認待ち）。
根拠: docs/handoff/inbox-deal-ui/thread-a/recon.md。成功条件: docs/handoff/inbox-deal-ui/requirements.md §11 A1〜A4（PO 承認 2026-11-01）。

## 1. 目的と利用者に見える変化
- 目的: スマホで会話を開いたとき、吹き出しと入力欄が WhatsApp と同じ大きさ・形・置き方になる。
- 変化（スマホのみ）: 吹き出しの角が小さくなり受信側に尾が付く。時刻が本文と同じ行の右下に入る。入力欄が1行の丸いピル（高さ48）になり、文字が大きくなる（18）。送信が直径48の丸になる。吹き出しの上の「ヒューマンエージェント」の行が消える（PO 決定 2026-11-01、PC も同じ）。
- 変わらないもの: 色（スマホの今の色のまま）、PC の見た目（上の1行を除く）、送る・受ける動き。

## 2. 対象と対象外
- 対象: frontend/src/pages/inbox/InboxMessageThread.tsx の吹き出し（:522-664）と入力欄（:724-852）、frontend/src/pages/inbox/InboxPage.css の該当規則、frontend/src/tokens.css への部品トークン追加、新しい金型（§4 の案1の場合）、benchmark 記録の訂正（whatsapp-reproduction-spec.md:155）。
- 対象外: 色、表示の切り替え（B）、既読の印（C。ただし送信側の時刻の右に場所だけ空けない＝C で決める）、「＋」の中身（D）、一覧・上の帯（一致済み）、PC の値。

## 3. 目標値（px。dp をそのまま px に使う）と使うトークン

| 部位 | 目標 | 根拠 | トークン（既存 / 新規） |
|---|---|---|---|
| 吹き出しの角 | 10 | spec :175 | 既存 `--radius-badge`(10px) は用途違いのため使わない。新規 `--comp-chat-bubble-radius-mobile: 10px` |
| 受信の尾 | 左上に 7 張り出す | spec :174 | 新規 `--comp-chat-bubble-tail-w-mobile: 7px` / `--comp-chat-bubble-tail-h-mobile: 10px`（card-a2 §3） |
| 行の左右の余白 | 17 | spec :121, :172 | 新規 `--comp-chat-row-inset-mobile: 17px`（同じ用途の段に無い値。spec 5-4 の表） |
| 吹き出しの上下 | 5 ずつ | spec :122 | 新規 `--comp-chat-row-gap-group-mobile: 5px`・続きの中は `--comp-chat-row-gap-inner-mobile: 1.333px`（card-a2 §3） |
| 本文の文字・行の間隔 | 16 / 19 | measure2 | 既存 `--font-md`(16px)、新規 `--comp-chat-line-height-mobile: 19px` |
| 時刻の文字 | 12 | measure-cal1 | 既存 `--font-xs`(12px) |
| 時刻の場所 | 本文と同じ行の右下、本文の右に 37 先取り、高さ 16.3、左右 6 | spec :123-125 | 見えない時刻の写しで場所を取る（固定の 37 は使わない）。新規 `--comp-chat-time-inset-mobile` / `-time-bottom-mobile`、既存 `--space-6px`（card-a2 §3） |
| 本文の内側の余白 | 上下 7（高さ 33 から）・左右は初期値 9 を端末で 1px 刻みに決める（U5） | measure-a2.md U1・墨の位置 | 新規 `--comp-chat-bubble-pad-x-mobile` / `-pad-y-mobile`（最終の値と全トークンは card-a2.md §3） |
| 入力欄の帯 | 高さ 56（48＋上下4） | spec :99-100 | 既存 `--space-1`(4px) |
| ピル | 高さ 48・角の丸み 24（伸びても 24 のまま）・左 8 | 2026-11-01 測り直し・measure-a2.md U4b | 既存 `--comp-btn-height-lg`(48px)・`--space-2`、新規 `--comp-chat-input-radius-mobile: 24px`（card-a2 §3） |
| ピルの中のボタン | 48x48 | spec :101, :141 | 既存 `--comp-btn-height-lg` |
| 入力の文字 | 18 | measure3 | 新規 `--comp-chat-input-font-mobile: 18px`（文字の段に 18 は無い。`--font-lg` は 17.6 で、測定で 17.5 は不一致だった） |
| 送信の丸 | 直径 48・ピルとの隙間 8・右端 10 | 2026-11-01 測り直し | 既存 `--comp-btn-height-lg`・`--space-2`・`--space-10px` |

- 新規トークンは色以外のみ（tokens.css の :root）。ADR-067 :129-134 の手順で追加し、ADR-067 のコンポーネントトークン表に書く。check:new-tokens のため PR 本文のチェック表を埋める。
- スマホだけに効かせる方法: 既存の作り（CSS:1112 以降の `@media (max-width: 767px)` の中で規則を差し替える）に合わせる。トークン自体を @media で上書きしない（ADR-067 :119、recon 2-2）。

## 4. 作り方の選択（**PO 決定 2026-11-01「1」＝案1**）

- 案1【推奨】 吹き出しと入力欄を金型として新しく登録する（components/ChatBubble・components/ChatComposer。各 .tsx＋.css(var() のみ)＋.stories.tsx）。会話画面はそれを使うだけにする。
  - 理由: PO の常の指示「金型登録のないハードコード禁止」に正面から合う。B（訳の表示）・C（既読の印）・D（「＋」）も同じ部品に足すので、1か所で直せる。ADR-144 :59-64 は金型の新設に PO の許可を求めている。
  - 弊害: 作業が増える。PC の見た目を1画素も変えずに移す必要がある（A3 で確かめる）。
- 案2 今の場所（ページの中の生の要素とクラス）のまま値だけトークンにする。
  - 理由: 作業が少ない。ADR-144 は生 button・生 textarea を禁止していない（:34-39）。
  - 弊害: 吹き出しと入力欄が部品として登録されないまま残る。B〜D で足す物もページに直接書くことになる。

## 5. 進め方（変更は一度に1つ）

- 段0 測り足し（PO のスマホが要る）: recon §3 の U1〜U6 を、同じ端末で撮って測る。同時に、端末の Chrome に見本ページを出し、本文の墨の位置が WhatsApp と合う内側の余白を 1px 刻みで決める（U5）。生出力は /tmp/CC報告ファイル/inbox-deal-ui/ に残す。入力欄の自動の伸び（U4）は、Chrome と Safari の対応を公式資料で確かめてから作り方を決める。
- 段A-1（案1の場合）金型へ移すだけ。見た目は PC・スマホとも変えない。合格: 幅1280と幅360の前後の写真が全画素一致（「ヒューマンエージェント」の行を除く）。
- 段A-2 スマホの値を目標値へ。合格: A1〜A4。
- 段A-3 benchmark 記録の訂正（whatsapp-reproduction-spec.md:155 の入力欄の角を「24（伸びても同じ）」に。測り直しの生出力を出典に書く）。文書だけ。

## 6. 影響範囲
- 会話画面の吹き出しと入力欄（スマホ・PC）。InboxMessageThread を使う画面は InboxPage.tsx:194 の1か所だけ。
- 試験: InboxMessageThread.discordSendError.test.tsx、tests-e2e/visual-language/inbox-baseline.spec.ts・inbox-single-column.spec.ts（写真の基準を撮り直す場合がある）。
- 「ヒューマンエージェント」の行を消しても、送るときの Meta の決まり（backend/app/services/messaging_window.py）は変えない。

## 7. リスクと対処
| リスク | 対処 |
|---|---|
| PC の見た目が変わる | 段A-1 と A-2 で幅1280の前後の写真を比べる（A3） |
| Chrome と WhatsApp の書体が違い、日本語の墨の位置が合わない | 長さは英字で合わせる（10/31 と同じ方法）。日本語の差は書体の差として記録し、A1 の対象は箱の大きさと英字の墨にする |
| 入力欄の自動の伸びが一部のブラウザで効かない | 段0 で公式資料を確かめ、効かない場合の作り方を決めてからカードにする |
| 尾が連続した吹き出しで重なる | 段0 の U2 で WhatsApp の実際を測ってから決める |

## 8. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| A1 スマホの角・余白・時刻の位置・幅・入力欄・送信・文字の大きさが実測と ±1px | 段0 と同じ端末の Chrome（幅360）で SA を撮り、同じ道具（measure_pill.py 等）で画素を測って表にする |
| A2 新しい値はすべてトークン経由・直書き0件。TSX:568 の直書きも0件 | check:all・ui-governance-gate・grep（`style=` と px 直書き） |
| A3 PC が前後で変わらない（「ヒューマンエージェント」の行を除く） | 幅1280の前後の写真を全画素比較 |
| A4 PO が写真を見て合格 | 本番に出す前に写真を PO に見せる |

## 9. 戻し方
- 段ごとに1つの PR。戻すときはその PR を戻す（revert）。DB と本番データは触らない。

## 10. 維持の仕組み
- 守り手: CI の check:css-values・check:new-tokens・ui-governance-gate と、見た目の基準写真の試験（frontend/tests-e2e/visual-language）
- 値はトークンと金型に集め、CI（check:css-values・check:new-tokens・ui-governance-gate）が直書きの増加を止める。
- 金型の stories を Storybook に置き、見た目の基準写真（tests-e2e/visual-language）で変化を見張る。

## 11. 外部・過去事例の参照と我々への応用
- 手本は本物の WhatsApp（Android 実機の実測）。他社の再現例は使わない（要件 §1: 手本はクローンではない、PO 2026-10-29）。参考として既存の比較表（size-compare.md: chatwoot・zernio・WhatsAppClone）があるが、値の根拠にはしない。

## 4-1. 吹き出しの金型を1つにまとめる（**PO 決定 2026-11-01「1」**）
- 事実: A-1 の PR #4974 と同じ時期に、秘書のチャット（ADR-1056・PR #4976）が同じ名前の金型 `components/ChatBubble` を main に入れた。#4974 は衝突してマージできない。
- 決定: 受信箱の金型を土台にして1つにまとめ、秘書のチャットもそれを使う。どちらの画面の見た目も変えない。
- 案: 金型に `layout`（thread=受信箱 / panel=秘書）・`failed`・`pending`・`wide` を持たせる。色・角・余白・字・行の間隔の規則は1か所にし、2画面の違い（幅・並べ方・赤の出し方・スマホの色）は props で選ぶ。クラス名は components の慣習 `comp-` に合わせて `comp-chat-bubble` にする。
- 退けた案: (a) 名前を変えて2つ並べる → 同じ役目の金型が2つになり SSOT に反する。(b) 秘書の金型を土台にする → PO の決定（受信箱を土台）と違う。受信箱の時刻の行・赤の枠・スマホの色を後から足すことになる。
- 受入: 受信箱は A-1 と同じ写真比べ、秘書は写真（画素 0）と値（項目 0）の比べ。作業指示は card-a1-unify.md。

## 12. 審査（Architect・同じ AI による自己審査）
- 第1回 判定: REVISE。理由: (1) §4 の金型の新設は ADR-144 :59-64 により PO の許可が要る。(2) U1〜U6 が測れていない。
- 第2回（2026-11-01・PO「1」の後）判定: **段A-1 と段A-3 は APPROVE。段A-2 は REVISE のまま**。
  - (1) は解決（PO が案1を選んだ＝金型新設の許可）。
  - (2) は未解決。段A-2 の値のうち U1〜U6 に当たるもの（内側の余白・送信側の尾・連続・幅の上限・入力欄の伸び・時刻の右端）は推測で決めない。段0（PO のスマホでの測り足し）の後に段A-2 のカードを書く。
  - 段A-1 は値を1つも変えない移し替えなので U1〜U6 に依存しない。カード card-a1.md の §12 で整合検査済み。
- 合格している点: 既存 ADR と記録との突き合わせ済み。目標値はすべて実測の出典つき。記録の誤り（入力欄の角）は測り直して出典を残した。受入条件は写真の画素と CI で ○× が付く。スマホだけに効かせる方法は既存の作りに合わせた。
- 第3回（2026-11-01・段0 の測り足しの後）判定: **段A-2 は APPROVE（card-a2.md）**。
  - (2) は解決: U1・U2・U3・U4・U6 は実測済み（measure-a2.md）。U5 は実装後に端末の Chrome で 1px 刻みに決める手順と合格の幅を card-a2 §7 に書いた。
  - 入力欄の自動の伸び（§7 のリスク）は `field-sizing: content` を使う。公式資料で確かめた（card-a2 §3）。対応しないブラウザは今の2行のまま。
  - 未実測で残るもの: 送信側の幅の上限と続き。U1 で4項目が左右対称だったので同じ値を使う（card-a2 §12）。
  - 段0 で分かったことを §3 に反映: 吹き出しの上下は「続きの境目 5・続きの中 1.3」（U2）、幅の上限 286（U3）。
- 次: PO の実装承認の後、card-a2.md で実装する。
