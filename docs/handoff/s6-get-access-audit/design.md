# 設計 — S6 一覧の全件取得・CSV 出力（GET）を記録し、閲覧の大量取得を検知する（get-access-audit）

**日付**: 2026-10-17　**根拠**: [docs/handoff/s6-get-access-audit/recon.md](recon.md)　**仕様書**: [docs/specs/get-access-audit/README.md](../../specs/get-access-audit/README.md)、KGI [kgi.md](../../specs/get-access-audit/kgi.md)　**ADR**: data_access_events を定めた ADR は無い（recon 冒頭）。GO は ADR-1003 の委任に基づく

## 1. 目的（利用者に見える変化）

- 画面の見た目・動きは変わらない。
- 誰かが一覧の全件取得や CSV 出力をしたとき、「誰が・いつ・どこから・何を」が記録表 public.data_access_events に 1 行残る（いまは残らない。recon §1・§2）。
- 1 人が 10 分間に 500 回を超えて閲覧したとき、ログの警告と記録表の 1 行で分かるようになる（いまは書込だけを数えている。recon §1）。普段の最大は 1 接続元で 10 分 155 回（recon §2）なので、普段の使い方では鳴らない。

## 2. 変更前 → 変更後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| 全件取得・CSV 出力の GET（§3 の判定に当たるもの） | 記録なし | 応答が 400 未満なら data_access_events に event_type=`data_export` で 1 行 |
| 閲覧（GET）の回数 | 数えない | 利用者ごと 10 分の回数を Redis で数え、500 を超えた最初の 1 回だけ event_type=`bulk_read_alert` で 1 行＋logger.warning |
| 書込の記録・書込の大量検知 | data_write・bulk_export_alert | 変えない |

## 3. 実装（backend/app/middleware/audit.py だけを変える）

1. 定数（このファイルを唯一の正本にする）:

```python
# 一覧の全件取得・ファイル出力として記録する GET（docs/specs/get-access-audit/）
_EXPORT_PATH_SUFFIXES = ("/export", "/elogi-csv", "/download")
_EXPORT_PATHS = frozenset({
    "/api/v1/financials/orders",
    "/api/v1/companies/duplicates",
})
```

判定関数:

```python
def _is_export_get(method: str, path: str) -> bool:
    """全件取得・ファイル出力の GET か。"""
    if method != "GET":
        return False
    return path in _EXPORT_PATHS or path.endswith(_EXPORT_PATH_SUFFIXES)
```

（recon §3 の 16＋3＋2 本はすべてこれに当たり、§3 の対象外 5 本は当たらない。試験 T1 で確かめる。）

2. 閲覧の回数を数える関数（既存の `_check_and_record_bulk_export` と同じ方式。キーの接頭辞だけ分ける）:

```python
async def _count_read_and_check(user_email: str | None) -> bool:
    """閲覧（GET）の回数を利用者ごと 10 分で数え、閾値を超えた最初の 1 回だけ True。"""
    if not user_email:
        return False
    try:
        import hashlib

        from app.cache import get_redis
        r = get_redis()
        if not r:
            return False
        window = int(time.time()) // BULK_EXPORT_WINDOW_SEC
        email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
        key = f"bulk_read:{email_hash}:{window}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, BULK_EXPORT_WINDOW_SEC + 60)
        return count == BULK_EXPORT_MAX_CALLS + 1
    except Exception:
        logger.warning("閲覧回数の追跡に失敗")
        return False
```

閾値・窓は既存の `BULK_EXPORT_WINDOW_SEC`・`BULK_EXPORT_MAX_CALLS` を使う（写しを作らない）。

3. `dispatch` の書込の記録（:126-131）の後に足す:

```python
        # 閲覧の記録（S6: 全件取得・ファイル出力の GET と、閲覧の大量検知）
        if method == "GET" and status_code < 500:
            await self._record_read_access(
                request=request,
                status_code=status_code,
                duration_ms=duration_ms,
            )
```

4. `_record_read_access`（新規。例外は握りつぶし応答に影響させない＝既存 :224-225 と同じ）:
   - `user_email = _decode_jwt_email(...)`、`client_ip = get_client_ip(request)`。
   - `is_alert = await _count_read_and_check(user_email)`。True なら `logger.warning("大量閲覧検知: user=%s ip=%s path=%s", ...)` と event_type=`bulk_read_alert` の行を 1 行。
   - `_is_export_get(method, path)` かつ `status_code < 400` なら event_type=`data_export` の行を 1 行（is_alert と同じ要求なら 2 行目として別に入れる）。
   - どちらも当たらなければ DB に触らない（普段の GET は Redis の incr 1 回だけ）。
   - INSERT は既存 :202-223 と同じ列・同じ書き方。共通部分は `_insert_data_access(event_type, request, status_code, user_email, client_ip, duration_ms)` に切り出し、既存の `_record_data_access` もそれを使う（INSERT 文を 1 か所にする）。

5. モジュールの説明（:4-17）を実態に合わせる: data_access_events に「全書込（data_write）・書込の大量検知（bulk_export_alert）・全件取得/ファイル出力の GET（data_export）・閲覧の大量検知（bulk_read_alert）」。「バックグラウンドタスクで記録する」は「応答の生成後に記録する（失敗しても応答は変えない）」に直す。

触らない: migrations（列・型は今のままで入る。recon §1）、エンドポイント本体（件数の制限はしない。§4）、frontend、通知・遮断、60 日の削除。

