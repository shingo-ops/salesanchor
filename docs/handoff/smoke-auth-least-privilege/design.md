---
mode: handoff
---
# 設計 — smoke-auth-least-privilege

> この文書は何か：smoke 認証経路を「最小権限の専用ユーザーだけ」に絞り、全権ユーザーはコードで構造的に拒否するための作り方です。

**対象ADR**: ADR-1017（本テーマ）、ADR-1013（据え置き整理の対象）、ADR-125、ADR-135、ADR-136
**recon**: [docs/handoff/smoke-auth-least-privilege/recon.md](recon.md)
**日付**: 2026-10-15
**状態**: 設計済み（PO 2026-10-15「A」で案A採用）。Draft PR 起票。実装レビュー待ち。本番作業は GO 待ち。

---

## 1. 狙い

1. トークン漏洩時の被害上限を「全テナントの運営権限」から「1 テナントの送料計算のみ」へ縮める。
2. 全権ユーザーを smoke に結びつける事故を、コードで二度と成立させない（fail-closed）。
3. 新しい認証方式は作らない（既存方式を増やさない）。

## 2. 変更内容

### 2-1. コード（`backend/app/auth/dependencies.py`）

| 変更 | 内容 |
|---|---|
| 構造ガード | smoke で解決したユーザーが `is_super_admin` なら返さず 401 |
| 不具合修正 | `compare_digest` の TypeError／ValueError を「不一致」に倒す（新設の小関数 `_is_smoke_token`）。不一致は通常の検証経路へ進み 401 |
| 監査 | smoke 認証が成立する直前に、既存の logger で 1 行（ユーザーID・テナントID・IP。トークンは記録しない） |
| 不変 | env が空なら経路は不活性（従来どおり） |

owner／admin ロールの判定は入れない。理由：参照先の `user_roles` はテナントスキーマ内にあり、この位置では search_path が未設定（recon F7）。スキーマ名の直組みや search_path 変更は過剰設計になる。最小権限は「専用ユーザーに shipping.calculate だけを付ける」運用（2-2）と、super admin 拒否のコード保証の二重で担保する。

### 2-2. 本番データ（GO 待ち・実行しない）

- 該当テナントに、shipping.calculate だけを持つ一般ユーザーを 1 名作成する（owner／admin／super admin にしない。パスワードログイン不可）。
- 本番書込のため、スクリプト化したものを PO が実行する。登録前に候補を PO に提示する。

### 2-3. Secret 更新（GO 待ち・実行しない）

- `FEDEX_SMOKE_USER_EMAIL` を新ユーザーへ更新、`FEDEX_SMOKE_API_TOKEN` をローテーション。

## 3. 適用順

1. 専用ユーザー作成 → 2. Secret 更新 → 3. コードをデプロイ。
順序が前後しても、smoke が赤くなるだけで安全側（fail-safe）。戻し方は Revert と Secret の戻し。

## 4. 受入基準

| 基準 | 検証方法 |
|---|---|
| smoke トークンで super admin は返らない | pytest `test_smoke_token_resolving_to_super_admin_is_rejected_401` が緑。デプロイ後に専用ユーザーの is_super_admin=false を DB で確認 |
| 漏洩時の被害が送料計算のみ | 専用ユーザーの権限が shipping.calculate のみであることを DB で確認（GO 後） |
| FedEx 自動チェックは従来どおり動く | pytest `test_smoke_token_least_privilege_user_passes` が緑。デプロイ後 `FEDEX_SMOKE_ENABLED=true` の時、smoke が従来どおり PASS |
| 非ASCII Bearer で 500 が出ない | pytest `test_smoke_token_non_ascii_bearer_is_401_not_500` が緑 |
| smoke 使用が記録に残る | pytest が成立時のログ行とトークン非記録を確認。デプロイ後にアプリログで行を確認 |
| env 空で経路が不活性 | pytest `test_smoke_disabled_when_env_empty_falls_through_to_firebase` が緑 |
| 不一致トークンはバイパスしない | pytest `test_smoke_mismatched_token_falls_through_to_firebase` が緑 |

## 5. 外部事例

- OWASP ASVS V2（サービス認証）・Cloud の最小権限原則：サービス用資格情報には業務に必要な最小の権限だけを与え、特権アカウントとの兼用を避ける。
- GitHub Actions／GCP の短命トークン（OIDC）：長寿命の共有トークンより、短命・スコープ付きが推奨される。恒久策として別便で自社 JWT（ADR-1013 整合）に移す。
- 本設計は恒久策までの当面の縮小策であり、トークンのローテーションを運用に含める。

## 6. 弊害と対策

| 弊害 | 対策 |
|---|---|
| 適用順を誤ると smoke が赤くなる | 安全側に倒れるだけ。順序は 3 に記載 |
| 監査が logger のため検索性は限定的 | 将来 audit_logs へ（テナント文脈が揃う位置で）。別便 |

## 7. 触らない範囲

`.github/workflows/deploy.yml`・migrations・frontend・既存の Firebase／自社トークン経路。

## 8. 計画・継続

実装カード `docs/handoff/smoke-auth-least-privilege/card.md` に従う。ローテーションは運用（四半期目安）。恒久策（短命 JWT 化）は別便で ADR 起案。
