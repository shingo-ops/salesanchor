# CARD-LINE-GUIDE-01

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
Astraが設計/自己審査、Solが忠実実装/試験を担当する。本セッションPOの明示委任に基づく。
受領確認: 実装役は冒頭で本カード名を示す。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、01-read.md、03-file.md、04-worktree.md、11-lint.md。
設計パートナー§5.5事前照合: 1記号○、2ready PR指定○（本便PRなし）、3報告宛先○、4一目的○、5起点○、6書式○、7出力を含む基準○。
人手L32: 未確定placeholderなし。実装の詳細契約はdesign追補に確定済み。

## 目的と権限

システム欄に7段階のLINE業務ガイドを追加する。実装・ローカル試験までのカード。
設計: docs/handoff/pipeline-procedure-map/design.md の2026-09-28追補。recon: 同ディレクトリrecon.md。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide
ブランチ: release/line-workflow-guide、起点: origin/main ae783c7f583e2d5628c19d999ed7ce6c7944e9b8。
共有作業なので他者の変更を上書き/巻き戻さない。作成済みのAstra文書変更は保持する。
コード生成はPOが指名したSolが担当する。設計の再解釈やスコープ追加は禁止。

## 触るファイル

frontend/src/pages/super-admin/components/LineWorkflowGuidePanel.tsx
frontend/src/pages/super-admin/components/LineWorkflowGuidePanel.css
frontend/src/pages/super-admin/components/LineWorkflowGuidePanel.test.tsx
frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx
frontend/src/pages/super-admin/AnalysisRulesPage.tsx
frontend/src/locales/ja.json
frontend/src/locales/en.json
frontend/tests-e2e/analysis-rules-line-guide.spec.ts
.claude-pipeline/active-work.d/release-line-workflow-guide.md
tasks/todo.md
docs/ai-agents/evidence-registry.md
設計/reconの実在パス誤記のみ修正可（意味変更はAstraへ戻す）。文書は同テーマ内で集約する。
本便で削除するファイルはない。既存コードの削除行は後続PR本文に正しく列挙する。
API/DB/backend/マイグレーション/CI/secrets/共通金型/tokens/既存map/無関係な画面は変更禁止。
commit/push/PR/merge/deployは本便では行わない。ガードの解除、trustの代行は禁止。

手順0 preflight・担当確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && ./scripts/dev/executor-preflight.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && git status --short --untracked-files=all
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && git diff --name-status origin/main

手順1 契約読取とカード検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && cat docs/ai-agents/executor-preamble.md frontend/AGENTS.md frontend/CLAUDE.md docs/CC_UI_GOVERNANCE.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && cat docs/handoff/pipeline-procedure-map/design.md docs/handoff/pipeline-procedure-map/recon.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && bash scripts/card-lint.sh docs/handoff/pipeline-procedure-map/CARD-LINE-GUIDE-01.md

期待する出力: card-lint exit0、違反0。L24警告は記録する。実在参照の不一致は根拠を照合して誤記のみ修正、意味が変わる場合は停止報告。
locale等の対象pathに新しい先約がないことを現行ledger/claimsで再確認する。共有本店の既存変更は変更しない。
自動登録された本ブランチledgerを正規運用で作業机へ取り込み、担当範囲・次の一手を記載する。

手順2 実装

許可したコードファイルをSolが生成/編集する。Astra設計追補の構造・7段階原稿契約・SSOT・導線・金型を忠実実装する。
編集ツールには必ずこの作業机の絶対パスを指定する。相対apply_patchを起動cwd本店へ向けない。
新規パネルは静的説明のみ。操作先はcallback/navigate、書込API追加0。全表示文字列をja/enで揃える。
見出しは通常文書構造、目次anchor、7つのCard、既存Badge/Button。新token/未登録金型追加0。
画面狭幅は縦配置と折返しで対応。外観CSSを新設しない。
既存ファイルは必要箇所の差分だけ。全置換やJSON全体の再整形で他の変更を混ぜない。

手順3 検証
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide/frontend && npm run check:all
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide/frontend && npm run build
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide/frontend && npm run test:unit -- src/pages/super-admin/components/LineWorkflowGuidePanel.test.tsx src/features/tcg-import-workflow/ImportWorkflowPanel.test.tsx

既存package/playwright設定に沿って新規E2Eを実行する。依存不足なら既存lockfileに従うnpm ciは許可、lockfile変更は禁止。
期待する出力: 各終了値0、既存基準から新規違反0、7段階と実導線/ja enのテスト成功。
E2Eは実hubのSystem→ガイド、hub callbackとquery一致、外部pathname、390/1440幅、light/dark、キーボード、表示中の業務書込0を確認。
モックと本番の検証を区別する。失敗した検証は隠さずAstraへ根拠付きで戻す。

手順4 差分検算と報告
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && git diff --check
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && git diff --stat
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && git status --short --untracked-files=all

期待する出力: 範囲外変更0、製品コードはfrontend指定ファイルのみ、削除ファイル0。行数を予測値で縛らない。
進捗は未マージ/未デプロイとして台帳と根拠へ記録し、DONEと書かない。
完了報告冒頭は「本報告はカード CARD-LINE-GUIDE-01 の実行結果である」。宛先はAstra。
報告に変更ファイル、検証コマンド/終了値/失敗箇所、画面証跡、未確認を含める。要求された検証の生出力を含め、秘密は除く。
teeで報告ファイルへ書かない。必要なら先に伏せ字方式をAstraへ確認する。
停止時は手順番号・最後のコマンド・理由をAstraへ報告。権限拒否を別手段で迂回しない。
実装完了後はAstraレビューまで待機する。

END OF CARD
