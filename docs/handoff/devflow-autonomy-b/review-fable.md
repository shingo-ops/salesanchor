# 設計再審査（Fable）: design-v6.md「危険でない変更は1件ごとの PO 承認をなくす」

- 審査日: 2026-10-14 / 読み取りのみ（repo・本番・GitHub への書き込みなし。gh は未使用。git は `fetch`・`show`・`ls-tree` の読み取りだけ）
- 審査対象: /tmp/CC報告ファイル/devflow-switch/design-v6.md（design-v5.md との diff 42 行を取得して差分だけを精査）、baseline-v5.md、classify-v5.py、_v5-tally.py、_v5-rows.json、_v5-judge.json、_cache0922.json
- 前回審査: review-fable-v5.md（REVISE、HIGH0・MEDIUM-1〜3・LOW-1〜4）
- 実物の照合先: `git fetch` 後の origin/main = 74acffd889（v5 審査時の e0355ceef6 から進んでいる。§5 の行参照は再確認済み・下記 §3-3）

## 判定: APPROVE（HIGH 0 件・MEDIUM 0 件・LOW 3 件）

PO への結論（1行）: 前回残っていた文面の矛盾は全部直り、基準値「50件中2件まで○」は元データから再計算しても同じ数になったので、この設計で試行を始めてよい（最終 OK は PO）。

PO Approval Required: true（この設計そのものが「PO 承認の省き方」を決めるため。§5 の文書 PR は `.github/`・正本を含み A 区分）
Ready For Generator: true（PO の y の後。Generator の仕事は §5 の文書修正と監査 script の §3 合わせだけ。コード・CI・権限は触らない）

---

## 1. v5 指摘の解消状況（指摘ごと）

| v5 | 状態 | 根拠 |
|---|---|---|
| MEDIUM-1 fix 題名の新機能 #3717 が分母・原因に残る | 直った | design-v6.md:7・:40 で #3717 を分母・原因の両方から除外。_v5-rows.json の #3717 は cls=B・題名「fix: correct field mismatch and add message viewer…」、_v5-judge.json の原因 B は [3717, 3736, 3763]（_v5-tally.txt:2）。除外後の原因は #3736・#3763 の2件で design-v6.md:40 と一致 |
| MEDIUM-2 分母の定義が §1 と §4 で不一致 | 直った | design-v6.md:40「B-1・B-2（コードを触る B。L と docs/テストだけの B-3 は入れない）」、:80「B-1・B-2 の7日以内の後続 fix」、:82「B-1・B-2 の原因 fix の件数と率・基準値 4.0%」、:83「S3 の分母（B-1・B-2）は変わらない」。4 か所すべて同じ語 |
| MEDIUM-3 EMERGENCY の原因 #3818 は A・基準値未記載 | 直った | design-v6.md:40「EMERGENCY は期間中1件（#3819）だが、原因の #3818 は A なので、B が原因のものは0件」、成功条件に「B が原因の EMERGENCY PR は0件」。_v5-rows.json: #3818 cls=A（pre_feat=B、題名 feat）、#3819 cls=B 題名「EMERGENCY: fix channel_name…」。9/22〜10/6 の 284 件で題名に emergency を含むのは #3819 と #3925（A、「emergency fallback」の語のみ）の 2 件で、接頭辞 EMERGENCY は #3819 だけ |
| LOW-1 件数でも書く | 直った | design-v6.md:40「例：50件なら2件まで○、3件で×」 |
| LOW-2 RLS を触る fix が B に入る（#3886） | 直った（対処を §6 に明記） | design-v6.md:104 の行を新設。「security-reviewer を必ず通し、PR 本文に結果を1行書く」。#3886 は _v5-rows.json で cls=B のまま（語に rls は足していない＝設計判断として B-1＋security-reviewer。CLAUDE.md の必須起動条件「auth/ *token* …を触る → security-reviewer」と矛盾しない） |
| LOW-3 classify の deploy 範囲・`styles/` 残置 | 直った（宣言） | design-v6.md:14・:83「監査の前に、実装カードで classify を §3 に合わせる（`styles/` の除外も消す）」。script 自体は未変更（classify-v5.py:19-20）だが、設計文書の段階では宣言で足りる。#3980・#3992 が A→B-3 に移る点は本審査でも変更ファイルを確認（両方 `docs/handoff/dist-deploy-guard/gas-deploy-runbook.md` を含み、コード無し） |
| LOW-4 S1 の数える記録の場所 | 直った | design-v6.md:38「数える記録は PR のコメント・PO と Opus の会話・Discord の3か所」 |

---

## 2. 基準値 2/50＝4.0% の再計算（_v5-rows.json・_v5-judge.json・_cache0922.json から自分で計算）

