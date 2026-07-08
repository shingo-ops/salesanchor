# 理想の設計図（design-system・PO承認済 2026-07-04／2026-07-07改訂）

> この文書は何か（専門用語なしの1行）: 画面の色・部品の設計図を1ヵ所に集め、1ヵ所直せば全ページが変わる仕組みの作り方。この図だけで実装者が迷わず作れる粒度で書く（この文書以降で新たな仕様決定を発生させない）。

親（あるべき姿＋KGI）: [README.md](README.md)／現状実測: [full-recon.md](../../handoff/design-system-recon/full-recon.md)

## 0. この設計図の使い方（design定義・PO確定）
本設計図は「完成図」であり絶対の正とする。実装は本図とrecon差分に従うのみ。本図に無い仕様判断が実装中に生じたら、それは本図の不足であり、実装を止めて本図を先に直す（design.md以降で仕様決定を発生させない）。

## 1. あるべき姿
[ideal-state.md](ideal-state.md) を正本とする（PO自筆・書き換え禁止）。

## 2. KGI / 3. KPI
[kgi.md](kgi.md) の6項目。KPI: 達成KGI数 ◯/6。

## 4. recon（現状把握・完了）
現状は [full-recon.md](../../handoff/design-system-recon/full-recon.md) で網羅把握済（5問×3検品）。要点: 本物色36件(config21/RolesPage13/schedule-owner1/Dashboard1)・index.css色正本はADR-067準拠で0違反・TSXインライン0・素の<table>28・素の<h1>6・空状態独自3・共通部品は概ね金型あり・関所隙間5つ。

## 5. design（技術How・3層＋2つの支え）

### 5.1 参照の3層（一方向: パレット → 用途 → 部品 → ページ）
| 層 | 理想のルール | 素人向けに言うと |
|---|---|---|
| 層0 パレット | 色そのものに名前を付ける。--color-{色相}-{階調}（例: --color-blue-700: #1d4ed8）。値はhex直値。index.css の :root / :root.force-dark にペアで定義（ADR-067 dark-parity必須） | 絵の具に名前を付ける |
| 層1 用途トークン | 役割に色を割り当てる。--{役割}（例: --accent: var(--color-blue-700)）。値はパレットへのalias参照。hex直値を用途トークンに書かない。:root / :root.force-dark ペア | 「アクセントは青」と決める |
| 層2 共通部品 | プルダウン・検索欄・ボタン・アイコン・テキスト書式・ページ骨格・カード・表・バッジ・空状態は1部品=1定義。差分はprops(variant/size)で吸収。色は用途トークンのみ参照 | 部品の金型は各1つ |
| 層3 ページ | 部品をimportして使うだけ。部品再定義・生値ベタ書き・パレット直参照を禁止（用途トークン経由のみ） | 画面は部品を並べるだけ |
| 支え1 カタログ | 全共通部品と使用例をStorybookに常備（KGI④） | 部品の見本帳 |
| 支え2 関所 | CIがページ側の生値ベタ書き・部品重複・パレット直参照を機械検出しfail（KGI⑤） | 直書きを止める見張り番 |

参照は常に一方向: パレット → 用途 → 部品 → ページ。逆流・飛び越し（ページが生値やパレットを直接持つ）を禁止。

### 5.2 命名規約（誰が付けても同じ名前になるルール）
- パレット層: --color-{色相}-{階調}。色相=blue/red/green/gray/amber/purple等の英名、階調=50〜900の百刻み。例: --color-red-600。
- 用途層: --{役割}。役割=accent/text-primary/border/danger/success/warning 等。既存の用途名があればそれを使う（新設しない）。
- 選択肢として並ぶ色群（役割色パレット・カレンダー種別色）: 用途接頭辞＋連番。役割色=--role-palette-{n}（n=1..）、カレンダー=既存 --calendar-* を踏襲。各連番はパレット層をalias参照。
- 禁止: 生値命名（--color-hex-1e3a8a のような値そのものを名前にする方式。便1旧版の失敗）。

