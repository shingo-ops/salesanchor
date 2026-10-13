# 設計審査（Fable）: design-v2.md「危険でない変更は1件ごとの PO 承認をなくす」

- 審査日: 2026-10-14 / 読み取りのみ（編集・commit・本番接続なし）
- 審査対象: /tmp/CC報告ファイル/devflow-switch/design-v2.md
- 根拠資料: rules-recon.md、gap.md、autonomy-list.md、article.md
- 実物の照合先: 本店 /Users/tanizawashingo/salesanchor の `git show origin/main:<path>`
  - 【事実】審査時点の origin/main は d1dd0ad6（recon の 84eda6a4 より進んでいる）。`git merge-base --is-ancestor` で 84eda6a4 が祖先であることを確認。`git diff --stat 84eda6a4 origin/main -- <照合対象11ファイル>` は空＝引用先ファイルは同一内容。以下の file:line は両コミットで有効。

## 判定: REVISE

方向（A/B を分け、B は PO 承認なしで PR まで進め、GO は ADR-1003 のまま、マージは PO が押す）は既存規則と両立し、CI・フックの変更なしで成立する【事実・§C】。ただし、(1) M 区分が PO の「y」の範囲を超えている、(2) B の判定基準が文言・見た目・テスト・文書の変更に対して自己矛盾し抜け道にもなる、(3) 成功条件 S2・S3 の測定機構と基準値が存在しない、の3点は試行前に直さないと「確実に成功するエビデンス」を出せない。

---

## A. 指摘

### HIGH-1: M 区分は PO の「y」の範囲外。ADR-1003 は GO（マージ前承認）だけを委譲しており、KGI・設計の PO 承認は委譲していない
- 【事実】PO の決定原文（design-v2.md:4）は「危険でない変更は1件ごとのPO承認をなくしPRまで任せる」。gap.md「寄せ方の案」も「危険な変更の GO（データ削除・migration・deploy・secrets・お金）は残す」としている。
- 【事実】design-v2.md:35-37 の M 区分は「migration（DROP なし）・deploy.yml・scripts/・auth/・payment」を「PO 承認なしで進む」としている。ここでの「PO 承認」は §2 の表（design-v2.md:17-18）どおり KGI 承認と設計承認のこと。
- 【事実】ADR-1003 が委譲したのは「GO（危険変更・ユーザー影響変更・外部API変更のマージ前承認）の発行権限」のみ（docs/adr/ADR-1003-go-delegation-to-opus.md:14）。KGI 承認・設計承認・仕様書作成の PO 関与には触れていない。
- 【事実】docs/STANDARD-WORKFLOW.md:36 は「危ない変更（`migrations/`・`deploy.yml`・本番 `scripts/`）を含む開発」を仕様書必須（Planner＋PO、:24）としている。design-v2.md:27 の「v1 はこれを PO 判断に戻す形になっていた」という読みは、GO と KGI/設計承認を混同している。v1（autonomy-list.md A-1, A-2）は KGI/設計承認の話で、ADR-1003（GO）と衝突していない。
- 影響: PO は「画面・文言・不具合修正」に y と言ったのに、migration・deploy.yml・scripts・auth・payment の設計承認までなくなる。PO が気づかないまま範囲が広がる。
- 直し方: M 区分を廃止し、migration（DROP なし）・deploy.yml・scripts/・auth/・payment を A 区分（KGI・設計は PO 承認、GO は ADR-1003 のまま Opus）に戻す。もし M を残すなら、設計の冒頭に「PO の y の範囲外の追加提案」と明記し、PO に独立した y/n を1問で取る（y/n なしで試行に含めない）。

