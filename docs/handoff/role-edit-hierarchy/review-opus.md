# Opus 審査記録: ロール画面の編集の決まり

同一 AI（Claude Opus）による自己審査。独立した第三者の審査ではない。マージ前の審査役（reviewer・opus）は別に立てる。

## 設計審査（2026-11-09）

- 判定: APPROVE（design.md 末尾の審査欄と同じ）。
- PO 承認: 2026-11-08「それであればオーナーとシステム管理者はそもそもロールに表示しなくて良い、点検用もページに表示する必要はない、合意できるか？」に Opus が合意。2026-11-09「2」= マネージャーにも作成・削除・割当を渡す（上位に届く道は止める）。

## 実装の確認（Opus が自分で読んだもの）

- 差分 affd7785e..2361fab05 の全行（backend 4・試験 5・画面 9・文書 9）。
- `backend/tests/test_error_detail_guard.py` を手元で流した: self_check / no_increase / no_stale_baseline すべて ok（クラウドの全件実行で出た 1 件の失敗は基準を書き直す前のもの）。
- 入れ忘れ 1 件を見つけた: 新しい 6 つの失敗の印が画面の文の表（`frontend/src/lib/apiErrorReason.ts`）に無く、英字のまま画面に出る。追加カード2 で直した（00d167871）。クラウドの試験: 63 passed・vitest 3 passed・tsc 0。
- `roles.*` を使う場所を全部見た（`backend/app/routers/roles.py:198,240,295,370,423,452,538,571`・`backend/app/routers/staff.py:78`・`frontend/src/constants/menuPermissions.ts:65`・`frontend/src/components/DesktopShell.tsx:188`）。計算で鍵が決まる前提と食い違う所は無い。
- データ SQL（`data/`）: precheck と apply は同じ照合を持ち、1 件でも違えば全体を止める。apply は 7 件・4 行の件数を確かめてから COMMIT。rollback は audit_log の記録から戻す。
- 追記（2026-11-09）: 本番の読み直しで、消す行は 4 行ではなく 6 行と分かった（t005・t006 のマネージャーにも roles.view が1行ずつ）。apply・dryrun・rollback の期待値は 9b45d94f3 で 6 に直した。

## 残る注意

- 順番: データ SQL → コードの反映。間はマネージャーのロール画面が数分消える（保存行を先に消すため）。
- 本番の書き込み（apply）は自動判定に止められる前例がある。止められたら PO に `!` で流してもらう。
