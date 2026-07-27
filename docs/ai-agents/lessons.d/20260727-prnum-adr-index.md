分類: 6-2
出所: （2026-07-27 ADR-150便 #3115）

- PR番号は設計パートナーが手書きせず、カード内で `PR=$(gh pr list --head <branch> --state open --json number --jq '.[0].number')` として変数で受け、以降のコマンドは "$PR" を使う。あわせて `CNT` を数え 1 でなければ停止する。記憶や連番からの類推は取り違えを生む（2026-07-27 本セッションで #3113→実#3115、別便で #3103→実#3102 と2度取り違え・実測）。
- docs/adr/README.md は scripts/generate-adr-index.js の自動生成物（冒頭に「手動編集禁止」と明記）。手で行を足すと adr-index-check.yml の `node scripts/generate-adr-index.js --check` が exit 1 で落ちる。ADR追加時は ADR本文だけ書き、索引は `node scripts/generate-adr-index.js`（引数なし＝書き込み）で生成する。日付欄はADR本文から抽出され、本文に日付が無ければ `—`。手書きの日付は不一致の原因になる（2026-07-27 実測）。