### HIGH-2: B の判定基準「根拠仕様の file:line が書けなければ A-2」が、B の2・3項目（文言・見た目、テスト追加、文書更新）と自己矛盾し、同時に抜け道にもなる
- 【事実】design-v2.md:44「判定の基準は『書かれた状態に戻すか（B）／書かれていない状態を作るか（A-2）』。根拠になる仕様の file:line を design.md に必ず書く。書けなければ A-2 として止まる」。
- 【事実】design-v2.md:41-42 の「画面の文言・見た目の修正」「テスト追加、A に当たらない文書更新」には、通常「書かれた状態」の仕様 file:line が存在しない（文言の誤字修正・余白調整・テスト追加に対応する ideal-state の行はない）。この規則をそのまま適用すると B の2・3項目はすべて A-2 で止まり、S1 の目的（PO への問いかけ1回）が成立しない。逆に「文言・見た目は file:line 不要」と運用すれば、新機能を「見た目の修正」と言い換える経路が残る（design-v2.md:63 のリスクの対処が機能しない）。
- 【事実】「既存の仕様書・ideal-state・ADR に書かれた状態」（design-v2.md:40）の「ADR」は docs/adr/ に ADR-1014 まで存在し（`git ls-tree origin/main docs/adr/`）、どれか1本を引けば形式上は根拠になる。Fable 審査（同じ AI 系統）だけがそれを見る。
- 直し方（判定を機械的にするための最小修正）:
  1. B-1（不具合修正）: 根拠の正本を `docs/specs/*/ideal-state.md`・`kgi.md`・ADR の「Decision/What」節に限定し、「期待値（正本の引用）／実際の挙動（再現手順か画面・ログ）」の2点を design.md に必須とする。どちらか欠ければ A-2。
  2. B-2（文言・見た目）: 「変更ファイルが `frontend/src/` 配下のみ、かつ API・DB・ルーティング（routers/、migrations/、routes 定義）に触れない、かつ i18n／UI governance／design-token の必須チェックが緑」をパス条件で定義し、file:line 不要と明記する。新画面・新ルート追加は A-2。
  3. B-3（テスト・文書）: 「変更ファイルが `backend/tests/`・`frontend/**/*.test.*`・docs/（正本 docs/STANDARD-WORKFLOW.md・CLAUDE.md・AGENTS.md・docs/ai-agents/・docs/adr/ を除く）のみ」をパス条件で定義。
  これで判定の大半が「変更ファイルの一覧」で決まり、AI の自己申告への依存が B-1 だけに絞れる。

### HIGH-3: S2・S3 の測定機構が存在せず、基準値も無いため「悪化したか」を判定できない
- 【事実】design-v2.md:10「週1回、マージ済み PR の変更ファイルと A 一覧を突き合わせる（governance 監査）」。リポジトリ内に「governance 監査」を実行する workflow・script は無い（`git ls-tree -r origin/main .github/workflows scripts` の全ファイルを grep: 当たりは ui-governance-gate.yml・check-ui-governance.js・claude-dispatch.sh・test-ui-governance.js のみで、いずれも UI 金型検査）。文書上の「governance 監査」は人手の約束に留まる（docs/ai-agents/design-partner.md:216「歯止めは人手と governance 監査で担保する」）。
- 【事実】ADR-1003:58 は「ADR-1002 の振り返り運用（governance監査）」を根拠にしているが、ADR-1002 は「商品IDをINTEGER一本化し、旧テーブル参照migrationを修復する」（docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md:1）で、監査の運用を定めた ADR ではない。既存の歯止めの根拠が宙に浮いている。
- 【事実】design-v2.md:11 の S3「B 区分の変更が原因の障害 0 件」には、試行前の基準値（直近2週間の障害件数・原因 PR 区分）が無い。試行で悪化したかは基準値との差でしか言えない（~/.claude/CLAUDE.md「測る前に基準値を取る」）。
- 直し方:
  1. S2 の監査を具体化する: 実行者（agent-console の定期実行か PO の `!` 実行か）、コマンド（例: `gh pr list --state merged --base main --search "merged:>=<日付>" --json number,files` を A のパス一覧と突合）、保存先（`docs/handoff/<仕事名>/audit-YYYY-MM-DD.md`）、PO への提示形式（件数のみの3行）を設計に書く。試行開始前に1回「空振り実行」して動くことを確かめる。
  2. 基準値を取る: 試行開始前に、直近2週間（または直近 N 件）の main マージ済み PR について「PO への y/n 質問回数」「障害件数と原因 PR」「A パス接触件数」を同じ手順で数え、成績表の「前」列に置く。
  3. S3 の「障害」の定義を書く（例: Discord 不具合報告チャンネルへの投稿、本番 5xx、PO の目視報告のいずれか）。定義なしでは 0 件かどうかを PO が○×判定できない。

