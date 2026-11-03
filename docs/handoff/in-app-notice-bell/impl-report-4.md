# impl-report-4

## 結果: 完了

CI の test-schema-dup gate が `backend/tests/test_user_notices.py` の CREATE TABLE 8 件で落ちていた件を直した。

## 変更

- `backend/tests/conftest.py`: 表定義 8 件を `USER_NOTICE_DDL` に移し、`create_user_notice_tables(conn)` を追加（conftest.py は gate の除外対象で、決まり §4-3 の集約先）。
- `backend/tests/test_user_notices.py`: 自前の `DDL` を消し、`maker` フィクスチャが `create_user_notice_tables` を呼ぶ形にした。
- 試験の中身・期待値・製品コードは変更なし。除外の追加・AS 構文は使っていない。
- 同じ表を使う他の試験（test_discord_outside_ticket_notice.py / test_realtime_topics.py）には CREATE TABLE も `DDL` の参照もなく、変更不要。

commit: `0550ab509`（枝 `release/in-app-notice-bell`、main は取り込んでいない）

## 検証

| 項目 | 結果 |
|---|---|
| `BASE_SHA=origin/main HEAD_SHA=HEAD python3 scripts/check_test_schema_dup.py` | 通過（test_user_notices.py: 0 → 0、「新規スキーマ複製なし(pass)」） |
| pytest（Python 3.12.3） 3 ファイル `--no-cov` | 49 通過・0 失敗 |
| ruff check（変更した 2 ファイル） | 通過（0 件） |
| ruff check（backend 全体） | 1 件: `backend/tcg_migration/scripts/write_mirror_once.py:334` F841。今回触っていない既存ファイルで、今回の変更とは無関係（未対応） |

注: gate は commit 済みの内容を見るため、commit 後に流した。
