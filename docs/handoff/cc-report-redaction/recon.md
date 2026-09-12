# CC報告の機密混入を止める recon（2026-09-06）

対象: 実装役（CC）の報告ファイルと、そこから設計パートナー・チャットへ運ばれる出力。
根拠: 2026-09-06 の実測（本番DB読み取り・origin/main 読み取り）。

## 1. 発端

TCG の抽出失敗を調べる読み取り便で、`extraction_jobs.error_message` に保存されていた
Gemini API のエラー文が、API キーを含む URL のまま報告ファイル・チャットに転載された。
露出先は3か所（本番DBの列・報告ファイル・チャット）。

## 2. 確定した事実

- アプリ側には Gemini 例外用の伏せ字関数がある: `backend/app/services/gemini_extraction_svc.py:68`
  （`_safe_error_message`）。抽出タスクからも呼ばれている: `backend/app/tasks/tcg_extraction.py:95`。
  専用テストも存在する: `backend/tests/test_gemini_error_redact.py:20`。
- したがって新規の記録はキーを含まない形式で保存される。露出したのは 2026-09-04 の古い記録1件。
- リポジトリには gitleaks の設定がある: `.gitleaks.toml:1`（プロジェクト固有ルールと許可リスト）。
  CI でも走る: `.github/workflows/secret-scan.yml:1`。
- ただし報告ファイルの置き場（実行役のローカル一時領域）は git 管理外のため、
  上記 CI の検査対象にならない。ここが穴。
- 実装役の常設ルールで出力の扱いを定めているのは1行のみ: `docs/ai-agents/executor-preamble.md:23`
  （要約せず生のまま全文返す）。伏せ字への言及は無かった。
- 設計パートナーのカード発行前チェックは12条まで: `docs/ai-agents/design-partner.md:193`。
  報告に秘密を混ぜない条項は無かった。
- 関所は正本を含む PR で宣言照合を行う: `scripts/check-process-artifacts.js:53`。
  設計docには受け入れ基準の表・recon 相互参照・ADR 参照・外部事例欄・維持の仕組み欄が必須:
  `scripts/check-process-artifacts.js:407`、`scripts/check-process-artifacts.js:424`、
  `scripts/check-process-artifacts.js:430`、`scripts/check-process-artifacts.js:436`、
  `scripts/check-process-artifacts.js:460`。

## 3. 決定事項（PO 合意、2026-09-06）

- 3段構えで防ぐ。①出力時に伏せ字 ②共有前に検査 ③正本に記載して強制。
- ①はカードの全 `tee` の手前に伏せ字フィルタを挟む形で即日運用を開始した。
- ②は既存の gitleaks 設定を報告ファイルの置き場に対して走らせる（新規ルールは作らない）。
- ③は正本2本に分けて追記する（1便=1GO=1PR）。

## 4. 未確認・要実測

- 露出した API キーが現在も有効か（PO 確認事項）。
- 本番DBに残る古い `error_message` の消去（migration 経由で行う。別便）。
- 伏せ字フィルタが捕まえられない形式の秘密（既知パターン以外）。