### MEDIUM-1: 直す文書の一覧（design-v2.md §5）に漏れがある
- 【事実】CLAUDE.md:53「リリース相当の大きな変更は `--draft` で起票（必ず Draft）→ PO が GO を出すまで誰も un-draft/マージしない」。design-v2.md:76 は「B 区分は Draft にしない、と新 ADR に書く」としているが、§5（design-v2.md:51-58）に CLAUDE.md:53 が無い。新 ADR だけに書くと CLAUDE.md:53 と文面上衝突したまま残る。rules-recon.md 矛盾表も「要改定 CLAUDE.md:53」としている。
- 【事実】docs/ai-agents/design-partner.md:116「危険操作（正本・関所・migrations・deploy.yml・本番scripts）はPO自筆GO必須。設計パートナー/実装役は代筆しない」は ADR-1003:14-16 および同文書 :215「実装役が転記してよい」と食い違う。rules-recon.md 矛盾表は「:116 を ADR-1003 に合わせる」としているが、design-v2.md §5 は :72,:106 のみ。
- 【事実】docs/STANDARD-WORKFLOW.md:75「区分の判定に迷う場合は不明点プロトコル（§3）に従いPOに確認する」と :118「POに相談」は、design-v2.md:47「A に当たったら止まり PO に y/n を1問」と方向は同じだが、B の中で生じた不明点（例: 仕様の行が見つからない）をどう扱うかの接続が無い。新 ADR から §3 を参照する一文を §5 の STANDARD-WORKFLOW.md 行に足す。
- 【事実】docs/adr/ADR-1012-ai-ops-247.md:5-6 は Proposed で「段階ごとに実装カードと PO の実装承認を取る」。rules-recon.md 矛盾表は「矛盾（Proposed のうちに調整）」。design-v2.md に扱いが無い。「ADR-1012 は migration を含むため A 区分。変更しない」と1行書けば足りる。
- 【事実】AGENTS.md:59 に `→ PO Approval` の行がある。design-v2.md:58「同上（Codex 側）」だけでは、どの行を直すか Generator が判断できない。AGENTS.md:26 と :59 を列挙する。
- 直し方: §5 に上記5行を追加し、各行に「変更前の文→変更後の文」を書く（CLAUDE.md:80「Planner が file:line＋変更前後コード＋触らない範囲まで設計」）。

### MEDIUM-2: CLAUDE.md は上限 120 行ちょうどで、1行追加すると必須チェックが赤になる
- 【事実】`git show origin/main:CLAUDE.md | wc -l` = 120。frontend/scripts/check-claude-size.js:23 `{ path: 'CLAUDE.md', limit: 120 }`。「CLAUDE.md line count check」は main の必須チェック15件に含まれる（rules-recon.md §2-A）。
- 【事実】design-v2.md:56「要約1行（90行の上限内か確認）」は上限の数値が実体（120）と異なり、「追加」前提になっている。
- 直し方: CLAUDE.md:70-72 の既存文を置き換える形（行数増なし）で設計し、置換前後の文を §5 に書く。

### MEDIUM-3: S1 の測り方が AI の自己申告で、ADR-1003 条件3（PO への3行報告）との関係が未定義
- 【事実】design-v2.md:9「PO への y/n 質問の回数を PR 本文に記録 → 0回」。記録者は AI 自身。PO が独立に確かめる手段が書かれていない。
- 【事実】ADR-1003:29「PO に3行まとめ（対象・変更内容・バックアップ確認）を報告済み」は Opus GO の必須条件。B 区分 PR（frontend/src 等）は USER_IMPACT で GO 記録が必須（scripts/check-process-artifacts.js:136-143, :937-947）なので、B 区分でも PR ごとに PO へチャットが1通届く。これを「問いかけ」に数えるかが S1 に書かれていない。数えれば S1 は構造的に達成不能、数えなければ PO は「毎回チャットが来る」と感じる。
- 直し方: S1 を「PO が答える必要がある y/n は『マージしてよいか』だけ。ADR-1003 の3行報告は『読むだけ・返答不要』と PR 本文と報告文の冒頭に明記」と定義し、測定は PO 側で「返答した回数」を数える（PO が○×判定できる形）。

### MEDIUM-4: B 区分の PR の進み方（CI が一時的に赤になる順序）が書かれていない
- 【事実】GO 原文は `GO #<PR番号>` で現在の PR 番号と一致必須（check-process-artifacts.js:373-379）。PR 作成前には書けない。したがって B 区分の流れは「PR 作成（gate 赤）→ Reviewer APPROVE → Opus が GO 記録を `gh pr edit --body` で転記 → gate 緑 → PO がマージ」になる。
- 【事実】これは今の流れと同じ（rules-recon.md §2-C-2）だが、design-v2.md:19「実装〜PR 同じ（変えない）」としか無く、PO が「赤い PR が来た」と見て止まる余地がある。
- 直し方: §2 の表に「PR 作成直後は process-artifacts gate が赤。GO 記録転記後に緑になる。PO は緑になってからマージ」を1行足す。

