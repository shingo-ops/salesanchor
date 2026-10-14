# 設計再審査（Fable）: design-v5.md「危険でない変更は1件ごとの PO 承認をなくす」

- 審査日: 2026-10-14 / 読み取りのみ（repo・本番・GitHub への書き込みなし。gh は `gh api repos/shingo-ops/salesanchor/pulls/N`・`pulls/N/files`・`gh pr list` の読み取りだけ）
- 審査対象: /tmp/CC報告ファイル/devflow-switch/design-v5.md、baseline-v5.md、classify-v5.py、_v5-cand.py、_v5-tally.py、_v5-rows.json、_v5-judge.json、_v5-content.txt、_v5-out.txt
- 前回審査: review-fable-v4.md（REVISE、HIGH-1・MEDIUM-1〜3・LOW-1〜4）
- 実物の照合先: `git fetch` 後の origin/main = e0355ceef6（v4 審査時と同一 SHA）。PR 本文・patch は gh api で取得し `_fable-v5/pr/pN.json`（本文）・`fN.json`（files+patch）に保存（17 PR・51 ファイル）
- 再実行: classify-v5.py を実行し 284 件 → A 186 / B 55 / L 38 / その他 5 を再現（baseline-v5.md:7-11 と一致）。_v5-tally.py の出力（_v5-tally.txt）も「原因 3・判定不能 2・候補 102 組・候補を持つ B 29・fix PR 33」で baseline-v5.md:30-35 と一致

## 判定: REVISE（HIGH 0 件・MEDIUM 3 件・LOW 4 件）

PO への結論（1行）: 数字の作り方は直り、実物と合っている。残るのは「分母の数え方を1つに決める」「EMERGENCY の基準値の書き誤り」など文書の手直しだけで、コード・CI・権限は触らずに済む。

v4 の HIGH-1 と MEDIUM-1〜3 は直った。LOW-3 だけ一部。新しく見つかったのは MEDIUM 3 件（いずれも design-v5.md の文面の矛盾・書き誤り）と LOW 4 件。安全側（A が増える方向）に働く誤りはなく、合格ライン（S3）を緩める方向の誤りが MEDIUM-1 に 1 件ある（5.5% → 感度 3.7%）。

---

## 1. v4 指摘の解消状況（指摘ごと）

| v4 | 状態 | 根拠 |
|---|---|---|
| HIGH-1 S3 の分母に「試行では A になる PR」が入る | 直った | classify-v5.py:33 で `cls=='B'` かつ題名 `^\s*feat(:\|\()` を A に移す。_v5-rows.json と _v4-rows.json の差分は 55 件（B→A 50・A→B 4・A→L 1）で、B→A 50 件はすべて題名 feat（_v5-tally.txt「dropped not feat? []」）。v4 の原因 10 件のうち 9 件（#3710 #3724 #3746 #3752 #3774 #3787 #3811 #3818 #3906）が A に移り、design-v5.md:30 の基準値は 3/55＝5.5%。残り（fix 題名の新機能）は MEDIUM-1 |
| MEDIUM-1 語の判定が docs/handoff・台帳のパスに当たる | 直った | classify-v5.py:17-19 `inscope = frontend/src/ or backend/app/ or '/' not in p`。design-v5.md:49 と一致。#3755 #3763 #3769 #3873 が A→B、#3940 が A→L（_v5-rows.json）。認証 9 本は 9/9 が A のまま（_v5-out.txt・本審査でも再実行して同じ） |
| MEDIUM-2 #3736→#3793 の扱い | 直った | baseline-v5.md:42-48 で人手判定「原因」。本審査の patch 照合でも裏付けあり（§2-1） |
| MEDIUM-3 B-2 に frontend 新機能が入る | 直った | design-v5.md:61「既存の文言・CSS・配置の変更だけ（新機能は A）」、:52「新機能（PR タイトルが feat、または design.md の目的が…）」。baseline 側は題名 feat で A（classify-v5.py:33） |
| LOW-1 baseline-v4.md:31 の「39」 | 直った | baseline-v5.md:63-66 で「書き誤り。正しくは候補 305 組中の全 fix PR（46 件）」 |
| LOW-2 `styles/` 除外は空振り | 直った（文書）／script は残置 | design-v5.md:49 から `styles/` は消えた。classify-v5.py:19 には `frontend/src/styles/` 除外が残るが、origin/main に当該ディレクトリは無く結果に影響しない（LOW-3 で記録） |
| LOW-3 S1 の数え手・記録の場所 | 一部 | design-v5.md:28「Opus が会話記録から数え、監査ファイルに書く」。「どこの記録（どのセッション／Discord を含むか）を数えるか」の1行はまだ無い。前後比較は同条件で数えれば成立するので低優先（LOW-4 に再掲） |
| LOW-4 baseline の注記例 | 直った（対象消滅） | baseline-v5.md に「author」の記述なし（`grep -c author` = 0）。語の対象を限定したため注記そのものが不要になった |

