# 設計再審査（Fable）: design-v3.md「危険でない変更は1件ごとの PO 承認をなくす」

- 審査日: 2026-10-14 / 読み取りのみ（編集・commit・本番接続なし）
- 審査対象: /tmp/CC報告ファイル/devflow-switch/design-v3.md
- 根拠資料: review-fable.md（v2 審査）、baseline-prs.md、baseline-prs-0922-1006.md、baseline-explicit-fix.md、classify-0922-1006.py、_explicit.py、_baseline-raw-0922-1006.json、_f0922/<PR>.json、_w0922.json
- 実物の照合先: 本店 /Users/tanizawashingo/salesanchor の `git show origin/main:<path>`
  - 【事実】origin/main = d1dd0ad6（v2 審査時と同一）。`git ls-remote origin main` も d1dd0ad6 で、リモートと一致。
- 作業ログ（生出力）: /private/tmp/claude-501/-Users-tanizawashingo-salesanchor/76107781-c1ca-4ee0-8eab-b12dd6cc5c3a/scratchpad/{b_check,pairs,s3_check,b1_feas}.txt

## 判定: REVISE

方向（M 廃止・パス条件で B を判定・GO は ADR-1003 のまま・マージは PO）は v2 の HIGH-1/HIGH-2 の主旨どおりに直っており、CI・フック変更なしで成立する点も変わらない【事実・v2 審査 §B 観点4】。
ただし、(1) §3 の区分と分類スクリプトが食い違い、台帳 PR（B の 24%）が v3 では「どちらでもない→PO に y/n」になる、(2) S3 の基準値 7.7% は誤カウント3件・取りこぼし4件以上を含み、分母の中身も v3 の B と別物、(3) S2 は監査コマンドでは測れない（承認の有無が記録されていない）、(4) `backend/app/auth/` の外にある認証ファイルが B に落ちる、(5) 2 階層以上の正本 ideal-state.md／kgi.md 44 本が B に落ちる、の5点（HIGH 5 件）は試行前に直す必要がある。いずれも文書修正で足り、コード変更は不要。

---

## 1. 前回指摘の解消状況

| 前回 | 状態 | 根拠 |
|---|---|---|
| HIGH-1 M 区分は y の範囲外 | 解消 | design-v3.md §3: M 廃止。migration・scripts・ops・.github・auth・token/password/payment・ADR・正本は A。GO は ADR-1003 のまま（§2） |
| HIGH-2 B 判定の自己矛盾・抜け道 | 一部 | B-1/B-2/B-3 をパス条件化（§3）。残り: ①`.claude-pipeline/` が §3 に無い（下記 HIGH-A）②認証ファイルの所在と A 条件のずれ（HIGH-D）③B-2「API 契約変更なし」を CI 緑で代用（MEDIUM-A） |
| HIGH-3 S2・S3 の機構と基準値 | 一部 | 監査の実行者・コマンド・保存先・提示形式を定義し、空振り実行済み（§4）。S3 に基準値 7.7% を置いた。残り: S2 は監査では測れない（HIGH-C）、S3 の基準値の数え方に誤り（HIGH-B）、S1 の「前」の値が規則からの推定で実測でない（MEDIUM-E） |
| MEDIUM-1 §5 の漏れ5件 | 解消 | §5 に CLAUDE.md:53、design-partner.md:116、STANDARD-WORKFLOW §3 接続、ADR-1012、AGENTS.md:26/:59 を追加。「変更前→変更後の文」は実装カードへ送る旨あり（可） |
| MEDIUM-2 CLAUDE.md 120 行上限 | 解消 | §5「120行上限・行数を増やさず置換」。【事実】`git show origin/main:CLAUDE.md \| wc -l` = 120。:53 は Draft 規則、:70 は①KGI設定の行（照合一致） |
| MEDIUM-3 S1 の測り方 | 解消 | S1「PO が返答するのはマージ可否だけ」、3行報告は読むだけ、PO 自身が数える |
| MEDIUM-4 CI が一時赤になる順序 | 解消 | §2 表「CI の順序」行。check-process-artifacts.js:373-379 照合一致 |
| LOW-1 自律停止の語 | 解消 | §5 新 ADR 行に明記 |
| LOW-2 S4 の担当・期日 | 解消 | S4「試行開始＋14日、Opus が docs/handoff/ に保存」 |
| LOW-3 ADR-135 の develop 表記 | 該当なし | v3 は ADR-135 を引いていない。問題なし |

