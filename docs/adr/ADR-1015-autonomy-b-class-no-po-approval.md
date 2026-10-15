# ADR-1015: 危険でない変更（B 区分）は KGI・設計の PO 承認なしで PR まで進める

| 項目 | 内容 |
|------|------|
| ステータス | Accepted |
| 備考 | 2026-10-14 に PO が「y」で方針を了承（危険でない変更（画面・文言・不具合修正）は1件ごとの PO 承認をなくし PR まで任せる）。同日、設計 design.md に PO が「y」（ADR 案と文書だけの PR を作る）。2026-10-15 PO 決定で、審査担当を Fable から Opus へ変更（標準の審査は Opus） |
| 起案日 | 2026-10-14 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1003（GO 委譲。本 ADR は GO の範囲を変えない）、ADR-1011（許可の自律保守。本 ADR は許可を変えない）、ADR-135・ADR-136（危険パスの扱いは A 区分のまま） |

---

## What（何を決めたか）

1. PR を、変更ファイルと目的によって A／B-1／B-2／B-3／L に分ける。上から順に判定し、最初に当たったものに決める。条件の正本は本 ADR とする。細かい条件と監査の手順は `docs/handoff/devflow-autonomy-b/design.md` §3 に書く。両者が食い違えば本 ADR を優先する。
   - **A（PO の判断を待つ）**: 次のどれかに当たる変更。
     - 危険パスを触る：`migrations/`・`scripts/`・`ops/`・`tools/`・`backend/tools/`・`backend/app/tools/`・`backend/app/tasks/`・`backend/scripts/`・`frontend/scripts/`・`frontend/api-contract/`・`.github/`・`backend/app/auth/`。
     - ファイル名に auth／session／permission／payment などの語を含む（見るのは `frontend/src/`・`backend/app/`・リポジトリ直下だけ）。
     - 正本の文書（ADR・STANDARD-WORKFLOW・CLAUDE.md／AGENTS.md・ai-agents・specs の ideal-state／kgi）を触る。
     - .sql を含む。
     - 新機能（PR タイトルが feat、または今は無い状態を作るもの）である。
     - 新しい画面・API・表のファイルを足す。
     - ADR-1003 の7つの例外に当たる。
   - **B-1 不具合修正**: `frontend/src/`・`backend/app/`・テストだけを触る。design.md に次の2つを書く。書けなければ A とする。Opus が `git show origin/main:<path>` で根拠の実在を確かめる。
     - 期待値：ADR 番号、What/Decision 節（または ideal-state／kgi）の file:line、その行の引用文。
     - 実際の挙動。
   - **B-2 文言・見た目**: 既に在る文言・CSS・配置だけを変え、変更は `frontend/src/` の中に限る。`frontend/api-contract/` と新しい画面ファイルは含まない。
   - **B-3 テスト・文書**: テストと、`docs/` のうち正本でないものだけを触る。
   - **L 台帳**: `.claude-pipeline/` だけを触る。
2. B 区分（B-1・B-2・B-3・L）は、KGI の PO 承認と設計の PO 承認を取らない。AI が KGI・recon・design を書いて記録に残し、Opus 審査が APPROVE なら実装へ進む。審査の記録は docs/handoff/<仕事名>/review-opus.md に置く。
3. B 区分でも、次は今までどおりとする。
   - 必須 CI。
   - Reviewer・Evaluator。
   - GO：ADR-1003 に従い Opus が出す。
   - マージ：PO が押す。
   - B 区分の PR は Draft にしない。
4. B 区分の PR の本文には、次の3つの欄を必ず書く。
   - 区分：A／B-1／B-2／B-3／L のどれか。
   - PO承認：PO の言葉そのままと日時。B なら「不要（B）」と書く。
   - Opus 審査記録：記録ファイルのパス。
5. どれにも当たらないとき、AI は止まって PO に y/n を1問だけ聞く（STANDARD-WORKFLOW.md §3）。
6. 試行は 14 日とする。Opus は毎週月曜に監査し、14 日目に成績表を PO に3行で出す。成功条件は次の4つとする。
   - S1：B 区分の PR で、PO の返答はマージの判断だけになる。
   - S2：A 区分が PO の承認なしにマージされた件数が 0。
   - S3：B-1・B-2 の PR のうち、それが原因の fix PR が 7 日以内に出た割合が 4.0% 以下。あわせて、B が原因の EMERGENCY PR が 0。
   - S4：成績表が 14 日目に PO に届く。

