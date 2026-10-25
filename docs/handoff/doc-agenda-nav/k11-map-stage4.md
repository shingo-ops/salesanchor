# K11 意味の対応表（段4 frontend・backend の入口をそろえる）

> この文書は何か：frontend・backend の CLAUDE.md と AGENTS.md を1本の AGENTS.md にまとめるとき、一字一句の一致では見つからない行が、まとめた後のどこに同じ意味で在るかを1行ずつ示す表です（KGI-11）。設計: design.md §25。

- 起点: d7924ae70（origin/main、2026-10-25）。frontend/CLAUDE.md 78行・frontend/AGENTS.md 63行・backend/CLAUDE.md 70行・backend/AGENTS.md 91行。ルート AGENTS.md:47-53（i18n・UI ガバナンス。design.md:408 で「段4で frontend/AGENTS.md へ移す」と決めた行）と、書き直す AGENTS.md:45・CLAUDE.md:7（design.md §25）も数える。
- まとめた後: frontend/AGENTS.md ＝ draft/frontend-AGENTS.md（77行）、backend/AGENTS.md ＝ draft/backend-AGENTS.md（70行）、ルート AGENTS.md（45行。:45 は実装カード card-stage4.md §4 の文）、ルート CLAUDE.md（9行。:7 は同カード §4 の文）。行番号は案文のもの。
- 数え方: 起点の各行（空行・`---`・コードの囲み記号の行を除く）を前後の空白を外して、まとめた後のファイルに部分一致で探す。対象 172 行を、まとめた後の5本（ルート AGENTS.md・frontend と backend の AGENTS.md・CLAUDE.md）に探す。一致は 129 行で、この表に載せない。不一致の 43 行と、CLAUDE.md に残る表題2行（frontend・backend の CLAUDE.md:1）の計 45 行を下に載せる（生出力: リポジトリ外 /tmp/CC報告ファイル/an-s4/k11-unmatched.txt）。
- 「削除」は移り先を作らないと判断した行。理由を書く。

