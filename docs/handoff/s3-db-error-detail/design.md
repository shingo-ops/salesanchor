# 設計 — S3 例外の中身（SQL 文・入力値）を応答に出さない（db-error-detail）

**日付**: 2026-10-16　**根拠**: [recon.md](recon.md)（docs/handoff/s3-db-error-detail/recon.md）　**仕様書**: [docs/specs/db-error-detail/README.md](../../specs/db-error-detail/README.md)、KGI [docs/specs/db-error-detail/kgi.md](../../specs/db-error-detail/kgi.md)　**ADR**: 例外の応答内容を定めた ADR は無い（recon 冒頭）。GO は ADR-1003 の委任に基づく

## 1. 目的（利用者に見える変化）

- 保存が重複などで失敗したとき、画面に出る文から SQL 文・入力した値・表名・制約名が消え、「重複または制約違反」などの短い案内だけになる（recon §2、§5）。
- 取り込みの確定や ERP 出力が失敗したとき、応答に SQL 文と入力値が入らなくなる（取り込み画面は今も detail を使わず固定文言を出しているため、見た目は変わらない。recon §5）。
- 失敗の中身は backend のログにだけ残り、調査はこれまでどおりできる。
- ステータスコード（409・500）は変えない。

## 2. 変更前 → 変更後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| 409（IntegrityError 44 件） | `detail=f"重複または制約違反: {exc.orig}"` など | `detail="重複または制約違反"`（前置きだけ。末尾の `: ` も消す） |
| 500（Exception 15 件） | `detail=f"CONDITION_IMPORT_COMMIT_ERROR: {exc}"` など | `detail="CONDITION_IMPORT_COMMIT_ERROR"` など（前置きだけ） |
| ログ | 58 件はどこにも出さない | 共通関数で backend のログに例外の型・中身・スタックを残す |

共通関数は既存の DB 例外の正本 backend/app/routers/_utils.py（recon 冒頭）に足す。中身（実装はこのとおり）:

```python
def log_hidden_error(where: str, exc: BaseException) -> None:
    """応答に出さない例外の中身を backend のログにだけ残す（docs/specs/db-error-detail/）。

    応答の detail には例外の文字列を入れない。SQL 文・入力値・制約名が含まれるため。
    """
    logger.error("%s: %s", where, exc, exc_info=exc)
```

各箇所の書き換えの型（rollback の行と順番はそのまま）:

```python
    except IntegrityError as exc:
        await db.rollback()
        log_hidden_error("conditions.create_condition_alias", exc)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="重複または FK 違反")
```

- `where` は「ファイル名（.py 抜き）.関数名」。
- 既に logger.exception を呼んでいる buyback_prices.py:692 は log_hidden_error を足さず、detail から `{exc}` を外すだけ。
- erp.py:144-154 は erp_sync_logs への `str(e)` の保存（DB 内の記録。応答ではない）はそのまま。log_hidden_error を raise の直前に足し、detail を `"ERP エクスポート失敗"` にする。
- `from exc` / `from e` がある箇所は残す。
- import は `from app.routers._utils import log_hidden_error`（ルーターは同じパッケージ）。

## 3. 触るファイルと変更内容

