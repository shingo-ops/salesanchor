# SEC-01 PR-D rate bucket implementation note

> Issue: #2179  
> Recon: `docs/handoff/security/sec-01-rate-bucket/recon.md`  
> Design: `docs/handoff/security/sec-01-rate-bucket/design.md`  
> 作成日: 2026-06-14

---

## 状態

このブランチはPR-Dのrecon/designブランチであり、実装PRは別ブランチで作る。

理由:

- #2180 はdocs-onlyの設計PRとして開いている。
- 実装PRを同じブランチに混ぜると、review gateが曖昧になる。
- 実装では `backend/app/middleware/rate_limit.py` とテストだけを小さく変更する。

---

## 実装方針

- 未検証JWT payload emailを user bucket に使わない。
- verified JWT cache hit時だけ user bucket を使う。
- それ以外は IP bucket を使う。
- Firebase検証はmiddleware内で実行しない。
- Nginx / deploy.yml / migrations / scripts は触らない。

---

## review gate

- targeted pytest: `backend/tests/security/test_rate_limit_identity.py`
- backend regression: `python -m pytest backend/tests -q` または未実行明記
- 正規ユーザー操作で429が増えすぎないことは、後続smokeで確認