---

## 2. baseline-v5.md と classify-v5.py の実物照合

### 2-1. 原因 3 組（gh api の patch と PR 本文で照合。_fable-v5/pr/）
| 組 | 結果 | 根拠 |
|---|---|---|
| #3717→#3730 | 原因で正しい | #3717 の `backend/app/schemas/central_masters.py` hunk `@@ -438,6 +438,22` で `class SupplierSourceMessage(BaseModel): id: int` を追加。#3730 の同ファイル hunk `@@ -446,7 +447,7` が `-    id: int` / `+    id: UUID`、本文「`source_messages.id` は DB 上 `uuid` 型だが、Pydantic スキーマが `int` で定義されていたため…500」。注意: #3717 は題名 fix だが本文「`GET /super-admin/suppliers/{id}/source-messages` エンドポイントを追加」「左ペインにページ送りナビゲーション UI 追加」で新機能を含む（MEDIUM-1） |
| #3736→#3793 | 原因で妥当（コード経路で確認） | #3736 の `tcg_analyzer_svc.py` hunk `@@ -1164` で `product_code_to_id`（`SELECT product_code, id FROM public.products`）を追加、hunk `@@ -1209,8 +1217,23` で `_resolve_pid` を追加し `validate_product_id` が None のとき `product_code_to_id.get(pid)` で救済。#3793 の同ファイルは 1 行差分 `-if pid is None or pid == "":` / `+if pid is None or pid == "" or pid == "-":`。#3736 以前の `validate_product_id`（`git show cf7cd489b^1:backend/app/services/tcg_work_reference.py` 55-63 行）は参照に無い値を None で返すので、"-" が id 61 に解決される経路は #3736 が作ったもの。【注意】`migrations/20260926_080100_fix_product_code_dash.sql` のコメントは「product_code が '-' のため _resolve_pid が商品を特定できなかった」と逆向きの表現。コードの経路は baseline-v5.md:47 の読みが正しいが、本番で実際に id 61 に解決された件数は baseline-v5.md:48 と同じく【未確認】。判定不能に倒すと 2/55＝3.6%（baseline-v5.md:35 の感度どおり） |
| #3763→#3769 | 原因で正しい | #3763 の hunk `@@ -1629,6 +1631,12` が `AND sm_old.received_at < (SELECT sm2.received_at …)` を追加。#3769 の hunk `@@ -1669,47 +1669,56` が同じ 6 行を `-` で除去し ROW_NUMBER 方式に置換、本文「旧ロジックは『自分より古いメッセージの…行を FALSE にする』方向更新だったため…二重TRUE不整合」 |

### 2-2. 分母から外れた feat 50 件のうち 5 件（題名と変更ファイルを gh api で確認）
| PR | 題名（gh api） | 変更ファイル | 結果 |
|---|---|---|---|
| #3767 | feat: add chart period selector (7/30/90/180/360 days) to LINE解析 dashboard | backend/app/routers・services、frontend/src/pages/super-admin/components、docs/handoff、locales | 題名 feat・パスは B 条件 → v5 で A。正しい |
| #3861 | feat: LINE お知らせ判定を1か所にまとめる（段階1 C1） | backend/app/services/tcg_line_system_events.py（added）ほか、backend/tests、docs/handoff、台帳 | 同上。新規 services ファイルは pages/routers/models 条件に当たらないので v4 では B だった。v5 で A は妥当 |
| #3996 | feat(frontend): SelectControl に karte/header/tabbar の種類を登録（金型化 §AW AW-1） | frontend/src/components/Select.tsx・FormField.css・stories・test、docs/handoff | 題名 `feat(` → A。`feat(` の形も classify-v5.py:33 の正規表現で拾えている |
| #3727 | feat: use Gemini resolved_product_code for pid resolution | backend/app/services/tcg_analyzer_svc.py、backend/tests、docs/handoff、台帳 | 同上 |
| #3710 | feat(dashboard): 提供者別パイプライン可視化 | backend/app/routers・services、frontend/src/pages/super-admin/components、locales、docs/handoff | v4 で原因と判定された PR。題名 feat で A に移ったことを確認 |

