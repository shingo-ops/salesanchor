"""
MIG-05 Task 3: 単発ミラー書き出しスクリプト（Celery・ワーカー不使用）

使用方法:
  python -m tcg_migration.scripts.write_mirror_once \
    --sa-key ~/.secrets/sales-ops-with-claude-71f7bf2fd932.json \
    [--list-only]             # Drive 全件列挙のみ（書き込みなし）
    [--ping-only]             # A1 を読むだけ
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

# 書き込み先固定 ID（変更はコードレビュー + PR 承認が必要）
MIRROR_SPREADSHEET_ID = "1IBIpge6Qz2arq93OHmRFnCGBMj2kVhrgEjtY8c5ecus"

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


# ---------------------------------------------------------------------------
# 認証
# ---------------------------------------------------------------------------

def _build_creds(sa_key_path: str) -> Credentials:
    return Credentials.from_service_account_file(sa_key_path, scopes=SCOPES)


# ---------------------------------------------------------------------------
# Drive API: 全件列挙
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


# ---------------------------------------------------------------------------
# permissions
# ---------------------------------------------------------------------------

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
# spreadsheetId 完全一致検証（シート作成は絶対に行わない）
# ---------------------------------------------------------------------------

def verify_spreadsheet_id(gc: Any, spreadsheet_id: str) -> Any:
    """
    gspread クライアントで指定 ID のシートを開き、
    返ってきた spreadsheetId が引数と完全一致することを確認する。

    - シートが存在しない場合: SpreadsheetNotFound で失敗（作成しない）
    - ID 不一致の場合: SystemExit(1)
    """
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
# タブ書き出し（DB接続なし: プレースホルダー）
# ---------------------------------------------------------------------------

def write_mirror_placeholder_tabs(sh: Any) -> None:
    """
    DB 接続なしでタブ構造とプレースホルダーを書き出す。
    実データは Celery タスク (app.tasks.tcg_mirror) が書き込む。
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    existing = {ws.title for ws in sh.worksheets()}

    # READ ME
    if "READ ME" not in existing:
        ws_readme = sh.add_worksheet(title="READ ME", rows=30, cols=5)
    else:
        ws_readme = sh.worksheet("READ ME")
    ws_readme.clear()
    ws_readme.update(values=[[README_BODY]], range_name="A1")
    ws_readme.update(values=[[f"最終更新: {now_iso}"]], range_name="A10")
    print("[WRITE] READ ME 完了")

    # [MIRROR] 5タブ
    for tab in MIRROR_TABS:
        if tab not in existing:
            ws = sh.add_worksheet(title=tab, rows=300, cols=30)
        else:
            ws = sh.worksheet(tab)
        ws.clear()
        ws.update(
            values=[[f"{tab} — 書き出し待ち（実データは Celery 日次タスクが書き込む）"]],
            range_name="A1",
        )
        ws.update(values=[[f"生成日時: {now_iso}"]], range_name="A2")
        print(f"[WRITE] {tab} 完了")


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="TCG 単発ミラー書き出し（Celery 不使用）")
    parser.add_argument("--sa-key", required=True, help="SA キー JSON のパス")
    parser.add_argument("--list-only", action="store_true", help="Drive 全件列挙のみ")
    parser.add_argument("--ping-only", action="store_true", help="A1 を読むだけ")
    parser.add_argument(
        "--get-user-email-from-sheet",
        default="",
        metavar="SHEET_ID",
        help="指定シートの permissions.list を取得して終了",
    )
    args = parser.parse_args()

    creds = _build_creds(args.sa_key)
    gc = gspread.authorize(creds)

    # --get-user-email-from-sheet
    if args.get_user_email_from_sheet:
        resp = list_permissions(creds, args.get_user_email_from_sheet)
        owner = next(
            (p.get("emailAddress") for p in resp.get("permissions", []) if p.get("role") == "owner"),
            None,
        )
        print(f"\n[OWNER EMAIL] {owner}")
        return

    # --list-only
    if args.list_only:
        all_sheets = list_all_sheets(creds)
        now_str = datetime.now(timezone.utc).isoformat()
        print(f"\n[LIST] Drive 全件列挙 ({now_str}) — {len(all_sheets)} 件")
        for f in sorted(all_sheets, key=lambda x: x.get("modifiedTime", ""), reverse=True):
            owners = [o.get("emailAddress", "?") for o in f.get("owners", [])]
            print(
                f"  id={f['id']}"
                f"  name={f['name']!r}"
                f"  modified={f.get('modifiedTime','?')}"
                f"  owners={owners}"
            )
        return

    # ID 完全一致検証（シート作成なし）
    sh, meta = verify_spreadsheet_id(gc, MIRROR_SPREADSHEET_ID)

    if args.ping_only:
        ws = sh.get_worksheet(0)
        a1 = ws.acell("A1").value
        print(f"\n[PING] シート1!A1 = {a1!r}")
        print("[spreadsheets.get 生出力]")
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return

    # タブ書き出し
    write_mirror_placeholder_tabs(sh)

    print(f"\n[DONE] spreadsheetId={MIRROR_SPREADSHEET_ID}")
    print(f"[URL]  https://docs.google.com/spreadsheets/d/{MIRROR_SPREADSHEET_ID}")


if __name__ == "__main__":
    main()
