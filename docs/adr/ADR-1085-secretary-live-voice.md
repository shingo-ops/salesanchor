# ADR-1085: 秘書チャットに声どうしの会話（LIVE）と聞き続けるマイクを足す（Gemini Live・秘書の仕事は今の道に任せる）

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（草案・2026-11-22。PO 未承認。目標の表の再確認、有料の声の AI と月の上限、ADR-1056 の改めの 3 点を PO が決めるまで実装しない） |
| 備考 | PO 2026-11-21「カメラと画面の共有は今回は不要。1. 表のとおりで決める【おすすめ】」。Amends ADR-1056（AI 会社へ送るのは書いた文だけ）・ADR-1080（声で返事）・ADR-1082（聞き取りは 1 回区切り・スマホだけ）の案 |
| 起案日 | 2026-11-22 |
| 方針の決定者 | Shingo（PO） |
| 関連 | [ADR-1056](ADR-1056-secretary-chat.md)、[ADR-1058](ADR-1058-ai-job-assignments.md)、[ADR-1080](ADR-1080-secretary-voice-tts.md)、[ADR-1082](ADR-1082-secretary-voice-input.md)、ADR-1004（使用量台帳）、ADR-027、ADR-067・ADR-144。設計: `docs/handoff/secretary-live/design.md`・調査: `recon.md`・事例: `research.md`・目標: `kgi.md` |

---

## What（何を決めるか・案）

1. LIVE の声の AI は Gemini Live（2.5 Flash Native Audio）。声の聞き取り・話す・割り込み・両方の書き起こしだけを受け持つ。
2. Gemini Live に渡す道具は「秘書に頼む（文）」の 1 つだけ。画面がその文を今の `POST /api/v1/assistant/messages` に本人のログインで送る。名前探し・カルテ・下書きは今の秘書の道のまま。Gemini Live に書き込みの道は無い。
3. 作るのは「作る」を押したとき、または LIVE 中に下書きが出ている間に**こちらの声の書き起こし**が決まった言葉に一致したときだけ。AI の判断で作らない。
4. Gemini の鍵は画面に出さない。backend の新しい口 `POST /api/v1/assistant/live/session` が 1 回だけ使える短い札を出す。
5. 本番の画面の CSP の `connect-src` に Gemini Live の接続先 1 つだけを足す。
6. LIVE の使用量を台帳 `public.llm_usage_events` に書く（使いみち `secretary_live`・`sdk` `google-genai-live`）。月の上限は backend が見て、超えたら札を出さない。
7. マイクの印は PC にも出し、押している間は聞き続ける。0 円の Web Speech のまま（iPhone のホーム画面のアプリで動かなければ Gemini Live の書き起こしに切り替える）。
8. 「声で返事」のチェックは最後の便で消す。

### ADR-1056 のうち改める点（案）
- 「AI 会社へ送るのは利用者が書いた文だけ」→ LIVE ではこちらの声と秘書の返事の文が Google（有料枠・学習に使わない）に送られる。

## Why（なぜ）

- 2 秒以内の返事と割り込みは、今の秘書（返事まで 5〜8 秒・読み上げ中はマイクを閉じる）では作りの上で満たせない（design.md §4）。
- Gemini は 1 分の下限が OpenAI の約 4 分の 1 で、有料の契約が既にある（design.md §4）。
- 秘書の仕事を今の道に任せれば、データの置き場・決まり帳・権限の確かめが今のまま効き、写しが増えない（design.md §5）。
- 聞き間違いで作る事故を防ぐため、作る判断を AI に渡さない（research.md F1）。

## 代わりの案

- OpenAI Realtime（速さの第三者値は少し上・費用は約 4 倍・新しい契約）。便 T で 2 秒を満たさなければ切り替える。
- 無料の組み合わせ（割り込み・2 秒を満たせない）。
- backend を声の中継にする（作る量と止まる箇所が増える）。

## 影響

- migration 1 本（台帳の値）。PO の「GO #番号」まで main に入れない（ADR-135・ADR-136）。
- nginx の CSP 1 行。配備で 2〜3 秒画面が止まる。
- 毎月 1 回、Google の請求と台帳の LIVE の合計を照らす。
