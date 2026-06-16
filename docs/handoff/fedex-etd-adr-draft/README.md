# fedex-etd-adr-draft

**目的**: FedEx ETD（Electronic Trade Documents / Paperless Trade）実装準備ドキュメント  
**作成日**: 2026-06-16  
**参照元**: `docs/handoff/fedex-etd-stamp-recon/recon.md`（PR #2234 recon）  
**ステータス**: APAC 確認待ち（実装・ADR 正式起案はまだ）

---

## ファイル一覧

| ファイル | 内容 |
|---------|------|
| `fedex-apac-questions.md` | apacfedexapi@fedex.com への確認質問 Q1〜Q6 |
| `adr-draft.md` | ETD 実装 ADR たたき台（番号未確定）|

---

## 次に Shingo が判断するもの

1. **APAC 質問を送信するか**: `fedex-apac-questions.md` を確認し、apacfedexapi@fedex.com に送信する
2. **ETD 実装タイミング**: Label Validation 申請前か後か（APAC Q1 の回答次第）
3. **ADR 正式起案**: APAC 回答後、`adr-draft.md` を `docs/adr/ADR-XXX-fedex-etd.md` として起案する
   - `node scripts/generate-adr-index.js` の実行も必要

---

## このフォルダで行っていないこと（確認）

- 実装変更: なし
- migration 変更: なし
- deploy.yml 変更: なし
- FedEx 外部設定変更: なし
- secrets 変更: なし
- 本番 DB 操作: なし
