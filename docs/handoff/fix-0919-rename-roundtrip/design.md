# 設計: 20260919_015000 の無効化（ADR-1007 決定2の適用）

状態: PO 承認済み（カード「y」、2026-10-17）。マージは PO の「GO #番号」が要る（ADR-136）。GO待ち。
事実: docs/handoff/fix-0919-rename-roundtrip/recon.md
関連 ADR: ADR-1007（決定2）、ADR-155、ADR-1005。

## 1. 目的
全件実行のたびに line_* 4表が約5秒消える往復 RENAME を止める。

## 2. 変更（これだけ）
|ファイル|変更|
|---|---|
|migrations/20260919_015000_fix_view_to_table_rename.sql|DO ブロックを RAISE NOTICE 1行に置換。冒頭に無効化の理由を追記|
|docs/adr/ADR-1007-migration-structure-only-run-once.md|決定2の適用例を追記|
|docs/adr/README.md|generate-adr-index.js の再生成（差分がある場合のみ）|
|docs/handoff/fix-0919-rename-roundtrip/recon.md, design.md|新規|
|.claude-pipeline/active-work.d/release-fix-0919-rename-roundtrip.md|台帳|

触らない: 20260922_080000、20260919_020000、20260925_*、scripts/run_all_migrations.sh、deploy.yml、コード全般。

## 3. 受入条件
|基準|検証方法|
|---|---|
|G1 反映後 postgres ログの line_* 4表の "does not exist" が 0件|本番反映後の postgres ログ（PO/Opus が読取）|
|G2 反映の migration ログに 0919 由来の RENAME / DROP VIEW が 0件|migration ログ。事前検証 B 2周目で 0件（recon.md §2）|
|G3 line_* 4表は BASE TABLE、旧名4つは VIEW、行数同じ|事前検証 C で形が同じ（recon.md §2）。本番反映前後で relkind と count を比較|
|G4 CI の migration 系チェックが緑|PR の CI|

## 4. 戻し方
この PR の revert。

## 5. 外部事例
該当なし: 自社 migration の無効化で、出典と数値のそろった外部事例は確認していないため。

## 維持の仕組み
- 往復 RENAME が再び入ると、事前検証と同じ 2 周実行で NOTICE として現れる。恒久の自動検出は今回の範囲外（未実装）。