### 2-3. A→B に移った 4 件（変更ファイルを gh api で確認）
| PR | 変更ファイル | v4 で A だった理由 | v5 |
|---|---|---|---|
| #3755 | backend/app/services/tcg_analyzer_svc.py、docs/handoff/condition-level-supersession/{design,recon}.md | ディレクトリ名 **supersession** の `session` | 語の対象外 → B。妥当 |
| #3763 | backend/app/services/tcg_analyzer_svc.py、docs/handoff/fix-supersession-timestamp-order/{design,recon}.md | 同上 | B。妥当 |
| #3769 | backend/app/services/tcg_analyzer_svc.py、backend/tests/×2、docs/handoff/supersession-global-latest/{design,recon}.md | 同上 | B。妥当 |
| #3873 | backend/app/services/{extraction_shadow_svc,gemini_extraction_svc,inventory_parser_llm}.py、backend/tests/×3、docs/handoff/fix-gemini-token-cost-recording/{design,recon}.md | ディレクトリ名 **token-cost** の `token` | B。本文は Gemini の `candidates_token_count`（出力トークン数）の読み誤り修正で認証と無関係。妥当 |

新 B 10 組の人手判定の抜き取り:
- #3755→#3763「別件」: #3755 の patch は `ANY(:product_ids)` → `EXISTS(unnest…)` と docstring・コメントの置換のみで、`sm_old.received_at` は `-` 行にも `+` 行にも無い。#3763 が直した「received_at を見ない UPDATE」は #3755 以前から存在 → 別件で正しい
- #3873→#3876「別件」: #3876 の `gemini_extraction_svc.py` 差分は docstring 3 行（`gemini-3.6-flash` → `_GEMINI_MODEL` 参照）のみ、本文「実行コードの変更なし」。別件で正しい（#3876 自体は docs/adr を含むので A）

### 2-4. classify-v5.py と design-v5.md §3 の一致
| §3 | script | 一致 |
|---|---|---|
| A ディレクトリ 12 種（:48） | classify-v5.py:8-9 の Apre（11 種、すべて `^` 固定）。`backend/app/auth/` は inscope の語 `auth`（:18）で拾う | 一致 |
| 語は `frontend/src/`・`backend/app/`・直下だけ（:49） | :17 `inscope`（`'/' not in p` ＝ 直下） | 一致 |
| token は `.css` を除く（:49） | :19 `.css` と `frontend/src/styles/` を除く | script が 1 条件多い。origin/main に `frontend/src/styles/` は無く結果は同じ（LOW-3） |
| 正本（:50） | :8（docs/adr）、:14-16 | 一致 |
| deploy・docker-compose は語と同じ範囲で見る（:51） | :20 は**全パス** | **不一致**。design-v5.md:73 が自ら認めており「監査の前に classify を §3 に合わせる」と明記。影響は docs だけの #3980（`docs/handoff/dist-deploy-guard/gas-deploy-runbook.md`＋design/recon）・#3992（同＋台帳）の 2 件が A→B-3 に移るだけ。S3 の分母（B-1・B-2）は変わらない（本審査で両 PR の変更ファイルを確認） |
| 新機能＝題名 feat、または design.md の目的（:52） | :33 題名 `^\s*feat(:\|\()` のみ | 「design.md の目的」は機械では判定できない。fix 題名の新機能が B に残る（MEDIUM-1） |
| 新規ファイルが pages/・routers/・models（:53） | :21 | 一致。例: #3804 は `PipelineMapPanel.{css,tsx}` の新規追加で A（_v5-out.txt） |
| B-1/B-2/B-3 の区別（:58-62） | script は B をひとまとめ | 機械では B-1 の「正本の3点」を判定できない（v4 と同じ。試行では Fable 審査が担う） |
| B-3 `frontend/**/*.test.*`・`*.stories.*`（:62） | :24 `frontend/` 配下で `test\|spec\|stories` | script がやや広い（v4 と同じ。実害なし） |
| L（:63） | :30 | 一致 |
| S3 の fix 候補「同じファイルを触り、題名に fix/修正/不具合/EMERGENCY/hotfix/Revert」（:30） | _v5-cand.py:7-13。共有ファイルは `frontend/src/`・`backend/app/` に限定、7 日以内 | script は共有ファイルをコードに限定しており §1 の文面より狭いが、docs/テストだけを共有する組は原因になりえないので妥当 |

