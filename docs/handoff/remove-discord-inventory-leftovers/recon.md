# recon: Discord 在庫取り込みの残り3ファイルの削除

- 日付: 2026-10-02（設計担当 Opus が origin/main で確認）
- 関連: PR #3932（機能のコード・画面を削除）、PR #3937（表の DROP、PO 本人の GO #3937）
- ADR 検索: `git grep -il -e inventory_drift -e parse_review -e seed_discord_inbound docs/adr/` → 該当 ADR なし（機能の ADR は存在しない。休眠方針はコードコメント「ADR-146 案ア」のみで、文書は無い：`docs/handoff/remove-discord-inventory-parse/recon.md`）

## 対象ファイル

| ファイル | 中身 | 参照元 |
|---|---|---|
| backend/app/services/inventory_drift_detector.py | `public.v_supplier_parse_stats`（`parse_logs` の上のビュー）を読み、パースのずれを Discord に通知する関数 `check_drift_and_notify` | 0 件 |
| backend/app/schemas/parse_review.py | 解析レビュー API（#3932 で削除済み）の入出力スキーマ | 0 件 |
| scripts/seed_discord_inbound_from_api_analysis.py | `public.discord_inbound_messages` に CSV から投入するスクリプト | 0 件 |

## 事実

1. 参照元の確認（このブランチ、origin/main 起点）:
   `git grep -n -e inventory_drift_detector -e check_drift_and_notify -e "schemas.parse_review" -e "schemas import parse_review" -e seed_discord_inbound_from_api_analysis -- backend frontend scripts .github`
   → 3 ファイル自身を除くと 0 件。
2. `public.parse_logs` に書き込むコードは無い（唯一の書き手 inventory_parser.py は #3932 で削除済み）。`v_supplier_parse_stats` を定義するのは `migrations/20260604_130000_create_supplier_parse_stats_view.sql` のみ。
3. `public.discord_inbound_messages` / `public.parse_logs` / `v_supplier_parse_stats` は PR #3937 で DROP する。
4. 経緯: #3937 の準備中、実装担当の `git rm` が自動安全チェック（Irreversible Local Destruction）で拒否されたため、PO の直接指示を待った。PO 本人の指示（2026-10-02）:「inventory_drift_detector.py・schemas/parse_review.py・scripts/seed_discord_inbound_from_api_analysis.py の3ファイルを git で削除することを許可する」