| 起点の行 | 起点の中身（要約） | まとめた後の在りか | 備考 |
|---|---|---|---|
| frontend/CLAUDE.md:1 | 表題 | frontend/CLAUDE.md:1（案文 frontend-CLAUDE.md:1） | 表題は CLAUDE.md に残す |
| frontend/CLAUDE.md:3 | frontend 配下のみ適用・全体は /CLAUDE.md | frontend/AGENTS.md:3 | 全体の正本は段3c から /AGENTS.md |
| frontend/CLAUDE.md:25 | 見出し「i18n ハードコード検出（ESLint 自動強制）」 | frontend/AGENTS.md:21「i18n 強制（ADR-027）」 | ルート AGENTS.md:47 の見出しにそろえ、節を1つにした |
| frontend/CLAUDE.md:43 | ADR-067 の詳細・ローカル確認 check:all | frontend/AGENTS.md:42 | 「（全デザインシステムチェック一括実行）」を足して frontend/AGENTS.md:46 と1行に |
| frontend/AGENTS.md:10 | raw h2 は ESLint が自動ブロック（CI で PR マージ不可） | frontend/AGENTS.md:7 | |
| frontend/AGENTS.md:22 | 新規ページは nav に同キー → navKey で参照 | frontend/AGENTS.md:19 | ファイル名の囲み記号だけ違う |
| frontend/AGENTS.md:23 | 右上ボタンは headerAction 経由・position: fixed 禁止 | frontend/AGENTS.md:19 | 理由と自動ブロックの説明つきの frontend/CLAUDE.md:21 版 |
| frontend/AGENTS.md:27 | 見出し「i18n ハードコード検出」 | frontend/AGENTS.md:21 | 上と同じ |
| frontend/AGENTS.md:30 | コミット前に自動ブロック | frontend/AGENTS.md:25 | 「lint-staged により」つきの frontend/CLAUDE.md:28 版 |
| frontend/AGENTS.md:36 | DB 由来の値は eslint-disable で除外可 | frontend/AGENTS.md:32 | 例が多い frontend/CLAUDE.md:35 版 |
| frontend/AGENTS.md:42 | 色トークンは :root と force-dark の両方 | frontend/AGENTS.md:40 | 太字の位置だけ違う |
| frontend/AGENTS.md:43 | 非色トークンは tokens.css の :root のみ | frontend/AGENTS.md:41 | |
| frontend/AGENTS.md:46 | check:all（全デザインシステムチェック一括実行） | frontend/AGENTS.md:42 | |
| frontend/AGENTS.md:55 | 全アイコンは icons.tsx から import | frontend/AGENTS.md:57 | |
| frontend/AGENTS.md:56 | lucide-react の直接 import は ESLint が禁止 | frontend/AGENTS.md:58 | |
| AGENTS.md:45 | 画面は frontend/AGENTS.md、サーバー側は backend/AGENTS.md の決まりにも従う | AGENTS.md:45 | 「触る前に開いて読む」と、Codex が下の階層を自動で読まない理由を足した（design.md §25） |
| CLAUDE.md:7 | 作業場所は new-worktree.sh … --claude で作る | CLAUDE.md:7・AGENTS.md:34 | 作り方のコマンドは AGENTS.md:34 だけに置き、CLAUDE.md:7 は `--claude` を付けることとその意味だけにした（K3 の重なりを消す。design.md §25） |
| AGENTS.md:49 | i18n 強制の本文・grep セルフチェックは frontend/CLAUDE.md | frontend/AGENTS.md:23・:27-28 | 「grep セルフチェック: frontend/CLAUDE.md」はファイル自身を指すので外した。確かめ方は同じ節の :27-28（npm run lint） |
| backend/CLAUDE.md:1 | 表題 | backend/CLAUDE.md:1（案文 backend-CLAUDE.md:1） | |
| backend/CLAUDE.md:3 | backend 配下のみ適用・全体は /CLAUDE.md | backend/AGENTS.md:3 | |
| backend/CLAUDE.md:26 | 1. 実機 Messenger + Instagram DM 送受信 | backend/AGENTS.md:16 | 空白だけ違う |
| backend/CLAUDE.md:29 | 4. 不足あれば手動 ALTER/INSERT で補完 | backend/AGENTS.md:19 | 空白だけ違う |
| backend/CLAUDE.md:44 | destructive は PO 確認のうえ ADR 起案 | backend/AGENTS.md:28 | 「要PO確認」の行の後ろにつないだ |
| backend/CLAUDE.md:49 | 適用経路の中の additive-only 原則（再掲） | backend/AGENTS.md:26・:28 | 同じファイルの additive-only 節の再掲なので1か所にした |
| backend/CLAUDE.md:53 | {schema} 入り SQL は deploy.yml で直接実行不可・DO $$ pg_namespace 形式に | backend/AGENTS.md:39 | backend/AGENTS.md:55・:57 と1行に |
| backend/CLAUDE.md:58 | 見出し「カラムコメント・スキーマ説明の必須化」 | backend/AGENTS.md:64「書き方の決まり」 | |
| backend/CLAUDE.md:60 | 新テーブルは全カラムに COMMENT ON COLUMN | backend/AGENTS.md:66 | |
| backend/CLAUDE.md:61 | Pydantic の Field に description | backend/AGENTS.md:67 | |
| backend/CLAUDE.md:62 | 計算ロジックは docstring に計算式 | backend/AGENTS.md:67 | |
| backend/CLAUDE.md:64 | 見出し「取引先 SSOT: companies（ADR-089 完了）」 | backend/AGENTS.md:68 | 箇条の頭に置いた。本文 :66 は一字一句一致 |
| backend/CLAUDE.md:67 | 見出し「Meta App Review テナント（tenant_006）パスワード管理」 | backend/AGENTS.md:8 | tenant_006 の行に寄せた |
| backend/CLAUDE.md:68 | setup_review_tenant.py の後はホスト側に保存 | backend/AGENTS.md:8 | 「パスワードを」を補った |
| backend/CLAUDE.md:69 | 手順詳細 backend/scripts/CLAUDE.md・受信翻訳の標準入口・品質チェック | backend/AGENTS.md:8・:69・:70 | 1行に3つ入っていたのを分けた |
| backend/AGENTS.md:24 | ADR-034 マージ前は 4 ステップ必須 | backend/AGENTS.md:14 | 「新規テナントを作る作業すべて」の backend/CLAUDE.md:24 版 |
| backend/AGENTS.md:37 | 削除・型変更の migration は禁止 | backend/AGENTS.md:26 | 「原則禁止」の backend/CLAUDE.md:38 版 |
| backend/AGENTS.md:38 | 理由: downgrade 未整備（ADR-045） | backend/AGENTS.md:26 | ADR-045:90 まで示す版 |
| backend/AGENTS.md:40 | 許可: カラム・インデックス・テーブル追加 | backend/AGENTS.md:27 | 「制約追加」を含む上位集合 |
| backend/AGENTS.md:41 | 要PO確認: 削除・リネーム・型変更 | backend/AGENTS.md:28 | 「データ移行を伴う変更」を含む上位集合 |
| backend/AGENTS.md:49 | PostgreSQL 実機で全テナント schema 整合 | backend/AGENTS.md:37 | 空白だけ違う |
| backend/AGENTS.md:53 | 見出し「Migration SQL の書き方（必須パターン）」 | backend/AGENTS.md:39 | 「Migration 適用経路」節の箇条にした。migration-guard.yml が名前で指す2つの見出し（:30・:24）は残す |
| backend/AGENTS.md:55 | {schema} は絶対使用禁止・前例 PR #1345 | backend/AGENTS.md:39 | |
| backend/AGENTS.md:57 | 全テナントへは DO $$ pg_namespace 走査形式 | backend/AGENTS.md:39 | 例の SQL（:41-62）と参考ファイルも同じ箇条に在る |
| backend/AGENTS.md:86 | 見出し「品質チェック」 | backend/AGENTS.md:70 | 箇条の頭に置いた |
| backend/AGENTS.md:89 | make lint（ruff / bandit / mypy） | backend/AGENTS.md:70 | |
| backend/AGENTS.md:90 | make check・初回 pip install | backend/AGENTS.md:70 | |

合計 45 行（frontend/CLAUDE.md 4・frontend/AGENTS.md 11・ルート AGENTS.md 2・ルート CLAUDE.md 1・backend/CLAUDE.md 15・backend/AGENTS.md 12）。「削除」は 0 行。
