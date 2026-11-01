# recon — 受信箱 会話画面 A「見た目」（スマホの吹き出し・入力欄を WhatsApp 実測へ）

- 基準: origin/main `dc99a062e2c409aeb1a851a01b8bd0fa09ac3b64`（クラウド調査の1行目）。追加の自分での確認も同じ origin/main を `git show` で読んだ（2026-11-01）。
- 生の調査結果: `docs/handoff/inbox-deal-ui/thread-a-recon-raw.md`（枝 `release/inbox-thread-a-recon-raw` @ 8241f96e7）。手元の写し `/tmp/CC報告ファイル/inbox-deal-ui/thread-a-recon-raw.md`（219行・全行読了）。
- 2026-11-01 追記: カード作成時に origin/main `508e86036b5b1ab519d49cd3edde888986ba6e22` で TSX・CSS の該当行を読み直し、本書と card-a1.md の行番号が同じであることを確かめた（`sed -n` で各範囲の先頭と末尾を照合）。e2e がクラス名で要素を探している6本、札の値が `HUMAN_AGENT` か無しの2つだけであること（`backend/app/services/messaging_window.py:134-149`）、`humanAgentLabel` の参照が TSX:569 の1件だけであることも同じ時点で確かめた。
- 要件と成功条件: `docs/handoff/inbox-deal-ui/requirements.md` §11（PO 承認 2026-11-01「1」）。A1〜A4 が本件の合格条件。
- 書き方: 【事実】は file:line かコマンド出力つき。【推測】【未確認】は分けて書く。

## 1. 既存 ADR の検索結果

【事実】
- ADR-064 `docs/adr/ADR-064-inbox-meta-exact-replica.md`: 吹き出し・入力欄の条文なし。トークン条は `--inbox-separator` `--inbox-hover` だけ（:34-45）。追記で「区切り線・hover・パネル幅・padding の記述は現実装と異なり根拠にしない。アバター48pxのみ有効」（:96, :117）。PC の手本。
- ADR-067 `docs/adr/ADR-067-design-token-enforcement.md`: トークンが唯一の真実（:21）。tokens.css=色以外 / index.css=色（:38-42）。新規トークン手順（:125-133: tokens.css の :root に追加 → 色なら index.css の :root と :root.force-dark の両方 → check:dark-parity → ADR のコンポーネントトークン表を更新）。CSS 変数は @media 条件式に使えない（:119）。
- ADR-144 `docs/adr/ADR-144-ui-component-governance.md`: pages/ は原則 components/ の金型を使う（:31）。禁止の種類は生 select・生 input・自作タブ・色直値/生pxインライン（:34-39）。生 button・生 textarea は禁止の表に無い。金型が無いときは実装を止めて PO に報告し、許可後に Xxx.tsx＋Xxx.css(var()のみ)＋Xxx.stories.tsx で新設（:59-64）。
- ADR-137（Shell 分離）: コードと ADR-140 は「ADR-137 Adaptive Shell Architecture」と呼ぶが、docs/adr の ADR-137 3本は別の題（docs/adr/README.md:154-156）。本文は【未確認】。本件は Shell を触らず CSS の @media だけで差を付けるので、この未確認は設計を止めない。
- ベンチマーク決定 `docs/specs/design-system/visual-language/benchmark/README.md:36`: 「吹き出しは PC と スマホ で分ける。PC は 20.8px を維持。スマホは実測（角丸約10dp＋左上に7dp の尾）」。PO 決定 2026-10-11（同 :35 dp をそのまま px に使う）。

## 2. 今の画面の作り

### 2-1 部品の経路
【事実】
- スマホと PC は同じ `InboxMessageThread` を使う（frontend/src/pages/inbox/InboxPage.tsx:194）。会話ヘッダだけ isMobile で出し分け（frontend/src/pages/inbox/InboxMessageThread.tsx:400-418）。吹き出しと入力欄の TSX（:522 以降）は分岐なし。差は CSS の `@media (max-width: 767px)` だけ。
- 吹き出しの要素: .inbox-messages :522 / .inbox-msg-row :553 / .msg-stack :554 / .msg-bubble-line :555 / .msg-bubble :559 / .msg-time :635（すべて frontend/src/pages/inbox/InboxMessageThread.tsx）。
- 入力欄の要素: 外側 `inbox-send-area sticky-bottom-bar` :724 / `send-card` :759 / `send-top-row` :775 / `send-input-wrap` :779 / 入力 `TextareaControl variant="embedded" className="inbox-textarea" rows={2}` :782-796 / 添付 生 `<button className="send-attach-btn">` :810-820 / 英訳 生 `<button className="inbox-translate-outbound-btn">` :822-833 / 送信 生 `<button className="inbox-send-btn">` :835-852。

