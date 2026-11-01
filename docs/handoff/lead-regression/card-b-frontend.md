---
mode: handoff
---
# 実装カード B: ダッシュボードに「成約しやすさの分析」の欄を足す

親: [design.md](./design.md)（第11版）§4-3・§4-4・§2（K4）。応答の形は [card-a-backend.md](./card-a-backend.md) §3（変えない）。

この文書は何か: ダッシュボードの「今やること」の下に、成約しやすさの分析の表を出す欄を足すための作業指示です。

- 状態: カード作成済み・カード自己審査済み（§8）・PO 実装承認 済（2026-11-01「PRマージ、デプロイまで完走させてくれ」）・クラウドの Sonnet へ実装依頼
- 担当: Sonnet（クラウドで実装〜push まで）。PR は Opus が手元で shingo-cc 名義で起票。
- 裏側（入口）はカード A が別の枝で作る。画面は入口が無くても壊れない作りにする（読み込み失敗は欄の中だけでエラーを出す）。

## 読んだ節と照合（Opus、2026-11-01）

- docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・05-pr.md・10-executor.md: 触るファイルを §1 で全部挙げた・形と期待値を §2〜§4 で書いた・PR は手元。○
- ADR-144（金型だけ）・ADR-067（デザイントークンだけ）・ADR-027（文字は t() で ja・en）・frontend/AGENTS.md（アイコンは constants/icons.tsx から・E2E と見本を同じ PR で直す）。○
- 受領確認: 着手前に、報告の1行目へ「受領確認: card-b-frontend を読んだ」と書く。

## 0. 実物（Opus が origin/main 508e86036 を取り込んだ枝で 2026-11-01 に確かめた）

- `frontend/src/pages/dashboard/DashboardPage.tsx:466` `<PriorityProspectsSection />`、`:468` `<WeeklyAdvisorSection />`（`<div className="db-content-stack">` の中）。
- 見本にする既存の欄: `frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx`（外枠 `db-section-card`・見出し `db-section-header`・アイコン `DashboardIcons`（`frontend/src/constants/icons.tsx:241`〜249）・読み込み `LoadingBlock`（`frontend/src/components/loading`））と `WeeklyAdvisorSection.css`。
- 入口を呼ぶ関数の置き場: `frontend/src/api/funnel.ts`（`api.get` を使う。例 `getWeeklyAdvisorDefensive`）。
- 表の金型: `frontend/src/components/DataTable.tsx`（`DataTableColumn`・`DataTableProps`、:147 で export）。
- 文字: `frontend/src/locales/ja.json`・`en.json` の `"dashboard"` の下（ja.json 730行。例 812行 `"weeklyTitle"`）。
- E2E: `frontend/tests-e2e/scene1-dashboard.spec.ts`（:32 のような `"GET /analytics/…"` の見本の並び）、`frontend/tests-e2e/fixtures/mock-dashboard.json`。

## 1. 作るもの・触らないもの

作る・変える（これ以外は触らない）:

1. `frontend/src/pages/dashboard/LeadConversionFactorsSection.tsx`（新規）
2. `frontend/src/pages/dashboard/LeadConversionFactorsSection.css`（新規。トークンだけ）
3. `frontend/src/api/funnel.ts`（追記: 型と `getLeadConversionFactors()` を1つ。新しいファイルは作らない）
4. `frontend/src/pages/dashboard/DashboardPage.tsx`（:468 の `<WeeklyAdvisorSection />` の次の行に `<LeadConversionFactorsSection />` と import を1行）
5. `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`（`"dashboard"` の下にキーを足す。両方同じキー）
6. `frontend/tests-e2e/scene1-dashboard.spec.ts`（見本の入口を1つ足し、§4 の確かめを足す）。`frontend/tests-e2e/fixtures/mock-dashboard.json` は、この試験が読んでいる場合だけ同じ内容を足す（読んでいなければ触らない。どちらだったかを報告に書く）
7. Storybook（`DashboardPage.stories.tsx`）が入口の見本を必要として壊れる場合だけ、見本を1つ足す

