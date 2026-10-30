# 実装カード 便4 — その他の画面の英語を辞書の言葉にする

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 設計・訳・実装 2026-10-29「1」。便の順番は design.md §2-7 のとおり（便3 のあと）
- 起点: origin/main 436886b47。ブランチ release/english-literal-misc（worktree `/Users/tanizawashingo/worktrees/salesanchor/release-english-literal-misc`。作業はこの中だけで行う）
- 設計: [design.md](design.md) §2-4、現在地 [recon.md](recon.md) §3-3
- 対象ADR: ADR-027（文字は t() 経由・ja.json と en.json は同じキー）、ADR-144
- 調査の生出力: `/tmp/CC報告ファイル/english-literal-i18n/bin4/recon/`（行番号は 436886b47 のもの。recon の行番号と全部一致）
- Opus の設計判断:
  - 判断1: 新しいキーは、その画面が既に使っている辞書の区分に置く（NotificationsPage は `notifications.*`、BadgesPage は `badges.*`、ChannelsPage は `channels.*`、InvoiceDetailPage は `invoices.*`）。既存キーで同じ意味のものがあればそれを使う（schedule.holiday・schedule.shiftLabel・common.done）
  - 判断2: `schedule-utils.ts` の `normalizeShift` は純関数で t を持たない。呼び出し元は `SchedulePageImpl.tsx:942` の1か所だけで、その useEffect は既に依存に t を持つ（調査 bin4）。そこで `normalizeShift(shift, t)` と t を引数で受ける形にする（便3 の relativeTime と同じ型の渡し方）
  - 判断3: `FedexLabelValidationTab.tsx` の `StepHeader`（:45-54）は部品の関数なので、中で `useTranslation()` を呼んで t を取る（15か所の呼び出し元の props を変えない）
  - 判断4: `CompanyBasicTab.tsx:92` の `pending_dedup_review` は、同じ選択肢の並び（:89-92）の `active`・`inactive`・`archived` と一緒に、便5（選択肢の言葉を1組のキーにまとめる）で扱う。この便で1つだけ訳すと、並びの中で日本語と英語の生の値が混ざるため。design.md §2-4 の9行のうち、この1行は便5 へ移す（便5 のカードに書く）
  - 判断5: 「Webhook URL」「Page ID」「ERP Key」は固有名詞・略語だが、design.md §3-4（固有名詞も t() を通す）によりキーにする