| ファイル | 変更 |
|---|---|
| backend/app/routers/_utils.py | `log_hidden_error` を足す（§2） |
| recon 付録の 59 件がある 28 ファイル（backend/app/routers/*.py） | 各箇所を §2 の型に替える。import を 1 行足す |
| backend/tests/test_no_exception_text_in_http_detail.py | 新規。見張り（§5 T1） |
| backend/tests/test_db_exceptions.py | `log_hidden_error` の試験を足す（§5 T2） |
| backend/tests/test_super_admin_unit_ignore_phrases.py | :119-120 の重複 409 の試験に、応答に入力値・`[SQL`・`DETAIL` が無いことの assert を足す（§5 T3） |

触らない: 対象外の 48 件（外部 API・入力検査の文言）、backend/app/main.py の全体ハンドラ、database.py の echo、frontend、migrations、deploy.yml、nginx。

## 4. 対象外とその理由

- 外部 API（FedEx・Meta・LLM・PokeAPI・Google）の失敗文言 48 件: DB の中身を含まない（recon §1）。外部サービスの文言を出す是非は別の判断になる。
- ログに SQL・入力値が残ること: PO 承認の範囲（「詳しい中身は記録（ログ）にだけ残す」）。ログの保存先・保持期間は変えない。
- 画面の文言の多言語化（ADR-027）: 今回は backend の文言の短縮だけで、frontend の表示の仕組みは変えない。既存の日本語の前置きが残るのは変更前と同じ。

## 5. 試験（KGI との対応）

- T1（K1）backend/tests/test_no_exception_text_in_http_detail.py: backend/app の *.py を全部 AST で読み、except 節（型が IntegrityError・Exception・BaseException・SQLAlchemyError・DBAPIError・StatementError のいずれかを含むもの、または型なし）の中で、`HTTPException(...)` か `JSONResponse(...)` の `detail` / `content` の式の中に except の変数名（例 `exc`・`e`）が現れたら、その file:line を集めて `assert not found`。除外集合は持たない。手本は backend/tests/test_time_handling.py:30-50 と backend/tests/test_tcg_mirror.py:56-80。**変更前のコードでこの試験が 59 件を見つけて落ちることを先に確かめ、出力を保存する。**
- T2（K1 の補助）backend/tests/test_db_exceptions.py: `log_hidden_error("x.y", ValueError("secret"))` が caplog に ERROR で "x.y" と "secret" を残すこと。
- T3（K2）backend/tests/test_super_admin_unit_ignore_phrases.py の重複 409 試験に足す: `phrase not in dup.text`、`"[SQL" not in dup.text`、`"DETAIL" not in dup.text`、`dup.json()["detail"] == "重複または制約違反"`（実際の前置きは実装時に super_admin_unit_ignore_phrases.py の該当行で確かめて合わせる）。実 PostgreSQL が要るため CI で走る（pg_client は migration 全体を適用するため手元では走らせない）。変更前の応答に入力値と DETAIL が入ることは recon §2 の実物で確認済みのため、変更前の赤は T3 では取らない。CI でこの試験が skip されていないことを PR の CI ログ（`-rs` の skip 一覧か、試験名の PASSED）で確かめる。skip されていたら K2 は未達として止まる。

既存の試験はすべて緑のまま（ローカルで T1・T2 と、59 件のファイルに対応する既存試験を走らせる。全件は CI）。

## 6. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1: DB 例外を捕まえる except 節で、例外の中身を応答に入れる箇所が 0 | T1 が CI で緑。変更前のコードで T1 が 59 件を見つけて赤になった出力を PR に記す |
| K2: 重複エラーの応答に SQL 文・入力値・DB の詳細が無い | T3 が CI で緑（skip ではないことを CI ログで確認） |
| K3: 反映後、エラーが増えない | 反映後の backend ログの Traceback・ERROR 件数と nginx 記録の 5xx 件数が、反映前の基準（prod-baseline.txt と同じ方法で反映直前に取る）から増えない。増えたら中身を見て本変更が原因か切り分ける |
| 既存機能 | CI の Backend Tests 全件緑 |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| 59 件の書き換えで 1 件でも取りこぼす | T1 が全ファイルを毎回検査する。取りこぼしは CI で赤になる |
| 書き換えで rollback の順番や `from exc` を壊す | §2 の型を守る。差分を Opus が全件読む |
| 画面で原因が分かりにくくなる | 前置き（「重複または制約違反」等）は残す。詳細はログで調べる |
| ログに入力値が残る | PO 承認の範囲（§4） |

## 8. 戻し方

PR を Revert して再デプロイ。DB・設定の変更は無い。

## 9. 外部・過去事例の参照と我々への応用

- SQLAlchemy 2.0 の StatementError（IntegrityError の親）は文字列化すると SQL 文と引数を含む。これは手元の実物で確認した（recon §2、sqlalchemy 2.0.38）。Context7 は月間上限で使えず、公式文書の出典は【未確認】。本設計は実物の出力だけを根拠にする。
- 社内の過去事例: backend/app/routers/_utils.py の handle_db_exceptions と backend/app/main.py の全体ハンドラは既に「中身はログ・応答は固定文言」で動いている。本件はこの方式を個別の except 節にも広げる。
- 数値を伴う外部の導入事例は使わない（本件は社内の実物と CI の試験で判定できるため）。

## 維持の仕組み

- 守り手: backend/tests/test_no_exception_text_in_http_detail.py（CI の Backend Tests で毎回 backend/app 全体を検査し、DB 例外の中身を応答に入れる書き方が 1 件でも増えたら赤にする）。
- 応答に出さない例外の記録は backend/app/routers/_utils.py の `log_hidden_error` 1 つに集める（写しを作らない）。
- 重複時の応答に SQL・入力値が無いことは T3 が実 PostgreSQL で毎回確かめる。
