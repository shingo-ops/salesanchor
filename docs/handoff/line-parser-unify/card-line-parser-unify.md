# 実装カード: LINE お知らせ判定を1か所にまとめる（段階1 C1＋C3）

- 設計: `docs/handoff/line-parser-unify/design.md`（§3 C1・C3、§5 受入条件）、調査: 同 `recon.md`
- PO: 2026-09-30「確立したなら進める」＋フォルダ整理 y。実装範囲は本カードのみ
- 基準: origin/main（デプロイ済み SHA 5f32ca89b710b0dc0e2f4b456527f4ac1d0808bc 以降）。行番号は着手時に origin/main で必ず再確認し、ずれていたら実物に合わせる（ロジックが違えば停止）

## 0. 事前
1. `./scripts/dev/executor-preflight.sh || exit 1`
2. `/Users/tanizawashingo/worktrees/salesanchor/release-line-import-missed-0928-recon` の整理（PO 承認 y）: `git -C <そのパス> status --porcelain` が空、かつ `git -C <そのパス> rev-parse HEAD` と `git rev-parse origin/release/line-import-missed-0928-recon` が一致することを確認してから `git -C /Users/tanizawashingo/salesanchor worktree remove <そのパス>`（--force 禁止）。条件不一致・拒否・ブロックなら全停止して報告
3. `bash scripts/new-worktree.sh release/line-parser-unify --claude`
4. scratchpad の `recon.md`・`design.md`・本カードを `docs/handoff/line-parser-unify/` にコピー（scratchpad 絶対パスの記述はそのまま残してよい）

## 1. 変更するファイル（これ以外は触らない）
### 1-1 新規 `backend/app/services/tcg_line_system_events.py`
- scratchpad `evidence/system_event_table.py` の 13 パターンをそのまま移す（`SYSTEM_EVENT_PATTERNS`）
- 公開関数1つ: `match_system_event(display_name: str, body: str) -> str | None`（一致したラベル、なければ None）。判定対象は試作の `classify_new` と同じ（表示名＋" "＋本文1行目、1行目が空なら表示名のみ）
- 各パターンに実例コメント（どの本番/実ファイル文言か）を1行

### 1-2 `backend/app/services/tcg_line_import_svc.py`
- `_SYSTEM_EVENT_RE`（:46-49）を削除し、`parse_line_export` 内の2か所の判定（:185-186、:200-202 付近）を `match_system_event(...) is not None` に置き換える
- `import_line_export` で、パース直後（source_format で pc/android を選ぶ箇所 :580 付近の直後）に、全メッセージへ同じ判定を当てる: `is_system_event = 元の値 or match_system_event(...) is not None`。新しい list/dict を作る（元の dict を書き換えない）。スマホ用パーサ本体は変えない
### 1-3 変えないもの
- `backend/app/services/tcg_line_android_parser.py`、`tools/termux-line-import/` 配下の全ファイル、`_MSG_SEPARATOR`（改行は変えない＝設計 C2 除外）、DB・migrations・frontend・CI 設定

## 2. テスト
- 新規 `backend/tests/test_tcg_line_system_events.py`:
  - 13 パターンそれぞれの一致例（実ファイルの文言の形。個人名は仮名に置換）
  - 一致しない例: 「Whatnot ウェビナーに参加しました」を含む業務文、「価格を変更しました」、「OP-14 BOX 〆」、本文2行目にだけ定型文がある投稿
  - LINE WORKS 参加は1行目だけで一致すること
- `backend/tests/test_tcg_line_import.py` に PC 形式の統合ケースを追加: 招待＋しばらくお待ちください・グループから削除・グループ通話が終了 の各行が `parse_line_export` で is_system_event=True
- C3（本便から除外、2026-09-30: `.github/workflows/test.yml` の detect-changes が `tools/**` を含まず、tools 側だけの変更では CI が走らないため。CI 設定の変更は PO 判断が要るので別便） 同一性テスト: `backend/app/services/tcg_line_android_parser.py` と `tools/termux-line-import/android_parser.py` のバイト一致を確かめるテスト。**置き場所は CI で実際に実行され、かつ両ファイルに届く場所**を `.github/workflows/` の実物で確認して決める。該当がなければ実装せず停止して報告（skip で逃げない）
- 実ファイル回帰（CI 外・証拠用）: scratchpad `evidence/compare.py` を実装後のコードに向けて再実行し、「今=投稿→お知らせ 84 件、逆 0 件」が再現することを生出力で報告

## 3. 実行する検証
- `cd backend && pytest tests/test_tcg_line_system_events.py tests/test_tcg_line_import.py tests/test_tcg_line_android_parser.py tests/test_tcg_line_android_api.py tests/test_line_source_names.py -q`（PG が要るものは CI に任せ、その旨報告）
- 既存の全リント・型チェック（リポジトリの pre-commit／CI と同じもの）

## 4. 仕上げ
- 台帳 `.claude-pipeline/active-work.d/release-line-parser-unify.md` を既存の書式で追加
- commit（docs と実装を分けてよい）→ push → `gh auth status` で shingo-cc を確認 → `gh pr create --base main`（通常 PR。本文にテンプレの必須欄と `### 標準ワークフロー確認`、変更・削除ファイル全列挙、受入条件表）
- PR URL を報告して終了（CI の完了は待たない・マージしない）

## 5. 停止条件
- 行番号・ロジックがカードと食い違う／CI の置き場所が決まらない／既存テストが赤（本変更起因かどうかに関わらず）／フック・分類器に止められた → その時点で全停止し、生出力で報告
