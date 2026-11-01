# Phase 3 設計 — 試験の表の写し 13 件を 0 に戻す

- 下調べ: docs/handoff/test-schema-dup-ops-case/recon.md
- 実装の指示: docs/handoff/test-schema-dup-ops-case/card.md（変更前後・分岐・手順はカードが正）
- 対象 ADR: ADR-121（docs/specs/process-hardening/design-pillar3.md）
- KGI（○×）: PR の HEAD で `python3 scripts/check_test_schema_dup.py --check-inventory docs/specs/process-hardening/pillar3-inventory.md <sha>` が exit 0（MEASURED files=29 tables=71）

## 外部・過去事例の参照と我々への応用

- 外部事例は使わない。理由: 新しい技術の選択が無く、本リポジトリの決まり（design-pillar3.md）と手本（backend/tests/conftest.py:192-202・backend/tests/test_permission_resolution_pg.py）がそのまま当てはまるため。
- 過去事例: INBOX_BADGE の作り物の表を conftest.py に集めた件（conftest.py:192-202）。同じ形を ops の試験に当てる。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 写しが記録表と同じ数に戻る | PR の HEAD で `--check-inventory` が exit 0、MEASURED files=29 tables=71 |
| 3 つの試験ファイルに表の作り方が残らない | BASE_SHA・HEAD_SHA を付けた `python3 scripts/check_test_schema_dup.py` が exit 0 で、3 ファイルとも HEAD=0 |
| CI の照合の段が緑 | PR の「test-schema-dup gate」が success |
| 試験の数が直す前と同じ | `pytest -o addopts="" --collect-only -q` の collected が S と PR の HEAD で同じ |
| 試験が実際の PG で通る | PR の test.yml の backend の試験が success |
| 作り物の表の中身が変わらない | conftest.py の 8 つの定数が S の 12 行の文字列と 1 文字ずつ一致 |
| 触る範囲が守られる | 変わったファイルが conftest.py と 3 つの試験の 4 つだけ（クラウドでは台帳を commit しない） |

## 技術 How・KPI

- ops の 2 ファイル（12 件）: 作り物の表の作り方を backend/tests/conftest.py の定数にして import する。中身は変えない。bootstrap にしない理由は、試験が「superuser でない持ち主の表」を前提にしているため（recon の test_ops_case_db.py:144-152・509-518・686-699）。
- test_rls_auth_audit.py（1 件）: 本番の表の写しなので、本物の作り方 bootstrap_tenant_schema(admin_engine, 991) に置き換える。GRANT 3 行は残す。
- KPI: 照合の MEASURED の件数（84 → 71）。

## 弊害・トレードオフ

- test_rls_auth_audit.py は本物のテナントを作るので遅くなる（bootstrap を使うほかの 8 ファイルと同じ重さ）。
- conftest.py に定数が 8 つ増える（集約先の決まりどおり）。
- 記録表を作り直して 84 件を正にする案は採らない（§1「コピーはこれ以上増やさない」に反する）。

## 計画票

| 段 | 中身 | 担当 |
|---|---|---|
| 1 | このカード・設計・下調べの書類 PR | Opus |
| 2 | PO の実装承認 | PO |
| 3 | カードどおりの実装と push（PR は作らない） | Sonnet（クラウド） |
| 3.5 | PR を手元で shingo-cc 名義で作る | Opus |
| 4 | CI の確かめと審査、合流 | Opus・審査役 |

## 継続・維持の仕組み

- 守り手: .github/workflows/test-schema-dup-gate.yml
- 見張り .github/workflows/test-schema-dup-gate.yml の照合の段が、次に写しが増えたときに赤を出す（今回それで見つかった）。
- 見落としの再発防止: 設計担当は合流の前に、必須でない確かめの赤も全部読み、残す理由を PR に書く。
- 戻し方: 実装 PR を revert する。本番には触れない。
