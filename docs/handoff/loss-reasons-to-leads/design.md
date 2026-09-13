# Phase 3 設計 — 失注理由の登録をリード側へ移設

**対象ADR**: ADR-121  
**recon**: docs/handoff/loss-reasons-to-leads/recon.md  
**日付**: 2026-07-23  
**担当**: Planner

リードに失注理由をぶら下げ、商談側の登録をやめるための設計です。

---

## 外部・過去事例の参照と我々への応用

- 該当なし：本件はリポジトリ内の既存失注理由登録を lead 側へ移す作業であり、外部の一般事例を参照しなくても recon の実測で十分に設計できる。
- 参考として、`docs/specs/db-ssot/deal-removal/design.md:73,109` は deal_close_reasons を lead 参照へ移す正本であり、本設計の前提として使う。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 失注遷移時に close_reasons を要求する | `backend/tests/test_close_reasons.py:109-174` の移設後テストが 422 を確認 |
| close_reason_memo が必須になる | 同上の移設後テストで memo なし 422 を確認 |
| is_primary がちょうど 1 件になる | 同上の移設後テストで primary 数の 422 を確認 |
| deal_close_reasons が lead_id で保存される | 同上の成功系テストで `lead_id` と `reason_id` を検証 |
| 非失注遷移では理由を要求しない | 同上の non-closing 遷移テストで 200 を確認 |

---

## 技術 How・KPI

- KPI: 失注理由の登録が lead PATCH に移り、deal PATCH に close reason の責務を残さない
- 技術選択: `LeadUpdate` に `close_reasons` / `close_reason_memo` を追加し、`leads.py` 側で lost 遷移のみ検証・登録する

---

## 弊害・トレードオフ

- 画面の入力欄は次便で追加するため、本便直後は API 経由でのみ登録できる
- 商談側の成約/失注理由登録は機能ごと廃止になる

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `LeadUpdate` に失注理由入力を追加 | Generator |
| 2 | `leads PATCH` で lost 遷移時のみ登録する | Generator |
| 3 | `deals PATCH` 側の close reason 登録を除去する | Generator |
| 4 | テストを `leads PATCH` に移す | Generator |

---

## 継続

- 完了後の監視: process-artifacts gate で recon/design の実在を検査
- 次フェーズへの引き継ぎ: フロント入力欄の追加と画面導線の接続

## 維持の仕組み

- 守り手: `.github/workflows/` の `process-artifacts gate`
- 守る対象: 失注理由がリードに紐づかずに登録されることの防止
- DB側の守り: `deal_close_reasons.lead_id` の NOT NULL 制約（#3032 適用済み）
