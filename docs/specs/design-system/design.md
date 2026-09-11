---
mode: handoff
---

# 理想の設計図（design-system・PO承認済 2026-07-04／2026-07-07改訂）

> この文書は何か（専門用語なしの1行）: 画面の色・部品の設計図を1ヵ所に集め、1ヵ所直せば全ページが変わる仕組みの作り方。この図だけで実装者が迷わず作れる粒度で書く（この文書以降で新たな仕様決定を発生させない）。

> 最新状態（2026-09-10）: 追加全体設計は末尾§AAで自己審査APPROVE。過去のREVISE記録は調査履歴。POの具体的ADR承認・製品実装結果とは区別する。

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
色相はほぼ維持（±10度以内）、主色系は明度+18〜31、薄色系は明度-76〜-80、
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

### 5.3.3 便0.5-A 命名確定表（26件・2026-07-08確定）

5.2命名規約に基づき、層0パレット名・層1用途トークン名を確定する。
便0.5-B実装時はこの表のとおり定義するのみとし、命名判断は行わない。

| # | 用途層トークン名 | 層0パレット名 | ライト値 | ダーク値 |
|---|---|---|---|---|
| 1 | --calendar-meeting-text | --color-blue-800 | #174ea6 | #93c5fd |
| 2 | --calendar-personal-color | --color-purple-600 | #9333ea | #c084fc |
| 3 | --calendar-personal-tint | --color-purple-50 | #f3e8ff | #2d0e4e |
| 4 | --calendar-personal-text | --color-purple-800 | #6b21a8 | #d8b4fe |
| 5 | --calendar-procurement-color | --color-green-700 | #0f9d58 | #4ade80 |
| 6 | --calendar-procurement-text | --color-green-800 | #166534 | #86efac |
| 7 | --calendar-shipping-color | --color-red-600 | #d93025 | #f28b82 |
| 8 | --calendar-billing-color | --color-amber-500 | #f29900 | #f8d66d |
| 9 | --calendar-billing-tint | --color-amber-100 | #fef3c7 | #362a08 |
| 10 | --calendar-release-color | --color-gray-600 | #5f6368 | #94a3b8 |
| 11 | --calendar-holiday-color | --color-violet-700 | #7e22ce | #b771f4 |
| 12 | --calendar-holiday-tint | --color-violet-50 | #f5f3ff | #1e1b4b |
| 13 | --calendar-holiday-text | --color-violet-800 | #6b21a8 | #e9d5ff |
| 14 | --role-palette-1 | --color-red-500 | #ef4444 | #fca5a5 |
| 15 | --role-palette-2 | --color-orange-500 | #f97316 | #fdba74 |
| 16 | --role-palette-3 | --color-yellow-500 | #eab308 | #fde68a |
| 17 | --role-palette-4 | --color-lime-500 | #84cc16 | #bef264 |
| 18 | --role-palette-5 | --color-green-500 | #22c55e | #86efac |
| 19 | --role-palette-6 | --color-teal-500 | #14b8a6 | #5eead4 |
| 20 | --role-palette-7 | --color-cyan-500 | #06b6d4 | #67e8f9 |
| 21 | --role-palette-8 | --color-blue-500 | #3b82f6 | #b1cdfb |
| 22 | --role-palette-9 | --color-indigo-500 | #6366f1 | #bcbdfb |
| 23 | --role-palette-10 | --color-purple-500 | #a855f7 | #d8b4fe |
| 24 | --role-palette-11 | --color-pink-500 | #ec4899 | #f9a8d4 |
| 25 | --role-palette-12 | --color-slate-500 | #64748b | #94a3b8 |
| 26 | --role-palette-fallback | --color-gray-500 | #6c757d | #a8b3c2 |

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
- 守り手: `.github/workflows/design-token-guard.yml` / `scripts/check-design-token-ratchet.sh`（便0b稼働中）＋領域ペア関所（migration便1c/2/5/6-guard）＋部品台帳満数方式。
- 対象: 生値ベタ書き・部品重複・パレット直参照・素の<table>/<h1>/空状態の新規。
- 未確立（正直な明記）: 領域ペア関所は各guard便完了まで人が守る。

## 2026-09-10 統一定義・全体設計案（未承認）

