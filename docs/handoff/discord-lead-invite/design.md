# 設計 — discord-lead-invite / oauth_state extra param (Card #7)

**対象ADR**: ADR-091  
**recon**: docs/handoff/discord-lead-invite/recon.md  
**日付**: 2026-08-31  
**担当**: Planner (Card #7)

---

## 外部・過去事例の参照と我々への応用

- 標準 OAuth state 拡張パターン: Google / Facebook 公式実装でも state に任意メタデータを付加する事例あり（JWT クレームや暗号化 blob への追加情報埋め込み）。本実装では既存 Fernet 暗号化層を再利用するため安全性は変更前と同等。
- 既存呼び出し元 `backend/app/routers/discord_oauth.py`・`backend/app/routers/meta_inbox.py` は `extra` 未指定のままで影響なし（後方互換）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `issue_state(extra={"lead_id": N})` 後、`consume_state` 戻り値に `lead_id` が含まれる | `pytest backend/tests/test_oauth_state_extra.py::test_extra_lead_id_stored_in_payload` |
| `extra` に予約済みキーを渡すと `ValueError` が送出される | `pytest backend/tests/test_oauth_state_extra.py::test_extra_conflict_tenant_id_raises` |
| `extra` 未指定の既存呼び出しは 4 キー payload を維持する | `pytest backend/tests/test_oauth_state_extra.py::test_extra_none_payload_has_no_extra_keys` |
| 既存テストスイート全件 PASS | `pytest backend/tests/test_oauth_state.py backend/tests/test_discord_oauth.py backend/tests/test_meta_oauth_endpoints.py` |

---

## 技術 How・KPI

- KPI: `backend/tests/test_oauth_state_extra.py` 6件 + `backend/tests/test_oauth_state.py` 14件 + `backend/tests/test_discord_oauth.py` 9件 + `backend/tests/test_meta_oauth_endpoints.py` 21件 = 計 50 件 PASS
- 技術選択: `payload.update(extra)` — Fernet 暗号化の内側でマージ（暗号化フローは変更ゼロ）
- 予約キー衝突チェック: `set` 演算 O(1) で即 ValueError（`_RESERVED` = tenant_id / staff_id / created_at / nonce）

---

## 弊害・トレードオフ

- `extra={}` は `if extra:` の falsy 判定でスキップ → no-op（意図的設計、test_extra_empty_dict_no_op で確認）
- Redis value サイズ微増（int 1 フィールド追加程度）。TTL・prefix・暗号化方式は変更なし

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `issue_state` に `extra` kwarg 追加・予約キー衝突チェック実装 | Generator |
| 2 | `backend/tests/test_oauth_state_extra.py` 6 ケース新規作成 | Generator |
| 3 | `docs/handoff/discord-lead-invite/recon.md` 作成（Card #5 申し送り） | Generator |

---

## 継続

- Card #5（discord_lead_invite ルーター）で `extra={"lead_id": lead.id}` パターンを使用。`consume_state` 戻り値に `lead_id` が含まれることを結合テストで確認する
- 次フェーズへの引き継ぎ: `docs/handoff/discord-lead-invite/recon.md` 参照

---

## 維持の仕組み

- 予約キーセット `_RESERVED` は `issue_state` 内ローカル定数（スコープ外変更不可）
- 予約キーを追加・変更する際は `backend/tests/test_oauth_state_extra.py` の衝突テストを更新すること
- 守り手: backend/app/services/oauth_state.py
