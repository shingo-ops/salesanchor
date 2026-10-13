# Phase 3 設計 — devflow-autonomy-b（危険でない変更は1件ごとの PO 承認をなくす）

**対象ADR**: ADR-1015  
**recon**: docs/handoff/devflow-autonomy-b/recon.md  
**日付**: 2026-10-14  
**担当**: Planner（Opus・設計パートナー）  
**状態**: 設計審査済み（Fable APPROVE、review-fable.md）。PO の決定は「y」2回（2026-10-14、方針／この設計で ADR 案と文書だけの PR を作る）

根拠: recon.md、baseline.md、review-fable-v2.md〜review-fable-v5.md（各版への REVISE）、review-fable.md（v6 への APPROVE）、ADR-1003 本文。この文書は作業用の設計案 v6 を、リポジトリ内のファイル名に付け替えて写したもの。版ごとの修正の経緯は各 review-fable ファイルにある。

---

## 外部・過去事例の参照と我々への応用

- 事例1: PO が貼った zenn の記事（個人の SaaS。人は危険な所だけを見て、残りは AI に任せる）→ 我々への応用: 「A＝PO 判断／B＝AI に任せる」の分け方の参考にした。数値は著者の自己申告で第三者の確認がないため、成功の根拠には使わない。
- 事例2（自社の過去）: 9/22〜10/6 にマージされた PR 284件を、この区分で分けた実測（baseline.md）→ 我々への応用: S3 の基準値 2/50＝4.0% と、認証に関わる9本がすべて A に入ることを、成功判定の根拠にした。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| ADR-1015 が ADR 索引に載る | `node scripts/generate-adr-index.js --check` が終了コード0 |
| CLAUDE.md が上限の行数以内 | `node frontend/scripts/check-claude-size.js` が終了コード0 |
| 書き換え10か所が、実装カードの「変更後」の文と1文字も違わない | `git diff origin/main...HEAD` の該当行を実装カード §3 と照合（Fable が PR 差分を審査） |
| classify.py が 284件を分ける。#3980・#3992 が B-3、#4006 が A、認証9本がすべて A | `python3 docs/handoff/devflow-autonomy-b/classify.py` を作業用の入力で実行した出力（PR 本文に件数を書く） |
| 公開してはいけない文字列（IP・URL・鍵のパス・トークン）が入っていない | 追加ファイルへの grep が0件 |
| 試行の成功条件 S1〜S4（§1） | 毎週月曜の監査ファイル（維持の仕組み）と、14日目の成績表 |

---

## 1. 成功条件（PO が○×で判定）
| # | 成功条件 | 測り方 | 試行前の基準値 |
|---|---|---|---|
| S1 | B の PR で PO が返答するのは「マージしてよいか」だけ | PR ごとに、PO の返答（y/n・承認）の回数を Opus が数え、監査ファイルに書く。数える記録は PR のコメント・PO と Opus の会話・Discord の3か所。ADR-1003 の3行報告には「読むだけ・返答不要」と冒頭に書く | 試行を始める前の3営業日に、同じ数え方で実測する（PR 1件あたりの PO の返答回数） |
| S2 | A の PR が PO の KGI/設計承認なしにマージされた件数 0 | 週1回の監査（§4）。マージ済み PR の変更ファイルを §3 のパス条件で分類し、A なのに本文の「PO承認」欄が「不要」か空欄の PR を数える | 過去の PR にはこの欄が無いため、基準値はない。試行中の値だけで判定する（0件なら○） |
| S3 | B-1・B-2（コードを触る B。L と docs/テストだけの B-3 は入れない）の PR のうち、マージ後7日以内の fix PR で「その PR が原因」と判定されたものが 4.0% 以下（例：50件なら2件まで○、3件で×）。B が原因の EMERGENCY PR は0件 | 監査で、B-1・B-2 の後続 fix（同じファイルを触り、タイトルに fix/修正/不具合/EMERGENCY/hotfix/Revert を含む）の diff を読み、「原因／別件／判定不能」に分ける。判定不能は原因に数えない | 2/50＝4.0%（9/22〜10/6。原因は #3736・#3763。baseline.md の B 55件から、docs だけの B-3 4件（#4006・#3970・#3950・#3825）と、fix 題名で新機能を足した #3717 を除いた。review-fable-v5.md MEDIUM-1・2）。判定不能の2件（#3712・#3716）は数えていない。EMERGENCY は期間中1件（#3819）だが、原因の #3818 は A なので、B が原因のものは0件 |
| S4 | 試行開始から14日目に、成績表（S1〜S3 の前と後）が PO に3行で届く | Opus が作り、`docs/handoff/<仕事名>/` に保存する | — |

