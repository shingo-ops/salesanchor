# Phase 3 設計 — send-guard-phase-b

**対象ADR**: ADR-143（送信ガード Phase B）
**recon**: docs/handoff/conv-logs-direction-guard/recon.md
**日付**: 2026-06-24
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：Phase B はフロントエンド（useEffect 1箇所）＋バックエンド（新規 GET エンドポイント 1本）の最小変更。外部事例を参照する設計上の判断点は存在しない。ガード判定ロジック（多数決）は ADR-143 Phase B セクションで設計済み。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `GET /leads/{id}/recipient-language` が 200 を返す | `pytest backend/tests/test_lang_judge.py` 4/4 PASS |
| `confident=true && language="en"` のとき `languageOverrideByLead` に `"en"` が注入される | `useInboxState.ts:536-552` コードレビュー |
| 既に手動設定済みの lead は上書きされない | `useInboxState.ts:536`（Guard 1）+ `:544`（Guard 2）コードレビュー |
| 判定不能（`confident=false`）/ API 失敗時は `auto` 維持 | `backend/app/services/lang_judge.py:97-98` + `.catch(() => {})` コードレビュー |
| Phase A（InboxMessageThread.tsx）無改変 | `git diff main --name-only` に InboxMessageThread.tsx が含まれない |

---

## 技術 How・KPI

- KPI: `GET /leads/{id}/recipient-language` がデプロイ後に 404 でなく 200 を返す（PO 目視確認）
- 技術選択: schema-qualified SQL（`set_tenant_context` 不要）— `backend/app/services/lang_judge.py:49-53` の既存パターン踏襲

---

## 弊害・トレードオフ

- スレッドオープン毎に API 呼び出し 1 本増加 → `catch(() => {})` でエラー無視、UX 影響なし
- `confident=false` 時は `auto` のまま → Phase A が安全側で動作（意図的）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `GET /leads/{id}/recipient-language` エンドポイント追加（`backend/app/routers/leads.py` 末尾） | Generator |
| 2 | `useInboxState.ts` selectedLeadId useEffect に Phase B フェッチ追加 | Generator |
| 3 | `backend/tests/test_lang_judge.py` 新規（4テスト） | Generator |
| 4 | `docs/adr/ADR-143-send-guard.md` Phase B セクション追記 | Generator |

---

## 継続

- 完了後の監視: デプロイ後 `GET /api/v1/leads/{id}/recipient-language` が 200 を返すことを PO 目視確認
- 次フェーズへの引き継ぎ: localStorage 永続化は ADR-143 §Phase B で将来検討
