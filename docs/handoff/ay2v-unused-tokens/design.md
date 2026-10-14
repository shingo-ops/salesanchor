# AY-2v 設計: 参照 0 の未使用トークン 18 件の削除

- 状態: 設計審査済み（Fable r2 APPROVE）・PO 承認済み。実装は release/ay2v-unused-tokens
- PO 決定: 2026-10-14「y」（未使用トークン30件を、参照が0件と1件ずつ確かめたうえで消す）
- 基準: 設計時 e6923ba61、実装時 HEAD a39fb988f（frontend/src/tokens.css・index.css は両者間で差分なし）
- 調査根拠: docs/handoff/ay2v-unused-tokens/recon.md、docs/handoff/design-system-recon/evidence-20260910/ay2v-grep18.txt
- 対象 ADR: ADR-067（デザイントークン・dark-parity）、ADR-073、ADR-125（FedEx バッジ色ブロック）
- 前例: AY-2u（#4257、`--input-select-min-w` 1件削除）

## 1. 目的
監査（frontend/scripts/check-unused-tokens.js）が報告する未使用30件のうち、コード・テスト・lp・scripts・.github・docs/specs・docs/adr のどこからも名前で参照されず、動的組み立てでも使われない 18 件をトークン正本（tokens.css / index.css）から外す。正本を「実際に使われている値」だけにする。

