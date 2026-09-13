"""
MIG-05 Task 3: 単発ミラー書き出しスクリプト（Celery・ワーカー不使用）

使用方法:
  python -m tcg_migration.scripts.write_mirror_once \
    --sa-key ~/.secrets/sales-ops-with-claude-71f7bf2fd932.json \
    [--list-only]             # Drive 全件列挙のみ（書き込みなし）
    [--ping-only]             # A1 を読むだけ
    [--write-from-db]         # ローカル DB から実データを書き出す
    [--db-url URL]            # DB URL（省略時はデフォルトローカル）
    [--get-user-email-from-sheet <ID>]  # 指定シートのオーナーメールを取得

書き込み先は MIRROR_SPREADSHEET_ID に固定。--spreadsheet-id 引数は存在しない。
シート自動作成は一切行わない（SA の Drive quota=0 が実測で確認済み。
コード上も create 経路を持たない）。

安全ガード:
  1. spreadsheets.get で取得した spreadsheetId が MIRROR_SPREADSHEET_ID と
     完全一致することをコード上で検証。不一致なら即 SystemExit。
  2. gspread.exceptions.SpreadsheetNotFound が発生した場合はスキップ終了
     （シート作成は行わない）
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

MIRROR_SPREADSHEET_ID = "1IBIpge6Qz2arq93OHmRFnCGBMj2kVhrgEjtY8c5ecus"

DEFAULT_DB_URL = "postgresql+psycopg2://myapp_user:password@localhost:5432/myapp_db"

MIRROR_TABS = [
    "[MIRROR] 商品マスタ",
    "[MIRROR] 検索キーワード",
    "[MIRROR] 仕入元",
    "[MIRROR] 仕入元サマリー",
    "[MIRROR] DB構造",
]

README_BODY = (
    "このシートはシステム所有（salesanchor-drive サービスアカウント）です。\n"
    "消えても DB から再生成可能です。手動編集不可。\n\n"
    "生成元: SalesAnchor backend / MIG-05 Task 3\n"
    "更新: 日次（深夜 02:30 JST）またはデプロイ時\n"
)

# DB 構造タブ: テーブル日本語説明（旧シートとの対応付き）
DB_TABLE_DESCRIPTIONS = {
    "tcg_suppliers":            ("仕入元マスタ",        "旧: 仕入元マスタ シート"),
    "supplier_channels":        ("仕入元チャネル",       "旧: 仕入元マスタ シート（LINE ID 列）"),
    "tcg_products":             ("商品マスタ",           "旧: 商品マスタV2 シート"),
    "products_logistics":       ("商品物流情報",         "旧: 商品マスタV2 シート（物流列）"),
    "product_search_keywords":  ("商品検索キーワード",   "旧: 商品マスタV2 列内"),
    "product_exclude_keywords": ("商品除外キーワード",   "旧: 商品マスタV2 列内"),
    "units":                    ("単位マスタ",           "旧: 単位マスタ シート"),
    "unit_aliases":             ("単位別名",             "旧: 単位マスタ シート（別名列）"),
    "conditions":               ("状態マスタ",           "旧: 状態マスタ シート"),
    "condition_aliases":        ("状態別名",             "旧: 状態マスタ シート（別名列）"),
    "source_messages":          ("取込元メッセージ",     "新規（LINEエクスポート取込）"),
    "extraction_jobs":          ("抽出ジョブ",           "新規（Gemini 抽出）"),
    "extraction_items":         ("抽出アイテム",         "新規（Gemini 抽出結果）"),
    "analysis_results":         ("照合結果",             "新規（商品マスタ照合）"),
    "unparsed_lines":           ("未解析行",             "新規（解析不能行の保存）"),
    "item_notes":               ("アイテムメモ",         "旧: 商品マスタV2 メモ列"),
    "import_jobs":              ("インポートジョブ",     "新規（取込バッチ管理）"),
    "audit_log":                ("監査ログ",             "新規（操作履歴）"),
}


# ---------------------------------------------------------------------------
# 認証
# ---------------------------------------------------------------------------

def _build_creds(sa_key_path: str) -> Credentials:
    return Credentials.from_service_account_file(sa_key_path, scopes=SCOPES)


# ---------------------------------------------------------------------------
# Drive API
# ---------------------------------------------------------------------------

def list_all_sheets(creds: Credentials) -> list[dict]:
    drive = build("drive", "v3", credentials=creds)
    files: list[dict] = []
    page_token = None
    while True:
        resp = drive.files().list(
            q="mimeType='application/vnd.google-apps.spreadsheet'",
            fields="nextPageToken, files(id, name, createdTime, modifiedTime, owners)",
            pageToken=page_token,
        ).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def list_permissions(creds: Credentials, spreadsheet_id: str) -> dict:
    drive = build("drive", "v3", credentials=creds)
    resp = drive.permissions().list(
        fileId=spreadsheet_id,
        fields="permissions(id, emailAddress, role, type, displayName)",
    ).execute()
    print(f"[permissions.list on {spreadsheet_id}]")
    print(json.dumps(resp, ensure_ascii=False, indent=2))
    return resp


# ---------------------------------------------------------------------------
# spreadsheetId 完全一致検証
# ---------------------------------------------------------------------------

def verify_spreadsheet_id(gc: Any, spreadsheet_id: str) -> tuple[Any, dict]:
    try:
        sh = gc.open_by_key(spreadsheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        print(
            f"[ERROR] spreadsheetId={spreadsheet_id!r} のシートが見つかりません。"
            " シートの自動作成は行いません。",
            file=sys.stderr,
        )
        sys.exit(1)

    meta = sh.fetch_sheet_metadata()
    actual_id = meta["spreadsheetId"]
    if actual_id != spreadsheet_id:
        print(
            f"[ERROR] spreadsheetId 不一致: 期待={spreadsheet_id!r} 実際={actual_id!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[VERIFY] spreadsheets.get → spreadsheetId={actual_id}")
    print(f"[VERIFY]                  → title={meta['properties']['title']}")
    print("[VERIFY] OK — ID 一致")
    return sh, meta


# ---------------------------------------------------------------------------
# DB 接続ヘルパー
# ---------------------------------------------------------------------------

def _parse_db_url(url: str) -> dict:
    url = url.replace("postgresql+psycopg2://", "").replace("postgresql://", "")
    userinfo, hostinfo = url.split("@", 1)
    user, password = userinfo.split(":", 1) if ":" in userinfo else (userinfo, "")
    hostport, dbname = hostinfo.rsplit("/", 1) if "/" in hostinfo else (hostinfo, "")
    host, port = hostport.rsplit(":", 1) if ":" in hostport else (hostport, "5432")
    return dict(host=host, port=int(port), user=user, password=password, dbname=dbname)


def _db_connect(db_url: str) -> Any:
    import psycopg2
    return psycopg2.connect(**_parse_db_url(db_url))


# ---------------------------------------------------------------------------
# DB クエリ: 各タブデータ取得
# ---------------------------------------------------------------------------

def _fetch_products(cur: Any) -> tuple[list[str], list[list]]:
    cur.execute("""
        SELECT
            p.code         AS "商品コード",
            p.japanese_title AS "商品名（日本語）",
            p.release_date AS "発売日",
            p.category_class AS "カテゴリ",
            p.required_output_value AS "解析出力値",
            CASE WHEN p.is_active THEN '有効' ELSE '無効' END AS "状態"
        FROM tcg_products p
        ORDER BY p.code
    """)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    data = [[str(v) if v is not None else "" for v in row] for row in rows]
    return headers, data


def _fetch_keywords(cur: Any) -> tuple[list[str], list[list]]:
    cur.execute("""
        SELECT
            'search'       AS "種別",
            p.code         AS "商品コード",
            p.japanese_title AS "商品名",
            k.keyword      AS "キーワード",
            k.position     AS "順序"
        FROM product_search_keywords k
        JOIN tcg_products p ON p.id = k.product_id
        UNION ALL
        SELECT
            'exclude',
            p.code,
            p.japanese_title,
            k.keyword,
            k.position
        FROM product_exclude_keywords k
        JOIN tcg_products p ON p.id = k.product_id
        ORDER BY 1, 2, 5
    """)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    data = [[str(v) if v is not None else "" for v in row] for row in rows]
    return headers, data


def _fetch_suppliers(cur: Any) -> tuple[list[str], list[list]]:
    cur.execute("""
        SELECT
            s.code             AS "仕入元コード",
            s.name             AS "仕入元名",
            sc.channel         AS "チャネル",
            sc.external_id     AS "外部ID（LINE ID等）",
            CASE WHEN sc.is_active THEN '有効' ELSE '無効' END AS "チャネル状態",
            CASE WHEN s.is_active THEN '有効' ELSE '無効' END AS "仕入元状態"
        FROM tcg_suppliers s
        LEFT JOIN supplier_channels sc ON sc.supplier_id = s.id
        ORDER BY s.code, sc.channel
    """)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    data = [[str(v) if v is not None else "" for v in row] for row in rows]
    return headers, data


def _fetch_supplier_summary(cur: Any) -> tuple[list[str], list[list]]:
    cur.execute("""
        SELECT
            s.code              AS "仕入元コード",
            s.name              AS "仕入元名",
            COUNT(DISTINCT ei.id)  AS "抽出件数",
            SUM(CASE WHEN ar.needs_review THEN 1 ELSE 0 END) AS "要確認",
            SUM(CASE WHEN ar.pid_resolved = FALSE THEN 1 ELSE 0 END) AS "商品ID未解決",
            SUM(CASE WHEN ar.unit_resolved = FALSE THEN 1 ELSE 0 END) AS "単位未解決",
            SUM(CASE WHEN ar.pid_resolved = FALSE AND ar.unit_resolved = FALSE
                     THEN 1 ELSE 0 END) AS "両方未解決(N&U)"
        FROM tcg_suppliers s
        LEFT JOIN supplier_channels sc ON sc.supplier_id = s.id
        LEFT JOIN source_messages sm ON sm.supplier_channel_id = sc.id
        LEFT JOIN extraction_jobs ej ON ej.source_message_id = sm.id
        LEFT JOIN extraction_items ei ON ei.extraction_job_id = ej.id
        LEFT JOIN analysis_results ar ON ar.extraction_item_id = ei.id
        GROUP BY s.code, s.name
        ORDER BY s.code
    """)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    data = [[str(v) if v is not None else "" for v in row] for row in rows]
    return headers, data


def _fetch_db_structure(cur: Any) -> tuple[list[str], list[list]]:
    cur.execute("""
        SELECT
            t.table_name       AS "テーブル名",
            c.column_name      AS "カラム名",
            c.data_type        AS "データ型",
            c.character_maximum_length AS "文字数上限",
            c.is_nullable      AS "NULL許容",
            c.column_default   AS "デフォルト値"
        FROM information_schema.tables t
        JOIN information_schema.columns c
            ON c.table_name = t.table_name AND c.table_schema = t.table_schema
        WHERE t.table_schema = 'public'
          AND t.table_name IN (
            'tcg_suppliers','supplier_channels','tcg_products',
            'products_logistics','product_search_keywords','product_exclude_keywords',
            'units','unit_aliases','conditions','condition_aliases',
            'source_messages','extraction_jobs','extraction_items',
            'analysis_results','unparsed_lines','item_notes','import_jobs','audit_log'
          )
        ORDER BY t.table_name, c.ordinal_position
    """)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    # DB構造タブ: 先頭に日本語説明・旧シート対応を追加
    extra_header = ["テーブル日本語名", "旧シート対応"]
    full_headers = headers + extra_header
    data: list[list] = []
    for row in rows:
        table = str(row[0]) if row[0] else ""
        desc_ja, old_sheet = DB_TABLE_DESCRIPTIONS.get(table, ("", ""))
        data.append([str(v) if v is not None else "" for v in row] + [desc_ja, old_sheet])
    return full_headers, data


# ---------------------------------------------------------------------------
# Sheets 書き込みヘルパー
# ---------------------------------------------------------------------------

def _get_or_add_worksheet(sh: Any, title: str, rows: int = 500, cols: int = 30) -> Any:
    existing = {ws.title: ws for ws in sh.worksheets()}
    if title in existing:
        ws = existing[title]
        # 必要行数が現在のグリッドを超える場合はリサイズ
        current_rows = ws.row_count
        if rows > current_rows:
            ws.resize(rows=rows, cols=max(cols, ws.col_count))
        return ws
    return sh.add_worksheet(title=title, rows=rows, cols=cols)


def _write_tab(sh: Any, title: str, headers: list[str], data: list[list], now_iso: str) -> int:
    needed_rows = len(data) + 10
    ws = _get_or_add_worksheet(sh, title, rows=max(500, needed_rows), cols=max(30, len(headers) + 2))
    ws.clear()
    all_rows = [headers] + data
    ws.update(values=all_rows, range_name="A1")
    footer_row = len(all_rows) + 2
    ws.update(values=[[f"最終更新: {now_iso}  行数: {len(data)}"]], range_name=f"A{footer_row}")
    total = len(all_rows)  # header + data rows
    print(f"[WRITE] {title}: ヘッダ1行 + データ{len(data)}行 = 計{total}行")
    return total


# ---------------------------------------------------------------------------
# プレースホルダー書き出し（DB なし）
# ---------------------------------------------------------------------------

def write_mirror_placeholder_tabs(sh: Any) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    existing = {ws.title for ws in sh.worksheets()}

    ws_readme = _get_or_add_worksheet(sh, "READ ME", rows=30, cols=5)
    ws_readme.clear()
    ws_readme.update(values=[[README_BODY]], range_name="A1")
    ws_readme.update(values=[[f"最終更新: {now_iso}"]], range_name="A10")
    print("[WRITE] READ ME 完了")

    for tab in MIRROR_TABS:
        ws = _get_or_add_worksheet(sh, tab)
        ws.clear()
        ws.update(
            values=[[f"{tab} — 書き出し待ち（実データは Celery 日次タスクが書き込む）"]],
            range_name="A1",
        )
        ws.update(values=[[f"生成日時: {now_iso}"]], range_name="A2")
        print(f"[WRITE] {tab} 完了")


# ---------------------------------------------------------------------------
# 実データ書き出し（DB あり）
# ---------------------------------------------------------------------------

def write_mirror_from_db(sh: Any, db_url: str) -> dict[str, int]:
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = _db_connect(db_url)
    cur = conn.cursor()

    try:
        results: dict[str, int] = {}

        h, d = _fetch_products(cur)
        results["[MIRROR] 商品マスタ"] = _write_tab(sh, "[MIRROR] 商品マスタ", h, d, now_iso)

        h, d = _fetch_keywords(cur)
        results["[MIRROR] 検索キーワード"] = _write_tab(sh, "[MIRROR] 検索キーワード", h, d, now_iso)

        h, d = _fetch_suppliers(cur)
        results["[MIRROR] 仕入元"] = _write_tab(sh, "[MIRROR] 仕入元", h, d, now_iso)

        h, d = _fetch_supplier_summary(cur)
        results["[MIRROR] 仕入元サマリー"] = _write_tab(sh, "[MIRROR] 仕入元サマリー", h, d, now_iso)

        h, d = _fetch_db_structure(cur)
        results["[MIRROR] DB構造"] = _write_tab(sh, "[MIRROR] DB構造", h, d, now_iso)

        # READ ME 更新
        ws_readme = _get_or_add_worksheet(sh, "READ ME", rows=30, cols=5)
        ws_readme.clear()
        ws_readme.update(values=[[README_BODY]], range_name="A1")
        ws_readme.update(values=[[f"最終更新: {now_iso}"]], range_name="A10")
        print("[WRITE] READ ME 更新完了")

    finally:
        cur.close()
        conn.close()

    return results


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="TCG 単発ミラー書き出し（Celery 不使用）")
    parser.add_argument("--sa-key", required=True, help="SA キー JSON のパス")
    parser.add_argument("--list-only", action="store_true", help="Drive 全件列挙のみ")
    parser.add_argument("--ping-only", action="store_true", help="シート1!A1 を読むだけ")
    parser.add_argument("--write-from-db", action="store_true", help="ローカル DB から実データを書き出す")
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help=f"DB URL（デフォルト: {DEFAULT_DB_URL}）",
    )
    parser.add_argument(
        "--get-user-email-from-sheet",
        default="",
        metavar="SHEET_ID",
        help="指定シートの permissions.list を取得して終了",
    )
    args = parser.parse_args()

    creds = _build_creds(args.sa_key)
    gc = gspread.authorize(creds)

    if args.get_user_email_from_sheet:
        resp = list_permissions(creds, args.get_user_email_from_sheet)
        owner = next(
            (p.get("emailAddress") for p in resp.get("permissions", []) if p.get("role") == "owner"),
            None,
        )
        print(f"\n[OWNER EMAIL] {owner}")
        return

    if args.list_only:
        all_sheets = list_all_sheets(creds)
        now_str = datetime.now(timezone.utc).isoformat()
        print(f"\n[LIST] Drive 全件列挙 ({now_str}) — {len(all_sheets)} 件")
        for f in sorted(all_sheets, key=lambda x: x.get("modifiedTime", ""), reverse=True):
            owners = [o.get("emailAddress", "?") for o in f.get("owners", [])]
            print(f"  id={f['id']}  name={f['name']!r}  modified={f.get('modifiedTime','?')}  owners={owners}")
        return

    # ID 完全一致検証
    sh, meta = verify_spreadsheet_id(gc, MIRROR_SPREADSHEET_ID)

    if args.ping_only:
        ws = sh.get_worksheet(0)
        a1 = ws.acell("A1").value
        print(f"\n[PING] シート1!A1 = {a1!r}")
        print("[spreadsheets.get 生出力]")
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return

    if args.write_from_db:
        print(f"[DB] 接続: {args.db_url.replace(args.db_url.split(':')[2].split('@')[0], '***')}")
        results = write_mirror_from_db(sh, args.db_url)
        print(f"\n[DONE] 書き出し完了: {results}")
        print(f"[URL]  https://docs.google.com/spreadsheets/d/{MIRROR_SPREADSHEET_ID}")
        return

    # プレースホルダー書き出し
    write_mirror_placeholder_tabs(sh)
    print(f"\n[DONE] spreadsheetId={MIRROR_SPREADSHEET_ID}")
    print(f"[URL]  https://docs.google.com/spreadsheets/d/{MIRROR_SPREADSHEET_ID}")


if __name__ == "__main__":
    main()
