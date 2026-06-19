# ADR-1000: 外部API連携の実Sandboxスモーク必須化による虚偽完了報告の再発防止

## Status
Accepted（GO: Shingo 2026-06-18）

## 背景・課題（Why）

PayPal請求書発行機能が、実際には発行できずエラーが出る状態のまま「完了」報告され、マージされた（PR #1980, `feature/morimoto/paypal-invoicing` → develop）。recon により、単一の見落としではなく **4つの構造的な穴**が重なっていたことが判明した。

1. 検証パイプライン（Evaluator含む）が `claude-impl/*` のみ対象で、正規の人間ブランチ `feature/morimoto/*`（CLAUDE.md:70）では起動しなかった（`claude-pipeline.yml:63-70`）。今回 Evaluator は SKIPPED。
2. PayPalテストが全てモックで、実APIの故障を検知できない（実Sandboxテスト不在）。
3. process-artifacts gate は書類の存在・形式のみ検証し、動作確認の有無を見ない（`scripts/check-process-artifacts.js`）。
4. 完了の根拠が自己申告＋モック緑で、人間レビュー0件。

## 決定（What）

人間起因のミス（動作確認漏れ・スモーク用意忘れ）を仕組みで最小化する。**機械を一次防御、人間を最終確認とする二重防御**を採用する。順序が決定的（機械が一次に効くので、人間がサボっても壊れたコードは止まる）。

- **外部APIを叩くコードを変更したPRは、実Sandboxスモークが成功しない限りマージ不可**（`external-api-smoke.yml`：`paths`不使用の常時起動＋内部 git diff 判定、secrets未登録時はSKIPでなくFAIL）。本ADRで着手（PR-A：スモーク本体／PR-B：起動ワークフロー）。
- gate に外部API呼び出しの自動検出→スモーク必須を追加（PR-C。検出を人間の手動登録に依存させない）。
- 外部API連携PRに認可承認者の承認必須（PR-E。Ruleset方式は不成立のため gate 方式・ADR-136 流用）。
- 本番デプロイ安全化：本番相当素振り＋人間の証拠付き最終確認＋デプロイ後ヘルス＋異常時自動ロールバック（PR-F）。
- 完了定義のインライン明記（PR-D）：完了とは指定ゲートの緑＋人間の証拠付き確認であり、自己申告は根拠にしない。

## スコープ外・許容（本ADRで完全には閉じない）

- Sandboxと本番の差異（Sandbox成功は本番動作を保証しない）。
- 外部API呼び出し検出パターンの網羅性。
- 緊急時の手動通過（bypass）は今回封鎖しない。
- 人間確認者の空判子（機械では強制不能。機械の層を主防御に置くことで影響を抑える）。

## 関連

- 設計詳細: `docs/handoff/incident-paypal-invoicing-false-complete/design.md`
- recon: `docs/handoff/incident-paypal-invoicing-false-complete/recon.md`
- 関連ADR: ADR-051（claude-pipeline）, ADR-121 / ADR-135 / ADR-136（process-artifacts gate・develop保護・承認必須）, ADR-112（設計起点フロー v2）, ADR-012（ブランチ運用）, ADR-124（sop-health-reporter）