## 2. 「参照 0」の判定基準（PO 条件「参照が0件」の運用）
次のいずれかに名前（`git grep -F -- '<name>'`）が現れれば「参照あり」とし、本便では消さない:
frontend（src・tests-e2e・eslint.config.js・scripts）、lp、scripts、.github、docs/specs、docs/adr、および DesignSystemPage.tsx:72 の `var(${t.name})` 実行時参照（COLOR_TOKENS 掲載）。
除外（参照に数えない）: docs/handoff/**、docs/audits/**（過去時点の記録で現行の仕様ではない）、定義行自身、CSS コメント。
名前境界: ヒット箇所の直後の文字が `[A-Za-z0-9_-]` のときは別トークンの部分一致であり参照に数えない（例: `--schedule-slot-h` に対する `--schedule-slot-hover`）。判定には `git grep -n -E -- '<name>([^A-Za-z0-9_-]|$)'` を併用する。
既知の部分一致（参照ではない）: frontend/src/pages/schedule.css:530・frontend/src/tokens.css:378・:609 の `--schedule-slot-hover`、docs/specs/design-system/design.md:155 の `--color-amber-500`。
過去記録の言及（判断済み・残置）: docs/specs/design-system/design.md:1117 の AG 便（2026-09-11）記録にある `calendar-today-text`（`--` なし）は当時の作業記録で現行の依存ではない。docs/handoff/**（約145行）・docs/audits/**（4行）にも名前が残るが、いずれも過去時点の記録として書き換えない。

## 3. 対象 18 件（変更契約）
| # | トークン | 削除する定義行（origin/main e6923ba61） |
|---|---|---|
| 1-4 | --cat-import / --cat-discord / --cat-distribution / --cat-inventory | frontend/src/tokens.css:256-259 |
| 5 | --max-width-modal-sm | tokens.css:295 |
| 6 | --inbox-collapsed-panel-w | tokens.css:312 |
| 7 | --karte-ok-bg | tokens.css:331 |
| 8 | --topnav-email-max-w | tokens.css:343 |
| 9-12 | --schedule-cell-icon-size / --schedule-min-h / --schedule-mini-col-min-w / --schedule-slot-h | tokens.css:368-371 |
| 12' | --schedule-slot-h（@media max-width:1279px の上書き） | tokens.css:584 |
| 13 | --schedule-nav-btn-size | tokens.css:372 |
| 14 | --schedule-row-height-compact | tokens.css:380 |
| 15 | --color-blue-100 | frontend/src/index.css:157（:root）と :361（:root.force-dark） |
| 16 | --color-amber-50 | index.css:163 と :367 |
| 17 | --calendar-today-text | index.css:187 と :391 |
| 18 | --calendar-today-cell-bg | index.css:188 と :392 |

- 行番号は基準 SHA 時点。実装者は削除直前に各行の内容がトークン名と一致することを確認し、ずれていれば行番号ではなく名前で特定する（一致しなければ停止）。
- 1行に1定義であることを確認し、行ごと削除。前後の行は逐語。
- index.css は :root と :root.force-dark を必ず対で削除（ADR-067 dark-parity）。片側のみは不可。
- 見出しコメント・ブロックは空にならない（recon §3。@media ≤1279px ブロックには --schedule-allday-row-h が残る）。

触らない（本便の対象外）:
- 消さない 2件: --bg-disabled、--accent-bg（DesignSystemPage.tsx:34,44,72 が実行時参照、check-color-token-sync.js が掲載を要求）。check-unused-tokens.js の EXEMPT_NAMES への追加も本便ではしない（監査スクリプトの変更は別テーマ）。
- 参照あり 10件: --size-avatar-sm（visual-language spec:223）、--table-col-min-width（eslint.config.js:95,197・ADR-067:65）、--modal-commission-w・--modal-detail-max-w（ADR-067:71-72 の登録表）、--color-blue-700（design.md:30 の命名例）、--color-gray-100・--color-gray-600・--color-red-700・--color-amber-800・--color-border-subtle（docs/specs/design-tokens-ssot/color/calendar/design.md:34-38 の参照先）。
- ADR・docs/specs・eslint.config.js・scripts・他の CSS・TS。docs/audits・docs/handoff の過去記録。
- docs/specs/design-system/design.md は実装者は触らず、Opus が AY-2u 反映記録と §AY-2v 節を追記する。

## 4. 想定分岐（実装者は実物で確認し記録）
- B1: 実装直前に 18 件それぞれ `git grep -n -E -- '<name>([^A-Za-z0-9_-]|$)'` を再実行し、§2 の範囲（除外・既知の部分一致を除く）に定義行以外のヒットが 1 件でもあれば、削除せず NEEDS_DECISION で停止（他の件も進めない）。
- B2: 削除後の dev build で CSS に 18 件の名前が 0 件、かつ残すべき 12 件（§3 触らない）の名前が before と同数であること。違えば停止。
- B3: check:all（特に dark-parity・check-color-token-sync）が fail したら停止して報告（迂回しない）。

## 5. 受入条件
| 基準 | 検証方法 |
|---|---|
| frontend の差分が §3 の 23 行（※）の削除のみ | `git diff origin/main...HEAD -- frontend` の `-` 行を列挙し表と照合 |
| 18 件の名前が §2 範囲で 0 件 | B1 と同じ `git grep -n -E -- '<name>([^A-Za-z0-9_-]|$)'` 18 回の生出力 |
| 監査件数 30→12、消えた名前が 18 件と一致 | check-unused-tokens.js の before/after 差分 |
| dev build CSS の差分が 18 名の定義行（23 行）の削除のみ、残す 12 名は前後同数 | AY-2u と同じ整形手順（1 定義 1 行に整形した fmt-before/after.css の diff）と grep 件数 |
| 画面の見た目が変わらない | 参照 0 のため。dev build の CSS で 18 名以外の差分 0 を根拠とする |
| 品質: generate / tsc / lint / check:all / test:coverage(maxWorkers=1) / build / build-storybook 全成功 | 実行ログ |
| 本番: 反映後の CSS に 18 名が 0 件、残す 12 名・--calendar-today-bg・--schedule-allday-row-h は存在 | prod CSS grep |

※行数: tokens.css 15 行（:256-259 の4、:295、:312、:331、:343、:368-372 の5、:380、:584）＋ index.css 8 行（4名×2ブロック）＝ 23 行。

## 6. 代替案
- A 参照 0 の 18 件のみ削除（採用）: PO 条件に忠実。docs・ADR を書き換えない。
- B 30 件全部削除: 実行時参照 2 件で見本帳の色が消え CI も落ちる。ADR・計画書・lint 文言の書き換えが要る → 不採用。
- C 21 件削除（ADR-067 表の 2 件と命名例 1 件も含む）: ADR の登録表の改訂を伴う。ADR 変更は本便の範囲外 → PO 判断として残す。

## 7. リスクと戻し方
- 見えない参照（外部リポジトリ・ブラウザ拡張等）: recon で frontend・lp・scripts・.github を走査済み。外部は未確認だが、CSS 変数は同一オリジンの CSS からのみ解決されるため外部からの参照は成立しない。
- 戻し方: merge commit の revert（DB 影響なし）。

## 外部・過去事例の参照と我々への応用
- 過去: AY-2u（#4257）で同じ手順（git grep・監査件数・dev build CSS 差分・本番 CSS grep）による 1 件削除を本番まで完了。本便はその手順を 18 件に適用する。
- 外部事例: 不要（社内正本の未使用値の削除。外部の数値根拠に依存しない）。

## 維持の仕組み
- 守り手: frontend/src/tokens.css・frontend/src/index.css（トークン正本）と check:all の dark-parity・color-token-sync チェック。
- 守り手2: frontend/scripts/check-unused-tokens.js（週次監査、非ブロック）。残り 12 件は本便の §3 に理由付きで記録し、design.md 残件に載せる。

## 10. 残件（本便範囲外・記録のみ）
- index.css の FedEx バッジ色ブロック（ADR-125）に残る 7 名のうち 6 名は calendar 計画書由来の保留分で、見出しと実態がずれている。計画書の現行性の確認とあわせて別便で判断。
- PO への報告では「コード・仕様・ADR で参照 0 件。過去の作業記録（docs/handoff・docs/audits）には名前が残る」を明示する。

## 相互参照
- recon: docs/handoff/ay2v-unused-tokens/recon.md
- 証跡: docs/handoff/design-system-recon/evidence-20260910/ay2v-acceptance.md（ay2v-audit-before.txt / ay2v-audit-after.txt / ay2v-audit.diff / ay2v-css.diff / ay2v-grep18.txt）