---

## 2. 指摘

### HIGH-A: §3 の区分と classify-0922-1006.py が一致しない。台帳のみ PR（B 156 件中 38 件＝24%）が v3 では「どちらでもない」になる
- 【事実】classify-0922-1006.py:19 `isB` は `.claude-pipeline/` を B に含める。design-v3.md §3 の B-1〜B-3 に `.claude-pipeline/` は無い。A にも無い。よって v3 の文面では台帳のみ PR（例 #4014「chore(ledger): PR #4013 を DONE 化（自動）」）は「どちらでもない→AI は止まって PO に y/n を1問聞く」に落ちる。
- 【事実】_f0922 の変更ファイルで数えると、B 156 件のうち台帳（`.claude-pipeline/`）のみは 38 件、docs＋台帳のみは 5 件（b_check.txt）。
- 影響: ①S1 が構造的に崩れる（台帳 PR は週 15 件以上、毎回 PO に質問）②S3 の分母 156 に「修正が起きえない PR」が 38 件入り、率が薄まる。台帳のみを除くと 12/118 = 10.2%（s3_check.txt）。
- 直し方: §3 B-3 に `.claude-pipeline/` を明記するか、台帳自動 PR を「区分の対象外（既存の自動 GO 不要運用のまま）」と1行書く。S3 の分母も台帳を除いた値で置き直す。

### HIGH-B: S3 の基準値 7.7%（12/156）は数え方に誤りがあり、合否の閾値に使えない
明示参照 16 組（baseline-explicit-fix.md）の本文を全件読んだ（pairs.txt）。
- 誤カウント（B の不具合ではない）3 件:
  - #3912 ← #3934・#3954: 本文は「前の便は PR #3912」「前提の便（PR #3912・#3934）」。続きの便であり修正ではない。
  - #3822 ← #3824: #3824 は scripts/ のゲート修正。本文の #3822 は「main #3822先行によるBEHINDを確認」（取り込みの記録）。
  - #3821 ← #3822: #3822 の「なぜ」は empty/filtered 行の表示ノイズ削減（#3821 の不具合ではない）。#3821 は GO原文「（PR #3821 委任を継承）」にだけ出る。
  - 疑い 1 件: #3962 ← #3963 は migration phase2c の FK 問題で、#3962 のデプロイが引き金になっただけ（#3962 は migration 変更なし）。#3964 は #3962 が残した古いコメントの修正（挙動の不具合ではない）。
- 取りこぼし（B の不具合を直したが PR 番号を書いていない）4 件以上:
  - #3787（B, 9/25 18:24 ランキング追加）→ #3789（9/26 00:12「抽出ランキングAPI応答形状の修正（白画面解消）」本文に PR 番号なし）
  - #3776（B, 9/25 13:21 破線枠追加）→ #3780（9/25 14:01「破線ボーダーが表示されない問題を修正」。本文の #475569 は PR 番号でない）
  - #3755（B）→ #3763、#3763（B）→ #3769: いずれも `_merge_supplier_products()` の supersession 修正の連鎖（fix(pipeline)）。本文に前 PR 番号なし。
  - 他に #3715・#3798（/api/v1 二重 prefix）・#3753（i18n キー未登録）・#3772 は原因 PR が本文に無く【未確認】。
- 分母の中身: 台帳を除く B 118 件の題名は feat 60・fix 48・docs 6・refactor 3・EMERGENCY 1（s3_check.txt）。v3 の B は「不具合修正・文言見た目・テスト文書」で、feat は B-1 の2点が書けないので A か「どちらでもない」になる。基準値の集団と試行の集団が別物。
- 影響: 誤カウントを引き 取りこぼしを足すと 12→13 前後で率は 8〜11% の間を動き、「7.7% を超えない」は観測誤差の中に入る。14 日の試行で B が 50 件前後なら修正 1 件＝2% で、閾値の意味がない。
- 直し方（いずれか）: ①基準値を「台帳を除く B のうち fix/docs 題名の PR（約 55 件）」に限って人手で 1 件ずつ『後続 fix の原因になったか』を判定し、件数で置く（55 件なら 1 時間以内で終わる量）②S3 を率でなく「B が原因の EMERGENCY／本番 5xx 復旧 PR の件数が基準（9/22〜10/13 で 1 件）を超えない」の件数指標に変える。明示参照方式を残すなら、fix PR の本文に「原因 PR: #N」の行を必須にして、試行中は取りこぼしが起きない形にする（これは §6 の PR 本文先頭3行に足せる）。

