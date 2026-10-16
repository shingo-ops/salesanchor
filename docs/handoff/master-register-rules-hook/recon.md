# recon: 共用商品の新規登録ルールを読ませるフック

> この文書は何か: design.md §2 の事実を、生出力ファイルの名前と行番号つきで書き写したもの。新しい推測は足していない。
> 生出力の置き場: /tmp/CC報告ファイル/master-required-fields/hook/（以下 q*.txt、wt.txt）
> 実測時の origin/main: b31b40593cf621941b53a4f05e71344e70fd791f（2026-10-16）
> 設計: docs/handoff/master-register-rules-hook/design.md

## 1. 登録の値の決め方を1か所にまとめた文書は無かった
- 【事実】ADR-1020 案に登録項目の規則がある。/tmp/CC報告ファイル/master-required-fields/hook/q1_adr1020.txt の行 6・16〜24・25・39・41〜42
  - 例: 同 :41「型番: 公式に出ているものだけを採用する」、:42「英語名: 公式の英語名が無ければ…」
- 【事実】規則の語を含む handoff 文書の一覧と件数: q1_kw_counts.txt（40行。先頭 docs/handoff/viewer-keyword-kana-search/design.md が20件）、q1_rule_kw.txt（35行）
- 【事実】specs 配下の該当: q1_specs_hits.txt（4行）、q1_adr155_specs.txt（11行）
- 【事実】集約文書は docs/specs/product-master/registration-rules.md（本 PR で新設）

## 2. AI の本番登録は create_product を呼ぶ使い捨て台本
- 【事実】台本の例 /tmp/CC報告ファイル/inventory-6checks/box-priority/unreg/reg4/create.py:217 に `res = await create_product(`（q2_scripts_files.txt:22 に一覧あり）
- 【事実】呼び先は backend/app/services/tcg_product_master_svc.py:331 `async def create_product(`（実測 grep）
- 【事実】台本の注記 create.py:7 「直接 INSERT はしない」、:10 「create_product は nextval で PM 番号を消費する」（grep -n 出力）
- 【事実】画面の新規作成・解析レビュー・CSV もすべて create_product 経由: docs/handoff/master-register-required-fields/recon.md:29〜31（q2_git.txt:16〜18 に同行の写し）
- 【事実】リポジトリ内の git grep 結果: q2_git.txt（107行）

## 3. 「文書を読ませる」「読んでいないと止める」既存フックは無い
- 【事実】q3_grep_gates.txt（4行）: 該当は .claude/hooks/require-status-label.sh:67,83 と check-freshness.sh:3,25 のみ。登録ルールを読ませるものは無い
- 【事実】~/.claude/settings.json の既存フック全一覧: q3_user_hooks_full.txt（37行）。UserPromptSubmit は :4 card-lint-hook.sh と :5 activity-hook.mjs。PreToolUse の Write は :26 worktree-only-guard.sh と :27 worktree-access-guard.sh
- 【事実】リポジトリ側の設定: q3_repo_settings.txt（74行）、台本の頭: q3_script_heads.txt（65行）、~/.claude/scripts の一覧: q3_scripts_ls.txt（37行）

## 4. 公式のフック仕様（https://code.claude.com/docs/en/hooks 、2026-10-16 取得。生出力ファイルは無く、design.md §2 の記述を写す）
- 【事実】PreToolUse は deny と permissionDecisionReason を返せる（deny の理由は Claude に表示される）
- 【事実】UserPromptSubmit は additionalContext を足せる。上限 10,000 文字
- 【事実】設定ファイルのフックはサブエージェントのツール呼び出しにも発火する
- 【事実】Write の tool_input に content、Edit に new_string が入る
- 【未確認】サブエージェント内の PreToolUse で transcript_path がどちらの記録を指すか

## 5. 本店が古い
- 【事実】本店 /Users/tanizawashingo/salesanchor は origin/main より 2766 コミット遅れ（wt.txt:33 `[G2.2 WARN] …2766 コミット遅れています`）
- 【事実】親テーマのブランチ release/master-register-required-fields の差分: q0_ahead.txt（2行: 2e472e467、7d1d84788）
