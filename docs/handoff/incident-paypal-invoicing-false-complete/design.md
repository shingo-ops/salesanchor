# design: PayPal請求書発行 虚偽完了報告インシデント 再発防止 PR-C

**仕事名**: incident-paypal-invoicing-false-complete  
**作成**: Planner（Web Claude）  
**実装**: Generator（Claude Code）  
**参照 recon**: docs/handoff/incident-paypal-invoicing-false-complete/recon.md  
**対象 ADR**: ADR-1000  
**日付**: 2026-06-20  
**正本**: docs/STANDARD-WORKFLOW.md。矛盾時は正本優先。

---

## 外部・過去事例の参照と我々への応用

- **過去事例**: PayPal Sandbox 実スモークは `backend/tests/sandbox/test_paypal_sandbox.py:1-80` に実在し、`external-api-smoke.yml` からのみ実行する前提で分離されている。→ 今回も PayPal だけは実スモーク必須にする。
- **過去事例**: `backend/pyproject.toml:54-59` で `sandbox` を通常 pytest から除外し、実スモークを CI 専用に閉じ込める。→ 本 PR でも通常 test と分離する。
- **該当なし**: 外部 API gate の既存実装は固定パス判定だったため、コード内容ベースの検出は今回が初導入。

---

## PR-C の目的

外部サービスを呼ぶコードの変更を、固定パスや手動登録に依存せず、差分内容から検出する。

- `scripts/detect-external-api-change.js:11-20` で docs / tests / workflow / smoke script を除外し、実コード差分に限定する
- `scripts/detect-external-api-change.js:30-150` で PayPal / FedEx / Meta / Firebase / Discord / Google / PokeAPI / FX rate を API 別に判定する
- `scripts/detect-external-api-change.js:168-232` で diff の +/- 行だけを評価する
- `scripts/detect-external-api-change.js:248-319` で PR 差分を走査し、GitHub Actions の outputs に `paypal_detected` / `unprepared_apis` を渡す
- `.github/workflows/external-api-smoke.yml:29-73` で PayPal だけ実 Sandbox smoke を走らせ、他 API は `実環境スモーク未整備` をログに出す

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 既知の外部APIファイルが全件検出される | `node scripts/tests/test-detect-external-api-change.js` |
| 無関係な UI / docs / workflow / smoke は検出されない | 同上 |
| PayPal 変更 PR は PayPal Sandbox smoke が実行される | `.github/workflows/external-api-smoke.yml:48-73` の実行ログ |
| PayPal 以外の外部API変更は「実環境スモーク未整備」と出る | workflow ログ確認 |

---

## 技術 How・KPI

- KPI: 外部API変更の検出漏れ 0
- KPI: PayPal 以外の外部API変更で未整備可視化 100%
- 技術選択: 変更ファイルの中身を diff 行単位で分類する。パス登録方式は使わない
- 技術選択: 既存の PayPal Sandbox smoke は継続利用し、新規 smoke はこの PR では作らない

---

## 弊害・トレードオフ

- 誤検知の可能性: コメントや文字列にも API 名があると拾う。→ tests / docs / workflow / smoke を除外してノイズを抑える
- 未整備 API はブロックしない: 失敗させると gate 化が先走る。→ まず可視化して整備対象を見える化する
- PayPal 以外の API は smoke が無い: しかし黙って通す方が事故になる。→ ログで明示する

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `scripts/detect-external-api-change.js` を追加 | Generator |
| 2 | `scripts/tests/test-detect-external-api-change.js` を追加 | Generator |
| 3 | `.github/workflows/external-api-smoke.yml` を detector ベースに更新 | Generator |
| 4 | `backend/tests/sandbox/test_paypal_sandbox.py` と `backend/pyproject.toml` を整備 | Generator |
| 5 | `docs/handoff/incident-paypal-invoicing-false-complete/recon.md` を更新 | Generator |

---

## 継続

- 新しい外部 API 連携を追加するたび、この detector のパターンに反映されることを確認する
- PayPal 以外の外部 API の実環境 smoke は別タスクで整備する

---

## PR-D: 完了の定義

### 背景

PayPal 請求書発行の PR #1980 では、自己申告とモックテストの緑だけで「完了」と扱われ、本番でエラーになった。完了判定に、実証と人の動作確認が欠けていた。

### 役割

「完了とは何か」を `docs/STANDARD-WORKFLOW.md` の §2 で定義した4条件に束ねる。

### 5層防御 / PR-A〜F 対応地図

| 層 | 役割 | 対応PR | 状態 |
|---|---|---|---|
| L1 | 実スモークの実行 | PR-A / PR-B | 完了済み（PayPal Sandbox smoke を維持） |
| L2 | 変更検出 | PR-C | 完了済み（コード内容ベース detector） |
| L3 | 自動チェックの束ね | 既存 CI + process-artifacts gate | 完了済み |
| L4 | 人の実動作確認 | PR-D | 今回追加する定義 |
| L5 | 人の承認を仕組みで必須化 | PR-E | 次段階で必須化 |
| F | 本番デプロイ安全化（deploy後 health + auto-rollback は既達、事前リハーサルはローンチ後） | PR-F | 一部既達 / 残件は staging 前提 |

### PR-E との境界

- PR-D は「完了」の定義そのものを決める。
- PR-E は、その定義に含まれる人の動作確認／承認を仕組み（ゲート）で必須化する。
- つまり、PR-D は定義、PR-E は必須化の仕組みである。

### PR-F の決定

- 本番デプロイの安全化については、`deploy.yml` に **Pre-deploy DB backup**、**backend health check**、**health 失敗時の自動ロールバック**、**blue-green 切替** が既に実装されている。
- したがって PR-F のうち **deploy 後 health + auto-rollback は既達** と扱う。
- 残る **別環境での事前リハーサル** は、ステージング環境が前提であり、ローンチ後に構築する。
- そのため PR-F は「既存 deploy 安全網の確認」と「ステージング前提の事前リハーサル」を分けて管理する。
- `docs/adr/ADR-1000-external-api-smoke-mandatory.md` にも同じ区切りを記録する。

### 既存ゲートの束ね

- 自動チェック部分は PR-A/B（外部APIスモーク）＋PR-C（検出）＋process-artifacts gate＋CI が担保する。
- 今回は新規ゲートを作らない。完了記録は `tasks/todo.md`・`.claude-pipeline/active-work.md`・`docs/ai-agents/evidence-registry.md` に残す。
- `docs/handoff/incident-paypal-invoicing-false-complete/recon.md` と相互参照する。