### HIGH-C: S2「A が PO 承認なしにマージされた件数 0」は §4 の監査では測れない
- 【事実】§4 の監査コマンドは「変更ファイルを A のパス条件と突き合わせる」。得られるのは「A に当たった PR の件数」だけで、その PR が KGI/設計の PO 承認を得たかは分からない。v3 自身が §1 S2 の基準値欄で「承認の有無は過去 PR では測れない」と認めている。試行後も同じ理由で測れない。
- 【事実】PR 本文の必須欄（.github/PULL_REQUEST_TEMPLATE.md、scripts/dev/validate-pr-body.sh:31-75、check-process-artifacts.js validateDesignDoc）に「PO 承認の原文・日時」を書く欄は無い（v2 審査 §B 観点4）。
- 直し方: A 区分の PR 本文（`### 標準ワークフロー確認` の中）に「区分: A／PO承認: <原文・日時>」の 2 行を必須と §6 に書き、監査はその行の有無で S2 を数える。B 区分も「区分: B-1/B-2/B-3」を書けば、監査で「B と自己申告したが A パスに当たる PR」を機械で拾える（§6 第1行のリスクの検出手段になる）。

### HIGH-D: 認証ファイルは `backend/app/auth/` の外にもあり、v3 のパス条件では B に落ちる
- 【事実】`git ls-tree -r origin/main` で認証・セッション・OAuth・権限に関わるファイルのうち A 条件に当たらないもの: `backend/app/routers/auth.py`、`backend/app/middleware/session_guard.py`、`backend/app/routers/discord_oauth.py`、`backend/app/services/oauth_state.py`、`backend/app/services/google_drive_oauth.py`、`frontend/src/contexts/AuthContext.tsx`、`frontend/src/lib/firebase-auth.ts`、`frontend/src/lib/firebase.ts`、`frontend/src/hooks/usePermissions.ts`。
- 【事実】基準値の B に実例あり: #3912（B）は `backend/app/services/google_drive_oauth.py` を変更（b_check.txt「suspicious」）。
- 【事実】逆の誤りもある: ファイル名 `token` の条件で `frontend/src/tokens.css`（デザイントークン）と `frontend/src/pages/design-preview/sections/TokenSection.tsx` が A になる。直近 60 件の A 28 件のうち #4237・#4234・#4196 の 3 件は tokens.css だけが理由（baseline-prs.md）。tokens.css は PO の y の「画面」に入るものを A に押し戻している。
- 直し方: A 条件に `backend/app/routers/auth.py`・`backend/app/middleware/`・`backend/app/routers/discord_oauth.py`・`backend/app/services/*oauth*`・`frontend/src/contexts/AuthContext.tsx`・`frontend/src/lib/firebase*`・`frontend/src/hooks/usePermissions.ts` を追加（または「auth/oauth/session/permission をパスに含む」に広げる）。`token` は `tokens.css`・`TokenSection.tsx` を除外するか、「token」の対象を backend に限る。