## 4. 対象外とその理由

- 全件取得の件数を区切る（ページ送り）: /financials/orders は 2 画面が全件前提（recon §4）で画面の作り直しが要る。どれも権限必須・同じ会社の中だけ（原文）。今回は「誰が取ったか残す」ことで穴を塞ぐ。
- 検知時の通知（Discord 等）や遮断: 今の書込の検知にも無い（recon §1）。通知の仕組みを足すのは別の判断。
- 普段の GET すべての記録: 1 日 460〜1,900 件増え、記録表が数倍になる（recon §2）。全件取得・出力に限る。
- migrations/071 のコメント（event_type の例）: 危険パスのため触らない。正本の説明は audit.py に置く。

## 5. 試験（KGI との対応）

試験ファイル: backend/tests/test_get_access_audit.py（新規）。手本は test_client_ip.py:116-170（AsyncSessionLocal の差し替え）と test_security_hardening.py:419-476（Redis の差し替え）。

- T1（K1）`_is_export_get`: recon §3 の全件取得・出力 21 本（{order_id}・{task_id} は具体値で）が True、対象外 5 本・POST の /export・GET の普通の一覧（例 /api/v1/companies）が False。
- T2（K1）ミドルウェア経由: 小さな FastAPI に AuditMiddleware を付け、Bearer（email 入りの未署名 JWT 形式）で GET /api/v1/suppliers/export（200）→ 捕まえた INSERT の params に event_type=`data_export`・method=GET・path・user_email が入る。403 を返す出力路では data_export が入らない。普通の GET（/api/v1/companies、200）では INSERT が 0 回。
- T3（K2）`_count_read_and_check`: incr が 500→False、501→True、502→False。email 無し→False（incr を呼ばない）。Redis 不通→False。初回 TTL=窓+60。キーが `bulk_read:` で始まる（書込の `bulk_access:` と別）。
- T4（K2）ミドルウェア経由: Redis の incr が 501 を返す状態で GET /api/v1/companies → INSERT が 1 回で event_type=`bulk_read_alert`。
- T5（既存を壊さない）POST は従来どおり data_write で記録される（既存 test_client_ip.py の t6 と TestBulkExportDetection が緑のまま）。

**変更前のコードで T1〜T4 が落ちる（関数が無い・INSERT が 0）ことを先に確かめ、出力を保存する。**

## 6. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1: 全件取得・ファイル出力の GET が成功したら、誰が・いつ・何を取ったかが記録表に 1 行残る | T1・T2 が CI で緑（変更前は赤）。反映後、本番の data_access_events に event_type=data_export の行が現れるかを観測（利用は 7 日で 12 回程度＝観測は反映後の利用待ち） |
| K2: 1 人が 10 分に 500 回を超えて閲覧したら、警告と記録表の 1 行が残る（1 窓 1 回） | T3・T4 が CI で緑（変更前は赤） |
| K3: 閲覧の回数を数える処理が本番で失敗していない | 反映後、GET が 1 件以上通り、backend ログの「閲覧回数の追跡に失敗」が 0 件。Redis のキーを直接数える方法は安全装置に止められたため使わない（Redis 未設定時の素通りとの区別は未確認。kgi.md） |
| K4: 反映後、エラーが増えず、普段の使い方で大量閲覧の誤検知が出ない | 反映後の backend の Traceback・ERROR と nginx の 5xx が反映前の基準から増えない。反映後の観測時間内で bulk_read_alert が 0 行 |
| 既存機能 | CI の Backend Tests 全件緑 |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| 毎回の GET に Redis の incr 1 回が増え、遅くなる | 同じ VPS 内の Redis で 1 往復。既存の書込でも同じことをしている。K4 で 5xx・エラーを見る。Redis 不通でも応答は止めない（fail-open） |
| 普段の画面の自動更新で誤検知が出る | 普段の最大は 1 接続元 10 分 155 回（閾値 500 の約 3 割）。出ても警告と 1 行だけで、遮断はしない |
| 記録表が膨らむ | 全件取得・出力は 7 日 12 回程度、警告は 1 窓 1 行。60 日で消える |
| `/download` で終わる新しい GET が自動で記録対象になる | 意図どおり（ファイル出力の記録漏れを防ぐ側に倒す）。T1 で現在の対象を固定する |
| JWT の email は署名検証なし | 既存と同じくログ用途。認可には使わない |

## 8. 戻し方

PR を Revert して再デプロイ。DB・設定の変更は無い。記録された行は 60 日で自動的に消える。

## 9. 外部・過去事例の参照と我々への応用

- 社内の過去事例: 同じファイルの書込の大量検知（Redis で 10 分の固定窓・fail-open）がそのまま手本。キーの接頭辞と記録の種類だけ分ける。
- 数値を伴う外部の導入事例は使わない（本件は社内の実測値＝Loki の 7 日分と CI の試験で判定できるため）。Context7 は月間上限で使えないため、redis.asyncio の incr・expire の仕様は既存コード（audit.py:86-88）と既存試験の実績を根拠にする。

## 維持の仕組み

- 守り手: backend/tests/test_get_access_audit.py（CI の Backend Tests で毎回。記録対象の判定・大量閲覧の検知・ミドルウェア経由の記録を確かめる）。
- 記録対象の判定と閾値は backend/app/middleware/audit.py の定数 1 か所（写しを作らない）。INSERT 文も 1 か所。
