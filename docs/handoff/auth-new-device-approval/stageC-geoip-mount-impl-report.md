# ADR-1055 段C 直し: geoip つなぎ 実装報告

## 開始時
- `git rev-parse HEAD`（`git switch -C release/auth-geoip-backend-mount origin/release/auth-geoip-backend-mount` の後）: `b2261cca4946f3b8c9a47357d592fdcce10a40fe`（b2261cca4 で一致）
- `executor-preflight.sh` は流していない（クラウドでは GitHub API が使えないため Opus が免除）
- 実物の `scripts/blue-green-cutover.sh:94-96` は §2 の3行と同じ文字だった

## 変更
- `scripts/blue-green-cutover.sh`: `:96` の次に `--volume "${COMPOSE_PROJECT}_geoip:/geoip:ro" \` を1行追加
- 新規 `backend/tests/test_bg_cutover_volume_parity.py`（2試験: 名前つき置き場が0個でないこと／compose の backend の名前つき置き場が入れ替え手順に同じ行き先・同じ ro で1つずつあること）

## 確かめの環境（カードとの違い）
- システムの python は 3.12 ではなく py312-guard に止められたため、`python3.12 -m venv <scratchpad>/venv` を作り `pip install pyyaml pytest` を流した
- `pip install -r requirements.txt pytest-asyncio` は依存解決が終わらず（backtracking）中止した
- そのため conftest（app 全体を読む）と pyproject の addopts（xdist・cov）を外して流した。この試験は conftest を使わない
- コマンド: `cd backend && <venv>/bin/python -m pytest -q --noconftest -c /dev/null --rootdir=. tests/test_bg_cutover_volume_parity.py`
- CI の通常の形（`python -m pytest -q tests/...`）での確認は未実施（CI で確かめる）

## G-b: 1行を足す前（落ちた）
```
E       AssertionError: compose の backend にあるのに blue-green-cutover.sh に無い置き場: ['geoip']
E       assert not ['geoip']

tests/test_bg_cutover_volume_parity.py:55: AssertionError
=========================== short test summary info ============================
FAILED tests/test_bg_cutover_volume_parity.py::test_cutover_has_every_backend_named_volume
1 failed, 1 passed in 0.16s
```
（`attachments_data` は一致しており、`geoip` だけが出た）

## 1行を足した後（通った）
```
..                                                                       [100%]
2 passed in 0.13s
```
`bash -n scripts/blue-green-cutover.sh` も通った。

## git diff --stat origin/main（コード commit 時点）
```
 backend/tests/test_bg_cutover_volume_parity.py     | 57 +++++++++++++++
 .../stageC-geoip-mount-card.md                     | 85 ++++++++++++++++++++++
 scripts/blue-green-cutover.sh                      |  1 +
 3 files changed, 143 insertions(+)
```
（カード本体は元から枝にある。本報告の追加分は含まない）

## コード commit
`028955728`（active-work.d の未追跡ファイルは commit していない）

DONE
