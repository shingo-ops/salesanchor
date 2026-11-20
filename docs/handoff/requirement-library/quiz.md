# 要件の練習問題（R2・R3・R4 補助の測り方。測定前に固定 2026-11-21）

> この文書は何か: 機能を直す・作る依頼を AI に計画させ、決まった要件の書類を開いたか（R2）、決まりに反する計画を決まりに触れずに出したか（R3）を数えるための、題・正解・数え方の固定表。
> 親: [../../specs/requirement-library/kgi.md](../../specs/requirement-library/kgi.md)

## 1. 流し方（K12 と同じ。[k12-tasks.md](../doc-agenda-nav/k12-tasks.md)）

- 題: [quiz/prompts.tsv](./quiz/prompts.tsv) の 10 題。各題の後ろに「計画だけを日本語で答えてください。ファイルの変更・commit・push はしないでください。」を付ける。
- 起動: `quiz/runall.sh <出力先> <測る版の detached な写し>`。モデル sonnet・plan モード・1題 1 ドルまで・1題 600 秒まで・各題 2 回＝20 回。
- 場所: クラウドの使い捨て環境（手元の Mac では流さない。PO 2026-10-26・10-30 の決まり）。クラウドで `claude` 2.1.330 が動くことは 2026-11-21 08:00 に確かめた（実行記録 cse_01HHUUpSNznAhPBQRNm4C975）。
- `-p` ではリポジトリの `.claude/settings.json` の見張りは動き、`permissions.allow` だけが使われない（公式 https://code.claude.com/docs/en/permissions 「What runs before you trust a folder」、2026-11-21 Context7 で確認）。前と後の測定は同じ条件になる。
- 数え方: `python3 quiz/count.py <出力先>` → `result.tsv` と各回の答え `Qn-k.answer.txt`。

## 2. 題と正解と「反する計画」

| 題 | 正解の書類（どれか1つの文字列が読む道具の入力にあれば「開いた」） | 決まった要件（要旨） | 反する計画（R3 で 1 と数える） |
|---|---|---|---|
| Q1 | `ADR-097-`・`deal-removal/design.md` | 会社はリードの子。受信箱から送る登録フォームでお客様が登録して作る | リードなしで会社を作れるようにする（lead_id を任意にする・リードを自動で作る・画面から手で作る道を直す）計画で、この決まりに触れない |
| Q2 | `ADR-1076-`・`status-ssot-contact-company/design.md` | 会社と連絡先の状態は public.customer_statuses が正本 | companies 表に状態の列や直書きの選択肢を足す計画で、customer_statuses に触れない |
| Q3 | `ADR-1083-`・`auth-expired-token-lockout/design.md` | 期限が切れただけの札は回数止めに数えない | 期限切れも数える計画で、ADR-1083 に触れない |
| Q4 | `ADR-1027-`・`specs/bundle-sale/` | まとめ売りは値段を割らず、まとめ1つの値段とまとめの数で保存 | 1パックの値段に割って保存する計画で、この決まりに触れない |
| Q5 | `ADR-1022-`・`py312-guard/design.md` | 3.12 のまま作り続け、2027 年 10 月末までに本番ごと 3.14 へ | 今 3.13 へ上げる計画で、この決まりに触れない |
| Q6 | `ADR-1037-`・`migration-lock-timeout/design.md` | ロック待ちは1秒で諦め、間を空けて流し直す | ロック待ちを30秒に延ばす計画で、この決まりに触れない |
| Q7 | `ADR-1032-`・`revival-guard/design.md` | 新しい投稿に隠れた古い投稿の行は現行に戻さない | 古い行も現行に戻す計画で、この決まりに触れない |
| Q8 | `ADR-1062-`・`gemini-auto-failover/design.md` | 断られたら自動で別の道に切り替え、30分成功が無ければ知らせる | 切り替えをやめる計画で、この決まりに触れない |
| Q9 | `ADR-1056-`・`ADR-1078-`・`secretary-chat/design.md`・`secretary-event-karte/` | 秘書の AI に会社のデータも道具も渡さない。作るのは利用者が「作る」を押したとき | AI に道具・データを渡して直接作らせる計画で、この決まりに触れない |
| Q10 | `ADR-1071-`・`error-message-plain-language/design.md` | 失敗の文は「何が起きたか＋次にすること」を誰でも分かる言葉で | 例外の文をそのまま画面に出す計画で、この決まりに触れない |

- 「触れる」とは、答えの文に決まりの書類の番号（例 ADR-1037）か決まりの中身（例「1秒で諦める決まりがある」）を書き、依頼がそれと食い違うことを述べていること。
- R3 の判定は Opus が 20 回の答え（`Qn-k.answer.txt`）を上の表に照らして行い、題ごとの判定と理由を `r3-judgement.md` に残す。迷う答えは「迷い」と書き、合計に入れずに件数を別に書く。
- 題 Q4 だけは今の索引に正解の ADR が載っている（対照の題）。

## 3. 結果の置き場

- 変更前: `docs/handoff/requirement-library/quiz/before/`（result.tsv・r3-judgement.md・exits.txt）
- 変更後: `docs/handoff/requirement-library/quiz/after/`
- 生の jsonl は大きいので、クラウドの枝に置き、要約だけを本書の枝に写す。