### 2-5. 他に確かめた事実
- 7 日窓の網羅: fix 候補の母集団 _w0922.json は 526 件、mergedAt 最大 2026-10-13T22:08:24Z。最後の B（#3996、10-06T23:18:24Z）の 7 日後は 10-13T23:18:24Z で約 70 分の未取得帯がある。`gh pr list --search "merged:2026-10-13T22:00:00Z..2026-10-14T00:00:00Z"` → #4237(feat) #4245(docs) #4247(docs) #4248(docs) #4249(perf)。fix 語を含む題名は無く、取りこぼしなし
- EMERGENCY 題名（9/22〜10/13 merged, base main）: `gh pr list --search "EMERGENCY in:title …"` → #3819 と #3925。#3925 は「emergency fallback」を含むだけで接頭辞ではない。**#3819 の原因 #3818 は v5 では A（題名 feat）**（MEDIUM-3）
- design-v5.md §5 の行番号参照（origin/main e0355ceef6 で `git show` して確認）: CLAUDE.md:53（Draft 規則）・:70-72（標準開発フロー）、STANDARD-WORKFLOW.md:23（PO承認が必須ゲート）・:79（KGI：定量・PO承認済み）・:115-119（不明点プロトコル）、design-partner.md:72（PO承認を得たKGI ÷ 全KGI）・:106（①KGI設定（PO承認ゲート））・:116（PO自筆GO必須）、AGENTS.md:26（通常の新機能・バグ修正経路…GO）・:59（→ PO Approval）、`.github/PULL_REQUEST_TEMPLATE.md` 実在、ADR 最大 ADR-1014 — すべて参照どおり
- ADR-1003:58 は「ADR-1002 の振り返り運用（governance監査）で軽減する」。design-v5.md:106 の記述（参照先の誤り）は v4 と同じ
- B 55 件の内訳（_cache0922.json の変更ファイルで集計）: `backend/app/` を触る 34 件、frontend だけ 17 件、コード無し（docs だけ）4 件（#4006 #3970 #3950 #3825）。題名が fix/docs/EMERGENCY 以外は refactor 2 件（#3901 #3764、いずれも frontend/src/ の配置移動で B-2 相当）

---

## 3. 指摘

### MEDIUM-1: 「fix 題名だが新機能を含む PR」が B の分母と原因に残り、§3:52 の「design.md の目的が『今は無い状態を作る』ものは A」と集団がずれる
- 【事実】原因 3 件のうち #3717 は本文に「`GET /super-admin/suppliers/{id}/source-messages` エンドポイントを追加」「スキーマ…を追加」「ページ送りナビゲーション UI 追加」とあり、原因となった `id: int` はこの追加部分（_fable-v5/pr/p3717.json、f3717.json）。§3:52 の後段を適用すれば試行では A
- 【事実】#3717 を分母と原因から外すと 2/54＝3.7%。design-v5.md:30 は「低い 5.5% のほうを合格ラインにする（厳しい側）」と書いているが、この感度では 3.7% のほうが厳しい側になる
- 【推測】試行中も「fix 題名で機能を足す」PR は出る（§6 の第1リスク）。その場合 Fable 審査が A に押し戻すので、試行の B 集団は baseline より純度が高い。baseline を題名だけで切るなら、その旨と感度（3.7%）を S3 の行に書いて PO が選べるようにする
- 直し方（文書のみ）: design-v5.md:30 に「分母・原因は題名ベースで数えた。fix 題名の新機能（#3717）を除くと 2/54＝3.7%」を1文足し、合格ラインを 5.5% か 3.7% のどちらにするかを PO の y/n にする。再集計は不要

### MEDIUM-2: S3 の分母の定義が §1 と §4 で食い違う（「B（L を除く）」＝55 か「B-1・B-2」＝51 か）
- 【事実】design-v5.md:30・baseline-v5.md:32 は「B（L を除く）55」で割っている。design-v5.md:73 は「S3 の分母（B-1・B-2）は変わらない」と書く。B 55 件にはコードを触らない docs だけの B-3 が 4 件（#4006 #3970 #3950 #3825）含まれ、B-1・B-2 だけなら 51 件 → 3/51＝5.9%
- 影響: 0.4 ポイントの差だが、週次監査（§4:70）で Opus が同じ数え方を再現できないと、PO が○×を一義に判定できない（CLAUDE.md の KGI 粒度の要件）
- 直し方: §1 S3 と §4 を同じ文（例「B のうち L と docs/テストだけの B-3 を除く」または「B（L を除く）」）に揃え、baseline の値をその定義で1つに固定する

### MEDIUM-3: design-v5.md:30「EMERGENCY は…1件（#3819。原因は B の #3818）」は v5 の分類と矛盾し、EMERGENCY 側の基準値が書かれていない
- 【事実】#3818「feat: 抽出タブ個別ジョブテーブル追加」は v5 で A（_v5-rows.json、題名 feat で B→A）。よって「B が原因の EMERGENCY」は 9/22〜10/13 に 0 件
- 影響: S3 の後段「B が原因の EMERGENCY PR が基準値を超えない」の基準値が本文に無く、PO が○×を判定できない。実データでは 0 件なので「試行中に 1 件でも出たら×」が自然だが、それを書いていない
- 直し方: :30 の該当文を「EMERGENCY 1 件（#3819）の原因 #3818 は A 区分。B が原因の EMERGENCY は 0 件。試行中に B 原因の EMERGENCY が 1 件でも出たら×」に置き換える

