# 実装カード T: 区分ごとに取れる単位の表（ADR-1041 便1）

設計者: Opus（2026-10-23）。PO の実装承認: 2026-10-23 チャット「1」（単位の表から作り始める）。
設計: docs/handoff/v102-heading-and-unit/design.md（origin/main 5efd3afb6 以降）の「T」「便1（T）」「受入条件 K1〜K3・K8・K10」。recon: 同じフォルダの recon.md。ADR-1041 What 1〜3。
社外秘: 仕入元名・人名・投稿の原文は、コード・テスト・コミット・PR に書かない。原文つきの出力は社外秘フォルダ ~/CC報告ファイル-keep/shime-auto-check/heading-fix/bin1-T/ にだけ置く。

読んだ節（docs/handoff/design-partner-card-ops/guards/ の 00-common・02-db・04-worktree・05-pr・10-executor）と照合: 全コマンドを cd フルパス && で始める／1手順1コマンド／出力に上限を付け、出力は列挙対象の外に置く／本番 DB は reader 鍵の逐語のコマンドだけ（ヒアドキュメントを psql に渡さない）／worktree は前の便で作成済み（このカードでは作らない）／commit・push・PR は段ごとに git log と .pr-number で実在を確かめる／gh run watch を使わない（gh pr checks）。

受領確認: 着手の前に「カード T を受領しました。worktree は /Users/tanizawashingo/worktrees/salesanchor/release-v102-kubun-allowed-units です」と 1 行だけ書く。

本カードは新規である。過去の報告の再送を禁止する。表・要約・チェックマークだけの報告を禁止する。

## 0. 着手前の確認（読み取り。ずれたら NEEDS_DECISION）
0-1. design.md「便1（T）」に書いた file:line（gemini_raw_copy_v102_product_first.py の :126-148・:361-384・:683-715・:718-762・:750-753・:760、tcg_analyzer_svc.py:817-842、gemini_raw_copy_v101.py:935、line_analysis_v102_svc.py:567-568・:757-780・:967・:979・:1028-1043、v102_buyback_unit_svc.py:56）を、今の origin/main で確かめる。ずれていれば新しい行番号を報告に書く（中身が違えば止まる）。
0-2. 本番の表の名前: reader 鍵（ADR-1024。コマンドは逐語で次の形。SQL は 1 文ずつ標準入力で渡す: printf '%s\n' "SELECT canonical, kubun, is_active FROM ai_ro.line_units ORDER BY id" | ssh -F /dev/null -i ~/.ssh/salesanchor-reader -o IdentitiesOnly=yes -o BatchMode=yes ubuntu@49.212.137.46 。~/.ssh/manual-only は使わない。ビューの名前が違えば前例 ~/CC報告ファイル-keep/shime-auto-check/heading-fix/formal-recon2/ と同じ形で読む）で public.line_units（canonical・is_active）と public.tcg_product_categories（kubun_type・is_active）を読み、Box・Case・Pack・MasterCarton・Booklet と 箱系・プロモパック系・ブックレット系 がすべて有効であること。public.tcg_distribution_settings に key v102_kubun_allowed_units がまだ無いこと。
0-3. ログの置き場（K8 用）: monitoring/promtail/promtail.yml で、コンテナのログに付く label 名と、celery-worker のコンテナが入るかを確かめる。本番のコンテナ名は astro-webapp-celery-worker-1 の形。Loki で引くときの式（例 {container_name=~".*celery-worker.*"}）を報告に書く。入っていなければ「入っていない」と書く（止まらない）。

## 1. 変更（v102 の経路だけ）
1-1. ProductFirstMasters の末尾に kubun_allowed_units: Mapping[str, frozenset[str]] = field(default_factory=dict) を足す。空なら T は働かない。
1-2. 表の読み込みと検査の関数を別に作る（テストから直接呼べる形）。load_product_first_masters で設定 key v102_kubun_allowed_units を読み、次のどれかなら logger.warning を出して空の表にする: key が無い／JSON として読めない／「区分名 → 文字列の配列」の形でない／区分名が tcg_product_categories.kubun_type（有効）に無い／単位の名前が line_units.canonical（有効）に無い。区分名・単位名をコードに書かない。
1-3. 新しい関数 _fix_unit_by_kubun を、resolve_product_first の _resolve_unit_from_state の後（:750-753 の直後）で 1 回だけ呼ぶ。
  - 商品の区分が表に無い／単位が無い（空を含む）／単位が表にある → 何もしない。
  - 表に無い単位で、状態の単位（masters.condition_unit[状態]）が表にある → (a) その単位に置き換え、resolve_unit_v2(状態の単位, unit_alias_to_info) で unit_kubun も揃える。unit_basis に kubun_unit_fix: "a" と kubun_unit_from（値は置き換える前の単位の名前） を残す。
  - そうでなければ (b) 単位はそのまま、理由 {"kind": "unit_unknown"} を返す。unit_basis に kubun_unit_fix: "b"。
  - (a)・(b) のたびに、モジュールの logger で INFO を 1 行: 印 kubun_unit_fix・a/b・区分・元の単位・後の単位・商品 id。原文は出さない。
  - 戻り値の理由の配列は :760 の review_extra の末尾に足す。状態・商品は変えない。
1-4. 未登録の単位語（区分「不明」になる語）が (a) で置き換わる場合も、上の規則どおりに動くことをテストで示す（審査 4 回目の任意）。
1-5. 設定の記録 SQL（ADR-1007。既存の data/ の設定 SQL と同じ型・同じ置き場）: key v102_kubun_allowed_units を 1 行 INSERT。値は次の JSON と一字一句同じ:
  {"箱系": ["Box", "Case", "Pack", "MasterCarton"], "プロモパック系": ["Booklet", "Pack"], "ブックレット系": ["Booklet"]}
  precheck（key が無い）／dryrun／commit／verify（値が上と一致）／rollback（行を消す）を用意する。本番には流さない。
