# design — deal-removal-track-a

**仕事名**: deal-removal-track-a  
**日付**: 2026-06-23  
**対象ADR**: ADR-121  
**担当**: planner

---

## 0. 全体

dashboard から商談ボード系の可視参照だけを外す。`deals` テーブル自体や `/deals` ページは残し、成約率と W-2① は維持する。

---

## 1. 外部・過去事例の参照と我々への応用

- `#2467` の dashboard フロント変更では、表示中心の変更でも `frontend/src/` が process-artifacts gate の対象になり、GO 記録が必要だった。今回も同様に、見える参照外しでもゲート確認を前提にする。

---

## 2. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| dashboard API から deal 系の summary/pipeline/recent を返さない | `pytest backend/tests/test_dashboard.py -q` |
| dashboard cache 側でも deal 系を返さない | `pytest backend/tests/test_celery.py -q` |
| frontend で商談 KPI と停滞商談導線が消え、W-2① と成約率が残る | `npm --prefix frontend run build` + Playwright |
| `tenant_006` で画面が正常に描画される | PG/RLS 実走テスト |

---

## 3. recon / ADR 相互参照

- recon: `docs/handoff/deal-removal-track-a/recon.md`
- ADR: `ADR-121`

---

## 4. 弊害対策

- フロントとバックを同一 PR で合わせ、欠損フィールドでフロントが落ちないようにする。
- `deals` テーブルや `/deals` への導線は残すため、撤去範囲は dashboard 表示に限定する。