## 2. 変更前と変更後（B 区分だけ）
| 段 | 今 | 変更後 |
|---|---|---|
| KGI | PO 承認 | AI が書いて記録に残す（承認は取らない） |
| 設計 | 実装前に PO の明示承認 | recon/design を AI が書き、Fable 審査が APPROVE なら実装へ進む。審査記録は docs/handoff/<仕事名>/review-fable.md |
| 実装〜PR | 同じ | 同じ。PR 本文に「区分」「PO承認」「Fable 審査記録のパス」の3欄を必須にする |
| CI の順序 | 同じ | PR を作った直後は process-artifacts gate が赤になる（GO 原文に PR 番号が要るため。check-process-artifacts.js:373-379）。Reviewer APPROVE → Opus が GO 記録を転記 → 緑。PO は緑になってからマージする |
| GO | ADR-1003 で Opus | 同じ |
| マージ | PO が押す | 同じ。B は Draft にしない |

【事実】今の CI・フックは KGI 承認・設計承認を見ていない（review-fable-v2.md §B 観点4 で実物を確認済み）。変更は文書だけで足り、CI・フック・許可設定は触らない。

## 3. 区分（上から順に判定し、最初に当たったものに決める）
### A：PO の判断を待つ
- 変更ファイルが1つでも次に当たる
  - ディレクトリ: `migrations/`・`scripts/`・`ops/`・`tools/`・`backend/tools/`・`backend/app/tools/`・`backend/app/tasks/`・`backend/scripts/`・`frontend/scripts/`・`frontend/api-contract/`・`.github/`・`backend/app/auth/`
  - ファイル名の語（大文字と小文字は区別しない。見るのは `frontend/src/`・`backend/app/`・リポジトリ直下のファイルだけ）: auth・oauth・session・permission・firebase・credential・secret・password・payment・billing・stripe のどれかを含む。token を含む（`.css` は除く）
  - 正本: `docs/adr/`・`docs/STANDARD-WORKFLOW.md`・各 `CLAUDE.md`/`AGENTS.md`・`docs/ai-agents/`（lessons.d を除く）・docs/specs/**/ideal-state.md・docs/specs/**/kgi.md（全階層）
  - 拡張子が .sql のファイル（`docs/` の下も含む。本番データの変更記録のため。review-fable.md LOW-3）
  - deploy・docker-compose を名前に含むファイル（見る範囲は上と同じ。`.github/` の下は上の条件ですでに A）
- 新機能（PR タイトルが feat、または design.md の目的が「今は無い状態を作る」もの）
- 新しいファイルが `frontend/src/pages/`・`backend/app/routers/`・`backend/app/models` に追加される（新しい画面・API・表になりうるため）
- ADR-1003 の7例外（DROP・大量 DELETE・secrets・Ruleset/保護・workflow-lint.yml・外部 GUI・force push）、本番データの手直し、Legacy の削除
- B-1 の根拠（下記）が書けない変更

### B：PO 承認なしで PR まで進む（マージは PO）
- B-1 不具合修正: 変更が `frontend/src/`・`backend/app/`（A に当たるものを除く）・テストだけ。design.md に次の2点が必須
  1. 期待値: 正本の3点＝(a) ADR 番号、(b) What/Decision 節（または ideal-state.md・kgi.md）の file:line、(c) その行の引用文。Fable が `git show origin/main:<path>` で実在と一致を確かめ、結果を review-fable.md に書く
  2. 実際の挙動: 再現手順、または画面・ログ
- B-2 文言・見た目: 既存の文言・CSS・配置の変更だけ（新機能は A）。変更が `frontend/src/` だけで、`frontend/api-contract/` を含まない。新しい画面ファイルがない。i18n・UI governance・design-token のチェックが緑。file:line は要らない
- B-3 テスト・文書: 変更が `backend/tests/`・`frontend/**/*.test.*`・`*.stories.*`・`docs/`（A の正本を除く）だけ
- L 台帳: 変更が `.claude-pipeline/` だけ。B-3 として扱い、S3 の分母には入れない（コードが変わらないため）

### どちらでもない
- AI は止まって、PO に y/n を1問聞く（STANDARD-WORKFLOW.md §3 の不明点プロトコル）