触らない: _resolve_unit_from_state、resolve_condition_v2、v102_buyback_unit_svc.py、_UPSERT_SQL、要確認の理由の一覧・画面の文字（unit_unknown は既にある）、指示書、migrations、deploy.yml。

## 2. テスト（backend/tests/test_gemini_raw_copy_v102_product_first.py に足す。合成のデータで）
- 箱系 × Set、状態 Sealed box → Box（a）。
- 箱系 × MasterCarton → 変わらない。
- プロモパック系 × Case、状態の単位 Pack → Pack（a）。
- 箱系 × Booklet、状態の単位も表に無い → 単位そのまま・unit_unknown が足される（b）。
- 表に無い区分（セット系 × Set）→ 変わらない。単位が空 → 変わらない。
- 表が空 → 今と同じ結果（上の全組）。
- (a)・(b) でログが 1 行ずつ出て、原文を含まない（caplog）。
- 検査: key 無し・JSON 不正・形が違う・知らない区分名・知らない単位名 → 表が空・warning が出る。
- 未登録の単位語の件（1-4）。

## 3. 置き換え試験（マージ前の証拠。本番は reader 鍵で読むだけ。出力は社外秘フォルダ bin1-T/）
道具の前例: ~/CC報告ファイル-keep/shime-auto-check/heading-fix/kubun-unit-sim/（judge5.py＝見本 100 投稿の採点、fetch_all2.py・combo.py＝直近 30 日の再計算、patch_T.diff＝試算の差分）。新しい道具は bin1-T/ に置き、前例のファイルは書き換えない。
3-1. K1: 見本 100 投稿を、このブランチのコードと本番と同じ表（1-5 の JSON）で採点。商品 97.8%・状態 93.0% から下がらず、単位 95.3% 以上なら合格。
3-2. K2: 直近 30 日の v102 の現行全件（本番の行数を数え、試算の 4873 行との差と理由を書く）について、変更前と変更後で次を通す。
  - resolve_product_first（変更後は表あり）
  - 保存処理の中で後から単位を変える処理: 値段で単位を決める処理（line_analysis_v102_svc.py:967・:979 が呼ぶ is_candidate・apply_buyback_units と、その物差しの読み込み）と、まとめ売りの処理（:1028-1043）。DB に書かずに、保存の直前の値を作る。
  - 3 商品（466089／466090／466091）の区分を箱系（id 1）にした形（M）も、別に 1 回通す（DB は変えず、読み込んだ商品の区分を手元で差し替える）。
  - 変わる行を全件、TSV で出す（行の id・投稿 id・商品 id・商品名・区分・単位の前後・状態の前後・理由の前後・どの処理で単位が決まったか（表 a／表 b／値段／まとめ売り）・選択行と前後の原文）。表に無い区分の行・単位以外の値（商品・状態）が変わったら、その行も全部出す。
  - 保存処理の中の 2 つが DB への書き込みと切り離せず、手元で通せないときは止まる。
3-3. K3: 3-2 の前後で、要確認の行数（tab_true の数え方。前例の道具と同じ）を出す。
3-4. 合格かどうかの判定はしない（判定は Opus）。数と TSV のパスを報告する。

## 4. 手順（worktree は作成済み: /Users/tanizawashingo/worktrees/salesanchor/release-v102-kubun-allowed-units）
1. cd /Users/tanizawashingo/worktrees/salesanchor/release-v102-kubun-allowed-units && ./scripts/dev/executor-preflight.sh （止まったら止まる）。
2. 0 → 1 → 2 → ruff・pytest（足したテストと backend/tests/test_gemini_raw_copy_v102_product_first.py 全体、v102 関係のテスト）→ 3。Bash は毎回 cd /Users/tanizawashingo/worktrees/salesanchor/release-v102-kubun-allowed-units && の形で始める。
3. このカードを docs/handoff/v102-heading-and-unit/card-T.md として worktree に置く（写しは /private/tmp/claude-501/-Users-tanizawashingo-salesanchor/e9342e9a-8ab4-4130-8abd-daac8688e12b/scratchpad/card-T.md を cp する）。
4. .claude-pipeline/active-work.d/release-v102-kubun-allowed-units.md の担当機能エリア欄に「ADR-1041 便1 区分ごとの単位の表」と書く。
5. git commit（feat:、末尾 Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>）→ git log -1 --stat で commit の実在を確かめる。
6. git push -u origin HEAD → git status -sb で上流が origin/release/v102-kubun-allowed-units であることを確かめる。
7. gh auth status が shingo-cc であることを確かめ、bash scripts/gh-pr-create-safe.sh --draft --title ... --body-file （本文ファイルのフルパス）で Draft PR を作る → cat .pr-number と gh pr list --head release/v102-kubun-allowed-units --json number で番号の一致を確かめる。PR 本文に社外秘を書かない。書式で関所が赤なら自己修正してよい。
8. マージ・本番の設定 SQL の実行はしない。

## 停止条件
- 0 で前提が違う／v102 以外の経路を変えないとできない／3-2 の 2 つの処理を手元で通せない／テストが通らない → NEEDS_DECISION（理由と生出力のパス）。
- フックに止められたら言い換えず止まる。本番への書き込みはしない（reader 鍵の読み取りだけ）。
- 報告: 生出力はファイルに保存し、チャットにはパスと数だけ。最終行は DONE、または BLOCKED: と NEEDS_DECISION: のどちらかに理由を続けた 1 行。

END OF CARD
