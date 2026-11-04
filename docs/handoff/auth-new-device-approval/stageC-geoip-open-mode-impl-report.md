# ADR-1055 段C 直し2 実装報告（geoip 開く命令の名前）

## 前提
- 開始時の HEAD: `git rev-parse HEAD` = `15283ddbabc0787b9567522ee56be85deb5950e0`（先頭 15283ddba で一致）
- executor-preflight.sh は流していない（クラウドでは GitHub API が使えないため Opus が免除）
- 実物の `geo.py:53` は §3-1 の「変更前」`new_reader = maxminddb.open_database(path, maxminddb.Mode.MMAP)` と同じ文字だった
- Python 3.12.3。backend の依存: `python3.12 -m venv` のうえ `pip install -r requirements.txt`、続けて `pip install -r requirements-dev.txt`（pytest 用）。`pip show maxminddb` → Version: 3.2.0（一致）
- conftest のまま動いた（`--noconftest` は不要）

## 変更
- `backend/app/auth/geo.py:53`: `maxminddb.Mode.MMAP` → `maxminddb.MODE_MMAP`（1行）
- `backend/tests/test_new_device_approval.py`: `test_geo_lookup_opens_database_and_formats_place` を1つ追加（試験側で maxminddb の名前は足していない。`open_database` だけ偽物に差し替え）

## G-b 落ちたとき（geo.py 未修正・試験だけ追加）
命令: `cd backend && python -m pytest -q tests/test_new_device_approval.py -k geo_lookup`
```
E       AssertionError: assert None == 'Phoenix, アメリカ合衆国'
E        +  where None = <function lookup at 0x7f38ea5db060>('4.249.21.1')
E        +    where <function lookup at 0x7f38ea5db060> = geo.lookup
tests/test_new_device_approval.py:1106: AssertionError
TOTAL                                                45977  45118     2%
FAIL Required test coverage of 60% not reached. Total coverage: 1.87%
FAILED tests/test_new_device_approval.py::test_geo_lookup_opens_database_and_formats_place
1 failed, 1 passed in 9.07s
```

## 通ったとき（§3-1 を直した後・同じ命令）
```
TOTAL                                                45977  45104     2%
FAIL Required test coverage of 60% not reached. Total coverage: 1.90%
2 passed in 8.87s
```
（終了コード 1 は一部の試験だけ流したことによる全体カバレッジ下限の未達で、試験の失敗ではない）

## git diff --stat origin/main（commit 前）
```
 backend/app/auth/geo.py                            |  2 +-
 backend/tests/test_new_device_approval.py          | 32 ++++++++
 .../stageC-geoip-open-mode-card.md                 | 85 ++++++++++++++++++++++
 3 files changed, 118 insertions(+), 1 deletion(-)
```
（本報告の追加分は commit 後に増える。最終 HEAD は commit・push 後の `git rev-parse HEAD`）

DONE