## 1. 直す所（行は 436886b47 のもの）

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `frontend/src/pages/notifications/NotificationsPage.tsx:128` | `Webhook URL *`（label の中） | `{t("notifications.webhookUrlLabel")} *` |
| `frontend/src/pages/notifications/NotificationsPage.tsx:155` | 同上 | 同上 |
| `frontend/src/pages/notifications/NotificationsPage.tsx:183` | `header: "Webhook URL"` | `header: t("notifications.webhookUrlLabel")` |
| `frontend/src/pages/badges/BadgesPage.tsx:86` | `` `User #${e.user_id}` `` | `t("badges.userFallback", { id: e.user_id })` |
| `frontend/src/pages/channels/ChannelsPage.tsx:493` | `Page ID:`（strong の中） | `{t("channels.pageIdLabel")}` |
| `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:51` | `aria-label="done"` | `aria-label={t("common.done")}`（StepHeader の中で `const { t } = useTranslation();`） |
| `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:310` | `ERP Key:`（strong の中） | `{t("invoices.erpKeyLabel")}` |
| `frontend/src/pages/schedule/schedule-utils.ts:188` | `shift.shift_type === "holiday" ? "Holiday" : "Shift"` | `shift.shift_type === "holiday" ? t("schedule.holiday") : t("schedule.shiftLabel")` |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx:942` | `.map(normalizeShift)` | `.map((shift) => normalizeShift(shift, t))` |

- `normalizeShift` の形: `export function normalizeShift(shift: <今の型>, t: (key: string) => string): <今の戻り値の型>`。他の中身は変えない
- 上の行が今の中身と違っていたら（行がずれていても同じ文字が1か所だけならそこを直す。2か所以上・0か所なら BLOCKED:）

## 2. 辞書（`frontend/src/locales/ja.json`・`frontend/src/locales/en.json`。既存のキーは変えない）

| キー | ja | en |
|---|---|---|
| notifications.webhookUrlLabel | Webhook URL | Webhook URL |
| badges.userFallback | ユーザー #{{id}} | User #{{id}} |
| channels.pageIdLabel | ページID: | Page ID: |
| invoices.erpKeyLabel | ERPキー: | ERP Key: |

- 置き場は、それぞれの区分の中の、近い意味のキーの隣にする（区分の末尾でもよい）。同じ名前のキーが既にあれば足さずに BLOCKED:
- 閲覧ページの辞書（`frontend/src/locales/viewer/`）は触らない（この画面たちは閲覧ページから読み込まれない。調査 bin4）

## 3. 触らない範囲
- 各画面の props・DOM・クラス名・`data-testid`・style
- `frontend/src/pages/company-detail/CompanyBasicTab.tsx`（便5）
- `*.stories.tsx`・閲覧ページ・`scripts/`・`.github/workflows/`・バックエンド
- 文書: design.md・recon.md（便5 への移しは便5 のカードに書く）

## 4. 実測（生出力は `/tmp/CC報告ファイル/english-literal-i18n/bin4/impl/`）
- 最初に `cd frontend && npm ci`
- 残りが0: `git grep -nE "Webhook URL|User #|Page ID:|ERP Key:|aria-label=\"done\"|\"Holiday\"|\"Shift\"" -- frontend/src/pages/notifications frontend/src/pages/badges frontend/src/pages/channels frontend/src/pages/integrations/FedexLabelValidationTab.tsx frontend/src/pages/invoice-detail frontend/src/pages/schedule ':!*.stories.tsx' ':!*.test.*'` が0行（コメントに残る場合はその行を示す）
- 検査: `BASE_SHA=origin/main HEAD_SHA=HEAD node scripts/check-ui-governance.js` exit 0。触った .tsx に countEnglishUiLiteral をかけて、変更前より増えていない・この表の行の分が減っている
- 辞書: `npm run check:i18n-missing-keys` exit 0。2つの JSON が読める
- 試験: 触ったファイルの近くの試験（`npx vitest run src/pages/schedule src/pages/notifications src/pages/badges src/pages/channels src/pages/integrations src/pages/invoice-detail`）と、`normalizeShift` の試験を新しく1つ（`schedule-utils.test.ts`。無ければ作る。holiday→「祝日」・それ以外→「シフト」を本物の i18n の t の ja で確かめる）
- 全体: `npm run lint`・`npx tsc --noEmit`（`api/generated/schema` が無いための既存4件だけであることを示す）・unit の試験全体（手元が重くて揺れたら、揺れたファイルだけ流し直した結果も保存）

## 5. 検証
| 基準 | 検証方法 |
|---|---|
| 英語が残っていない | §4 の grep が0行 |
| 辞書のキーがそろう | check:i18n-missing-keys exit 0 |
| 予定表のシフトの名前が ja で出る | 新しい試験が通る |
| 既存の試験が壊れない | 触った画面の試験・unit 全体が通る |
| 範囲 | `git diff origin/main...HEAD --name-only` が §1 のファイル・新しい試験・辞書2つ・本カード・台帳だけ |
| CI | PR の必須の検査がすべて緑 |
| 画面（反映後・PO） | 予定表のシフトが「シフト」「祝日」と出る。請求書の詳細に「ERPキー:」と出る |

## 6. 想定分岐
- 既存の試験が英語の文字で探していて赤 → 試験の名前と失敗の文を保存し NEEDS_DECISION:（期待値を自分で書き換えない。調査 bin4 では0件）
- `normalizeShift` を §1 以外でも呼んでいた → 呼び出し元の一覧を保存し NEEDS_DECISION:
- lint の react-hooks で依存の警告が出た → その行を保存し NEEDS_DECISION:
- 足すキーの名前が既にある → BLOCKED:
- check:i18n-missing-keys が今回と関係ない所で赤（origin/main でも赤） → origin/main の結果も保存して報告。直さない
