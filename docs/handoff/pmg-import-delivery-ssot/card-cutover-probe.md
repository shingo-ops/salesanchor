---
mode: handoff
---
CARD-PMG-CUTOVER-PROBE-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: guards/00-common.md、guards/03-file.md、guards/11-lint.md。cd接頭辞・対象限定・正式lintを照合済み。
設計: design.md「Linux/Docker隔離検証便」。当該試験実装の自己審査APPROVE。製品設計はREVISE。
カード発行前照合: 1記号○、2ready PR○、3宛先○、4一目的○、5既存作業場所○、6書式○、7実出力/対象確認○。
実装担当: Codex Terra。設計担当: root。PO原文「codex terra」「進める」。作業場所例外「許可する進める」。
受領確認: 最初にカード名と受領を返す。
作業場所は既存release/pmg-cutover-rehearsal、起点89ad29ae、UUID c4aca19e-0e68-4a1c-acd7-f37c63d92ff9。
新作業場所/別AIの起動、他者変更の撤回、製品コード/本番/DB/認証情報への接触を禁止する。
許可する新規ファイルは tests/pmg_cutover_probe.py と .github/workflows/pmg-cutover-probe.yml の2件だけ。
設計文書/台帳はrootが編集するため触らない。commit/push/PR/マージ/デプロイはこのカードでは実施しない。
後続PRはreadyで作成し下書きにはしない（root担当）。

手順0
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-cutover-rehearsal && bash scripts/validate-worktree-start.sh
期待する出力: worktreeチェック通過、exit0。

手順1（実装）
設計の試験契約を満たす上記2ファイルを新規作成する。コード生成と編集ツールの使用を明示的に許可する。
両ファイルを完成形で作成し、契約の再設計をしない。既存nginx/nginx.confの変更は0件。
fixtureの細部はADR-113で許された裁量。実動作の不明は推測せずrootへ停止報告する。

手順2
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-cutover-rehearsal && /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m py_compile tests/pmg_cutover_probe.py
期待する出力: exit0、構文エラー0。Linux/Docker試験はローカルで未実行として明記する。

手順3
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-cutover-rehearsal && git diff --check
期待する出力: exit0。新規2ファイルの名前と内容を読み取り検査する。rootの文書差分と区別する。

完了報告の冒頭: 本報告はカード CARD-PMG-CUTOVER-PROBE-01 の実行結果である。
完了報告はrootへの本文に実行した検証の生出力を全文含め、実行していないDocker試験を分ける。
停止時は停止手順番号・最後のコマンド・理由・エラー全文をrootへ返す。権限/ガードを迂回しない。
END OF CARD
