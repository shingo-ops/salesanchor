# ADR-1082: 秘書に声で話しかける（ブラウザの聞き取り・本番の画面でマイクを自分にだけ許す）

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（2026-11-19 PO が目標 K1〜K6 と聞き取りのやり方 A に「1」。昇格は本番での K1〜K6 の確かめの後） |
| 備考 | PO 2026-11-19「今は喋れるようになっただけ？こちらから喋る機能もつけてほしい」・目標の承認「1」・声の機能を先に仕上げる「1」・無料のやり方で試しの画面から「1」。Amends ADR-1080（What 4「画面の安全設定は変えない」→ マイクだけ自分の画面に許す） |
| 起案日 | 2026-11-19 |
| 方針の決定者 | Shingo（PO） |
| 関連 | [ADR-1056](ADR-1056-secretary-chat.md)（秘書）、[ADR-1080](ADR-1080-secretary-voice-tts.md)（読み上げ）、ADR-1078（予定のカルテ）、ADR-027（i18n）、ADR-067・ADR-144（金型とデザイントークン）。設計: `docs/handoff/secretary-voice-input/design.md`・調査: `docs/handoff/secretary-voice-input/recon.md`・事例: `docs/handoff/secretary-voice-input/research.md`・目標: `docs/handoff/secretary-voice-input/kgi.md` |

---

## What（何を決めたか）

1. 声を文字にするのは、ブラウザが元から持つ聞き取り（Web Speech API の `SpeechRecognition`）。backend に聞き取りの口は作らない。費用は 0 円で、使用量台帳には書かない。
2. 本番の画面の安全設定 `Permissions-Policy` のうち、`microphone` だけを `()` から `(self)` にする（`nginx/nginx.conf` の app の枠 1 か所）。他の画面に埋め込まれたときは許さない。camera・geolocation は今のまま禁止。
3. 聞き取りの部品は `frontend/src/features/secretary/useSecretaryListen.ts` の 1 か所。声 → 文字だけを受け持ち、秘書への送り・会話の扱いは持たない。
4. 聞き取った文は入力欄に入れるだけで、勝手に送らない（K2）。音声モードで予定を作るのは「はい」と答えたときだけ（K6・次の便）。
5. マイクを使うのは、押している間・音声モードの間だけ。窓を閉じる・送る・画面から消えるときは止める（K5）。
6. 最初の便は「試しの便」とし、iPhone のホーム画面のアプリで聞き取れるかを PO が確かめてから、PC のスペース長押し・音声モードへ進む（design.md §14）。

### ADR-1080 のうち改める点
- What 4「画面の安全設定は変えない」→ マイクの許可だけを自分の画面に開ける。読み上げの鳴らし方（`AudioContext`・`<audio>` と blob: を使わない）は改めない。

## Why（なぜ）

- PO の目的は、手を使わずに秘書に用事を頼むこと（kgi.md §1）。
- 本番の画面はマイクを禁止していて、どのやり方でも聞き取れない（recon.md §2・`curl -sI` の実測）。
- 無料のやり方を選んだのは PO の判断（2026-11-19「1」）。有料の Google の聞き取りとの比べは design.md §4。
- iPhone のホーム画面のアプリで動かないという報告が 2021〜2023 年に複数あり、今の iOS では未確認（research.md §6）。全部を作る前に試しの便で事実をそろえる。

## 代わりの案

- Google Cloud の有料の聞き取り（design.md §4 の B）: 使用量を画面で見られ、音が会社の契約の中に閉じる。月 約 320 円の見込み。PO が無料を選んだため選ばない。試しの便で iPhone で動かなければ、もう一度 PO に聞く。
- ChatGPT・Grok のアプリからつなぐ: 書き込みに会社向けの契約が要る、または公式で確かめられない（research.md §4・§5）。
- 別の試しのページ: ホーム画面のアプリには住所の欄が無く、メニューの追加が要る（design.md §14-1）。

## 影響

- 画面: 秘書の窓のスマホの入力欄の右にマイクの印。押すと「聞いています」と出る。
- 本番: nginx の設定が変わる配備で nginx を作り直し、2〜3 秒画面が開けない（`.github/workflows/deploy.yml:574`）。
- 音の送り先: ブラウザの会社のサービスに送られることがある（MDN）。iPhone での送り先は未確認（design.md §14-6）。

## 戻し方

- 便の PR を戻す。マイクの許可は `microphone=()` に戻る。