### LOW-1: 「自律停止」の言葉は既存の「委譲停止」（ADR-1003:49）「許可保守停止」（ADR-1011:43）と重複しない
- 【事実】3語とも別。問題なし。ただし新 ADR に「自律停止は ADR-1003・ADR-1011 の状態を変えない」と1行書くと誤解がなくなる。

### LOW-2: 試行終了の仕組みが受動的
- 【事実】design-v2.md:12 S4 は「成績表の有無」。誰が・いつ・どこに書くかが無い。「試行開始日＋14日に agent-console の定期実行で成績表を生成し、PO に3行で提示」と書けば S4 が○×で判定できる。

### LOW-3: ADR-135 本文は develop 前提の記述のまま
- 【事実】docs/adr/ADR-135-release-stowaway-prevention.md:23「develop にマージされたものは…」。CLAUDE.md:56 では main に置き換わっている。本設計の対象外だが、新 ADR で ADR-135 を引く際は CLAUDE.md:56 の文面を引用する。

---

## B. 審査観点ごとの結論

| 観点 | 結論 |
|---|---|
| 1. 既存規則・ADR-1003 との矛盾 | GO 段を変えない点は ADR-1003 と両立【事実】。ただし M 区分は ADR-1003 の委譲範囲（GO）を KGI/設計承認に拡大解釈しており、PO の y の範囲外（HIGH-1）。直す文書の一覧に5件の漏れ（MEDIUM-1） |
| 2. A/M/B の機械的判定 | B-1 は「正本の期待値＋実際の挙動」の2点、B-2/B-3 はパス条件に落とせば判定できる。現行の文面は自己矛盾かつ抜け道あり（HIGH-2）。M と B の違いが security-reviewer の有無だけで、区分として独立していない（HIGH-1 の修正で解消） |
| 3. S1〜S4 の○×判定可能性 | S1 は定義修正が要る（MEDIUM-3）。S2・S3 は機構と基準値が無く判定不能（HIGH-3）。S4 は担当と期日を書けば判定可能（LOW-2） |
| 4. 「文書を直すだけで済む」の真偽 | 【事実】真。scripts/check-process-artifacts.js に KGI 承認・設計承認を見る処理は無い（grep `kgi|PO承認|approv` → :106 の kgi.md 正本パターンのみ）。.github/PULL_REQUEST_TEMPLATE.md:21 の「PO の GO を確認済み」は危険パスのみ。scripts/dev/validate-pr-body.sh:31-75 はセクション・対象ADR・recon・設計の存在のみ。~/.claude/scripts/pr-body-guard.sh は同じ検査。~/.claude/scripts/agent-danger-hook.sh に `gh pr create` を止める語は無い（grep `gh pr` は :68 のコメントのみ）。~/.claude/scripts/gh-scope-guard.sh:2 は `exit 0`（無効）。soft_deny は `gh pr merge *` と `docker compose restart *` の2件で、PO がマージする設計と両立。ただし gate が PR 作成直後に赤になる順序の明記は要る（MEDIUM-4） |
| 5. リスクの見落とし | 監視が無い A 項目（新機能・ADR 新設・Legacy 削除・大量 DELETE）は設計も認めている（design-v2.md:48）。問題は「無い」ことではなく、代替の S2 監査が実在しないこと（HIGH-3）。悪化検知は基準値が無いため不可（HIGH-3） |
| 6. 「確実に成功する」の根拠不足 | 試行前に取れる事実で補える: (a) 直近 N 件の main マージ済み PR を A/B で仮分類し、B と判定された PR の中に A 要素が混ざった件数（判定基準の精度の事前測定）、(b) 直近2週間の PO への y/n 回数・障害件数（基準値）、(c) S2 監査コマンドの空振り実行結果。これら3つが揃えば「成功の根拠」を PO に事実で示せる |

---

## C. 検証した file:line の照合結果（origin/main、84eda6a4 と d1dd0ad6 で同一内容）