### 5.3 追加するもの（recon差分＝理想に足りないもの・提案）
1. 用途トークン/パレットの新設: 本物色36件のうち既存トークンで吸収できない分を、5.2規約でパレット層＋用途層として新設（正確な新設数は便0.5で確定）。
2. 素の<table> 28件→DataTable金型へ寄せる。
3. 素の<h1> 6件→PageLayout・骨格CSS 2系統→1系統。
4. 空状態独自3件→EmptyState。
5. 検索欄・テキスト書式の共通金型化。
6. 関所隙間5つ（TS色定数/<h1>/<table>/空状態/visual gate範囲外）を領域ペアで塞ぐ。
（便への割当は [migration.md](migration.md) §2・§5）

### 5.3.1 便0.5-A確定表（本物色36件の振り分け・2026-07-08実測確定）

実測基準SHA: ab09284ef417f40dd6f1cb03b4f60b7835c859ee

| # | hex | ソース | トークン名候補 | 分類 | 根拠 |
|---|---|---|---|---|---|
| 1 | #1a73e8 | calendars.config.ts:23 | calendar-meeting.colorVar | a | 既存 --calendar-google-blue と一致 |
| 2 | #e8f0fe | calendars.config.ts:24 | calendar-meeting.tintVar | a | 既存 --calendar-google-blue-light と一致 |
| 3 | #174ea6 | calendars.config.ts:25 | calendar-meeting.textVar | b | calendar用途は既存だが値は新設 |
| 4 | #9333ea | calendars.config.ts:31 | calendar-personal.colorVar | b | 同上 |
| 5 | #f3e8ff | calendars.config.ts:32 | calendar-personal.tintVar | b | 同上 |
| 6 | #6b21a8 | calendars.config.ts:33 | calendar-personal.textVar | b | 同上（holidayと値重複→分割確定） |
| 7 | #0f9d58 | calendars.config.ts:39 | calendar-procurement.colorVar | b | 同上 |
| 8 | #e6f4ea | calendars.config.ts:40 | calendar-procurement.tintVar | a | 既存 --calendar-status-ok-bg と一致 |
| 9 | #166534 | calendars.config.ts:41 | calendar-procurement.textVar | b | calendar用途は既存だが値は新設 |
| 10 | #d93025 | calendars.config.ts:47 | calendar-shipping.colorVar | b | 同上 |
| 11 | #fce8e6 | calendars.config.ts:48 | calendar-shipping.tintVar | a | 既存 --calendar-status-error-bg と一致 |
| 12 | #b91c1c | calendars.config.ts:49 | calendar-shipping.textVar | a | 既存 --color-red-700 と一致 |
| 13 | #f29900 | calendars.config.ts:55 | calendar-billing.colorVar | b | calendar用途は既存だが値は新設 |
| 14 | #fef3c7 | calendars.config.ts:56 | calendar-billing.tintVar | b | 同上 |
| 15 | #92400e | calendars.config.ts:57 | calendar-billing.textVar | a | 既存 --color-amber-800 と一致 |
| 16 | #5f6368 | calendars.config.ts:63 | calendar-release.colorVar | b | calendar用途は既存だが値は新設 |
| 17 | #f3f4f6 | calendars.config.ts:64 | calendar-release.tintVar | a | 既存 --color-gray-100 と一致 |
| 18 | #374151 | calendars.config.ts:65 | calendar-release.textVar | a | 既存 --color-border-subtle と一致 |
| 19 | #7e22ce | calendars.config.ts:71 | calendar-holiday.colorVar | b | calendar用途は既存だが値は新設 |
| 20 | #f5f3ff | calendars.config.ts:72 | calendar-holiday.tintVar | b | 同上 |
| 21 | #6b21a8 | calendars.config.ts:73 | calendar-holiday.textVar | b | 同上（personalと値重複→分割確定） |
| 22 | #ef4444 | RolesPage.tsx:76 | role-palette-1 | c | role-palette体系は新設前提 |
| 23 | #f97316 | RolesPage.tsx:77 | role-palette-2 | c | 同上 |
| 24 | #eab308 | RolesPage.tsx:78 | role-palette-3 | c | 同上 |
| 25 | #84cc16 | RolesPage.tsx:79 | role-palette-4 | c | 同上 |
| 26 | #22c55e | RolesPage.tsx:80 | role-palette-5 | c | 同上 |
| 27 | #14b8a6 | RolesPage.tsx:81 | role-palette-6 | c | 同上 |
| 28 | #06b6d4 | RolesPage.tsx:82 | role-palette-7 | c | 同上 |
| 29 | #3b82f6 | RolesPage.tsx:83 | role-palette-8 | c | 既存--infoと値偶然一致だが独立新設（PO決定2026-07-08） |
| 30 | #6366f1 | RolesPage.tsx:84 | role-palette-9 | c | role-palette体系は新設前提 |
| 31 | #a855f7 | RolesPage.tsx:85 | role-palette-10 | c | 同上 |
| 32 | #ec4899 | RolesPage.tsx:86 | role-palette-11 | c | 同上 |
| 33 | #64748b | RolesPage.tsx:87 | role-palette-12 | c | 既存--neutral/--cal-holidayと値偶然一致だが独立新設（PO決定2026-07-08） |
| 34 | #6c757d | RolesPage.tsx:262 | role-palette-fallback | c | role-palette体系は新設前提 |
| 35 | #1a73e8 | schedule-owner.ts:34 | calendar-owner.default | a | 既存 --calendar-google-blue と一致 |
| 36 | #1e3a8a | DashboardPage.tsx:175 | dashboard.accent | a | 既存 --accent と一致 |