触らないもの: `backend/`・`migrations/`・`.github/`・`frontend/src/components/`（金型は使うだけ。足さない・変えない）・`frontend/src/constants/icons.tsx`（既存のキーを使う）・デザイントークンの定義ファイル。

## 2. 形

- 外枠: `<div className="db-section-card" data-testid="lead-factors-section">`、見出しは `db-section-header` の中に `DashboardIcons.forecast` のアイコンと `t("dashboard.leadFactorsTitle")`（WeeklyAdvisorSection と同じ並べ方）。
- 見出しの下に注意書きを2つ（どのテナントにも出す。design §4-3）:
  - `leadFactorsNoteCausal`: ja「成約しやすさの目印です。原因を示すものではありません。」／en "These are signs of who tends to close, not causes."
  - `leadFactorsNoteReverse`: ja「返信の速さには、見込みの高い相手ほど急いで返すという逆向きの影響が混ざります。」／en "Reply speed is mixed with the reverse effect: we tend to reply faster to more promising leads."
- 件数の行 `leadFactorsCounts`: ja「分析に入れた件数 {{included}}件（成約 {{won}}件・失注 {{lost}}件）／外した件数 {{excluded}}件」（excluded は `excluded` の7つの合計）。en も同じ差し込み。
- `status` ごと:
  - `"ok"`: DataTable で 15行。列は 項目（`leadFactorsItem.<key>` の名前）・強さ（odds_ratio）・95%の幅（`ci_low 〜 ci_high`）・差があると言えるか（significant が true なら `leadFactorsSignificantYes`「言える」、false なら `leadFactorsSignificantNo`「言えない」。computable が false の行は3つの数の欄も含めて `leadFactorsNotComputable`「計算できない」）。行の順は応答の順のまま（並べ替えない）。`rowKey` は key、`rowTestId` で `lead-factors-row`。
  - `"insufficient"`: 表を出さず `leadFactorsInsufficient`: ja「件数が足りないため、まだ計算できません（成約・失注それぞれ {{need}}件以上が必要です）。」need は `required_per_item × item_count`。
  - `"not_computable"`: `leadFactorsNotComputableAll`: ja「この記録では計算できませんでした。」
  - 読み込み中: `LoadingBlock` に `leadFactorsLoading`。失敗: `leadFactorsError`「分析を読み込めませんでした。」（欄の中だけ。ほかの欄を止めない）。
- 数の表示: 小数2桁に丸めて表示（入口は丸めない。Fable 注意5）。`toLocaleString(i18n.language, { minimumFractionDigits: 2, maximumFractionDigits: 2 })` を使う関数を1つこのファイルに置く。
- 15項目の名前のキー（`dashboard.leadFactorsItem.` の下。ja / en）:
  - initiative_inbound: 相手から来た（こちらから営業より）／ Inbound (vs outbound)
  - sales_form_wholesale: 卸・代理店（それ以外より）／ Wholesale (vs others)
  - first_reply_within_1h: こちらの最初の返信が早い（1時間まで）／ Our first reply within 1 hour
  - partner_reply_within_6h: 相手の返信が早い（平均6時間まで）／ Their replies within 6 hours on average
  - channel_whatsapp: WhatsApp（Messenger より）／ WhatsApp (vs Messenger)
  - channel_instagram: Instagram（Messenger より）／ Instagram (vs Messenger)
  - country_gb: イギリス（アメリカより）／ UK (vs US)
  - country_au: オーストラリア（アメリカより）／ Australia (vs US)
  - temperature_hot: 温度感 Hot（Cold より）／ Hot (vs Cold)
  - temperature_warm: 温度感 Warm（Cold より）／ Warm (vs Cold)
  - message_count: やり取りの回数（1回増えるごと）／ Messages (per one more)
  - scale_large: 想定規模 Large（Small より）／ Scale Large (vs Small)
  - scale_medium: 想定規模 Medium（Small より）／ Scale Medium (vs Small)
  - customer_type_trust: 信頼重視（価格重視より）／ Values trust (vs price)
  - competitor_found: 相見積もりあり（なしより）／ Comparing other sellers (vs not)
