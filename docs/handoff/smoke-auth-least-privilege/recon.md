---
mode: handoff
---
# recon — smoke-auth-least-privilege

> この文書は何か：デプロイ後の送料見積もり確認（smoke）が使う「サービス用トークンで認証を省く経路」の現状を、実物で確かめた記録です。本番の具体値（メール・トークン・IP・個別ID）は書きません。

**仕事名**: smoke-auth-least-privilege
**日付**: 2026-10-15
**対象ADR**: ADR-1017（本テーマ・起案）、ADR-1013、ADR-125、ADR-135、ADR-136
**基準**: origin/main `94e774533`

---

## 既存 ADR 検索の結果

- `git grep -n -i "SMOKE_SERVICE" -- docs/adr` ・ `docs/adr/FEATURE-INDEX.md` で機能キーワード検索（smoke／認証）を実施
- ADR-1013（`docs/adr/ADR-1013-self-hosted-auth-and-passkey.md`）の Consequences に「Firebase に依存する運用スクリプト・CI・監視（qa-smoke・rotate-qa-firebase・snapshot・smoke）は便6 で置き換える」とある
- `docs/handoff/auth-self-hosted-passkey/design.md` §4 は SMOKE_SERVICE_TOKEN を「先頭のまま変えない」と記す（据え置き）。ADR-1013 の「便6 で置換」と食い違う → ADR-1017 で整理する
- ADR-125（認証・権限の基本）、ADR-135・ADR-136（危険パスと GO）は関連として参照
- 専用のsmoke最小権限 ADR は存在しなかった（本テーマが新規）

## file:line 引用表（origin/main 基準）

| # | 事実 | 出典 |
|---|---|---|
| F1 | smoke 用の 2 つの env を読む（TOKEN と EMAIL。どちらかが空なら経路は不活性） | `backend/app/auth/dependencies.py:41-42` |
| F2 | `get_current_user` の先頭付近に smoke バイパスがある。ブラックリスト・キャッシュ・Firebase・MFA より前 | `backend/app/auth/dependencies.py:140-157` |
| F3 | 一致判定は `secrets.compare_digest(token, ...)`。非ASCII の str を渡すと TypeError（500 になる） | `backend/app/auth/dependencies.py:145` |
| F4 | 一致すると EMAIL の is_active ユーザーを返す。そのユーザーが super admin かの確認は無い | `backend/app/auth/dependencies.py:147-157` |
| F5 | smoke 認証の成立を記録する処理は無い | `backend/app/auth/dependencies.py:140-157` |
| F6 | super admin は `users.is_super_admin` 列で判定する（全テナント横断の運営権限） | `backend/app/models.py:33` |
| F7 | 権限判定の正本は `user_roles`（`users.role` は使わない）。ただし参照はテナントのスキーマ内で、smoke 経路の位置では search_path が未設定 | `backend/app/auth/dependencies.py:526-541`・`backend/app/auth/system_roles.py:17-19` |
| F8 | deploy が .env に 2 つの値を注入する（Secrets 由来） | `.github/workflows/deploy.yml:314-315` |
| F9 | FedEx smoke は `FEDEX_SMOKE_ENABLED=true` の時だけ動く（既定は skip） | `.github/workflows/deploy.yml:555-573` |
| F10 | 設計書の受入基準にあるバイパスの pytest は未実装 | `docs/handoff/fedex-smoke-switch/design.md:38-40` |
| F11 | 既存テストは smoke 経路を空にして Firebase 経路を試験している（バイパス自体の試験は無い） | `backend/tests/test_event_loop_nonblocking.py:172` |

## 結論（事実に基づく）

- smoke 経路は、解決先ユーザーの権限がそのままトークン漏洩時の影響範囲になる（F2・F4）。
- 解決先に制約が無いため、設定次第で全権ユーザーにも到達し得る（F4）。コードで防いでいない。
- 非ASCII 入力で 500 になる欠陥がある（F3）。
- 使われた記録が残らない（F5）。