集計: a(既存吸収)=10件 b(新設パレット+既存用途)=13件 c(両新設)=13件

PO決定事項（2026-07-08）:
- #3・#6・#21（personal/holidayのtextVar、値重複#6b21a8）は `--calendar-personal-text` /
  `--calendar-holiday-text` に分割する。
- #29・#33（role-palette-8/12）は既存トークンとの値の偶然一致を無視し、独立パレットとして新設する。

新設対象（ダーク値算出が必要な件数）: b(13) + c(13) + 分割による追加1件 = 27件

### 5.3.2 便0.5-A ダーク値確定表（26件・2026-07-08実測確定）

算出方針: 既存 --cal-* のlight/dark対（21組）から抽出した傾向を目安に算出。
色相はほぼ維持（±10度以内）、主色系は明度+18〜31、薄色系は明度-76〜80、
文字色系は明度+30〜51を目安とする（厳密な数式ではなく傾向レンジ）。

| # | トークン名 | ライト値 | ダーク値 | 備考 |
|---|---|---|---|---|
| 1 | calendar-meeting.textVar | #174ea6 | #93c5fd | |
| 2 | calendar-personal.colorVar | #9333ea | #c084fc | |
| 3 | calendar-personal.tintVar | #f3e8ff | #2d0e4e | |
| 4 | calendar-personal.textVar | #6b21a8 | #d8b4fe | |
| 5 | calendar-procurement.colorVar | #0f9d58 | #4ade80 | |
| 6 | calendar-procurement.textVar | #166534 | #86efac | |
| 7 | calendar-shipping.colorVar | #d93025 | #f28b82 | |
| 8 | calendar-billing.colorVar | #f29900 | #f8d66d | |
| 9 | calendar-billing.tintVar | #fef3c7 | #362a08 | |
| 10 | calendar-release.colorVar | #5f6368 | #94a3b8 | |
| 11 | calendar-holiday.colorVar | #7e22ce | #b771f4 | |
| 12 | calendar-holiday.tintVar | #f5f3ff | #1e1b4b | |
| 13 | calendar-holiday.textVar | #6b21a8 | #e9d5ff | 目安上限をわずかに超過（+52.4pt、許容） |
| 14 | role-palette-1 | #ef4444 | #fca5a5 | |
| 15 | role-palette-2 | #f97316 | #fdba74 | |
| 16 | role-palette-3 | #eab308 | #fde68a | |
| 17 | role-palette-4 | #84cc16 | #bef264 | |
| 18 | role-palette-5 | #22c55e | #86efac | |
| 19 | role-palette-6 | #14b8a6 | #5eead4 | |
| 20 | role-palette-7 | #06b6d4 | #67e8f9 | |
| 21 | role-palette-8 | #3b82f6 | #b1cdfb | |
| 22 | role-palette-9 | #6366f1 | #bcbdfb | |
| 23 | role-palette-10 | #a855f7 | #d8b4fe | |
| 24 | role-palette-11 | #ec4899 | #f9a8d4 | |
| 25 | role-palette-12 | #64748b | #94a3b8 | |
| 26 | role-palette-fallback | #6c757d | #a8b3c2 | |