## Why（なぜ）

- **PO の手間**: 今は1件ごとに、KGI と実装前の2回、PO の承認が要る（STANDARD-WORKFLOW.md:23・:79、CLAUDE.md:72）。PO の願いは、危険でない変更を AI に任せ、PO は危険な所だけを判断することである。
- **変えるのは文書だけで足りる**: KGI 承認と設計承認を見ているのは文書の規則だけで、CI もフックも見ていない（`docs/handoff/devflow-autonomy-b/recon.md` の実物確認。Fable も同じことを確かめた）。そのため、CI・フック・許可は緩めなくてよい。
- **基準値は実測した**: 9/22〜10/6 にマージされた PR 284 件を、この区分で分けた。結果は A 186・B 55・L 38・どれにも当たらない 5 件（直す前の版で分けた値。リポジトリの classify.py は直した版で、A 185・B 56 になる。移る #3980・#3992・#4006 は docs だけか .sql を含むもので、下の分母 50 件には入らない）。
  - B のうちコードを触るもの 50 件では、それが原因の fix PR が 2 件あった（#3736・#3763）。2/50＝4.0%。
  - ログインに関わるファイル9本は、すべて A に入った。
  - 根拠は `docs/handoff/devflow-autonomy-b/baseline.md`（284 件の明細と原因の判定）と、`docs/handoff/devflow-autonomy-b/design.md` の S3 の行（2/50 の導き方）にある。
- **審査**: Fable が v2 から v6 まで5回審査し、v6 で APPROVE を出した（`docs/handoff/devflow-autonomy-b/review-fable.md`）。

## 範囲外（この ADR では変えない）

- GO の範囲と、ADR-1003 の7つの例外。
- 許可・フック・CI・Ruleset。
- A 区分の進め方（今までどおり PO が判断する）。
- マージを押すのは PO であること。
- なお、docs/ai-agents/design-partner.md の「PO 自筆 GO 必須」の行は、ADR-1003（2026-09-29）に合わせて書き直した。これは本 ADR の新しい決定ではない。

## 解除

PO が「自律停止」と言えば、この ADR より前の規則（1件ごとの PO 承認）に戻る。試行の 14 日が終わったら、成績表を見て、続けるか戻すかを PO が決める。自律停止は、ADR-1003（GO 委譲）と ADR-1011（許可の自律保守）の状態を変えない。

## 弊害・トレードオフ

- **新機能を不具合修正と言い換える恐れ**: B-1 は正本の3点（ADR 番号・file:line・引用文）と実際の挙動を必ず書く。Opus が実在を確かめ、新機能は区分の条件で A になる。さらに週1回の監査で見る。
- **認証やお金のファイルが B に落ちる恐れ**: ファイル名の語で A にする。ログインに関わる9本は実測ですべて A になった。
- **RLS（テナント分離）を触る修正は、ファイル名の語では見つけられない**: B-1 で RLS を触るときは、security-reviewer を必ず通す。
- **件数の少なさ**: 14 日で B-1・B-2 は 50 件ほどの見込み。原因の fix が 2 件までなら○、3 件で×になる。

## 外部・過去事例

zenn に貼られた記事（個人の SaaS）では、人は危険な所だけを見て、残りは AI に任せていた。ただし数値は著者の自己申告で、第三者による確認がない。そのため成功の根拠には使わず、やり方の参考にとどめる。成功の根拠は、自社の実測（Why の基準値）に置く。

## 維持の仕組み

- 守り手: Opus（設計パートナー）。
- 監査: 毎週月曜に `docs/handoff/devflow-autonomy-b/classify.py` で、マージ済みの PR を分ける。そのうえで次を確かめる。
  - PR 本文の「区分」「PO承認」欄と、分けた結果が合っているか（S2）。
  - fix PR の原因の判定（S3）。
  - PO の返答回数（S1）。
- 監査の記録は docs/handoff/devflow-autonomy-b/audit-YYYY-MM-DD.md に残す。