| rules-recon.md / design-v2.md の引用 | 照合結果 |
|---|---|
| docs/STANDARD-WORKFLOW.md:4,:23,:24,:79,:92,:115,:118-119,:127,:134-135,:142,:165,:166 | 一致（:23「PO承認が必須ゲート」、:79「KGI：定量・PO承認済み」、:92 ユーザー影響変更の GO、:127 ADR-012/113 上書き、:134 自律クラフト、:165-166 変更は PR＋PO承認・ゲート弱体化は PO 確認） |
| docs/STANDARD-WORKFLOW.md:36-37（本審査で追加） | :36 危ない変更は仕様書必須、:37 バグ修正・リファクタは対象外 |
| CLAUDE.md:51,:53,:56,:57,:70-72,:80 | 一致（:53 Draft 規則、:56 ADR-135、:57 ADR-136＋ADR-1003 委譲、:70-72 3フェーズ①KGI PO承認）。行数 120 |
| AGENTS.md:26,:59,:146-150,:188 | 一致（:26 GO は Opus 委譲、:59 `→ PO Approval`、:146 不可逆操作、:188 PO GO なしの危険変更） |
| docs/ai-agents/design-partner.md:72,:106,:108,:115-116,:157,:195,:215,:216,:308,:355,:421-424 | 一致（:72 KGI PO承認、:106 ①KGI設定（PO承認ゲート）、:116 PO自筆GO・代筆しない、:215 実装役が転記してよい、:421-424 PO 相談3場合） |
| docs/adr/ADR-1003-go-delegation-to-opus.md:14,:16-17,:25-29,:31-41,:43,:45,:47-49,:53,:58 | 一致（:14 委譲対象は GO、:25-29 条件3つ、:35-41 例外7件、:45 機械検証不能5件、:49 委譲停止、:58 ADR-1002 参照＝誤参照） |
| docs/adr/ADR-135-release-stowaway-prevention.md:23-60 | 一致（:39-44 B-2 scripts/ 全体を DANGEROUS に、:50 gate を必須チェックに）。本文は develop 表記 |
| docs/adr/ADR-136-cc-bot-github-identity.md:20,:49-69 | 一致（:20 AUTHORIZED_AUTHORS、:59-69 承認フロー v2） |
| docs/adr/ADR-1011-permission-self-maintenance.md:5-6,:15-19,:29-37,:39,:43 | 一致（:15 SM- の allow のみ、:33 soft_deny/hooks は範囲外、:43 許可保守停止） |
| scripts/check-process-artifacts.js:38,:43-45,:49-51,:69,:77,:80,:92-101,:104-109,:115-124,:126-134,:136-143,:346-387,:373-379,:645-695,:765-770,:801,:805-810,:937-947,:953-964,:967,:972 | 一致（:43-45 GO 発行者 allowlist、:49-51 PO 専用例外、:77 DROP 判定、:115-124 DANGEROUS_PATTERNS 8件、:136-143 USER_IMPACT 6件、:765-767 書類のみ自動スキップ、:967 免除は非ユーザー影響のみ） |
| scripts/check-process-artifacts.js:472-521 validateDesignDoc（本審査で追加） | 受け入れ基準表・recon 相互参照・ADR 参照・外部事例欄のみ検査。KGI 承認の検査なし |
| frontend/scripts/check-claude-size.js:23（本審査で追加） | CLAUDE.md の上限 120 |
| .github/PULL_REQUEST_TEMPLATE.md:21,:28-33,:37（本審査で追加） | PO GO チェックは危険パスのみ。免除欄・recon・対象ADR・触るファイル欄あり |
| scripts/dev/validate-pr-body.sh:31-75（本審査で追加） | セクション・対象ADR・recon 実在・設計 実在のみ |
| ~/.claude/scripts/gh-scope-guard.sh:2 | `exit 0`（recon の【未確認】4 を解消: 無効化中は事実） |
| ~/.claude/settings.json autoMode.soft_deny | `Bash(gh pr merge *)`・`Bash(docker compose restart *)` の2件（$defaults を除く）。hard_deny なし |

## D. 【未確認】（本審査でも確認していない）
- GitHub Mobile／スマホブラウザでのマージ可否（recon と同じ。設計 §9 のとおり試行初日に PO が実機で1回試す）
- Opus の `gh pr merge` 拒否の再測定（10/13 の記録のみ）
- docs/specs/design-partner-loop/README.md「KGI-3 段階別チェックリスト」の中身（STANDARD-WORKFLOW.md:75 が参照。B 区分の必要物の物差しとして使えるかは未読）
