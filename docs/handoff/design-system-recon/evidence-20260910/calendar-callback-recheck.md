# 接続状態通知の依存修正・事前確認（2026-09-11）

[設計§AF](../../../specs/design-system/design.md)の根拠。基準eefa9143df4ba47b5f3854b222df595b302b503c。76c6dff9から対象TSX差分0、対象blob SHA256 f72bdf39fa2303317942445af8d684aff42bf9837f106ecda0f1e3182d1661ec。前Icon便の製品/文書stageは別作業台へ保持し、本便に持ち込まない。

実物: frontend/src/components/GoogleCalendarStatusBar.tsx:51–81でonSyncStatusChangeを参照する一方、依存配列はonStatusChangeのみ。:83–87でcheckStatus依存のeffectが状態取得と30秒intervalを登録/解除。:90–97で再接続後finally内に状態再取得。全srcで同部品を使うのはstories.tsx:9/13だけ。

前便のcommitは警告1件で拒否。rootが76c6dff9のTSXをgit showで取り、同eslintへstdin入力して--max-warnings=0で既存警告/exit1を再現した。全体check:allの警告許容と保存前max-warnings=0を区別する。

本便の公式worktree作成は、reaper自動削除の範囲に対する自動承認レビュー拒否を受けた。公式dry-runで68作業場所の削除候補0を確認して同じ操作を再申請、許可された。公式実行時も削除候補0、専用branch作成成功。スクリプト改変/回避や無関係作業の削除は行っていない。

Context7一覧0、公式React useCallback/useEffectを直接確認。契約・代替案・未解決の非同期取消範囲・自己審査は§AFに記録。既存配布React18.3.1を保持。外部事例は不要（限定修正を回帰試験で測定）。新規CI/業務仕様/API変更なし。