### 5.4 優れて残すもの（理想図に明記なくとも採用・提案）
recon で確認した既存の優良資産は、作り直さず残して採用する:
1. index.css の色正本（ADR-067準拠・:root/:root.force-dark パリティ済・違反0）→ そのまま土台に使う。
2. Storybook 37ストーリー（カタログの器が既にある）→ 拡張して使う。
3. Card / Badge（独自CSS 0・既に金型化済）→ 追加作業不要、現状維持。
4. 用途トークンのalias参照パターン（--inbox-*-icon-color: var(--text-*)）→ 5.2の用途層alias方式の既存前例として踏襲。

## 6. 弊害・トレードオフ（空欄不可）
1. 自由度の低下: ページ固有の微調整がやりにくい。意図した制約。正当な例外は関所の許可リストで逃がす＝管理コスト発生。
2. 2段命名の手間: パレット＋用途の2段は定義が増える。ただし「色を1ヵ所で差し替え」の要件はこの2段でしか満たせない。
3. props肥大リスク: 1部品1定義に寄せすぎると引数が膨らむ。variant上限はmigration便で決める。
4. 移行コスト: 既存を金型へ寄せる作業量はmigration.md便構成で管理。

## 7. 外部・過去事例
デザイントークンの2段（パレット/用途）構造は Salesforce Lightning・W3C Design Tokens CG の標準。大規模FW導入はせず内製規模の最小構成。alias参照はリポジトリ内 --inbox-* に既存前例あり。

## 8. 受入基準（design定義⑤の自己検査）
KGI①〜⑥に加え、本設計図の完成条件として次を満たす:
- 実装者が本design.mdとfull-recon.md・migration.mdだけで、追加の仕様判断なしに各便を実装できること。
- 色の命名は5.2規約で一意に決まること（同じ色に二人が別名を付けない）。
- 「追加するもの」(5.3)と「残すもの」(5.4)がPO承認済みで、実装中に新たな取捨選択が発生しないこと。

## 9. 接触面分析（6面走査）
①人: PO承認＋各便の画面確認。②エージェント: 索引経由で全設計セッションへ周知。③機械: 領域ペア関所を順次新設。④データ: 影響なし。⑤本番: 便0.5〜7はUI直結（同値置換で緩和）。⑥外部: 影響なし。

## 維持の仕組み
- 守り手: design-token-guard.yml/check-design-token-ratchet.sh（便0b稼働中）＋領域ペア関所（migration便1c/2/5/6-guard）＋部品台帳満数方式。
- 対象: 生値ベタ書き・部品重複・パレット直参照・素の<table>/<h1>/空状態の新規。
- 未確立（正直な明記）: 領域ペア関所は各guard便完了まで人が守る。
