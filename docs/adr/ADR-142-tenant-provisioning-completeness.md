# ADR-142: 新テナント provisioning に必須テナント別テーブルが漏れなく揃うことを保証する

**状態**: Accepted
**日付**: 2026-06-24
**決定者**: PO (Shingo)
**関連**: recon `recon2-D2-own-inventory-new-tenant.md` / 設計 `design-D2-own-inventory-new-tenant.md` / PR #2547 / ADR-SA-18（app-db least-privilege）

---

## Context（背景）

SalesAnchor はマルチテナント構成で、テナント別データは各テナントスキーマ（`tenant_NNN`）配下のテーブルに置き、Row Level Security（RLS）でテナント間を隔離する。新テナントの作成は `backend/app/services/tenant.py` の `create_tenant_schema()` が担い、テーブルDDL・RLS有効化・分離ポリシー・GRANT を provisioning コード（`_TENANT_TABLES_SQL` / `_RLS_ENABLE_SQL` / `_RLS_POLICY_SQL`）で生成する。

2026-06-24 の recon で、**A在庫テーブル `own_inventory`（自社保有在庫）が、後付け migration（`20260604_140000`）では既存テナントに作られていたが、新テナント作成の provisioning コードには定義が無かった**ことが判明した（problem②）。結果、新テナントは `own_inventory` が**そもそも作られない**状態だった。

根本原因は「**新テナントに必須テーブルが漏れなく揃っていることを保証する正典（ADR）も、検査ゲートも無かった**」こと。migration でテーブルを足しても、provisioning コードへの反映が抜ければ、以後の新テナントだけが欠落する——この抜けを止める仕組みが存在しなかった。

## Decision（決定）

1. **新テナント作成時に、必須のテナント別テーブルは provisioning コードで漏れなく作られ、各々に RLS有効化＋テナント分離ポリシーが付与される**ことを正典とする。GRANT は `GRANT … ON ALL TABLES IN SCHEMA` の一括付与でカバーする。
2. **「テナント別テーブルを migration で追加する変更」は、同時に provisioning コード（`create_tenant_schema` 経路）への反映を必須とする**。片方だけの変更は不完全とみなす。
3. テナント別 RLS テーブルの**分離ポリシーは、既存テナントと同一の命名・定義に揃える**（同一テーブルは全テナントで同一ポリシー名）。D-2 では `own_inventory_tenant_isolation`（既存 migration と同名）を採用。
4. 将来的に、新テナントの生成結果が「必須テーブル一覧」と一致することを検査するゲート（provisioning の網羅性チェック）を設けることを推奨する（本ADRはその根拠）。

## Consequences（影響）

- **Positive**: 新テナントが必須テーブル欠落・RLS隔離漏れの状態で生まれることを防ぐ。problem② と同型の「migration では足したが provisioning に反映漏れ」の再発を、正典＋（将来の）ゲートで止められる。SaaS 化（新顧客＝新テナント作成）の前提が満たされる。
- **Negative / Cost**: テナント別テーブルを足すたびに provisioning コード3箇所（DDL / RLS有効化 / ポリシー）の更新が必要。GRANT は一括のため追加不要。
- **検証**: 新テナント作成後、対象テーブルが「列・制約・RLS有効・ポリシー存在」で既存テナントと差分0、かつ別号室から越境して見えない（漏れ0）ことを実測して確認する（D-2 §7 / KPI2-a〜d）。

## Status of provisioning-ADR before this（recon D の事実）

- 新テナント provisioning を扱う正典 ADR は **該当なし**だった（recon D）。
- ADR-SA-18 は GRANT/least-privilege モデルの根拠だが、provisioning の網羅性は扱っていない。
- 本ADRがその空白を埋める。

## 適用第1号

PR #2547（D-2: 新テナント作成に `own_inventory` を追加）。本ADRを根拠とする。
