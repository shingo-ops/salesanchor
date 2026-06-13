# recon — tenant_001 スキーマ・データ調査

**仕事名**: tenant_001-investigation  
**日付**: 2026-06-13  
**対象ADR**: ADR-036  
**担当**: shingo-cc

---

## 目的

tenant_001 が空テナントか否か・スキーマ欠損の有無を本番 DB で読み取り専用確認する。
使い捨てワークフロー（GitHub Actions workflow_dispatch）経由で実行。調査後削除。

---

## file:line 引用表

| 引用先 | 確認内容 |
|--------|---------|
| `backend/app/services/tenant.py:1488` | スキーマ命名: tenant_{id:03d} 形式 |
| `backend/app/models.py:11` | id = Column(Integer, primary_key=True) — SERIAL 連番 |
| `backend/app/models.py:13` | tenant_code = Column(String(50), unique=True) — 表示用識別子 |
| `.github/workflows/temp-tenant001-investigation.yml:8` | workflow_dispatch + confirm gate |
| `.github/workflows/temp-tenant001-investigation.yml:69` | SET TRANSACTION READ ONLY — DB レベル書き込み禁止 |

---

## 調査範囲

- public.tenants 一覧確認
- tenant_001 テーブル一覧・主要テーブル存在確認
- tenant_001 データ件数・最終更新（COUNT/MAX のみ）
- tenant_001 vs tenant_003・tenant_005 テーブル差分

## 変更内容

ワークフローファイル追加のみ（コード変更なし）:
- `.github/workflows/temp-tenant001-investigation.yml`（NEW）
