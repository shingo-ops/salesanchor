# recon — openapi-docstring-adr1010

**仕事名**: openapi-docstring-adr1010  
**日付**: 2026-10-13  
**対象ADR**: ADR-1010  
**担当**: Dev（実装担当）

---

## 既存ADR検索結果

- `docs/adr/ADR-1010-api-contract-and-wiring-ledger.md:1` の題名は「API型契約（OpenAPI→TypeScript）と配線台帳の自動生成」。OpenAPI 出力スクリプトが指すべき ADR はこれ。
- `docs/adr/ADR-1005-migration-run-once-ledger.md` は migration 台帳の ADR で、API 型契約とは別物。
- 経緯: PR #3942（2026-10-13 マージ、f0faa9e17）で API 型契約の ADR 番号を ADR-1005 から ADR-1010 に付け直した（PO 判断 2026-10-07）。このとき下の2か所が付け直されず残った。

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/tools/export_openapi.py:1` | docstring が「（ADR-1005）」のまま。内容は OpenAPI スキーマの書き出しで、API 型契約を指す |
| `docs/handoff/cross-dept-integrity-foundation/card-c1.md:24` | 上の docstring をそのまま写した行。同じく「（ADR-1005）」 |
| `docs/adr/ADR-1010-api-contract-and-wiring-ledger.md:1` | API 型契約の ADR（正しい参照先） |
| `docs/adr/ADR-1005-migration-run-once-ledger.md:1` | migration 台帳の ADR（別物。今回触らない） |

## 他の ADR-1005 参照（`git grep -n 'ADR-1005' -- backend/ frontend/`）

- 変更前の出力は `backend/tools/export_openapi.py:1` の1件のみ。frontend/ には無い。

## 不明点リスト

- なし