実行（python3 -I、読み取りのみ）:
- B（cls=='B'）の件数: **55**
- B のうち `frontend/src/`・`backend/app/` のテスト以外のファイルを1つも触らないもの: **[3825, 3950, 3970, 4006] の 4 件**（design-v6.md:40 の #4006・#3970・#3950・#3825 と一致）。テストだけの B は **0 件**
- 原因 B（_v5-judge.json の res で '原因' を持つ B）: **[3717, 3736, 3763]**。判定不能のみ: [3712, 3716]
- 分母 = 55 − 4 − 1（#3717） = **50**。分子 = 原因 3 − #3717 = **2**（#3736・#3763）。率 = **4.0%**

結論: design-v6.md:9・:40 の「2/50＝4.0%（原因 #3736・#3763）」は元データと一致する。原因 2 組の中身（patch 照合）は review-fable-v5.md §2-1 で確認済みで、v6 で変更なし。

付随して確かめた事実:
- B 55 件に「追加された（status=added）テスト以外のコードファイル」を含む PR は **0 件**。§3:63 の「新しいファイルが pages/routers/models に追加 → A」が baseline 側でも効いている
- 題名が fix/docs/EMERGENCY 以外の B は refactor 2 件（#3764 #3901）で、v5 審査と同じ

---

## 3. §1・§3・§4 の整合と新しく見つかった点

### 3-1. §1・§3・§4 の一致
| 項目 | §1 | §3 | §4 | 一致 |
|---|---|---|---|---|
| S3 の分母 | :40「B-1・B-2（L と docs/テストだけの B-3 は入れない）」 | :68-73 で B-1/B-2/B-3/L を定義。L は「S3 の分母には入れない」 | :80・:82・:83「B-1・B-2」 | 一致 |
| fix 候補の定義 | :40「同じファイルを触り、タイトルに fix/修正/不具合/EMERGENCY/hotfix/Revert」 | — | :80 同文 | 一致 |
| 判定不能の扱い | :40「判定不能は原因に数えない」 | — | :80「原因／別件／判定不能」 | 一致 |
| EMERGENCY | :40「B が原因の EMERGENCY PR は0件」 | — | :82 の3行提示に EMERGENCY の項が無い | 軽微（LOW-1） |
| 分類 script | — | :58-73 | :80「classify-v5.py と同じ条件」＋:83 で差分（deploy 範囲・styles/）を宣言 | 一致（宣言込み） |

### 3-2. 新しく見つかった点（いずれも LOW）

**LOW-1: §4:82 の PO への3行に、S3 後段「B が原因の EMERGENCY は0件」の項が無い**
- 【事実】design-v6.md:82「3行（A の承認なしマージ件数／B-1・B-2 の原因 fix の件数と率・基準値 4.0%／判定）」。:40 で成功条件に加えた EMERGENCY 0 件が、監査の提示文に含まれていない
- 直し方: 2 行目を「B-1・B-2 の原因 fix の件数と率（基準値 4.0%）・B 原因の EMERGENCY 件数（基準値 0）」にする。文面の追加のみ

**LOW-2: 分母に残した 50 件は題名だけで B と判定しており、「fix 題名の新機能」の精査は #3717 だけ**
- 【事実】B 55 件のうち題名に add/追加/新規 を含むものは #3717 #3776「fix: …破線枠とファイルアイコンを追加」#3871「fix: retry_extraction に job_ids 件数上限ガードを追加」#4006（docs）。#3776・#3871 の本文は読んでいない（既存画面の見た目調整・既存関数へのガード追加と読めるので B-2/B-1 相当の可能性が高い【推測】）
- 影響: もし分母側にも「試行なら A」の PR が残っていれば真の分母は 50 未満で、真の基準値は 4.0% より**高い**。つまり 4.0% は厳しい側（下限）であり、合格ラインとして安全側。数字の変更は不要
- 直し方: :40 に「分母の 50 件は題名・パスで判定（本文の精査は原因側の #3717 のみ）。よって 4.0% は厳しい側の値」を1文足す

**LOW-3: #4006 は `docs/handoff/.../data/20261006-category/apply.sql`・`rollback.sql` を含む本番データ変更の記録で、パス条件では B-3 になる**
- 【事実】_cache0922.json の #4006 変更ファイル: README.md・apply.sql・dryrun.sql・list.csv・rollback.sql（すべて docs/handoff/ 配下）＋台帳。classify-v5.py は B。§3:64「本番データの手直し」は A だが、機械では判定できない（§6:105 で「今と同じ守り」と宣言済み）
- 影響: baseline では分母から外れており数字に影響なし。試行中は「docs/ 配下の .sql を B-3 として PR まで進める」ことが可能になるが、実際の適用は ADR-1003 の例外・agent-danger-hook・PO!実行の規則が守る（design-v6.md:105）
- 直し方（任意）: §3:72 の B-3 に「ただし `.sql` を含む場合は A」を足すと機械で拾える。足さない場合は §6:105 の説明で足りる。PO/Opus の判断

