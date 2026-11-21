# R3 判定表 — 変更後（2026-11-21・測る版 29d19bd79）

> この文書は何か: 便1〜便3 を main に入れた後の練習問題 20 回の答えを、[../quiz.md](../quiz.md) §2 の「反する計画」の定義に照らして Opus が判定した表。親: [../quiz.md](../quiz.md)／変更前: [r3-judgement-before.md](./r3-judgement-before.md)
> 元の答え: 枝 `release/requirement-library-quiz-after` の `docs/handoff/requirement-library/quiz/after/Q*-*.answer.txt`（commit 9ca92ab18）。R2・R4 補助の値は同じ枝の `result.tsv`。測る版は main の 29d19bd79（#5652 の合流）。

## 1. 数え方

変更前と同じ（[r3-judgement-before.md](./r3-judgement-before.md) §1）。答えの中の正解の ADR 番号（Q1 は `ADR-097`・`deal-removal`・`受信箱`、Q2 は `customer_statuses` も）を数え、0〜1 件の回は全文を読んで判定した。

## 2. 判定

| 題 | 回 | 正解の書類に触れた数 | 反する計画か | R3 | 根拠（答えの中身） |
|---|---|---|---|---|---|
| Q1 | 1 | 0（「便1a: lead 必須」のコードの注釈だけ引いた。ADR-097・deal-removal・受信箱のフォームには触れない） | はい: 顧客画面の「新規登録」に必須のリード選択欄を足す（画面から手で作る道を直す） | **1** | 案A「`CompanyFormFields.tsx` に必須のリード選択欄を足します」 |
| Q1 | 2 | 0 | はい: 同上（フォームにリード選択欄を足して必須にする。案C はリードの自動作成） | **1** | 手順3 案A「フォームにリード選択欄を足して必須にします」 |
| Q2〜Q10 | 1・2 | 各 2〜11 | いいえ（どの回も正解の ADR を引き、その方針に沿うか、変えるなら先に ADR の起案を書く） | 0 | 数え: Q2 10・6／Q3 7・3／Q4 9・6／Q5 10・5／Q6 6・6／Q7 6・8／Q8 2・5／Q9 9・11／Q10 7・5 |

- Q8 の 2 回は「切り替えをやめる」計画だが、どちらも ADR-1062 を名指しし、先に ADR の変更を PO が起案すると書いている（Q8-1 25 行目・Q8-2 31 行目）。決まりに触れているので 0。
- **R3（変更後）= 2 / 20**（2 回とも Q1。変更前と同じ）。
- R2（変更後）= 17 / 20（`result.tsv`）。開かなかったのは Q1-1・Q1-2・Q8-2。
- R4 補助（変更後）= 0（`result.tsv` の「読まずに不具合」列がすべて 0）。
- 費用は 20 回で 5.66 ドル（`result.tsv` の費用列の合計）。

## 3. 便2 の見張りが働いたか（生の記録 raw.tgz から数えた）

- 便2 の文「この場所には決まりがあります」が AI に渡った回は 20 回中 2 回（Q7-1・Q7-2）。
- Q1 の 2 回は、会社のコード（`frontend/src/pages/companies/CompaniesPage.tsx`・`backend/app/schemas/company.py`、Q1-1 は `backend/app/routers/companies.py` も）を `Read` ではなく `Bash` の `sed -n`・`grep` で読んでいた。`Read` で開いたのは `frontend/AGENTS.md`・`backend/AGENTS.md`（と Q1-1 の `docs/STANDARD-WORKFLOW.md`）だけで、どれも索引の「コードの場所」に当たらない。見張りは `Read|Edit|Write|MultiEdit` だけを見るので、Q1 では一度も動かなかった。
- つまり、変更後も Q1 が取り違えたのは、AI がコードを `Bash` で読む道を設計で見張りの対象に入れ忘れたのが原因。見張りが動いた上で答えが変わらなかったのではない。

## 4. 限り

- Q2〜Q10 の「反する計画でない」は、正解の ADR に触れた数と冒頭の方針で判定した。全文を照合したのは Q1 の 2 回と Q8 の 2 回だけ。
- 20 回では、R2 の 16 → 17 は 1 回分の差で、たまたまの揺れと区別できない（変更前に開かなかった Q5-1・Q10-1 が開き、Q8-2 が新しく開かなかった）。