### 2-2 今の値（スマホに効く値）
【事実】（frontend/src/pages/inbox/InboxPage.css を CSS と略す。トークンは frontend/src/tokens.css を tok と略す）
- 吹き出し: padding var(--space-2) var(--space-3)（8/12px）、font var(--font-md)=16px、line-height 1.45 直書き（CSS:504-511）。
- 角: 送信 var(--radius-bubble-out)=20.8px、受信 var(--radius-bubble-in)=20.8/20.8/20.8/4.8px（tok:103-104、CSS:513-523）。スマホでも同じ。
- 幅の上限: .msg-stack 70%（CSS:502）、スマホ 85%（CSS:1173）。吹き出しは中身に合わせて縮む（CSS:504-511, :1937）。
- 色（スマホ）: 送信 var(--accent)、受信 var(--neutral-bg)（CSS:1312-1313。コメント 1304-1311「紫はスマホでは使わない」）。
- 時刻: 吹き出しの下の別の行。font var(--font-2xs)=11.2px、薄さ 0.7（CSS:530-536）。
- 吹き出しの並び: .inbox-messages padding 16px・gap 8px（CSS:488-497）。
- 入力欄: 帯 padding 4/12/12（CSS:594-596）、カード 角12px・枠線1px（CSS:598-605）、ピル 角 var(--radius-pill)=20px・padding 8px 14px（CSS:614-624）。入力の文字 var(--font-base)=14.4px・行高1.4（frontend/src/components/FormField.css:286-296）。rows=2。
- 添付 28px（CSS:630-644。スマホの上書き無し、CSS:1176-1186 のコメントで「ピル内の28pxは触らない・別途判断」）。送信 36px・スマホ 44px（CSS:709-723, :1190-1193）。角 50% 直書き（CSS:719）。
- 1000〜1279px のブロック（CSS:1000-1111）と 560px 以下のブロック（CSS:1687-1689）に吹き出し・入力欄の規則は無い（自分で grep。生出力: /tmp/CC報告ファイル/inbox-deal-ui/InboxPage-dc99.css）。InboxPage.css 以外に上書きは無い（raw J）。

### 2-3 点検の仕組み
【事実】 check:css-colors / check:css-values（opacity・border-radius・z-index の数値）/ check:dark-parity / check:new-tokens（新トークンは PR 本文のチェック表が必須）/ stylelint / design-token-guard.yml / ui-governance-gate.yml（main の必須チェック）。場所は raw L 179-196。

### 2-4 試験
【事実】 InboxMessageThread を参照: InboxMessageThread.discordSendError.test.tsx、useInboxState.autoSelectBadge.test.tsx、tests-e2e/inbox-header-menu.spec.ts、tests-e2e/visual-language/inbox-baseline.spec.ts、inbox-single-column.spec.ts、inbox-helpers.ts。InboxMessageThread を直接使う stories は無い（raw M）。

## 3. WhatsApp の実測（目標値）

端末 SC-51G・1080x2340・480dpi（1dp=3画素）・文字倍率1.0。dp を px にそのまま使う（PO 決定 2026-10-11）。

【事実・既存の記録】 `docs/specs/design-system/visual-language/benchmark/whatsapp-reproduction-spec.md`（origin/main。写し /tmp/CC報告ファイル/inbox-deal-ui/wa-repro-spec-dc99.md）
- 入力欄の帯 55.7dp（:99）。ピル 286.7x48.3dp、余白 左8・右4・上3.3・下4（:100）。ピルの中 絵文字48 → 文字欄 142.7x32.3（左48・上7.7）→ 添付48 → カメラ48（:101）。送信は枠の外の別の丸（:102）。
- 吹き出しの行 360x42.7dp、吹き出し 行の左から17dp・上下5dp、本文の外側に2dp、時刻は吹き出しの中の右下・同じ行（左64・上14.3・高さ16.3・左右6）、本文の右に37dp 先取り（:108-125）。
- 吹き出しの形（ライトで確定）: 角丸 10dp＋受信側の左上に 7dp 張り出す尾（:170-183）。
- 送信の丸 48x48dp・完全な円・影なし・色 #21c063（:155-161）。

【事実・2026-10-31 の測定】（/tmp/CC報告ファイル/inbox-deal-ui/measure1-summary.md と生出力 measure1〜3.txt・measure-cal1〜2.txt）
- 本文の文字 16、行の間隔 19、時刻の文字 12、入力欄の文字 18（英字で高さ・幅・行の間隔が見本と一致）。
- 受信吹き出し（1行）高さ 98画素=32.7dp、文字の墨の左端は吹き出しの左端から 33画素=11dp。

【事実・2026-11-01 自分で測り直し】（生出力 /tmp/CC報告ファイル/inbox-deal-ui/input-pill-wa1.txt・send-circle-wa1.txt、道具 scratchpad/measure_pill.py、写真 scratchpad/phone/wa1.png）
- 入力欄のピルは**両端が完全な半円**。上端 y2138・下端 y2282（145画素=48.3dp）、左端は中央の高さで x24（8dp）、右端 x883（幅 860画素=286.7dp）。半径 72.5画素の円で各高さの左端を計算すると、y2156 で 48.1（実測48）、y2174 で 33.6（実測34）、y2138 で 88（実測91）。→ 角は「高さの半分」。
- 記録 :155 の「角丸 約3〜4dp」は、この測り直しと合わない。記録の誤りとして扱い、設計は測り直しの値を使う（記録の訂正も本件の作業に含める）。
- 送信の丸: 左端 x908・右端 x1051（144画素=48dp）。ピルとの隙間 25画素=8.3dp、画面右端まで 28画素=9.3dp。

【未確認】（設計の段0で測り足す。要件 §1 の PO 決定 2026-10-29「足りない値は着手時に測り足す」に当たる）
- U1 送信側の吹き出し: 右端からの距離、尾の形（写真 wa3 で右上に尾が見えるが入力欄に隠れて測れない）。
- U2 同じ人が続けて送ったとき: 尾が最初の1つだけか、吹き出しの間の距離。
- U3 吹き出しの幅の上限（長文の1行の幅）。
- U4 入力欄が複数行になったときの伸び方と最大の行数。
- U5 本文の墨の位置に合わせた内側の余白（2dp の外側余白＋文字欄の内側。Chrome と WhatsApp の書体差があるため、端末の Chrome で表示して墨の位置で合わせる）。
- U6 時刻の行の右端（送信側は C で既読の印が入るので C と合わせて測る）。

## 4. 推測と分かっていないこと

【推測】なし（設計判断は design.md に理由つきで書く）。
【未確認】 ADR-137 本文の場所。eslint.config.js の中身。tests-e2e の吹き出し・入力欄を見る行（inbox-baseline.spec.ts の中身）。