- 列見出しのキー: `leadFactorsColItem`「項目」・`leadFactorsColOdds`「強さ（1より大きいほど成約しやすい）」・`leadFactorsColCi`「95%の幅」・`leadFactorsColSignificant`「差があると言えるか」。en も足す。
- 「テスト用データ」の注意書きは画面に出さない（design §4-3）。仕込んだ値も画面に出さない。
- CSS は余白・文字の大きさ・色をトークン（`var(--space-*)`・`var(--font-*)`・`var(--text-secondary)` 等。WeeklyAdvisorSection.css で使っているもの）だけで書く。色の直値・px の直書きを入れない。新しいトークンを足さない。
- 生の `<table>`・`<select>`・`<input>` を使わない（ADR-144）。合う金型が無いと分かったら実装を止めて `BLOCKED: 合う金型が無い`。

## 3. 入口を呼ぶ関数（`frontend/src/api/funnel.ts`）

- 型 `LeadConversionFactorsResponse` をカード A §3 の形のまま書く（status は `"ok" | "insufficient" | "not_computable"`、ci_low・ci_high・odds_ratio は `number | null`）。
- `getLeadConversionFactors(): Promise<LeadConversionFactorsResponse>` は `api.get("/analytics/lead-conversion-factors")` だけ。引数なし。

## 4. 試験と確かめ（K4）

- E2E（`scene1-dashboard.spec.ts`）: 見本に `"GET /analytics/lead-conversion-factors"` を足す（status ok・15項目。値は作り物で、うち1行は computable false、1行は significant true）。確かめ:
  - `lead-factors-section` が見える
  - `lead-factors-row` が 15個
  - computable false の行に「計算できない」の文字（ja の文言）
  - significant true の行に「言える」
  - 数が小数2桁で出る（例 odds_ratio 2.034567 が `2.03`）
  - 件数の行に 470・150・320
- 流すもの（結果の最後の行を報告に書く）: `cd frontend && npm run check:all`、`npm run check-ui-governance`（無ければ package.json にある同じ点検の名前を報告に書いて流す）、`npx playwright test tests-e2e/scene1-dashboard.spec.ts`、型の点検（check:all に含まれていなければ `npx tsc --noEmit`）。
- 文字の点検: `frontend/CLAUDE.md` の grep のセルフチェック（直書きの日本語 0件）。ja・en のキーが同じ（既存の点検が CI にあればそれ）。

## 5. 停止する条件

- §0 の行番号が5行以上ずれる・名前が無い → `BLOCKED:` に続けて合わなかった名前と行番号。
- 合う金型が無い・トークンが足りない → `BLOCKED:`（足さない）。
- 既存の E2E が今回の変更の前から落ちている → 落ちている試験の名前を書いて `NEEDS_DECISION:`。

## 6. 終わりの条件

- §4 の点検がすべて通る。
- `git diff --name-only origin/main...HEAD` が §1 のファイルと docs だけ。
- 枝 `release/lead-regression-frontend` に push 済み。PR は作らない。
- 報告の最後の行は `DONE` / `BLOCKED:` ＋理由 / `NEEDS_DECISION:` ＋内容 のどれか。

## 7. Opus が本番で確かめること（Sonnet はしない）

- 両方の PR の反映後、テナント001のダッシュボードで欄が出て、テスト用データを入れたあとは 15行が出る（K4 の本番側）。テナント004 では「件数が足りない」と出る。

## 8. カードの自己審査（2026-11-01 Opus。同じ AI による自己審査）

- 判定: APPROVE
- 設計との整合: design §4-3（置き場 ③・全テナント ④・注意書き2つ・テスト用の注意書きと仕込んだ値は出さない・金型とトークン・E2E と見本を同じ PR）、§4-4 の6（注意書き）、Fable 注意5（丸めは画面だけ）、K4。
- 残る未確認: `check-ui-governance` の実際のコマンド名（§4 で Sonnet に package.json から確かめさせる）。mock-dashboard.json を scene1 が読むか（§1 の6）。

END OF CARD
