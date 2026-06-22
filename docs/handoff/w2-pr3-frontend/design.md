# design: W-2① PR-3 フロント（優先見込み客を「今やること」に表示）

**対象ADR**: ADR-138
**recon**: docs/handoff/w2-pr3-frontend/recon.md

## 目的

W-2② の read-only 優先見込み客リストを、Dashboard の「今やること」に攻め/守り分離で表示する。

## 変更方針

- 既存の `WeeklyAdvisorSection` は壊さず、攻め側として `PriorityProspectsSection` を追加する。
- 優先見込み客は `rank_score` の降順で backend から返る前提を活かし、frontend 側で再ソートしない。
- 表示は `lead/customer` 名、しやすさ%、見込み金額、rank score、属性内訳、サンプル少/金額未設定フラグ、[フォロー追加]。
- [フォロー追加] は W-1c の composer 体験を再利用し、`PATCH /leads/{id}` に `next_action` / `next_action_date` を送る。
- `lead_id` は backend 契約に従い lead detail 取得と follow-up 保存のキーとして使う。

## 外部・過去事例の参照と我々への応用

該当なし。今回は既存の Dashboard / W-1c composer をそのまま拡張するだけで、外部導入事例を参照しなくても要件を満たせるため。

## 受け入れ基準

| 基準 | 検証方法 |
| --- | --- |
| Dashboard で「今やること」に攻めカードが追加される | `frontend/tests-e2e/scene1-dashboard.spec.ts` の Playwright 実行で確認する |
| 攻めカードは `priority-prospects` の先頭順で並ぶ | mock した `GET /analytics/priority-prospects` の `rank_score` 順と画面表示を照合する |
| `しやすさ%` / `見込み金額` / `サンプル少` / `金額未設定` が表示される | Playwright で各ラベルと値のレンダリングをアサートする |
| `priority` 側の [フォロー追加] から `PATCH /leads/{id}` が送信される | 保存操作後の request payload を Playwright で検証する |
| 既存 W-1 守り 3 種は変更しない | 既存の表示・スナップショット・E2E の期待値が崩れないことを確認する |
| Playwright で dark mode でも表示と保存フローが通る | `ADR-067` の dark mode プロジェクトで E2E を実行する |
| Chromatic 用の story baseline が用意される | Storybook の対象 story が追加され、Chromatic でベースライン判定できることを確認する |

## テスト方針

- `frontend/tests-e2e/scene1-dashboard.spec.ts` で priority 表示と follow-up 保存を確認する。
- `GET /analytics/priority-prospects` と `GET /leads/{id}` を mock し、表示内容が deterministic になるようにする。
- `priority-prospect` の UI では `rank_score` と `ease_pct` を画面上で確認できるようにする。
