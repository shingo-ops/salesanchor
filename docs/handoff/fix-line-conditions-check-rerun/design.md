# design: 再実行で制約を狭め直さないガード

recon: docs/handoff/fix-line-conditions-check-rerun/recon.md
対象ADR: ADR-1031・ADR-1035

## 方針
DROP の前に pg_get_constraintdef で現在の定義を取り、目的の値（19: promo_pack と single、20: booklet）を含めば RAISE NOTICE で skip。含まない・制約が無いときだけ従来の DROP → ADD → COMMENT。他の migration・runner・deploy.yml は触らない。

## 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K1 booklet の行がある状態で 19 → 20 を再実行してもエラー0・定義は booklet を含む | CI の PG テスト backend/tests/test_line_conditions_value_group_rerun_pg.py |
| K2 box/case/pack だけの状態から 19 を流すと広がる | 同上 |
| K3 マージ後の deploy が success で create_ai_ro_views.sql が流れる | Opus が deploy ログで確認 |

## 外部・過去事例の参照と我々への応用
過去事例: migrations/037 が同じ pg_get_constraintdef 判定で冪等にしている。同じ形に合わせた。外部事例は該当なし（社内 migration の再実行不具合のため）。

## 維持の仕組み
守り手: 人手で守る（今後 value_group に値を足す migration は、この2本と同じガード形にする。新しい仕組みは作らない）