### HIGH-E: §3 A「`docs/specs/*/ideal-state.md`／`kgi.md`」は 1 階層しか見ず、2 階層以上の正本 44 本が B に落ちる
- 【事実】classify-0922-1006.py:8 の正規表現は `^docs/specs/[^/]+/(ideal-state|kgi)\.md$`。§3 の文面 `docs/specs/*/ideal-state.md` も同じ読み。`git ls-tree -r origin/main docs/specs` で ideal-state.md／kgi.md は 110 本、うち 2 階層以上（design-system/visual-language、design-system/component-ssot/*、inbox/*、inventory-management/*、management-center/*、order-management/unpaid、process-hardening/proof-of-behavior）が 44 本。
- 【事実】基準値の B に実例あり: #3927（B）は `docs/specs/design-system/visual-language/ideal-state.md`・`kgi.md` を新規追加している（b_check.txt 抜き取り）。正本の新設が PO 承認なしの区分に入っている。
- 直し方: §3 と監査スクリプトの条件を `docs/specs/**/ideal-state.md`・`**/kgi.md`（階層を問わない）に直す。基準値の A/B 件数も再計算する。

### MEDIUM-A: B-2「API 契約変更なし（必須チェック『API contract is up to date』）」は CI 緑では判定できない
- 【事実】.github/workflows/api-contract-check.yml は OpenAPI を書き出して `git diff --exit-code -- frontend/api-contract/` を見る（:31-55）。PR が `frontend/api-contract/openapi.json` を更新していれば契約が変わっていても緑。
- 直し方: B-2 の条件を「変更ファイルに `frontend/api-contract/` を含まない」に置き換える（パス条件で機械判定できる）。

### MEDIUM-B: `backend/app/tools/`・`backend/app/tasks/` は本番運用コードだが B
- 【事実】v3 が A に足したのは `backend/tools/`（中身は export_openapi.py の 1 本）。別に `backend/app/tools/`（prompt_ab.py・prompt_ab_recompute.py・sync_review_reason_labels.py＝本番 DB を読む比較試験・同期ツール）があり、基準値の B が 10 回触っている。`backend/app/tasks/`（celery 定期実行）も B が 9 回。
- 直し方: PO の y の範囲（画面・文言・不具合修正）に照らし、`backend/app/tools/` と `backend/app/tasks/` を A にするか B のままにするかを §3 に明記する（どちらでも可。書いていないのが問題）。

### MEDIUM-C: B-1 の「正本」は実態として ADR のみ。LINE解析・買取相場の領域に ideal-state.md が無い
- 【事実】台帳を除く B のうち fix 題名 48 件の design.md（45 件に存在）を origin/main で読んだ: `ideal-state.md`／`kgi.md` を引いたもの 0 件、`ADR-NNN` を引いたもの 45 件（b1_feas.txt）。
- 【事実】`docs/specs/*/ideal-state.md` は 54 本あるが、B の大半が触る LINE解析（super-admin）・買取相場・抽出パイプラインの ideal-state は無い（一覧に tcg/line/extraction/buyback を含む spec なし）。
- 影響: B-1 の「期待値＝正本の引用」は事実上「ADR の行を引く」になる。ADR は AI が起案したものが多く、v2 HIGH-2 で指摘した「どれか 1 本引けば形式上は根拠になる」経路が残る。
- 直し方: B-1 の正本に ADR を含める場合、「ADR 番号＋Decision/What 節の file:line＋その行の引用文」を 3 点セットで必須とし、Fable 審査がその行を `git show` で実在確認することを §2 に書く。または、LINE解析領域は ideal-state を先に作る（STANDARD-WORKFLOW.md:24 の 1.5 と同じ扱い）と書く。

### MEDIUM-D: Fable 審査 APPROVE の記録先が無い
- 【事実】§2「recon/design を AI が書き、Fable 審査 APPROVE で実装へ」。保存先・形式の指定なし。監査（§4）が「Fable 審査を経たか」を確かめる手段が無い。
- 直し方: `docs/handoff/<仕事名>/review-fable.md`（判定行を先頭に）を必須成果物とし、PR 本文の `### 標準ワークフロー確認` に行を足す。

### MEDIUM-E: S1 の「前」の値が実測でない
- 【事実】§1 S1 基準値「今は1件ごとに KGI 承認・実装承認の2回」は規則（STANDARD-WORKFLOW.md:23,:79）からの導出。baseline-prs.md の KGI/PO承認/承認済/y-n の出現回数は参考値で、PO の返答回数ではない。
- 直し方: 試行初日から PO が「返答した回数」を数えるのと同じ方法で、試行前の 3 営業日だけ先に数えて「前」に置く（PO の手間は 1 日 1 行）。

### LOW-A: `frontend/scripts/`・`backend/scripts/`（CI の検査スクリプト）が §3 のどこにも無い
- 【事実】classify では `^scripts/` のみ A。`frontend/scripts/check-*.js`（必須チェックの本体）は B でも A でもなく「どちらでもない」。STANDARD-WORKFLOW.md:166「ゲート弱体化は PO 確認」と整合させるため A に明記するのが自然。

### LOW-B: 新 ADR の番号
- 【事実】`git ls-tree origin/main docs/adr/` の最大は ADR-1014。§5「索引で空き番号を確認」で足りる。

---

## 3. 観点ごとの結論

| 観点 | 結論 |
|---|---|
| 1. 前回指摘の解消 | HIGH-1 解消／HIGH-2 一部／HIGH-3 一部、MEDIUM 1〜4 解消、LOW-1・2 解消、LOW-3 該当なし（§1 の表） |
| 2. classify と §3 の一致 | 不一致 1 点（`.claude-pipeline/` を B 扱い＝HIGH-A）。抜き取り 10 件（#3725・#3772・#3927・#3741・#3717・#3944・#3710・#3787・#3760・#3780、b_check.txt）はいずれも migrations・`backend/app/auth/`・scripts・.github を含まず、§3 のパス条件では B。ただし #3927 は `docs/specs/design-system/visual-language/ideal-state.md`・`kgi.md` を新規追加しており、§3 A「docs/specs/*/ideal-state.md」は 1 階層のみを見るため（正規表現 `docs/specs/[^/]+/`）、2 階層以上の spec の ideal-state.md／kgi.md 44 本（design-system/visual-language、inbox/*、management-center/* 等。`git ls-tree -r origin/main docs/specs` で確認）が A から漏れる。#3927 は実際に B に分類されている。§3 の文面「`docs/specs/*/ideal-state.md`」も同じ読みになるので、`docs/specs/**/ideal-state.md` に直す。B 156 件に migrations・`backend/app/auth/` を含むものは 0 件（b_check.txt「suspicious」は台帳のファイル名と docs の語のみ。例外 #3912 の oauth は HIGH-D） |
| 3. S3 7.7% の妥当性 | 妥当でない（HIGH-B）。誤カウント 3（#3912・#3822・#3821）＋疑い 1（#3962）、取りこぼし 4 以上（#3787・#3776・#3755・#3763）。分母に台帳 38 件、feat 60 件を含む |
| 4. 試行前にまだ足りない事実 | (a) 台帳 PR の扱いを決めたうえでの基準値再計算（HIGH-A）(b) fix/docs 題名 B 約 55 件の人手判定による S3 基準値（HIGH-B）(c) S2 を数えるための承認記録欄の定義（HIGH-C。これは事実でなく設計の追記）(d) 認証ファイル一覧の A 条件反映（HIGH-D。一覧は本審査で取得済み）(e) S1 の「前」3 日分の PO 返答回数（MEDIUM-E）(f) B-1 で引ける正本が ADR のみであることの PO への明示（MEDIUM-C） |
| 5. PO に伝えるべき結論 | 「条件付きで実現できる」。根拠は §4 |

---

## 4. PO への結論の根拠（条件付き）

- 実現できる側の事実: 今の CI・フック・許可設定は KGI 承認・設計承認を見ていないため、文書を直すだけで B 区分の PO 承認をなくせる（v2 審査 §B 観点4、v3 でも不変）。GO は ADR-1003 のまま、マージは PO が押すので、本番に入る最後の関所は変わらない。直近 15 日の PR 284 件を §3 の条件で機械分類できた（空振り実行済み）。
- 条件（直さないと「うまくいったか」を PO が○×で判定できない、または y の範囲を超える）:
  1. 台帳 PR（24%）の扱いを §3 に書く（書かないと毎回 PO に質問が飛ぶ）
  2. S3 の基準値を数え直す（今の 7.7% は誤カウントと取りこぼしを含む）
  3. S2 を数えるための「PO承認の原文・日時」欄を PR 本文に定義する
  4. 認証に関わるファイル 9 本を A に加える（今の条件では自動で B になる）
  5. 正本 `docs/specs/**/ideal-state.md`・`kgi.md` の条件を階層を問わない形に直す（今は 44 本が自動で B になる）
- 「できない」に当たる事実は無い。5 条件はいずれも文書の追記で、コード・CI・権限の変更を伴わない。

## 5. 【未確認】
- #3715・#3798・#3753・#3772 の原因 PR（本文に番号なし。B の取りこぼし数が 4 より増える可能性）
- スマホでのマージ可否（v2 と同じ。§9 のとおり試行初日に PO が実機で確認）
- `docs/specs/design-partner-loop/README.md` KGI-3 チェックリストの中身（v2 と同じ・未読）