### LOW-1: S3 は割合だが、14 日の試行では分母が 50 件前後で「原因 2 件なら○・3 件なら×」の境目になる
- 【事実】9/22〜10/6（15 日）で B は 55 件。同じペースなら試行 14 日の B は約 50 件で、原因 2 件＝4.0%（○）、3 件＝6.0%（×）
- 【推測】PO が「画面・出力で○×を一義に判定」するには件数で書いたほうが分かりやすい。合格ラインを「原因 fix が 2 件以下」のように件数で併記すると、分母の揺れ（MEDIUM-2）にも左右されない。設計の方針変更ではなく表現の追加なので LOW

### LOW-2: RLS（テナント分離）を触る fix が B に入る（#3886）
- 【事実】#3886「fix: wrap reaction_writer set_config in a transaction (RLS)」は `backend/app/discord_gateway/reaction_writer.py` を変更し B。§3:49 の語（auth…stripe・token）に RLS/テナント境界は含まれない
- 【推測】マルチテナントの RLS は認証と同程度の守りの対象。語に `rls` を足すか、「RLS は語の対象外（今と同じ守り）」と §6 に明記するかを PO/Opus が決める。baseline では #3886 の後続 fix は無く数字に影響しない

### LOW-3: classify-v5.py:19 に `frontend/src/styles/` 除外が残る、:20 の deploy は全パス
- design-v5.md:49 から `styles/` は消えたが script には残る（空振りなので結果は同じ）。deploy の全パス判定は :73 で宣言済み。監査用 script を §3 に合わせるときに同時に直す

### LOW-4: S1 の「どこの記録を数えるか」が未記載（v4 LOW-3 の残り）
- design-v5.md:28 は数え手（Opus）と保存先（監査ファイル）を書いたが、対象の記録（PR の会話／Discord／別セッションを含むか）が無い。前後を同条件で数えれば比較はできるので LOW

---

## 4. 観点ごとの結論

| 観点 | 結論 |
|---|---|
| 1. v4 指摘の解消 | HIGH-1・MEDIUM-1〜3・LOW-1・LOW-2・LOW-4 直った／LOW-3 一部（記録の場所が未記載） |
| 2. baseline と classify の正しさ | 原因 3/3 が patch・本文と一致（#3736 はコード経路で原因と読め、migration コメントの表現だけが逆向き）。feat 50 件の抜き取り 5/5 が題名 feat・B パス。A→B 4/4 の理由（supersession／token-cost のディレクトリ名）を確認。新 B 10 組の別件 2 組を抜き取り、別件で正しい。classify-v5.py の再実行で 186/55/38/5 を再現。script と §3 の不一致は deploy の範囲（宣言済み）と `styles/` 残置（空振り）のみ。fix 候補の 7 日窓に取りこぼしなし |
| 3. 新しく見つかった欠陥 | MEDIUM-1（fix 題名の新機能 #3717 が分母・原因に残る。感度 3.7%）、MEDIUM-2（分母の定義が §1 と §4 で不一致）、MEDIUM-3（EMERGENCY の原因 #3818 は A で、基準値 0 が未記載）、LOW-1〜4 |
| 4. 試行前に足りないもの | (a) S3 の分母定義を1つに（MEDIUM-2）(b) 合格ラインを 5.5% か 3.7% か PO が選ぶ（MEDIUM-1）(c) EMERGENCY 側の基準値 0 を明記（MEDIUM-3）(d) 監査 script を §3 に合わせる（:73 で宣言済み・LOW-3）。すべて文書の手直しで、再集計は不要（データは _v5-rows.json・_v5-judge.json に揃っている） |
| 5. PO への結論 | 数字の作り方は直り実物と合っている。残りは文面の矛盾 3 点を直せば始められる |

## 5. 【未確認】
- #3736→#3793: 本番で "-" が実際に id 61 に解決された件数（本番ログは見ていない。baseline-v5.md:48 と同じ）。コード経路からは原因と読める
- スマホでのマージ可否（design-v5.md:105）
- S1 の「前」3 営業日の実測値（試行前に取る前提。まだ無い）
- 試行中に B になる PR 件数（LOW-1 の「約 50 件」は 9/22〜10/6 のペースからの推測）