この追補は、部品の色・形を一か所で直し、使う全画面に反映できるようにする設計案。
親: [README.md](README.md) / 根拠: [recon.md](../../handoff/design-system-recon/recon.md#2026-09-10-追加調査と訂正)。
既存の承認済み本文を上書きしない。以下は今回の設計担当の提案であり、PO承認済み決定・実装カードではない。

### A. 目的・範囲・成功条件

POの今回の言葉（チャット原文引用、GOではない）:
> 目指すのはボタンの色味や形やトグルやデータテーブルなど使い回すものは形を統一化させたい、なのでデザインシステムやデザイントークンを使って材料は一箇所にSSOTさせたいと考えている

対象はSales Anchorアプリのfrontend/src全体。pagesだけでなくfeatures、共通部品内部、アイコン・グラフ、明暗表示、画面幅別の表示も含む。部品の見本は同じ部品を参照する。
backend/API/DB/認証処理/課金処理/Webhook/本番環境/デプロイ/LPは対象外。APIを呼ぶ業務コールバックは変更しない。機能不足を補うためにAPI変更を暗黙に追加しない。

成功条件は既存kgi.mdの6項目を継承し、次で確認する。新しい達成宣言や分母縮小ではない。
1. 同じ用途・状態・画面幅で見た目を決める定義元が各1か所。
2. 対象部品の色・文字・余白・角丸・寸法・影・動きは正本トークン参照。ページで独自の組み合わせを再定義する箇所0。
3. トークンまたは部品を1か所変えた実験で、登録済みの全利用箇所に反映。反映数/対象数=100%。実験は検証環境だけで実施し、実験値を出荷しない。
4. 部品ごとの全許可種類・状態が見本帳に載る。掲載数/登録数=100%。
5. 禁止例を入れたチェックが失敗し、正しい例・正当な画面幅切替は通過する。
6. 文書・部品・使用箇所・検査の対応が索引から辿れる。

### B. なぜこの方式か（ADRのWhyへ渡す根拠）

基準SHAは6e133572。現行origin/main 87e5748bとの差分も確認し、frontendと既存design-system文書に変更なし（取得時点）。
- Button/Select/DataTable/Card/Tabs等の共通部品が既に実在する。新ライブラリへの全面移行を必須にする根拠はない。
- pagesに生button395箇所。ただし292は静的btn-*クラスを含む。見た目を共有する経路とReact部品を共有する経路を区別して移行できる。
- トグルは8 JSX箇所でtoggle-switchを使う。共通40×22px、設定ページ44×24px、予定ページ2.625rem×1.5remの別定義を確認。値のトークン化だけでは形の統一にならない実例。
- 共通Button自体もprimary/secondary/dangerがradius-sm、outlineがcomp-btn-radiusを使用。部品名の統一だけでは同じ形を保証しない。
- 既存10チェックexit0でも個別定義とSVG固定色2宣言が残る。既存検査の成功を統一完成と同一視できない。
- ソース全体は186 TSXファイル（テスト・見本除外）。featuresに生button34・table2。pagesだけの検査では利用経路が抜ける。

上記は構造と指定検査に関する事実。工数削減率・品質改善率は未測定であり数値を創作しない。

### C. 定義を置く場所と参照方向

| 管理対象 | 編集する正本 | 参照する側 |
|---|---|---|
| 色の素材と用途別の色 | 既存src/index.css | 部品のCSS、必要なJS変換口 |
| 文字・余白・角丸・寸法・影・動き | 既存src/tokens.css | 部品のCSS |
| アイコンの絵柄と用途名 | 既存src/constants/icons.tsx | 共通部品 |
| 各部品の見た目と状態 | 既存componentsの該当TSX/CSS | 業務部品・ページ |
| 各ページの内容・業務処理 | 既存pages/features | 共通部品へ値・処理を渡す |
| 部品の例・状態見本 | 既存stories | 実部品と実トークンを直接参照 |

SSOTは「全部を1ファイル」ではなく「同じ決定を手編集する場所が1か所」。現在のindex.css/tokens.cssの分担を維持し、別の手書きJSONトークン台帳を増やさない。
値→用途→部品→画面の一方向。例えば「主要操作色」と「危険操作色」は現時点で同じ色でも用途が違うため、名前まで統合しない。
明暗と画面幅による差は、正本内で条件を明示して管理する。レスポンシブな値の切り替えは重複違反に数えない。

JS側へ数値が必要な既存iconSizes.ts等は、正本CSSから生成する派生物へ移す案。手編集を禁止し生成差分を検査する。ブラウザーで値を取得するグラフは、テーマ切替を追跡する共通の読み取り口を設ける案。既存のgetChartColorsの固定色フォールバックと色文字列への40付加を各ページで複製しない。これらの具体的な生成方式・変換APIは個別仕様で確定するまで実装不可。

### D. 部品の形を一つにする

| 種類 | 定義元の案 | ページが選べるもの | ページが決めないもの |
|---|---|---|---|
| ボタン | 既存Button.tsx/Button.css、重複CSSを一本化 | 用途variant、size、disabled/loading、文字、実行処理 | 任意の色・角丸・字体・内側余白 |
| 入力・プルダウン・複数行入力 | TextField/Select/TextareaとFormField.css | 入力値、label、size、状態、選択肢 | 枠線・背景・文字・矢印を自前描画 |
| トグル | 新規共通Toggle（既存同名部品なしを確認） | label、checked、disabled、変更処理 | ページ専用トラック・つまみ・移動量 |
| 表 | 既存DataTableとDataTable.css | 列・データ・並べ替え・選択・density・ページ送り | ヘッダー背景・行罫線・文字・角丸を個別上書き |
| カード・バッジ | 既存Card/Badge | 登録済みvariant/density、内容 | 色・形をpage CSSで再定義 |
| タブ | 既存Tabs | items、activeKey、切替、既存variant/size | page専用タブの外観定義 |
| モーダル・ドロワー・空状態 | 既存部品へ責務を集約 | 開閉・内容・サイズ・操作 | 別系統の同等部品を増設 |
| 見出し・操作台 | 既存PageLayout/ContentToolbar | 見出しと左右の内容 | 共通枠内部の余白・見出し位置の上書き |

現在components/loading配下にもModal/Drawer/EmptyStateが存在するが、同名だからと直ちに削除しない。import元・開閉仕様・フォーカス・使われ方を個別照合し、公開入口を既存正本へ接続する。

通常ボタンとカレンダーのセル・会話行のような別用途を同じ外観にしない。特殊用途も部品として登録し、外観定義をページへ逃がさない。例外には用途・所有部品・利用箇所・検証を記録する。

### E. 基準となる外観

確定値があるものは既存component-standard.mdと後続の承認済み子仕様を基準にする。
- 通常ボタン角丸は同文書の6px（comp-btn-radius）。現行primaryの4pxとの差は「同値置換」ではなく、統一に伴う意図した変更として見本確認に出す。
- カード角丸8px・標準内側余白24px、compact/mobile16pxを基準。業務ページが勝手に選ぶ独自寸法を残さない。
- 表のdensityは既存compact/default/relaxedを維持。列幅、長文、折返し、横スクロールを壊さない。行高トークンを長文を切り捨てる固定上限と解釈しない。
- トグルは共通CSSの40×22pxを初期の見本候補とする。つまみ16px・余白3px・移動18pxは既存値。最低44pxの操作領域は見えるトラックとは別に確保する案。最終仕様は見本・ラベル・キーボード確認後に確定する。
- 色の全面変更は行わず、既存の用途色と明暗定義を基準とする。個別部品で異なる色を採用する場合はその用途を説明して見本に出す。

ここは候補と確定値を区別する。未確定のトグル外観を「PO承認済み」と記録しない。

### F. ページからの上書きを防ぐ

1. 共通部品の見た目は部品自身で決める。任意style/classNameから内部の外観を変更する入口を、互換移行後に閉じる。
2. 外側の配置・伸縮はPageLayout/ContentToolbar等のコンテナで扱う。見た目の変更と外側の配置を混同しない。
3. データ由来の色や進捗率は登録済みの用途に限る。ユーザーが選ぶ色・グラフ値を固定トークンへ無理に変換しない。
4. field-sizeの高さ・幅は既存の独立選択を維持し、部品へ正式な指定方法として渡す。ページCSSによる内部上書きを許す理由にはしない。
5. 生タグの禁止は部品の実装本体を除外する。Button内部のbuttonやDataTable内部のtableまで禁止しない。

### G. 見本と検査

見本の正しさ:
- Storybookとアプリで必要なglobal CSS・フォント・テーマを揃える。現在preview.tsxはindex.cssだけを直接importし、アプリはcomponents.cssとloading-animations.cssも読み込む。実表示が同じかは未確認。
- 各部品のCSSは該当部品自身から到達させる。見本ページ専用の模倣CSSを作らない。
- 初回の基準画像はPOが見て承認し、未確認の現行画面を自動的に正解画像にしない。

検査対象: pages/features/業務用componentsを含むfrontend/src全体。デザイン見本も材料参照と部品参照の規則を守る。テストfixtureの意図的違反は専用の除外範囲で管理。
- トークン: CSS/TS/TSX/SVG/data URIを含め、生値・未定義参照・循環参照・同一条件内の多重定義を検査。色名やrgba、%23も扱う。明暗・media条件の違いは合法とする。
- 部品: 許可された実装元以外のnative要素、共通部品内部を対象にするpage CSS、任意の装飾styleを検査。
- 利用箇所: 単なる件数上限だけでなくファイル・要素・用途を記録。同数の別違反への入れ替えを見逃さない。
- 見本: components直下だけでなく登録部品と全状態を照合する。storiesのファイル存在だけを視覚合格にしない。
- 陰性/陽性ペア: 禁止例を入れて失敗することと、トークン参照・部品本体・正当なmedia切替で通ることを同じ検査で確認する。

既存違反を一度に全部ブロックして他セッションを止めない。未移行一覧を実測から固定し新規逸脱は拒否、移行した対象は再導入不可とする。例外の追加でKGIの分母を小さくしない。

### H. 段階的な移行・検証

| 段階 | 変更の単位 | 入る条件 | 終える条件 |
|---|---|---|---|
| 0 設計・見本の基準確定 | 共通部品の値と責務、見本の読み込み経路 | 現行の仕様・定義・使用箇所を照合 | 未確定の外観・矛盾が解決、見本確認済み |
| 1 材料・入口 | 色/非色/アイコン、検査の対象範囲 | 個別仕様と許可されたファイル一覧 | 手編集元各1か所、派生値一致、違反ペア検査通過 |
| 2 ボタン | 共通CSS経由292箇所から用途別に小分け | type/submit、disabled、loading、aria、処理の対応表 | 同一外観と操作を確認、移行範囲で再発拒否 |
| 3 トグル・入力 | トグル8箇所と個別入力 | Toggle仕様・操作領域・全状態、入力の対応表 | 開閉/入力/保存の動作維持、外観一元化 |
| 4 表・カード・タブ等 | 部品ごと、1ページ1部品 | 列固定・行選択・ページ送り等の互換確認 | データ・機能が同一、見た目が基準一致 |
| 5 全利用箇所の波及確認 | 全登録部品・全登録利用先 | 各移行範囲が検証済み | KGI6項目の実測記録とPO確認が揃う |

既存migration.mdの小口化に従う。残りを未調査のまま一枚の実装カードに詰めない。各段階の実装カードは対象ファイル・変更前後・保持する動作・試験を確定後に発行する。

見た目の検証条件案: light/dark × 390/767/768/1279/1280px。幅の境界は既存仕様、390pxは狭幅代表の提案。
通常・hover・focus-visible・disabled・loading・selected/on/offのうち部品が持つ状態を登録。非該当状態を水増しして試験数にしない。
日本語/英語、長文・空データ・多数行、keyboard/タッチ、画面の開く順番も確認する。

### I. 受入条件と確認方法

| 条件 | 検証 | 完了証拠 |
|---|---|---|
| 材料の手編集元各1 | 条件付き宣言を区別した定義表と生成差分検査 | 定義元一覧・検査出力 |
| 同用途の外観が同一 | 同じ状態・幅・テーマで計算済みスタイルと画像比較 | 比較対象一覧、差分結果 |
| 一括変更が届く | 検証環境でトークン/部品を1か所変更し全利用箇所を再取得 | 対象数と反映数が一致する記録 |
| 操作を壊さない | 既存E2E、変更した部品の操作試験 | 実行した試験結果と未実施の区別 |
| 新規逸脱を止める | 禁止例/正例のペア、同数置換も試験 | 期待したpass/failのログ |
| 全部品を見本確認 | 登録種類・状態とstoriesの対応を照合 | 未掲載0、POの実際の確認記録 |

### J. 代替案とリスク

| 案 | 採否案 | 理由・影響 |
|---|---|---|
| 値だけを変数へ置換 | 単独では不採用 | 個別selectとトグルの組合せが残り、形が揃わない |
| CSSの末尾から一括上書き | 不採用 | 定義元が増え、特殊操作や読み込み順へ影響する |
| 新UIライブラリへ全面移行 | 現段階では不採用 | 既存部品が実在。置換コストや機能互換の比較根拠がない |
| 既存部品とトークンを正本に一本化 | 推奨 | 現行設計を活かせる。個別機能の照合と段階移行は必要 |

一括変更の利点と同時に影響範囲も広がる。既存の外観と基準外観の差を明示し、変更範囲ごとの比較・操作試験で守る。失敗時は通常の修正PR/戻しPRで対応し、強制push・本番直編集をしない。

### K. 接触面と維持する担当

- 人: POが外観見本と実装結果を確認。設計担当が根拠を揃え、実装担当がレビュー済みカードを実行。
- エージェント: frontend限定。バックエンド担当へ変更を委ねる必要が出た時点で別設計。並行作業台帳を確認し同じファイルの変更を取り込む。
- 機械: 既存frontend-check、ui-governance、design-token-guardを活かし不足検査を追加する案。CIや保護設定は今回変更しない。
- データ: API契約・保存先・DBに変更なし。表示用propsと業務コールバックの接続維持を検証。
- 本番: UI移行の本番反映は別承認。設計合格・見本合格を本番GOと解釈しない。
- 外部: 既存外部APIを呼ぶ操作の意味を維持。新サービス契約・外部送信なし。

## 維持の仕組み（2026-09-10案）

守り手: `.github/workflows/frontend-check.yml`、`.github/workflows/ui-governance-gate.yml`、`.github/workflows/design-token-guard.yml`、既存component-standard.md、部品別計画と移行台帳。
不足する検査が実装されるまでは設計担当・Reviewerが変更差分と登録使用箇所を人手で照合する。現行CIだけで全保証できるとは記載しない。

### L. 公式資料・自己審査・未決事項

Context7 MCPはツール一覧から利用できなかった。起動指示の代替許可に従い2026-09-10に公式資料を直接確認。
- [Storybook Styling](https://storybook.js.org/docs/configure/styling-and-css): previewへのglobal CSS importとアプリのスタイル構成に合わせる説明。導入成功率の証拠ではない。
- [W3C Switch Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/switch/): 二値の役割とlabel/keyboardの要件。Toggleの細部設計で照合する。
- [DTCG glossary](https://www.designtokens.org/glossary/): tokenとaliasの用語確認。新しい保存形式導入の根拠にしない。

Planner: 全体方式の草案作成済み。
Architect（同一AIによる自己審査）: REVISE。採用不可ではなく、以下を埋めるまで実装可能と判定しない。
1. 外観候補の実表示未確認。ブラウザー指定スキルはNode REPL js経由の接続を指定するが、そのツールがセッションにない。代替ブラウザーで制約を回避しない。
2. 全使用箇所の業務動作・例外と最終部品への対応表は未完成。292箇所も自動置換可能と断定しない。
3. トグルの最終外観と操作領域、JS派生値生成方法、移行対象ごとの検査仕様は詳細化が必要。
4. 新規カード未発行。ADR-113/正式カードチェックは具体的な実装カードの発行前に行う。

PO承認は未取得、文書はローカル草案、PR未提出、製品実装未着手。


### M. 外観見本とトグルの接続仕様（未承認追補）

[明暗の外観見本](../../handoff/design-system-recon/evidence-20260910/proposed-controls.svg.png)。既存トークン値を読み取って作成した静的提案。実部品のスクリーンショット・Storybook・全状態の合格画像ではない。PNGを目視し、左右の切れと文字の重なりがないことを確認。資料内の取引先と金額は架空。

見本の6px角丸、40×22pxトグルは§Eの候補を表示。表は外観の方向を示すもので、行高・列幅・文字サイズを全用途の確定値として追加しない。実装時の見本帳は実部品を直接使用し、このSVGの模倣CSSを製品へ転記しない。

色の追加測定: [計算値](../../handoff/design-system-recon/evidence-20260910/contrast-proposal.json)。sRGBを0.04045の境界で線形化し、相対輝度の重み0.2126/0.7152/0.0722、(明るい輝度+0.05)/(暗い輝度+0.05)で算出。半透明・重ね合わせを含まない指定色2色の計算であり、全画面適合判定ではない。

| 指定色の組合せ | 比率 | 判定・提案 |
|---|---:|---|
| 現行dark主要: 白 / #5b8dd9 | 3.356 | 通常文字の4.5に未達 |
| 提案dark主要: #0f172a / #5b8dd9 | 5.319 | 通常状態の見本に採用する案 |
| 同じ文字と現行hover背景#4d7fc8 | 4.408 | 未達。全状態の色仕様は未確定 |
| 現行light危険色#e53e3e / 白 | 4.126 | 通常文字の4.5に未達 |
| 提案light危険文字#9b2c2c / 白 | 7.526 | 見本に採用する案 |

基準は[W3C Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)を2026-09-10に直接確認。表示は丸めているが判定は丸め前。無効状態の例外と通常文字を混同しない。根拠の色はsrc/index.css、主要ボタンの色参照はsrc/components.css:54。globalなon-accentを書き換えず、部品用途の前景色トークンを追加する案。hoverを含む色の組合せが全て確定するまでカード発行不可。

#### トグル8 JSX箇所の動作対応

行番号は基準6e133572のfrontend/src以下。繰り返し表示されるowner行も1 JSX箇所として数える。

| 使用元 | checkedの正本 | 変更時に維持する処理 |
|---|---|---|
| pages/account-settings/PreferencesSection.tsx:23 | themeがdarkか | changeThemeへdark/lightを渡す |
| pages/schedule/SchedulePageImpl.tsx:303 | draft.allDay | allDay変更と、on時startTime=00:00/endTime=23:59、off時既存時刻維持 |
| pages/schedule/ScheduleSettingsPage.tsx:162 | selfOwner.visible | selfOwner.staffIdでupdateOwner |
| pages/schedule/ScheduleSettingsPage.tsx:217 | owner.visible | 当該owner.staffIdでupdateOwner |
| pages/inbox/InboxSettingsModal.tsx:28 | showRightPanel | 同名設定更新 |
| 同:51 | defaultUnreadOnly | 同名設定更新 |
| 同:64 | browserNotifications | on時許可要求、denied時通知して更新せず戻る。それ以外は設定更新 |
| 同:82 | soundEnabled | 同名設定更新 |

Toggleの契約案: checked、onCheckedChange(nextChecked:boolean)、disabled、id/name、翻訳済みlabelを受け取る。内部に別のchecked状態を持たない。native checkboxにswitchの役割と入力自身の名前を与え、ネイティブのSpace操作を維持する。44×44px以上の操作領域を確保する案。外から色・角丸・styleを受け取らない。

通知許可のdefault結果でも現行は設定更新する。金型化のついでにgranted限定へ変えない。非同期処理の前に次のboolean値を確定し、await後のイベント再参照を避ける。API/保存処理はページ側の既存処理を接続する。

受入試験案: 各行のoff→on/on→offで対応処理が1回、owner IDと終日設定時刻が一致、許可deniedで更新0回、その他の既存分岐を保持。部品単体はlabelクリック・Space・disabled・親からのchecked変更・明暗と狭幅を検証。これらは未実行の試験設計。

#### 表の移行境界

既存DataTableは1段ヘッダー・1データ1行を描画する。products/ProductsPageのrowSpan、quote-detail/QuoteDetailPageとinvoice-detail/InvoiceDetailPageの合計colSpan、super-admin/ParseReviewPageの展開行を単純置換しない。共通外観は維持する方針だが、複雑な表の公開APIと全39 native tableの用途対応は未完。列結合・展開・編集の互換仕様がない表を実装カードへ入れない。

#### 追補後の自己審査

Planner: 8箇所の接続仕様と外観見本案を追加。
Architect（同一AI）: **REVISE継続**。通常状態の静的見本は確認済み、実画面未検証。hover色、複雑な表、全件移行表、JS生成方式・検査の詳細が残る。外観方向についてPO確認を求めるが、返答前に承認とは記録しない。製品実装・PR未着手。

### N. CIによる金型ルールの強制設計（2026-09-10・構築仕様草案）

PO応答原文: 「進める、CIでルールが守られる仕組みもなければ構築」。直前の外観方向確認への続行回答として記録する。外観方向で設計続行・CI不足分を構築対象へ追加。全状態・全体設計・実装開始・本番反映の承認とは記録しない。本セッションは設計担当を継続し、CIの製品設定変更は実装担当へ渡す。

#### 確認した現在地

- preflight成功。作業HEAD=6e133572、取得済みorigin/main=5386d664f40aa826e7e3d943b87bb65697d49165。frontend全体、以下の3 workflowと2検査スクリプトの差分0。未コミット設計文書は保持。
- `.github/workflows/ui-governance-gate.yml:6`は非必須と記載するが、GitHub `GET repos/shingo-ops/salesanchor/rules/branches/main`は`UI governance gate`をrequired_status_checksに登録済みと返した。実設定を優先。従来のbranch protection APIは404であり、保護なしとは解釈しない。
- [実設定の取得結果](../../handoff/design-system-recon/evidence-20260910/main-rules-20260910.json)。strict_required_status_checks_policy=true。Rulesetの例外権限まで監査した証拠ではない。
- 同workflowは全main PRで起動し、検査テストと本体を同じ必須jobで実行する。既存枠を拡張する案とし、新しい必須チェック名・Ruleset変更を必須にしない。
- `scripts/check-ui-governance.js:39`はpagesだけが対象。select/input一部/自作tabsの件数増加を検査し、button/table/textareaは対象外。`:51`と`:66`ではgit取得失敗を空結果にする経路がある。解析不能や取得失敗を「違反なし」にしてはならない。
- `scripts/check-design-token-ratchet.sh`はhex件数比較。`.github/workflows/design-token-guard.yml`の対象パスはfrontend/srcだけ。検査自身だけを変更するPRの起動条件も不足。
- `frontend/scripts/check-css-hardcoded-colors.js:24`はbasenameによる正本除外、変数定義行を除外。`frontend/scripts/check-stories-count.js`は直下の見本ファイル存在だけを見る。
- 今回実行した既存検査テストは22成功/0失敗。[出力](../../handoff/design-system-recon/evidence-20260910/ui-governance-recheck.txt)。以下の新規検査は未実装・未実行。

#### 検査の責務と配置案

既存`UI governance gate`を最終集約口とし、内部の責務を分ける。公開job名は維持する。CLI解析とfixture試験は既存Node/TypeScript/CSS解析依存を優先し、依存の直接宣言とlock一致を個別カード前に確定する。ライブラリ仕様未照合のまま実装可能とはしない。

| 層 | 検査するもの | 違反例 | 正当な例 |
|---|---|---|---|
| 材料 | 定義元、名前、参照、条件別の重複と循環 | pageに色値、SVG内%23固定色、別のindex.cssへ逃がす | 正本の素材値、用途別alias、明暗/media切替 |
| 金型 | nativeタグの所有元と利用先、装飾の上書き | featuresで生button、pageから内部radius変更 | Button本体のbutton、外枠の配置 |
| 派生物 | CSS正本から作るJS値の再生成差分 | TSだけ手で寸法変更 | 正本変更後の生成結果一致 |
| 見本 | 登録部品・許可variant・状態とstory対応 | 通常だけあってdisabled/loadingが欠落 | 部品が持つ全状態を登録 |
| 実表示 | 実部品の明暗/幅/操作/比較画像 | CSS読込漏れ、文字コントラスト未達、操作退行 | 基準画像と状態・操作が一致 |

対象はfrontend/srcのCSS/TS/TSX/JS/JSX/SVG、見本も含める。製品用静的assetがsrc外にある場合も読み込み経路から棚卸しして対象登録する。関係ない文章中の色名・ID・数値を装飾値として誤検出しない。字句検索だけで全保証を謳わず構文と装飾コンテキストを解析する。spread/動的class/動的styleが解決できないときは未確認として非ゼロで返し、手動登録された専用入口があるものだけ許可する。

正本の除外はbasenameでなくリポジトリ相対の完全パス＋宣言種別。index.css内の通常CSS宣言まで無条件免除しない。部品内部nativeタグの許可もファイル単位の全面免除でなく、登録部品と要素種別に限定する。

#### 既存違反を残しつつ新規違反を止める

移行中の違反一覧はルール・相対パス・包含コンポーネント・正規化した対象構文・出現数を識別情報とし、行番号は表示補助とする。空行で失効せず、別の要素や属性への変更は新規と判定する。動的処理の互換をこの識別情報だけで保証しない。

比較基準はPRのHEADで自由に増やせる許可一覧ではなく、BASE側の承認済み一覧。HEAD違反はBASE登録の同一項目・同数以内だけ暫定許容。同数でも別内容への置換は不合格。解消した項目をHEAD一覧から削除しなければ不合格。後から再導入するとBASEに項目がなく拒否される。renameは自動免除せず対応表を明示する。

初回一覧登録は現行全体の実測と対照し、件数・各項目の根拠・所有者・移行先をレビューする専用の導入便とする。チェック有効化時の自動baseline再生成は禁止。初回分母は残し、移行数と残数を別々に出す。

恒久例外は移行残件と別扱い。例: データ由来の色は専用部品の許可propsを通す。例外には用途/所有部品/試験/根拠を要求。ページの`ui-allow`コメント追加だけでは新規除外しない。正当な新例外・新部品の登録経路はルール変更のレビューとして扱い、一般PRが自己免除できる入口を作らない。

#### 必須jobの動作契約

1. main向け全PRでjob自体は必ず起動。対象差分0でも「解析対象なし」と明示した成功を返し、pathsで必須jobを消さない。検査・登録表・workflow・lockのみ変更したPRも検査する。
2. BASE/HEAD存在確認、対象ファイル列挙、構文解析を行う。欠損SHA/取得失敗/解析失敗/不正な登録表はexit2、違反はexit1、全条件を満たした場合だけexit0。削除ファイルと読み取りエラーを区別する。
3. fixture試験と実ソース検査のどちらも必須。同一PRの実際に検査したSHA、検査版、対象数、残件数、ルールID、ファイル行、推奨部品をログとJSONに残す。秘密情報・全ソースは出力しない。
4. continue-on-error、失敗の握り潰し、条件分岐による必須検査skipを禁止。期限切れ・欠落した画像比較環境を合格にしない。
5. 画像の基準更新は自動承認しない。意図した外観変更と比較画像をPO確認に出す。CI成功だけでPOの外観判断を代替しない。
6. 検査コード自体の無力化を同じ検査だけで完全防止とは称しない。既存Reviewerがworkflow/検査/許可一覧の差分とfixture結果を確認する。外部設定の保護強化が必要なら別承認の対象とする。

#### 実装後に必ず示す対照試験（まだ未実行）

| ID | 不合格を確かめる変更 | 合格を確かめる対照 |
|---|---|---|
| CI-01 | pages/features/業務components各1箇所へ生button追加 | 登録Button本体のbutton |
| CI-02 | 違反1件を別違反1件へ置換 | 同じ対象の前へ空行追加 |
| CI-03 | page CSSで共通部品の角丸を上書き | 外側コンテナの配置変更 |
| CI-04 | 生hex/rgb/色名/SVG %23色を装飾位置へ追加 | 正本alias/currentColor/文字列ID |
| CI-05 | 偽index.cssへ素材値追加・正本内重複・循環 | 正本の明暗/media条件差 |
| CI-06 | 派生TSだけ編集 | CSS変更と一致する再生成 |
| CI-07 | 入力SHA欠損・git失敗・CSS/TSX解析失敗 | 正常取得・解析、製品削除PR |
| CI-08 | HEADで例外追加して新違反を隠す | 登録済み例外の同一用途 |
| CI-09 | 消した違反を次PRで再導入 | 解消と一覧削除 |
| CI-10 | ネストした部品の必須story状態を削除 | 全状態登録・実部品参照 |
| CI-11 | 実部品のglobal CSS importを欠落 | アプリと見本の読込一致 |
| CI-12 | 色1か所変更で一部利用先が追従しない | 登録全利用先で変更反映 |

CI-01〜10は静的検査便、CI-11〜12は実表示便で成立させる。全部が実装済みになるまで全体の強制完成と宣言しない。単に既存22テストの成功を再掲して代用しない。

#### 構築順・受入・審査

第一便: 検査器の純粋関数化と新fixture、全体走査と初回一覧のレビュー。第二便: 既存必須jobへ接続し、実PRで意図的違反が赤になる証拠を取る。第三便以降: 部品移行に合わせ一覧を減らし、見本・実表示を必須jobに組み込む。既存チェックの削除は新旧対応と検出力を照合後、専用差分で扱う。

実装対象候補: scripts/check-ui-governance.js、scripts/tests/test-ui-governance.js、frontend/scriptsの既存token/story検査、frontend/package.jsonとlock、.github/workflows/ui-governance-gate.yml、および正式な違反一覧の保存先。保存先/解析依存/実表示実行基盤と各便の変更ファイルは個別設計で確定する。workflow-lint.yml/deploy.yml/Ruleset/secretsは対象外。

完了条件: 全対象種別の対照試験が期待通り、通常PRで必須jobが実行、違反PRで失敗、修正PRで成功、移行済み対象で再導入が失敗。そのPR URL・SHA・チェック結果を保存する。現在の設計文書保存をCI構築済みとはしない。

Planner: CI不足分の構築設計を追補済み。
Architect（同一AIによる自己審査）: REVISE。既存必須jobの拡張方針は実設定と整合する。解析依存・登録表形式の詳細・複雑な動的CSSの所有判定・実表示基盤が未確定で、実装カードは未発行。自動検査の保証範囲と人の承認を区別した。次は静的検査便の詳細仕様を確定する。


### O. CI第一便の設計確定

POの「合意進める」をCI補強方針への合意として記録。[第一便設計](ci-guard-design.md)をmode: handoffで作成。異常BASEと正常対照の両方が現行exit0となることを実行確認し、取得失敗をexit2にする仕様・16受入ID・2実装ファイルへ限定。同一AI自己審査APPROVEは第一便だけ。全体のREVISEを解除しない。正式カード未発行・実装未承認/未着手。

後続ではADR-144が現在許可するui-allowとpages限定を変更するため、既存ADRの承認済みDecisionを黙って上書きせず、後続ADR案または明示的改訂案を設計と一緒に審査する。方針合意だけで既存例外を即時失効させない。

### P. ボタンの状態別配色・読みやすさ（設計候補を更新）

§Mの通常状態見本をもとに、hover/active/selectedと背景を追加して計算した。見本方向の続行合意を、今回追加した全状態のPO承認と同一視しない。

根拠: [190組の指定色計算](../../handoff/design-system-recon/evidence-20260910/button-color-matrix.json)、[再計算手順](../../handoff/design-system-recon/evidence-20260910/button-color-matrix.py)。基準6e133572の保存済みCSS宣言表を入力とする。再測定時は宣言表も対象SHAに合わせて再取得する。

#### 状態と色の契約案

primary/secondary/ghost/danger/outline/tabの6種類、normal/hover/active、tabのみselected、light/dark、背景5種類（bg-primary/surface/subtle/hover/active）。計(6×3+1)×2×5=190組。重複色を含む「状態と背景の組合せ数」であり190画面の実測ではない。

| 用途 | 文字 | 通常背景 | hover背景 | active背景 |
|---|---|---|---|---|
| primary light | on-accent | accent | accent-hover | accent-hover |
| primary dark | #0f172aの素材参照 | accent | #7baee0の素材参照 | #7baee0の素材参照 |
| secondary | text-secondary | bg-surface | bg-subtle | bg-hover |
| ghost/outline | text-primary | 透明・親背景 | bg-subtle | bg-hover |
| danger | danger-text（両テーマ） | 透明・親背景 | danger-bg | danger-bg |
| tab未選択 | text-secondary | 透明・親背景 | bg-subtle | bg-hover |
| tab選択 | lightはaccent、darkはtext-primary | link-active-bg | 選択背景を維持 | 選択背景を維持 |

selectedはhover/activeより背景・文字の優先度が高い。通常ボタンの押下中activeとtabの選択済selectedを混同しない。disabled/loadingは操作可能な状態より優先し、hoverの色変更を無効にする。loadingはラベルとスピナーが読めるよう通常の組合せを維持する案。disabledを文字コントラストの適合件数に含めないが、識別可能な見本確認は別途必要。

#0f172aは現行darkのbg-primary、#7baee0は現行darkのlinkと同じ素材値。ボタンを「リンクの意味」に依存させないため、新しい素材名をindex.css内に各1か所置き、既存の用途名とボタン用途名がその素材を参照する。命名案: palette-ink-deep / palette-blue-soft。既存のlinkやbg-primaryの見た目はこのalias化で変えない。値をもう一つ手書きする案ではない。部品のCSSにhex値を置かない。

primaryの前景とhover背景には部品用途のtokenを追加する。全体on-accent/accent-hoverを書き換え、他部品の外観を一括で変えることはしない。ボタン全体の角丸は既定6px、通常/hover/activeで寸法を変えない。

#### 計算結果と修正理由

初期案のdanger dark文字f87171は、親背景bg-hoverで3.743、bg-activeで2.739となり通常文字4.5に未達だった。現行danger-text=fecacaへ切り替えた候補では190/190が4.5以上、最小5.064879620284947。dark primaryの旧hover背景との4.408未達も、上表の素材へ変更した候補で解消。

通常文字の基準は[W3C Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)。指定色の相対輝度から計算、比較時の四捨五入なし。画像・任意背景・祖先のopacity/filter・半透明overlayは対象外で、これらの上に透明ボタンを置く場合は専用surfaceを定義して再検証する。全画面のWCAG適合を宣言しない。

#### 実装時の確認

- approved state表からCSSを作り、実部品の計算済み文字色/合成背景を取り出して同じ基準で再測定する。静的SVGだけで合格にしない。
- focus-visibleは全variantで見えること、選択済tabでhoverしても選択状態が消えないことを試験。focus ringの色・太さ・背景との関係は次の部品詳細で確定する。
- Button.tsxのloadingが使うSpinnerはonAccentによる白固定がある。primary darkの前景と矛盾しないようButton内ではcurrentColorに追従させる接続を設計し、Spinner全利用先を無断変更しない。
- 日英の長い文言、iconOnly、disabled、loadingのサイズ・ラベル・フォーカスを確認する。190組の計算は操作試験の代わりにしない。

自己審査: 配色候補の指定色条件では合格。Button全体はREVISE（実部品・focus・Spinner・全利用箇所の対応未完）。PO承認済みの最終画像としては未登録。

### Q. Buttonのfocus・loading契約案

基準6e133572のButton.tsx:73はnative button、disabledはdisabled||loading、aria-busyはloading時true。:81でSpinnerのonAccentをprimaryに指定する。Spinner.tsxは現行label既定値が英語Loading。loading-animations.css:66はaccent色、:95はon-accent色で描画し、:538でreduced-motion時に回転を止める。

#### キーボードとフォーカス

- native buttonを維持し、Enter/Space用の独自onKeyDownを重ねて発火回数を増やさない。type/name/value/formと既存onClickの動作は移行表で維持する。type未指定を一律buttonへ変えるとフォーム送信が変わるため、利用箇所ごとに明示する。
- 全variantでfocus-visibleに2pxの実線、外側offset2pxを設ける案。色は部品用途tokenからtext-primaryへ参照。幅とoffsetの定義元はtokens.css。既存outline以外のvariantにも同じ方式を適用する。
- [focus色の10背景組合せ](../../handoff/design-system-recon/evidence-20260910/focus-color-pairs.json)で指定色の比率は最小6.916973995632248。これは輪郭色と背景の計算で、輪郭が隣の要素やoverflowに隠れない証明ではない。
- 2pxの間隔部分に親surfaceが見える前提。部品の外側4pxを親で切り取らない。表のスクロール端・モーダル端・隣接ボタンでTab移動し、輪郭が欠けないことを実表示試験に含める。
- disabled/loading時のnative disabledは今回維持。処理開始時にフォーカスがどう変わるか、処理完了後にどこへ戻るかは現物試験に含める。非同期完了時の自動focus移動を共通Buttonへ追加しない。ダイアログ遷移等の責務は既存の呼出側に置く。
- Buttonのvariant=tabは現行aria-pressedを使う選択ボタン。外観名だけを理由にrole=tabへ変更しない。本物のタブへ移すときはTabsの操作契約と一緒に移行する。

#### 読み込み表示

Spinnerにtone=inheritとdecorative=trueの正式な指定を追加する案。既存の既定動作は維持し、Button内部だけが指定する。inherit時は色の正本をButtonのcurrentColorに限定し、枠の一部をtransparentにして回転を示す。Spinner独自のonAccent白固定をこのモードには併用しない。装飾表示ではrole=status/既定Loadingラベルを出さずaria-hidden=trueとし、Buttonの名前とaria-busyを使う。

loadingText未指定時は元のchildrenを維持。指定時は翻訳済み文言を使用する。iconOnlyは操作のaria-labelを維持し、busyをラベルの代わりにしない。loading中のクリック・Enter・Spaceで業務処理を追加実行しない。これはloadingがpropsへ反映された後の契約であり、反映前の連打対策・API冪等性をButtonが保証するという意味ではない。

reduced-motion時の既存回転停止を維持する。静止してもラベル/aria-busyで処理中と判別できる。スピナー用CSSが実部品から到達するようにし、Storybookだけ専用CSSを複製しない。

受入項目: 6variantのTab/Shift+Tab、Enter/Spaceで各1回、type=submit/buttonの区別、loading/disabled時0回、busyとaccessible name、明暗で前景追従、reduced-motionで回転なし、overflow境界で輪郭の欠けなし。テストは未実行。指定色計算の合格と操作試験の合格を分ける。

公式資料: Context7未提供のため許可済み代替で[W3C Button Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/button/)と[Focus Visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html)を2026-09-10に確認。2px/offset2pxは本設計案であり、Focus Visibleの基準本文が指定する唯一の寸法とは説明しない。

### R. 表の共通化方式と保持する機能

全srcのnative table39か所を構文で再走査。[構造一覧](../../handoff/design-system-recon/evidence-20260910/table-structures.json)。セル結合属性を持つtable16、tfootを持つtable2、native入力/ボタンまたは対象イベントを持つtable28。共通DataTable内部も含む。カスタム部品内部の動作まで追跡する検査ではない。colSpanは空状態にも使うため、16をそのまま複雑な表の件数とは呼ばない。

#### 推奨する構造

既存DataTableは「列とデータを渡す便利な入口」として維持。その下に、表・ヘッダー・行・セル・合計欄の共通表示部品を置く。複雑な表はその表示部品を直接組み合わせる。どちらも外観CSSとトークンは同じものを参照する。

候補の配置: components/table/Table.tsxとTable.css。新しいデザインシステムやライブラリを別立てにしない。DataTable.cssの表外観をここへ移し、DataTable側には並べ替えやページ送り等の固有操作だけ残す。移行途中に2つのCSS定義を手編集しない。class互換が必要な間も一方から参照する。

| 表示部品候補 | 受け取る情報 | 部品が決めること |
|---|---|---|
| Table | accessible label、density、children | 枠・基本文字・スクロール枠 |
| TableHead/TableBody/TableFoot | 内容 | 適切なthead/tbody/tfootと共通背景 |
| TableRow | selected、disabled表示、stripe、イベント | 選択・ゼブラ・無効時の用途色 |
| TableHeaderCell | rowSpan/colSpan/id/scope/headers、align、列幅 | 共通余白・文字・罫線 |
| TableCell | rowSpan/colSpan/headers、align、内容 | 共通余白・罫線・縦位置 |

列幅は内容上の必要に応じて渡せるが、任意の背景色・角丸・内側余白・style/classNameは公開しない。列幅に許す表現とstickyの境界は既存の各表との対応を確定してから公開APIを固定する。propsを渡せるだけで全互換と判定しない。

#### 維持する具体的な機能

| 代表箇所 | 実物の構造 | 維持する契約 |
|---|---|---|
| products/ProductsPage.tsx:286 | 2段ヘッダー・1商品2行、選択セルrowSpan2 | 商品単位の選択・ゼブラ・名前sort・編集権限判定・並べ替えdrag/dropを維持 |
| quote-detail/QuoteDetailPage.tsx:175 | tfoot内colSpan6 | 小計・重量・送料・税・合計の値、表示順、書式を変更しない |
| invoice-detail/InvoiceDetailPage.tsx:305 | 上記と同型、換算行が条件付き | JPY/USD換算行の表示条件・数値・通貨を維持 |
| super-admin/ParseReviewPage.tsx:494 | 入力・商品候補展開・メモ別行、colSpan7 | 展開状態・選択商品・入力draft・skipped/isFinalの編集可否を維持 |
| components/DataTable.tsx:168 | 1段ヘッダー、通常1データ1行 | sort/select/pageの制御型props、空状態colSpanを維持 |

商品2行のゼブラはDOMのnth-childではなく同じ商品グループのstripeを2行へ渡す。rowSpanのある行の移動やhoverで別商品に見えることを防ぐ。チェックボックスクリックの伝播停止、並べ替え中の編集遷移抑止を接続表に含める。

不規則ヘッダーは各セルと見出しの関係をscopeまたはid/headersで明示する。商品マスタは同じ列の上下が別項目なので、単純にcolgroupと断定せずセル別headersの対応表を作る。表instanceごとにIDを分け、同じ画面に2表置いても重複させない。native tableをrole=gridへ変更しない。

在庫表については[ADR-093 在庫表等再設計](../../adr/ADR-093-inventory-table-product-master-redesign.md)の列集約・狭幅表示を保持する。ADR一覧には別のADR-093もあるためファイル名で特定した。全ての表へDataTable既定min-widthを強制し、個別仕様の狭幅表示を壊さない。

#### 移行順と検証

1. 共通表示部品を導入し、既存DataTableのpropsを変えず内部を接続。通常/空/選択/sort/pageの比較を実施。
2. 見積と請求のtfootを移行し、同じfixtureで全表示値と結合セルの位置を比較。
3. 商品2行表示を移行。1/2/3商品、選択、sort、drag、権限なし、長文・狭幅で比較。
4. ParseReviewを移行。展開/折り畳み、入力値保持、final/skipped、メモ・商品選択を比較。
5. 残りは39件の構造一覧へ利用目的と移行先を追記して小口移行する。

既存E2Eにはfrontend/tests-e2e/super-admin-parse-review.spec.ts等が実在する。存在確認だけで十分な試験とはせず、上記操作とのアサーション対応を確定する。API/保存値を変更せず、UIで送る値も移行前後で比較する。

公式根拠: [W3C irregular table headers](https://www.w3.org/WAI/tutorials/tables/irregular/)を2026-09-10確認。既存39表の実測とDataTableの実装を根拠に、外観共通部品を下層へ置く案を選択。外部企業事例はこの互換性の証拠にならないため不要。

自己審査: REVISE。Buttonのfocus/loadingと表の方式・代表5箇所の保持条件は具体化済み。Table公開APIの列幅/sticky・全39件の操作対応・実表示試験が未完。第一便CI取得エラー修正の設計合格は維持する。製品コードは未変更。

### S. 表の幅・スクロール・固定ヘッダーの契約案

対応先は[migration.mdのTB-01〜39](migration.md#2026-09-10-表39か所の移行対応案)。表の操作属性をonSelectまで再走査し、39/39へ移行先と維持する処理を割り当てた。自動生成の一覧だけで業務互換を合格にしていない。

#### 方式の整理

既存38表をDataTableのcolumns形式へ変換する作業は初回統一の必須条件から外す。Table表示部品で行構造・イベントを維持して置換する。既存DataTableも同じTable表示部品を使う。これにより外観の編集元を一つにしながら、業務処理の移植量を抑える。将来のDataTableへの整理は必要になった時の別便。

#### 公開する配置指定

- Tableのdensityはcompact/default/relaxed。幅の方式はcontent（内容に合わせる、table-layout:auto）とfixed（列定義に従う）の2つ。全体幅は100%。既存DataTableはcontentと現在のcomp-table-min-width=480pxを維持する。
- 生tableからの移行は現在の幅指定を最初に記録。480pxを全てへ強制しない。minWidthは共通の登録値名を渡し、ページ独自の直接指定を増やさない。
- 列のwidth/minWidthは列データとして扱う。現在のDataTableColumn.width文字列の公開互換は第一移行で維持し、後続の型制限へ勝手に混ぜない。Table表示部品の新規入口は登録列幅tokenとautoを基本とする。データに由来する可変幅は所有部品登録が必要。
- 外側の余白・配置はページのコンテナで決める。内側の色/文字/罫線/角丸/セル余白はTable側だけが決める。任意のclassName/styleで内部へ上書きしない。

#### スクロール枠

TableViewport候補をTable表示部品群に含め、角丸・枠線・overflowをこの枠へ一度だけ置く。table自身にoverflow:hiddenを置かない。既にページに枠がある場合はその枠を置換し、スクロール枠を二重に増やさない。

- 通常: 横スクロールを必要時だけ許可。縦の高さは内容。
- 高さ制限あり: 外側レイアウトが使える領域を渡し、Viewportがその中でoverflow:autoを管理する。全ページ共通の固定高さにしない。
- 初期互換値: Productsはcomponents.css:293のmax-height calc(100vh - 18rem)、ParseReviewはParseReviewPage.css:117のcalc(100vh - 22rem)。この差は表示領域の差として登録し、ページCSSが表内部を上書きする理由にはしない。
- 18rem/22remは既存の予約領域であり、最適な画面高を実測した値とは称しない。小さい高さや拡大表示で領域が潰れる場合の対応は実表示の受入で判定する。

#### 固定ヘッダー

- TableHeadにsticky指定を公開し、TableViewportの上端へ固定。2段ヘッダーはthead全体を固定して、2段目のtop位置をページで手計算しない。
- 不透明な共通ヘッダー背景・共通のz-index・下辺の罫線をTableHead自身で定義する。表示行が透けたりdropdownより前へ出たりしないことを確認する。
- Productsの現行thead stickyとParseReviewの現行th stickyを共通契約へ揃える。ParseReviewでは実装方式が変わるため同値置換とは呼ばず、見出しの位置・罫線を画像で比較する。
- 縦スクロール開始前/途中/末尾で、ヘッダーがViewportをはみ出さず固定されることを確認。横スクロールでは見出しと列の位置が一致することを確認。
- 商品2行のrowSpanセル、長文ヘッダー、メニュー/入力のフォーカス、本文と表が並ぶParseReviewの左右配置を試験する。

[CSS Positioned Layout Level 3](https://www.w3.org/TR/css-position-3/#sticky-pos)のstickyとscroll containerの関係を2026-09-10に確認。参照した版はWorking Draftであり、これだけでブラウザー実装互換を証明しない。Context7未提供のため許可済み代替を使用。既存CSSの実物と実表示試験を併用する。

#### 自己審査

REVISE。39か所の移行先と操作属性の対応を保存し、既存構造を維持する移行方式・代表2表の固定表示契約を確定。全表の装飾属性→共通props対応、実表示、各便カードは未完。実装の範囲を曖昧なまま発行しない。第一便CI設計のAPPROVEは維持する。

### T. 表の装飾を共通指定へ移す契約案

根拠: [表内属性の記録](../../handoff/design-system-recon/evidence-20260910/table-appearance.json)。39個のnative table内のtable/thead/tbody/tfoot/tr/th/tdにはstyle180属性、className59属性。180はプロパティ数・違反数ではなく、外側配置・列幅・動的値も含む。data-testid28、商品stripe属性2は別集計。

追加経路: CompaniesPage.tsx:422とContactsPage.tsx:414がDataTable.rowClassNameでrow-pending-dedupを渡す。components.css:429付近で警告背景と左線、hover時は通常row-hoverへ戻る。native table39件だけでこの入口を見逃さず、2呼出しを対象に加える。

#### 基準案

component-standard.md §9の角丸8px、横余白16px、行高さ32/44/56pxを継承。高さは長文を切り捨てる上限にしない。本文font-base、見出しfont-sm・semiboldを共有する案。compact/default/relaxedの縦余白は4/8/12px。現行DataTable本文font-smと個別12/13/14px等からの差は意図した変更として比較画像へ出す。

背景bg-surface、見出し背景bg-subtle、罫線border、本文text-primary、補助と見出しtext-secondary。指定色と実表示の通常文字4.5以上を受入条件とし、現行text-mutedを無条件に正解にしない。値は色/非色token、見た目の組合せはTable共通CSSの一か所で管理する。

#### 共通指定

| 対象 | 許可する指定 | 現行から移す内容 |
|---|---|---|
| Cell/HeaderCell | align=start/center/end | 左/中央/右寄せ |
| Cell | emphasis=normal/strong/total/secondary | 太字・合計強調・補助文字 |
| Cell | tone=normal/success/warning/danger/critical | 正負差・未解決件数・診断の強調 |
| Cell | wrap=normal/nowrap/ellipsis | 折返し・1行・末尾省略。完全な値へ到達する表示手段を維持 |
| Cell | numeric=true | 桁揃え。丸めや通貨書式は既存処理を維持 |
| Row | state=normal/inactive/archived/skipped/zero-stock/pending-review | 無効・廃止・除外・在庫0・重複確認の外観 |
| Row | selected/stripe/clickable/draggable | 選択、商品単位ゼブラ、pointer/grab |
| Row | groupPart=single/start/middle/end | 商品2行・メモ行の区切り |
| Cell/HeaderCell | columnRole=selection/actions/content | 選択列幅・操作列nowrap。列幅詳細は§S |
| Empty | columns/children | 空状態colSpan・中央寄せ・余白 |

外側marginはレイアウトへ移す。内部styleのspread/関数戻り値は共通部品へ透過させない。id/headers/rowSpan/colSpan/aria/data-testidとイベントは維持する。セル内の画像・バッジ・入力の外観は各部品の責務にする。

#### 状態の優先度

操作禁止は既存input/buttonのdisabledと業務条件で維持。row.stateだけで操作禁止としない。
zero-stock/pending-reviewは用途背景を保持し、hoverで警告の意味を消さない。pending-reviewの現行hoverが通常色へ戻る点は変更として記録する。
selected単独はinfo-bg。状態背景と選択が重なる場合は状態背景を保ち、選択欄と先頭の共通選択線で示す。
inactive/archived/skippedは行全体opacityを使わず、共通の背景・文字・既存ラベルで区別する案。操作可能な子まで薄くして読みやすさを落とさない。新しい業務上の意味を勝手に追加しない。
複数行の同じ商品/明細はgroup状態を共有。start/middleは下罫線なし、endで区切る。隣接行を別の商品と誤認しない表示を試験する。

#### 意味と判定条件の保持

TcgParallelReportPage.tsx:106のdiffColorはdiff>0がsuccess、diff<-5がcolor-error、-5以上0未満がdanger、0がtext-secondary。toneへ移す場合も閾値を維持する。DiagnosticsDrawerはisHighlighted、TcgLineImportPageはunresolved_count>0の条件を保持する。
統合先を選ぶTB-04〜06は現行warning-bgだが、意味は選択なのでselectedへ統一する提案。TB-11はi<3の順位強調をstrongへ。合計はtotal、換算はsecondary。計算・表示順は変えない。

#### 上書き入口を閉じる手順

rowClassNameの2呼出しをrowState(row)のpending-reviewへ接続してからrowClassNameを外す。DataTable.classNameも利用先を照合し、配置は外側へ移す。旧CSSが内部を上書きできるままCIへ統一完了を登録しない。
各TBの旧style/classを上表prop/外側配置/列幅/専用子部品へ対応付ける。tone/stateの全値、選択との組合せ、明暗・長文・空状態を見本に載せる。

自己審査: REVISE。39表の装飾と追加2経路を確認し、共通props・意味・優先度を設計。DataTable外観入口の全利用先照合と各属性の対応・実表示は未完。第一便CI設計APPROVEを維持。製品未変更。

保存時の記録: 省略表示の候補名にDB命令と同じ単語があり、PreToolUseガードが拒否した。文書のprop候補名をellipsisへ変更。許可解除・DB操作・ガード変更なし。


### U. 表の装飾移管先と上書き入口の照合結果

[属性別の移管先239件](../../handoff/design-system-recon/evidence-20260910/table-appearance-mapping.json)を作成。TA-001〜239に元ファイル/行/属性/式と移管先案を記録。style180＋className59。省略表示・行状態等の提案であり、実装結果ではない。thStyle/tdStyleは実物の定義を読み、rowStyleは商品廃止時のopacity代入を確認して分類した。

Cell.valign=top/middleを許可し、上寄せがある取り込み履歴等を一律中央へ変更しない。ColumnSpecの列幅・本文の意味によるemphasisと、全表共通の文字/余白の基準を分ける。属性の移管先239/239は、値や動作の実表示検証239/239を意味しない。

既存のsrc直接DataTable参照23個の明示属性にはclassName/style指定0、rowClassName2を確認。2個はCompaniesPage/ContactsPageのpending_dedup_review条件。明示属性の照合であり、任意の動的spread・外部importからの参照を証明する値ではない。

移行便は次に分ける。
1. Table表示部品と全状態の見本を作り、DataTable内部だけ接続する。
2. 上記2画面をrowStateへ移し、rowClassNameの公開口を閉じる。classNameを公開APIから外す際はtscで全呼出しを検査し、動的な使用が出れば対応表に戻す。
3. TB-01〜39/TA-001〜239の対象を小口移行し、旧CSSと装飾styleがその範囲で0になったことをCIへ登録する。

実装前の確認カードは正式lint通過済み。design-partner.mdの事前実測手順は実装役からの確認結果を要求するため、同じ設計担当の再測定を他者の報告として代用しない。別AIはPOが委任するまで起動しない。

自己審査: 全件の移管先整理は完了。全体設計はREVISE（実表示・新しい部品propsの最終受入・後続ADR整合・CI登録変更の運用未検証）。第一便CIの設計APPROVEを維持。製品実装未着手。


### V. 最新の実施順序（PO指定）

全体設計を先に完成させる。共通定義・移行・受入方法の確定と設計審査の後に画面統一を実装し、CI追加・補強は最後に行う。CI誤合格防止の先行実装は行わない。§N以降の「第一便CI」は過去の順序であり、本節が実施順序を更新する。既存CIは維持する。根拠: EV-20260910-FRONTEND-MOLD-13。

PRマージ・デプロイまでの依頼は受領。未承認の外観案、実表示、全体設計審査の残件を推測で完了にせず、必要なPO判断を得てから進む。


### W. 材料の互換制約と委任の現在地

[アイコン・グラフ実物照合](../../handoff/design-system-recon/evidence-20260910/icon-chart-audit.md)を受領。ICONの5値はCSSを手編集元とし数値TSへ生成する設計を具体化する。PlatformIconの数値計算を保つため、ICON自体をCSS文字列へ変更しない。生成器の仕様は未確定で、実装可能とは判定しない。グラフの残量色はページで文字列加工せず用途色へ集約する案。テーマ切替の実表示・ライブラリの受入形式を確認してから方式を確定する。

POは実装・レビュー担当への委任と、検証後のマージ・デプロイまでの続行を許可した。これは未確認事項を完了にする許可ではない。全体設計が合格してから実装役を起動する。CIは最後。実表示を確認する指定ツールが未提供のため、代替のローカル検証経路を確認中。


### X. 画面確認と実装前の重複調査

PO指定により、目視確認は完成後にPOが実施する。ブラウザー指定ツール不在は実装前の停止理由から外す。自動検証とコードレビューを維持し、目視だけはPO確認待ちと記録する。

既存OPEN PR7件の調査により、色/アイコン/Select/色検査の既存案との対応が未整理と判明した。全体設計はREVISEを維持。既存PRの差分を再利用する範囲と今回案に置き換える範囲を確定後に実装カードを発行する。詳細: EV-20260910-FRONTEND-MOLD-15、overlapping-prs.json。


### Y. 統合範囲と原因を追えるマージ順（PO指定）

PO原文: 「今回のフロントエンドのSSOTに関するものはまとめられるものはまとめて良い、ただし不具合発生時に原因が分かるように分離したほうが良いものは分離して順番にマージしてくれ」。既存PR7件との重複を理由とする停止を解除し、差分採用の調査を進める。

採用判断はPRタイトルや古い承認表記だけで行わない。各PRのmerge-base→HEADの差分を特定し、現在mainの実物と比較する。現在mainと古いbranchのtree差分全体を適用しない。既反映の変更は重複適用しない。現在の別機能の修正・作業中の変更は保持する。

順序:
1. 調査・全体設計・移行の根拠を文書PRへ保存。未審査部分を承認済みとは表記しない。
2. 材料の編集元一本化。色の同値alias、用途色、非色token、数値アイコン生成を責任別に分ける。配色・意味を変える変更を同値aliasへ混載しない。
3. Button/リンク外観・Toggle・入力本体の共通化。入力値/ref/submit/イベントは保持。利用先移行は部品ごと小口PRに分ける。
4. Table表示部品・DataTable内部を接続し、39表の対応表で順次移行。行結合・選択・編集・並べ替えは保持。
5. Card/Badge/Tabs/overlay/空状態と特殊用途の所有元を集約。業務処理・フォーカス仕様の変更が必要なら別修正として扱い、外観集約へ混載しない。
6. 全対象のコード/自動検証結果を確認後、最後にCIを追加・補強。既存CIはそれまで維持。

各PRは変更前のmain SHA、採用した旧PRの差分、対象ファイル、維持する操作、検証コマンド/出力、戻し対象のcommitを記録する。前PRのレビューと必須チェックが通りマージされた後、そのmainから次PRを作る。マージ方法はmerge commit。旧PRのcloseは同等の変更の採用/不採用理由と後継PRが確定した後に行い、理由なく閉じない。

目視は完成後にPOが担当し、PO確認待ちを明記する。CI/自動テストをPO目視で代用しない。全体設計の自己審査REVISEは未調査の意味分類・公開API互換と旧PR採用表を詰めてから再判定する。


## 文書保存時の受け入れ基準

調査正本: docs/handoff/design-system-recon/recon.md。以下は調査・設計草案を保存する文書PRの受入条件であり、製品実装の合格とは区別する。全体設計の未決事項は残件として明記する。

| 基準 | 検証方法 |
|---|---|
| 根拠ファイルがPRに含まれる | git ls-treeと参照先の実在を照合 |
| 製品変更が混ざらない | mainとの差分でfrontend/backend/scripts/workflowsが0 |
| 台帳で最新の合意と未完を区別 | 最新の実施順序・PO目視移管・旧PR採否を照合 |
| 証拠の構造を壊さない | JSON解析とTSV全セルの読み戻し一致を確認 |

### Z. 実物照合後の共通部品契約（2026-09-10、設計担当案）

本節は§A〜Yの調査から導いた最新の実装契約案。PO発話の代筆ではない。全体設計の自己審査は末尾で別判定し、文書保存・個別仕様の確定を製品完成とはしない。基準main `d715d998877e899206ba9bb4f82c726fc3175b30`。`git diff --name-only 3bdf33d5 HEAD -- frontend scripts .github` の出力0で既存入力調査の製品基準との一致を確認。

#### 分離する理由と責任

材料値、部品の外観、画面の業務処理を別の責任にする。SSOTは全てを1ファイルに詰める意味ではなく、同じ値・同じ外観の手編集元を1つにする意味。色はindex.cssのテーマ別定義、寸法はtokens.css、アイコン名はconstants/icons.tsx、各部品の外観は各部品CSSを正本とする。ページは値の写しを持たず、用途名・部品propsを参照する。既存ファイルを活用し別のデザインライブラリは導入しない。

同値の色aliasとアイコン数値生成を別PRとし、配色変更はさらに分ける。Button本体と利用画面、入力本体と利用画面、Table本体と各表、Overlay外観と業務イベントを分ける。各PRで問題が起きた場合、そのPRのmerge commitと依存する後続便が戻し対象。前提を含むPRだけ単独で戻して後続を壊さない。変更対象を共有する便は並行マージしない。

#### 入力本体：DOMと値の互換

根拠: [全577要素・属性の調査](../../handoff/design-system-recon/evidence-20260910/input-semantic-audit.md)、同名JSON。実測577は共通部品内部3を含む。8か所のref、onChange566/onBlur39/onKeyDown10/onFocus6、全74selectのchildrenを記録した。

- TextField.tsx/Textarea.tsxに裸のTextFieldControl/TextareaControlを公開。Select.tsxの既存SelectControlを拡張。裸の部品は元と同じinput/select/textareaを1つ返し、div/labelを増やさない。既存ラベル付き部品はその本体を使用し、classNameが外側divに付く既存仕様を維持する。
- React18のforwardRefでnative DOM自体を返す。関数refも転送する。DataTableのindeterminate、検索欄のgetBoundingClientRect、添付のclick/files、送信欄のfocusを保存する。ImperativeHandleで別オブジェクトに置き換えない。
- native属性・イベント・value/defaultValue/checked/defaultCheckedを同じ要素へ渡す。未指定を空文字やfalseで補わない。typeのurl/text、email/text、number/text分岐は元の式を維持する。数値化・整形・API呼出しを共通部品へ移さない。
- SelectControlはoptionsモードとchildrenモードを排他的な型にする。既存options/placeholder処理は維持。childrenモードは元のReactNodeをそのまま出力し、選択肢・空値・disabled・順番・key・value・条件分岐を再生成しない。placeholderの選択肢も新設しない。
- size=sm/md/lgは部品寸法。input/selectのnative数値sizeはnativeSizeで受け、同要素のsizeへ渡す。textareaはnativeSizeを受けず、rows/colsを維持する。既存明示native sizeは0だが型の意味を混ぜない。
- CheckboxControl43とToggle8を区別する。RadioControl7、RangeControl1、FileInputControl4、ColorInputControl2は別の専用owner。ファイル入力へvalueを追加しない。色選択のデータ値はUI色トークンへ置き換えない。

#### 入力外観：上書き口を限定

色・枠・角丸・文字・focus/disabledはFormField.cssが所有する。154のclass属性と60のstyle属性（138プロパティ）の移管先は入力JSONで追跡する。利用元の任意class/styleによる内部外観上書きを最終公開APIに残さない。

| 本体props | 契約 |
|---|---|
| invalid?: boolean | 既存エラー条件のまま外観へ接続。aria-invalidは既存の明示属性を透過し、自動付与/上書きしない |
| status?: normal/saved | 保存完了表示の既存条件を使用。invalid優先 |
| textStyle?: normal/secondary/code、emphasis?: normal/strong | 既存文字の用途を表す。任意font/color値は受けない |
| appearance?: standard/embedded | TextFieldControl/TextareaControlだけ。embeddedは親が枠を所有。本体に枠を重ねない。SelectControlの既存field/bareは別契約として維持 |
| leadingInset?: boolean | TextFieldControlだけ。既存の外側アイコン分の余白を確保し、input内にアイコンを描画しない。既存アイコンDOMは外側ownerに残す |
| emptyDatePlaceholder?: boolean | 空の日付だけ既存のネイティブ文字非表示を維持。値ありで非表示にしない |
| resize?: none/vertical/both | textareaだけ。未指定は現行本体の規則を維持 |
| visibility?: visible/sr-only/hidden | FileInputControlだけ。既存のsr-onlyとdisplay:noneを混同しない |

配置用の幅・最小高さ・余白・flexは元のDOM上で維持し、同値の名前付き配置tokenに移す。公開口は意味のある配置classの登録に限定し、登録CSSに色・枠・文字の宣言を禁止する。表の列幅は列の所有元へ接続し、入力ごとに列幅の写しを持たない。既存field-h-md/field-w-sm/mdの適用先が外側divかnativeかを変えない。定義のない旧classの見た目を名称から創作しない。

Checkboxのデータ由来accentColorは用途が限定されたdataColor入口へ移す。通常UIの固定色をこの入口で免除しない。Toggleは既存8件の状態式・通知許可・終日時間の処理をそのまま利用する。レール40×22px、つまみ16px、端の間隔3px、ON時移動18px、操作領域44pxの案を維持する。

#### ボタンの操作契約

根拠: [411件の分類・対応](../../handoff/design-system-recon/evidence-20260910/button-semantic-audit.md)。通常操作とタブ・絞り込み・会話選択・カレンダー座標操作を分類し、全native buttonを通常Buttonへ置換しない。

Buttonはnative buttonを維持し、forwardRefとnativeイベント属性を透過する。type省略143件へ一律type=buttonを追加しない。既存submit61、外部form4、stopPropagation18の契約を保持する。disabled/loadingや送信ガードを外観統一のために書き換えない。ButtonLinkはnative anchorの外観共有であり、href/target/rel/downloadと通常のリンク操作を保持する。anchorにbuttonのdisabled属性を付けて無効化できたとは扱わない。

Button外観はButton.cssを唯一の定義元にし、components.cssの重複btn宣言は利用先移行と整合して削除する。寸法mdはfield-h-md=36pxを用いる統一案で、既存btn-min-height-md=40pxと同値の移動ではない。iconOnlyは28/36/44pxの正方形、角丸6px。通常lgのmin-height48pxがiconOnlyを押し広げないようmin-heightも同じ値にする。モバイルでは幅・高さ・最小高さをすべて44pxにする。通常ボタンとアイコンだけのボタンを同じ寸法計算で処理しない。

フィルターをTabsのroleへ変えない。Tabsはパネル切替だけ。再クリック解除するフィルターと解除しない選択を別の状態契約として維持する。FedexのcurrentTarget.closest、カレンダーのgetBoundingClientRect、DataTableのtarget.closestが依存するDOM・イベントを維持する。外側配置は入力と同様の限定された配置入口で扱う。

#### Overlay：共通の見た目と異なる開閉動作

通常Modal/Drawerとloading配下の同名部品を名前だけで置換しない。共通header/title/body/footerの外観をcomponents/Overlay.cssへ集約し、各既存CSSは位置・サイズ・アニメーション・モバイル配置を保持する。

通常Modalは閉じるとunmount、loading Modalは閉じてもmountする既存差を維持する。通常Modalのtitle:string必須とloading Modalの任意ReactNodeを維持する。通常Drawerのfooter/fullpage/testidとloading Drawerのaria-hidden/SSR guardを維持する。閉じるボタンの新設、focus trap、Esc、body lock、複数重なりの修正を外観PRへ混載しない。特殊ダイアログへ通常Modalの動作を自動注入しない。

#### アイコン数値生成の仕様

tokens.cssの--icon-sm/md/base/lg/xlを手編集正本にする。constants/iconSizes.tsは生成物とし、ICONの5キーとIconSize型を維持する。現行14/16/20/24/48の値を変更しない。PlatformIconのMath.roundによる比率計算を壊すためCSS文字列を渡す案は採らない。

生成器はfrontend/scripts/generate-icon-sizes.js。PostCSSを直接devDependencyへ宣言し、lock更新を同じPRに含める。トークン値はトップレベルの単独:root宣言に各1件、正の有限px数値だけを受理する。対象5名の欠落・重複・条件内再定義・別selector再定義・式/別単位・CSS解析失敗は非ゼロ、出力を書き換えない。全項目を検証した後に同一ディレクトリの一時ファイルへ一定順序・一定書式で書き込み、成功時だけrenameで置換する。同値なら書き込まない。

通常コマンドは生成、--checkは書き込まず完全一致を検査する。dev/buildの開始前に生成を接続し、開発中のtoken変更後は再生成して数値利用元を更新する。常駐watchは今回増設しない。最後のCI便で--checkを接続し、生成忘れを不合格にする。既存check-icon-syncは移行中維持し、未実装の--fixを生成済みと呼ばない。

生成器試験: 現行5値一致、同入力で同出力、値1つ変更で対応キーだけ変更、欠落、重複、条件再定義、rem/var/calc、壊れたCSS、出力不能、--check不一致で変更0。失敗時に以前の有効な生成物が残ることも確認する。

#### グラフ：用途色の直接参照

Dashboardの実績と残量は--chart-actualと--chart-remainingへ集約する案。実績はaccentのalias、残量は現行のalpha40相当をテーマ別の用途色として定義し、ページで文字列を連結しない。Bar.fillへvar(--chart-actual/remaining)を渡す。数値集計・tooltip・軸・ラベルは変更しない。

採用根拠はRecharts3.8.1実物のBar→RectangleのSVG props透過と公式同版ソース。DOMへfill文字列を透過する経路を確認したが、PO目視の代用とはしない。実装時は明暗切替でfill属性がCSS参照のまま、固定6桁色へ戻らないことをテストし、生成された画面の最終目視はPO確認待ちと記録する。

#### 資料と確認の限界

Context7 MCPは利用可能ツール一覧に存在しない。PO許可の代替として2026-09-10に[React forwardRef公式](https://react.dev/reference/react/forwardRef)、[PostCSS API](https://postcss.org/api/)、[Recharts3.8.1 Rectangle](https://raw.githubusercontent.com/recharts/recharts/v3.8.1/src/shape/Rectangle.tsx)を確認。Reactの現行文書は19の注記があるが本製品は18のためforwardRefを用いる。採用版を今回更新する判断ではない。企業の改善率は今回のDOM互換の証拠にならないため外部導入事例は使わない。

#### 今回の自己審査

REVISE。入力の全属性と参照先、ボタン分類、生成器の失敗条件、Overlayの既存動作を具体化した。残るCard/Badge/Tabs等の全公開API・全ボタン外観対応・最後のCI所有元と動的CSSの検査契約を照合中。未決を実装担当の独断へ渡さない。PO目視は完成後であり、目視待ち自体を設計停止理由にはしない。製品実装未着手。

#### Card・Badge・Tabs・EmptyStateの公開契約案

[実物照合](../../handoff/design-system-recon/evidence-20260910/remaining-components-audit.md)では既存製品使用はCard3/Badge10/Tabs0/EmptyState0。部品が存在するだけで旧class経路の移行が済んだとはしない。§A以前の「追加作業不要」という過去記載を全体完了の根拠にしない。

Cardはasをdiv/section/articleだけに限定し元のタグ・children・native属性/refを維持する。interactiveは外観であり、既存にないrole・tabIndex・キー操作を自動追加しない。状態付きカードは用途別adapterで条件を保持し、共通surfaceへtone/outlineToneを渡す。bottleneck/urgent/step done/completeを同じactiveに潰さない。既存Card3件のうち2件のmarginBottomは共通の配置入口へ移す。

Badgeはspanのままtitle/aria/data/events/refを透過。表示文字や業務ステータスを共通部品へ埋め込まない。同値移管の見た目は現在のbadgeVariantと実CSSの対応を使い、既存statusPresentationへ表示用写像を追加する。prospectRankの仮Cはbucket=neutralでも現行pendingがwarning色のため、warning表示を保持する。論理bucket/API/ラベルを変更しない。appearanceにplain（枠/背景なしの数値・注釈）とcount（未読数）を追加する案。未読数の絶対配置は利用先の配置責任、桁数増加を切り捨てない。role.color等のデータ色は専用adapterが既存の背景式とvar(--on-accent)の前景をdataBackground/dataForegroundへ渡し、Badge素材を利用する。前景の自動算出や値補正を新設しない。通常UIの固定色をdataColorに流して免除しない。

Tabsはパネル切替だけに使用。既存items/activeKey/onChangeとdisabled/count=0表示を維持する。onChange(key,event)へReact.MouseEvent<HTMLButtonElement>を変換せず第2引数で渡し（event.nativeEventへ変換しない）、既存のkeyだけを受けるcallbackも互換維持する。項目別onClickは追加しない。既存イベント処理とkey更新を利用元の1つのonChangeへ元と同じ順序で移し、1クリックにつき1回だけ呼ぶ。disabled時は呼ばない。aria-controls/panelIdは実在パネルと接続する場合だけ付ける。ページ移動・絞り込みは用途別adapterで既存nav/button/anchorの意味を保持して外観だけを共有する。新しい矢印キー選択やフォーカス自動移動をこの外観PRで追加しない。

EmptyStateはdiv本体のaria/data/testidを透過し、title/descriptionは既存string型とp要素を維持する。ブロックを含む既存詳細は新しいdetails?:ReactNodeをdiv内に出力する。pをtitle/descriptionへ入れず、元の詳細DOMをdetailsへ保持する。TableEmptyがtd/colSpanを所有し、その内側に表示を置く。loading配下の互換入口は旧truthy条件を維持し、通常部品の!=null条件との差を失わない。InboxKartePanelの同じright-panel-empty classでも会話未選択とloadingProfileは別の用途であり、後者は待機表示の共通部品を使う。

#### 最後のCIの方針更新

CIは全体の画面移行後に設置する。今回の合格条件は全対象に未移行0・検査不能0。一時的なbaselineや件数増加だけの判定で移行完了を示さない。所有元は完全moduleパスとexportとnative要素種類で限定し、componentsフォルダ丸ごとの免除はしない。装飾値の正本と部品の所有CSSへの参照を検査する。

旧check-ui-governance.jsの22ケースにはui-allow免除やtable非検出の期待が含まれる。したがってci-guard-design.mdの「旧22期待を維持して読取だけ修復する」案を最終CIへそのまま適用しない。最終全件検査で取得不能をexit2へする契約を継承し、旧期待の変更はADR-144改訂案と対照試験へ明記する。先行CI実装は行わない。

任意のJavaScriptの意味・全divがカードかをCIだけで完全判定するとは約束しない。公開API型、限定された構文検査、移行表、コードレビューを組み合わせる。動的座標・顧客色・HTML表示には既存用途の専用adapterを設けるが、新しい値補正・fallback・業務上の制限を外観統一へ混載しない。新しい本人認証APIや承認操作は今回増やさない。

上記は設計案の補完。特殊用途の全件写像とCIの有限な検査契約を照合中であり、全体自己審査REVISEを維持する。


#### CSSの限定照合による補完

[selector対応表](../../handoff/design-system-recon/evidence-20260910/selector-impact-audit.md)は今回変更するclass/nativeタグに該当する314候補・27 CSSファイルを対象とした。:not内のcheckbox/radio指定を肯定条件と取り違えた初版4件を、設計担当の指摘とselector構文の再解析で訂正。修正後の表を正本とし、無関係な全selector照合を完了条件に膨らませない。

- CSSI-0209: InboxのTextareaControlはembedded/resize=none。枠0・padding0・transparent・line-height1.4を共通入力用途へ、flex1/min-width0を同nativeの配置入口へ移す。
- CSSI-0231: 右パネルSelectControlはindicator=none。現行appearance:noneと矢印なしを維持し、矢印DOMや外側wrapperを追加しない。
- CSSI-0233: 右パネルTextareaControlはresize=none、最小高さは同nativeの配置入口で既存inbox-textarea-min-hを参照。
- CSSI-0038: DataTable選択欄の外観はCheckboxControlの所有へ移し、indeterminateと選択処理は保持。
- karte-toggle-btnの表示/非表示と1279px条件は同buttonの配置専用classに維持する。

状態Cardの追加契約: doneはemphasis=mutedで既存opacity-muted、urgentは左3px danger、completeは全周2px accent、bottleneckはwarning枠と既存hover/focus accentを保持。全て既存条件の写像であり、状態を統合しない。Table行のopacity変更案をCardへ流用しない。


#### 限定文書レビュー4指摘の修正

leadingInsetは余白だけでnative1要素契約を維持する。SelectControlのappearanceは既存field/bare、既定bareを維持し、fieldの既存wrapper幅/size条件とbareの幅autoを保存する。TextFieldControl/TextareaControlのstandard/embeddedをSelectへ横展開しない。Selectのindicator=noneは両appearanceで矢印を消す独立軸、未指定は各既存表示を維持する。

TabsのbuttonAttributesはnative属性からrole/type/aria-selected/disabled/className/style/onClickを除外する。これらは本体が所有する。onChange(key,event)だけがクリックの処理入口で、既存callback内のpreventDefault/stopPropagationをそのまま保存する。新たにdefaultPreventedでkey更新を自動抑止する仕組みを設けず、既存利用元の処理を一度だけ呼ぶ。aria-controlsとdata-testid等は項目属性で透過する。

配置入口はlayoutClassName?:stringに統一し、共通部品のclassName/styleを最終公開APIから外す。文字列の各classに対応する配置宣言が検査対象CSS内に存在し、配置の許可propertyだけであることを最後のCIが確認する。途中移行中のclassName互換口は全利用先移管後に閉じる。既存FieldのlayoutClassNameは外側div、裸Control/Button等は同nativeへ付ける。任意装飾classを配置名と言い換えて免除しない。

EmptyStateのdetailsはdescriptionの後・actionの前のdiv。未指定ならDOMを増やさない。既存string表示/条件を維持し、詳細ブロックがない移行先へ不要なdetailsを追加しない。


#### 動的な配置・色と最後の検査の責任

[最後のCI契約と27受入ID](../../handoff/design-system-recon/evidence-20260910/final-ci-contract-audit.md)、[動的指定172項目](../../handoff/design-system-recon/evidence-20260910/dynamic-style-fixed-audit.json)を設計入力とする。113は共通外観、38は既存の配置/幅/数値処理、13は利用者色の既存入口、8はカレンダー用途色に割当済み。172はstyle属性数や違反数ではない。位置計算を全て新しいadapterへ寄せず、元の関数・式を保持する。

共通部品への自由なstyle/classNameは移管後に閉じ、一般ページの配置styleは維持する。座標のclamp/fallback等を新設しない。既存のrole/owner色は実在する関数とpropertyを限定した名前付き入口で受ける。新たな独立ラッパーは不要。完全パス+exportName+必要な既存implementationBindingの登録で、同ファイルの別機能へ許可を広げない。

CheckboxControlの寸法は既存--size-checkbox=16px、smは--size-checkbox-sm=14pxを参照する。既存のnative選択挙動、indeterminate、入力name/valueを保持する。RadioControlはradioのnative挙動を維持し、チェックボックス/トグルへ置換しない。

各実装便の台帳には元の対応ID、最終module/export/必要なimplementationBinding、所有CSS、nativeTag/type、実行した検証を記録する。これは最終CI登録への入力であり、未移行を許すbaselineではない。最後に対応表の全IDと実装済み台帳を突合し、未移行0・対応なし0を確認してから登録表を確定する。実装前の設計段階に実行結果や生成後行番号を創作しない。


#### Icon/Spinner最終契約と名前の固定

[Icon/Spinnerの実物照合](../../handoff/design-system-recon/evidence-20260910/icon-props-final-audit.md)を受領。通常Iconの外部styleは1件だけで同SVGの配置classへ移す。外部color/ref/spreadは0だが既存forwardRef契約は保持。PlatformIconの数値sizeと丸め式、LeadChatIconの数値20は保持する。通常Iconのstyle/colorとSpinnerの未使用color入口は、全参照0確認後に閉じる。PlatformIcon内部のwidth/height計算は許可する名前付き所有元に残す。

mailのwhiteはindex.cssの新しい用途名--icon-platform-mailから既存--on-accent（両テーマ#ffffff）を参照する。調査案の--on-solidは現在存在しないため、その参照だけを追加する実装は採らない。画像URL/比率/altと既存DOMはこの同値移管で変えない。

Spinner tone=inheritはonAccentより優先し、全枠currentColor・上辺transparentで回転を示す。通常/onAccentのhead/track tokenは従来どおり。Button内だけdecorative=trueを使い、SaveIndicatorの既存sm/label/通常toneは維持する。調査案の「inheritでも旧trackを残す」は本契約で採用しない。

通常Iconのaria属性未転送の修正は、数値生成/同値材料PRへ混載せず、Icon公開APIの移行便に分ける。aria-hidden/aria-label/aria-labelledby/aria-describedby/role/focusableを必要な型で明示透過し、style/colorを復活させる汎用restは作らない。refは同SVGへ渡す。これは現在の出力との意図した属性変更としてDOM試験する。

トグルの正規名はcomponents/Toggle.tsxのToggle。調査表のSwitch表記は意味分類名であり別部品を新設しない。表の正規公開名はcomponents/table/Table.tsxからTableViewport、Table、TableHead、TableBody、TableFoot、TableRow、TableHeaderCell、TableCell、TableEmpty。TableViewportが外枠/スクロールを持ち、Tableはnative tableを返す。TableEmptyがtd/colSpanを持つ。

本物のTabsとページ移動/絞込みの外観共有はTabControl（Tabs.tsx）を内部の共通button表示ownerにする。role/ariaは用途側で既存に合わせて渡し、見た目が似ているだけでrole=tabを追加しない。既存Button variant=tabの互換APIは維持するが、新しい用途をこのARIA既定へ強制しない。

layoutClassNameの許可propertyと部品ごとの寸法禁止は[最終CI契約](../../handoff/design-system-recon/evidence-20260910/final-ci-contract-audit.md)の有限リストを正本とする。C26/C27で配置のみの許可と装飾・共通寸法上書きの拒否を対照する。一般ページの動的styleへ同じ制限を広げない。

### AA. 全体設計の自己審査（2026-09-10）

判定: **APPROVE（設計合格）**。Plannerとして作成後、同じ設計担当AIがArchitectとして審査した。独立した第二者による全体設計レビューではない。限定APIレビューは別担当の読み取り補助を使用した。

この判定の対象は§V以降の最新順序、§P/Qのボタン配色・操作、§R〜Uの39表/239属性、§Zの最新公開契約と対応表、最新CI契約およびADR-144改訂案。§A〜Yと§Z途中に残るREVISEは調査中の履歴であり、以下の解消記録をもって現時点の判定を更新する。過去のPO承認済本文を新しいPO発言として書き換えない。

| 審査項目 | 根拠と判定 |
|---|---|
| 入力のDOM・イベント・値 | 577要素の属性/ref8と全74select childrenを照合。裸本体・forwardRef・options/children排他・native type/sizeの責任を確定 |
| ボタンの用途と外観 | 411件の対応、type省略143/submit61/外部form4/stopPropagation18を保持。通常操作とタブ/絞り込み/カレンダーを区別 |
| CSS適用先 | 314候補/27ファイルを限定照合。:not誤分類4件を訂正、入力3契約とCheckbox所有移管を確定 |
| 表の構造と操作 | 39表と239属性の対応。rowSpan/colSpan/tfoot/編集/選択/並べ替えを保持し、DataTableと表示部品の外観を共有 |
| Card/Badge/空状態等 | 279候補を用途分類、動的Badge33箇所166状態を照合。仮Cのwarning表示とデータ色前景を保持、待機を空状態へ誤分類しない |
| 動的配置と色 | 172項目を113外観/38配置・数値/13利用者色/8用途色へ写像。位置計算の全面移動と新入力制約を採らない |
| 公開APIの矛盾 | leadingInset、Select field/bare、EmptyState detailsのdiv、Tabs単一callback/React.MouseEvent透過に修正。未実装テストを設計完了の前提にはしない |
| 材料の互換 | 数値ICON5キーはCSSから生成し既存数値計算を維持。DashboardはSVG fill透過経路を確認し用途色へ接続。未確認のcolor-mixへの置換は採らない |
| 旧PRの扱い | 7PRの採否表で既反映/再利用/不採用を区別。古いbranch全体を上書き適用しない |
| CI・ADR | 全UI移行後に27受入IDの限定検査。旧22期待維持案を後続全件検査へ読み替えず置換点をADR改訂案に明記 |

#### 実装の受け入れ条件

| 基準 | 検証方法 |
|---|---|
| 各材料は手編集元1つ、既存値の同値移管と配色変更を別PRで追跡 | token定義/参照の差分、ICON5値と生成物一致、用途色対応表 |
| 操作の式・DOM/ref/type/formが保持される | 対応IDごとの差分レビューと送信/選択/添付/ref/無効時の部品テスト |
| 共通部品の公開APIと全呼出しが一致する | TypeScript検査、既存check:all、対象部品の意味のあるunit/DOMテスト |
| 39表/411ボタン/577入力の移管結果を取りこぼさない | 初期対応IDと各便の実装台帳を突合。元の共通内部は違反数へ水増ししない |
| 明暗・状態・文字長の見本が同じ定義を読む | Storybookのglobal CSS読み込みを実アプリと一致、部品状態の見本/ビルド、指定色再計算 |
| CIが未移行と検査不能を合格にしない | 全移行後にC01〜C27の対照fixtureと実CI。既存必須チェックも維持 |
| POが完成画面を確認できる | 原因別PRの変更箇所一覧と見本/対象ページを提示。目視はPO確認待ちとして区別 |

実装カードはこの設計の限定範囲・ファイル所有・正確な手順・停止条件を記載し、正式card-lintと手作業チェックを通してから渡す。初回は既存5値を変えない数値アイコン生成、次に材料の同値alias、部品本体、利用画面、最後にCIの順。各PRの結果を確認し、先行PRマージ後のmainを次便の基準にする。

#### 状態と承認の区別

設計案作成済み・全体設計自己審査済み。POから実装担当への委任と順次マージの依頼を受領しているが、具体的なPR番号付きGOやADR改訂のPO自筆承認を創作しない。文書PR #3407はマージ済み、本節は次の文書PRへ保存する。製品実装・自動テスト・PO目視・製品PRマージ・デプロイは未実施。この設計合格をそれらの完了・承認の代わりにはしない。


### AB. 同値カラー材料便の確定範囲（2026-09-10）

全体自己審査§AA後、第1実装便PR3412はマージ済み。次便は既存migrationの旧PR採否に従い、[候補全件表](../../handoff/design-system-recon/evidence-20260910/color-source-audit.md)と[実測JSON](../../handoff/design-system-recon/evidence-20260910/color-source-audit.json)の7製品ファイルに限定する。基準4734fe7f。これは同値の定義移管で、部品のAPI/大きさ/操作/画面構造を変える便ではない。

- index.cssの既存9宣言を同値参照へ置換。indicator、sidebar active border、light active color、sidebar-bg、accent-bg。新しい固定色は追加しない。
- icon-action/action-hover/action-danger/empty/decorative/search/status-success/platform-mailの8用途名を明暗各1定義で追加。具体的参照先と明暗値は上記候補全件表のとおり。元の汎用tokenを値の正本とし、用途名はaliasだけにする。
- components.cssのicon-btn通常/hover/danger-hover、EmptyStateのアイコン、Dashboard装飾、Inbox検索/ロックを対応用途名へ移す。見出し全体の文字色や一般ナビ文字へ広げない。
- mail/emailのPlatformIconは既存EnvelopeIconのcolor属性whiteだけを除き、既存mailラッパーにcolor:var(--icon-platform-mail)を追加する。既存DOM、Math.round(size*0.7)、width/height、aria-hidden、他platform分岐を保持する。既存--on-accentを参照し、未定義--on-solidは使わない。
- calendar21用途、未使用token削除、影のcolor-mix化、リンク/背景/文字の配色変更、useEffect修正、Iconの汎用style/ref/API再編、CI変更は別便。新しい見た目の判断を混載しない。

受入: 候補全件の明暗解決値が変更前後一致、参照欠落/循環0、変更箇所のブラウザーcomputed colorを明暗と画面幅390/1280で比較する。icon-btnは通常/hover/danger-hover、mail/emailは実コンポーネントのSVG描画色と数値寸法/ARIAを確認。対応表の旧token利用と新alias利用を比較し、暗黙の黒fallbackを一致と誤認しない。ブラウザー比較は局所fixtureの技術試験で、全画面のPO目視完了とは称しない。

既存check:all、ビルド、必要な既存CIを実行し、新token本文の4項目は実施後に正規テンプレで記載する。新CIは設置しない。検証用原稿・前後比較結果を既存recon根拠へ保存し、検証失敗を隠さない。通常のCI成功だけを同値の証明としない。

Architect自己審査: APPROVE（この7ファイルの同値移管契約）。設計担当がPlanner記述後に同一AIとして審査し、候補9宣言・8用途・使用9記録、全50CSSで対象上書き0、静的API書込検出0と照合した。独立した第二者設計審査とは称しない。実ブラウザー比較・製品実装・製品第二レビューはこれから実行する受入条件で、設計合格をそれらの実行済みとしない。外部導入事例は不要（自社の既存色の同値移管を実物で比較する変更のため）。

### AC. 2026-09-11 読み取りやすさの追加方針と実装順序

PO原文「進める、離席するので最後まで完走させて結果を報告してくれ」を、直前に提示したカレンダー保留・共通部品先行の続行指示として受領。さらに「心理学、脳科学、認知科学的に人間がパット見て何が書いてあるかを理解しやすい表示にしてくれ」を受領。POの新しいGO番号や効果の実測値を生成しない。

既存のSSOT設計に、読み取りやすさの確認を加える。業務文言の意味、操作/保存条件、APIは維持。新しい装飾や字体の導入自体を目的にしない。

| 基準 | 検証方法 |
|---|---|
| 見出し・本文・補助情報の役割が揃う | 既存type/weight/spacing tokensと意味的見出しの使用を代表画面で確認。情報の序列をページ独自CSSで逆転させない |
| 操作・状態は色だけに依存しない | ボタンの翻訳済み動作文言、選択/処理中のaria属性、危険操作文言を確認。ラベル欠落0 |
| 有効な通常文字のコントラスト4.5:1以上 | 既存P/Qの状態表とブラウザーcomputed色で再測定。大文字例外3:1/非活性例外を通常文字の達成数へ混ぜない |
| 情報のまとまりと余白を揃える | 関連する見出し/入力/説明を同じ部品内に置き、間隔は既存spacing tokensで管理。200%拡大と390px表示で文字/操作の欠落0を確認 |
| 分かりやすさを実装検査だけで実証したと言わない | 完成後POが対象画面で目的・現在状態・次の操作を説明できるか確認。未実施はPO確認待ち。理解秒数/改善率/脳活動の効果は未測定 |

根拠（2026-09-11公式資料確認）: [W3C Cognitive Clear Content](https://www.w3.org/WAI/WCAG2/supplemental/objectives/o3-clear-content/)は短い文章・明確な文言・余白/前景分離の補助指針（規範のWCAG必須条項ではない）。[WCAG Contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)は4.5:1/大文字3:1と非活性等の例外を説明。[Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)は色以外の手掛かりを要求。これは規格/指針の根拠で、Sales Anchorの理解速度改善を実測した事例ではない。外部導入の効果数値は採用しない。Context7は提供ツールに存在せず、必要なAPI確認は許可済み公式資料を代替使用する。

Planner追補後、同一AIがArchitectとして方針の整合を自己審査APPROVE。個々の部品実装の合格やPO完成画面確認とは区別する。既存全体設計Z/AA、P/QのButtonとSpinner契約を維持し、実物差分の再監査後に本体便をカード化する。カレンダーはMOLD-21の理由で保留、既存CIは維持し追加は最後。

### AD. Button機能契約と読み込み表示の先行便（2026-09-11）

57eb951eのButton再監査は実使用67箇所/18ファイル、className18、style/ref/spread各0、type明示26・省略41（stories/test/spec/design-preview除外、design-system含む）。CompanyDetailの6個はcompany-forms.cssのtab/activeに依存。外観全体の切替はこれらの移管と一緒に別便で行う。この便はQ/Zで承認設計済みのrefと読み込み表示に限定し、寸法/色/variantクラスを変えない。これは最終外観統一の完了ではなく、必要な機能契約を先に満たす段階。

所有製品: components/Button.tsx、components/loading/Spinner.tsx、loading-animations.css。新規検証: components/Button.test.tsx、components/loading/Spinner.test.tsx（すべてfrontend/src以下）。新CI/依存/翻訳/画面側変更なし。検証用ブラウザーfixtureは/tmpに限定。

ButtonはforwardRef<HTMLButtonElement, ButtonProps>で同じnative buttonへrefを渡す。propsからtypeの既定を足さず、className/style/nativeイベント/既存aria上書き順を維持。6variant、size、fullWidth、iconOnly、active、children/loadingText、disabled||loadingの条件を維持。Spinnerへtone=inherit、decorative=trueを渡し、loading時も翻訳済み既存の名前とaria-busyを保つ。新onKeyDownや自動focus移動を追加しない。

Spinnerにtone?:'default'|'inherit'とdecorative?:booleanを追加。従来のsize/onAccent/className/label/colorはこの互換便では維持。未使用color口を閉じるのは最終API移管便とし、未宣言の破壊的変更を混在させない。inheritはonAccent/colorより優先し、styleによる旧borderTopColor指定を使わない。CSSは全枠currentColor、上辺transparent。通常/onAccentは既存head/track tokenを保持。decorative時はaria-hidden=trueでrole/aria-labelなし。非decorativeの既定Loading/role=statusは維持し、新規UI文言は追加しない。Spinner自身から既存../../loading-animations.cssをimportし、アプリ/Storybookで同じ正本へ到達。既存main importは重複定義ではなく同モジュールの読み込みであり保持する。

| 基準 | 検証方法 |
|---|---|
| refが同buttonに到達、外部form/type/name/value/イベントの保持 | DOM unitでref.current、focus、form所属、click/submitとstopPropagationを検証 |
| busy時disabledで追加発火0、元名/指定loadingText/アイコン操作名を保持 | DOM unitと実ブラウザーでclick/Enter/Space、props反映後を検証 |
| inheritは全枠前景色・上辺透明、onAccent/colorより優先 | DOM props試験と実ブラウザーcomputed border色を明暗で比較、通常/onAccentを対照 |
| decorativeは読み上げ重複なし、通常Spinner/SaveIndicator互換 | role/label/aria-hiddenと既存使用先差分0を確認 |
| reduced-motion時回転停止、6variant操作回数1/無効0 | 実ブラウザーでprefers-reduced-motionとnative keyboard操作。外観全体/コントラスト190組は後続外観便 |
| 既存UI/依存/CI変更0 | diff範囲5ファイル、check:all/build/unit/Storybookと既存CIを実施 |

React公式forwardRef/APIとW3C Button Patternを2026-09-11確認。React19のref-as-propへ独断移行せず、実repo React18契約を維持する。外部の理解速度改善事例は不要（ネイティブ操作/読み上げの既存設計契約を具体化する便）。

6面: 人=読み込み状態の重複読み上げと視認性、エージェント=固定5ファイル所有と実検査、機械=既存CI維持、データ=DB/API非接触、本番=通常PR経由で部品反映、外部=外部API非接触。守り手は新規unitと既存check:all/build/CI、表示は局所ブラウザー比較と完成後PO。Planner作成後に同一AI Architect自己審査APPROVE。操作契約は既存設計の具体化であり、新規事業判断/PO最終目視を代替しない。


### AF. Icon便の前提となる接続状態通知の依存修正（2026-09-11）

既存Icon公開契約便の保存前検査でGoogleCalendarStatusBar.tsxのuseCallback依存不足が発覚。変更前main76c6dff9でもeslint --max-warnings=0が同警告1件でexit1となることを実測した。POに「この既存不備を別PRで先に修正してよいですか」と提示後、原文「次を進める」を受領した。番号付きGOやPRマージ済みの記録とは区別する。

目的: 親から通知関数onSyncStatusChangeが差し替えられた場合に、checkStatusが古い通知関数を使い続けないようにする。見た目やIcon契約の変更とは別PRとする。

基準コード: frontend/src/components/GoogleCalendarStatusBar.tsxのcheckStatus内でonStatusChange/onSyncStatusChangeを参照するが、useCallbackの依存は[onStatusChange]のみ。effectはcheckStatusを依存にして初回状態確認と30_000ms間隔の定期確認を登録、cleanupはclearInterval。部品の参照は現在storiesだけで本番利用0。APIは既存GET /google-calendar/status、結果のconnected/configured判定を維持する。

実装範囲は同TSXの依存配列1行を[onStatusChange, onSyncStatusChange]へ変更することと、新規同名GoogleCalendarStatusBar.test.tsxの回帰試験。CSS、Icon、翻訳、通信仕様、状態の分岐、タイマー間隔、再接続のfinally処理、依存manifest/lock/CIは変更しない。先行Icon便の未保存変更を持ち込まない。

変更後は通知関数の同一性が変わるとcheckStatusが更新され、旧intervalを解除して状態の再取得とinterval1本の再登録を行う。これが意図した動作差であり、単なる無挙動の警告抑止とは説明しない。依存が同じ再描画では余計な初回再取得やinterval増殖を起こさない。既に進行中の非同期取得を取消す機能は今回追加しない。アンマウント後の未解決リクエストまで通知0と保証しない。

| 基準 | 検証方法 |
|---|---|
| 通知関数の差替えが最新通知へ届く | 新規DOM回帰試験を変更前コードへ先に実行し失敗を確認、1行修正後に成功。旧通知が差替え後の新しい取得結果を受けないことを確認 |
| 既存3状態・boolean通知の意味を保持 | connected/configuredの既存3分岐と通知の引数をmock GETで検証。callback省略でも動作 |
| 定期取得を増殖しない | fake timersで依存不変rerenderはGET増加0、依存変更後intervalは1本、30秒ごとGET1回。解決済み状態でunmount後timer0/追加定期GET0 |
| 再接続後の状態再取得を保持 | 再接続をクリックし、onReconnect完了後のGETと最新通知、処理中disabled/終了後復帰を確認 |
| 保存前検査と既存品質検査を通す | 対象2ファイルeslint --max-warnings=0、既存unit/check:all/build、必要なCI。新チェックの設置や警告抑止なし |

代替案: 警告無効化/コミットhook迂回は採らない。通知関数をrefへ退避してeffectの再取得を抑える案は既存通知側2関数の扱いを分け、新しい契約を増やすため採らない。今回の1行依存修正を外観便へ混載しない。

根拠: React公式useCallbackは関数内で参照するreactive値を依存へ含める契約、useEffectは依存変更時に古いcleanup後に新しいsetupを実行する契約。Context7 MCPは利用可能一覧0のため起動指示の許可に従い公式資料を直接確認。https://react.dev/reference/react/useCallback / https://react.dev/reference/react/useEffect （2026-09-11確認）。現行資料のReact Compiler/useEffectEvent等は導入せずrepo React18.3.1/既存hooksを維持する。

外部導入事例は不要（自社の既存警告と古いcallbackの参照を回帰試験で確認する限定修正）。守り手は新規回帰試験・既存frontend-check.yml・保存前eslint。API/DB/backendは非接触、画面配色/心理学的効果は本便の対象外。Planner作成後、同一AIがArchitectとして既存仕様・実物・検証可能性を自己審査APPROVE。独立した第二者の設計審査とは称しない。製品実装・試験結果・PR番号付きGOは後続の実績として別記する。
