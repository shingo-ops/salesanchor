# ADR-1080: 秘書の返事を、一人ずつ選んだ声（Google Chirp 3: HD の 4 声・既定カロン）で読み上げる

| 項目 | 内容 |
|------|------|
| ステータス | Proposed |
| 備考 | 昇格の条件: PO の実装承認と、本番での目標 K1〜K5 の確かめの後。Amends ADR-1004（Decision 1）・ADR-1056（第 1 段は使用量台帳に書かない）。PO 2026-11-17「この４人を登録しておいて設定画面で音声は選択できるようにしておける？デフォルトはカロンで」・「声から先（おすすめ）」・目標の承認「この5つで決める（おすすめ）」 |
| 起案日 | 2026-11-17 |
| 方針の決定者 | Shingo（PO） |
| 関連 | [ADR-1056](ADR-1056-secretary-chat.md)（秘書）、[ADR-1004](ADR-1004-llm-usage-ledger.md)（使用量台帳）、ADR-1077（決まり帳・改めない）、ADR-027（i18n）、ADR-067・ADR-144（金型とデザイントークン）、ADR-1071（失敗の文）。設計: `docs/handoff/secretary-voice/design.md`・調査: `docs/handoff/secretary-voice/recon.md`・事例: `docs/handoff/secretary-voice/research.md`・目標: `docs/handoff/secretary-voice/kgi.md` |

---

## What（何を決めたか）

1. 秘書の声は Google Cloud Text-to-Speech の Chirp 3: HD の 4 つ（Aoede・Charon・Erinome・Zubenelgenubi）。既定は Charon。一覧と既定の正本は `backend/app/services/secretary_voice.py` 1 か所。
2. 一人ずつの声は `public.users.secretary_voice`（NULL＝未選択＝既定）に置く。言語・画面の色と同じ置き場。DB に値の決まりは付けず、書く口が一覧で拒み、読むときは既定に倒す。
3. 読み上げは backend の口 `POST /api/v1/assistant/speech` だけが行う。声は backend が本人の値を読む。守りは秘書と同じ 4 つ。
4. チャットの「声で返事」は最初は切れていて、保存しない。音は同じ場所の API から取り、`AudioContext` で鳴らす。画面の安全設定は変えない。
5. 読み上げた字数を使用量台帳 `public.llm_usage_events` に 1 回 1 行で書く（列 `billed_characters`・使いみち `secretary_tts`・`sdk` は `google-tts-rest`）。文そのものは書かない。
6. 今月の字数が 90 万字（無料枠 100 万字の 9 割）に届いたら backend が読み上げを止める。

### ADR-1004 のうち改める点
- Decision 1「1 行 = Gemini の応答 1 回」→ 読み上げの 1 回も 1 行とする。トークンの列は NULL、字数は新しい列 `billed_characters` に書く。

### ADR-1056 のうち改める点
- What「第 1 段は `llm_usage_events` に書かず、1 回ごとにログへ 1 行」→ 読み上げ（`secretary_tts`）は台帳に書く。秘書の文の返事（AI の呼び出し）の扱いは改めない。

## Why（なぜ）

- PO の目的は一人ひとりに合わせた秘書。声はその最初の一歩（kgi.md §1）。
- 声を `public.users` に置くのは、秘書を使う super admin が会社の staff 行に紐づかないことがあり、好みの表の書き込みが全列を上書きするため（design.md §4-2）。
- 台帳に書くのは、目標 K5（今月の字数を画面で見る）と月の上限に要るため。ログだけでは画面に出せず、上限も数えられない（design.md §5）。
- 費用の膨張は声の秘書の失敗の要因（research.md F1）。上限を backend に置けば、画面の不具合でも止まる。

## 代わりの案

- 声を `staff_ui_preferences` に置く・ブラウザに覚える・ブラウザ内蔵の読み上げ・Google の流しながら返す方式・`<audio>` と安全設定の緩和・ログだけに書く。選ばなかった理由は design.md §5。

## 影響

- 移行 2 本（`public.users` の列、台帳の列と値の決まり）。どちらも「無いときだけ」で、毎回の配備で流れ直しても変わらない。
- 本番に Google の読み上げ用の鍵を置く（便3・PO 本人の GO）。
- 毎月 1 回、Google の請求の字数と台帳の字数を手で照らす（design.md §11）。