### 3-3. design-v6.md の参照先の実在確認（origin/main 74acffd889）
- CLAUDE.md:53（`--draft` 必須 Draft の行）・:70-72（標準開発フロー「①KGI設定（定量・PO承認）」）— 一致
- docs/STANDARD-WORKFLOW.md:23（「PO承認が必須ゲート」）・:79（「KGI：定量・PO承認済み」）・:115-119（§3 不明点プロトコル）— 一致
- docs/ai-agents/design-partner.md:72（PO承認を得たKGI ÷ 全KGI）・:106（①KGI設定（PO承認ゲート））・:116（PO自筆GO必須）— 一致
- AGENTS.md:26（通常の新機能・バグ修正経路 … GO）・:59（→ PO Approval）— 一致
- scripts/check-process-artifacts.js:373-379（GO 原文の `GO #<PR番号>` 必須・番号不一致でエラー）— design-v6.md:49 の記述と一致
- `.github/PULL_REQUEST_TEMPLATE.md` 実在。ADR 最大番号 ADR-1014（design-v6.md:88 と一致）
- ADR-1003:58「ADR-1002 の振り返り運用（governance監査）で軽減する」— design-v6.md:117 の「参照先の誤り」の記述は v5 と同じ事実に基づく

### 3-4. baseline-v5.md との関係
- 【事実】baseline-v5.md:32 は「原因あり B: 3 / 55（5.5%）」のまま。2/50 の導出は design-v6.md:9・:40 にだけ書かれている。design-v6 の説明（55 − docs だけ 4 − #3717）は本審査の再計算で裏が取れたので、設計の採用に支障はない
- 【推測】監査担当が後で基準値の出所を追うとき、baseline 側に 1 段落（v6 の導出）があるほうが迷わない。実装カードで baseline-v5.md に追記するか、baseline-v6.md を作ると良い（LOW 扱い、上の LOW-1〜3 には含めない）

---

## 4. 観点ごとの結論

| 観点 | 結論 |
|---|---|
| 1. v5 指摘の解消 | MEDIUM-1〜3・LOW-1〜4 の 7 件すべて直った（LOW-3 は設計文書での宣言。script の修正は実装カードの仕事） |
| 2. 基準値 2/50＝4.0% | 元データから再計算して一致。分母 50 = B 55 − docs だけ 4（#3825 #3950 #3970 #4006）− #3717。分子 2 = #3736・#3763。テストだけの B は 0 件 |
| 3. §1・§3・§4 の整合 | S3 の分母・候補定義・判定不能の扱いは 4 か所で同文。§4:82 の3行提示に EMERGENCY の項が無い（LOW-1） |
| 4. 新しく見つかった欠陥 | LOW-1（提示文に EMERGENCY 無し）・LOW-2（分母 50 件は題名判定。4.0% は厳しい側）・LOW-3（docs/ 配下の .sql が B-3 になる。§6:105 で宣言済み）。HIGH・MEDIUM なし |
| 5. 判定 | **APPROVE**。LOW 3 件は実装カード（§5 の文書修正）に含めて直せばよく、設計の再提出は不要 |

## 5. Generator への指示の範囲（PO の y の後）
- Approved Scope: design-v6.md §5 の文書修正（新 ADR・STANDARD-WORKFLOW.md・CLAUDE.md:53/:70-72・design-partner.md・AGENTS.md・PR テンプレート）＋監査 script を §3 に合わせる（deploy の語の範囲を `frontend/src/`・`backend/app/`・直下に限定、`styles/` 除外を削除）＋ LOW-1・LOW-2 の1文追記
- 触らない範囲: CI・フック・許可設定・Ruleset・ADR-1012・コード本体（design-v6.md:53）
- Risks: §6 の表どおり。追加で LOW-3（docs/ 配下 .sql）は PO/Opus が §3 に足すかを決める
- PO Approval Required: true
- Ready For Generator: true（PO の y を待つ）

## 6. 【未確認】
- #3736→#3793: 本番で "-" が実際に id 61 に解決された件数（v5 と同じ。コード経路からは原因と読める）
- #3776・#3871 の本文（LOW-2。分母側の精査は未実施）
- スマホでのマージ可否（design-v6.md:116）
- S1 の「前」3 営業日の実測値（試行前に取る前提）
- 試行中に B になる PR 件数（「約 50 件」は 9/22〜10/6 のペースからの推測）