## 4. 監査（S1〜S3）
- 実行者: Opus。週1回、毎週月曜。agent-console の定期実行に載せるかは、別便で PO に確認する
- 手順: `gh pr list --state merged --base main` → 変更ファイルを取る → §3 のパス条件で分類する（classify.py。§3 と同じ条件）→ 本文の「区分」「PO承認」欄と突き合わせる（S2）→ B-1・B-2 の7日以内の後続 fix の diff を読み、「原因／別件／判定不能」に分ける（S3）→ PO の返答回数を数える（S1）
- 保存先: docs/handoff/<仕事名>/audit-YYYY-MM-DD.md
- PO への提示: 3行（A の承認なしマージ件数／B-1・B-2 の原因 fix の件数と率・基準値 4.0%・B が原因の EMERGENCY 件数／判定）
- 空振り実行: 試行前の版 classify-v5.py（作業用・リポジトリ外）で 9/22〜10/6 の284件を分類した。A 186・B 55・L 38・どちらでもない 5。認証9本はすべて A（baseline.md）。リポジトリの classify.py はこれを §3 に合わせて4点直した版（deploy・docker-compose の語を見る範囲、token の除外から `styles/` を消す、.sql は A、入力のファイルと期間は引数）。直すと、docs だけの #3980・#3992 が A から B-3 に、.sql を含む #4006 が B-3 から A に移る見込み。S3 の分母（B-1・B-2 の50件）は変わらない。実際の件数は文書 PR の作業で実行して PR 本文に書く

## 5. 直す文書（PO の OK 後・文書だけの PR。正本のパスを含むため GO 記録が要る。Opus が ADR-1003 で発行する）
| 文書 | 直し方 |
|---|---|
| 新 ADR（番号は索引で空きを確認。今の最大は ADR-1014） | §1〜§4・§7 を正本にする。「自律停止は ADR-1003・ADR-1011 の状態を変えない」と明記する |
| docs/STANDARD-WORKFLOW.md:23,:79 | 「B 区分は KGI/設計の PO 承認を要らないとする」例外を1文。§3 不明点プロトコル（:115-119）につなぐ |
| CLAUDE.md:70-72（行数に上限があるので、行を増やさず置き換える） | 「①KGI設定（定量・PO承認。B 区分は新 ADR により不要）」に置き換える |
| CLAUDE.md:53 | 「B 区分は Draft にしない」を同じ行に追記する（行は増やさない） |
| docs/ai-agents/design-partner.md:72,:106 | B 区分の例外を追記する |
| docs/ai-agents/design-partner.md:116 | ADR-1003 に合わせる（GO は委譲名義でよい。PO 本人が要るのは ADR-1003 の7例外） |
| AGENTS.md:26,:59 | `PO Approval` の行に B 区分の例外を追記する |
| PR テンプレート（.github/ の下） | 「区分」「PO承認」「Fable 審査記録」の3欄を足す。`.github/` は A なので、この文書 PR 自体が A になる（PO の OK が前提） |
| ADR-1012 | 変更しない（migration を含むため A 区分） |
各行の変更前と変更後の文は、実装カードに書く。

## 6. リスクと対処
| リスク | 対処 |
|---|---|
| 新機能を不具合修正と言い換える | B-1 は正本の3点と実際の挙動が必須。Fable が実在を確かめる。新しい画面/API/表のファイルはパス条件で A になる。週1回の監査 |
| 認証・お金のファイルが B に落ちる | ファイル名の条件を広げた（HIGH-D）。取りこぼしが無いかを、空振り実行の結果（baseline.md）で確かめる |
| RLS（テナント分離）を触る修正が B-1 に入る（例 #3886） | B-1 で RLS（set_config・テナント文脈）を触るときは security-reviewer を必ず通し、PR 本文に結果を1行書く |
| 機械で見つけられない A（大量 DELETE 等） | 今と同じ守り（文書の規則と agent-danger-hook）。ここは変えないので悪くならない |
| 修正が別の所を壊す | 必須 CI 15件・Fable 審査・Evaluator は変えない。S3 で基準値と比べる |
| PO が中身を見ずにマージする | PR 本文の先頭3行（何が変わるか・区分と根拠・戻し方）を必須にする |

## 7. 戻し方
PO が「自律停止」と言えば、元の規則に戻る。試行期間は14日。成績表を見て、続けるか戻すかを PO が決める。


## 8. 未確認（合格には影響しない）
- スマホでマージできるか（公式資料に記載がない）→ 試行の初日に PO が実機で1回試す。できなくても、今のターミナル操作で回る
- ADR-1003:58 の「ADR-1002 振り返り運用」は参照先の誤り（Fable の指摘）。この設計は §4 で監査を自分で定めているので、ここには依存しない。誤りの修正は別便で行う

## 維持の仕組み

- 守り手: docs/handoff/devflow-autonomy-b/classify.py（毎週月曜に Opus が実行し、マージ済み PR を分ける）
- 監査の記録: docs/handoff/devflow-autonomy-b/audit-YYYY-MM-DD.md。PR 本文の「区分」「PO承認」欄と分けた結果の突き合わせ（S2）、原因 fix の判定（S3）、PO の返答回数（S1）を残す
- 止め方: PO が「自律停止」と言えば ADR-1015 より前の規則に戻る。14日目の成績表で、続けるか戻すかを PO が決める
