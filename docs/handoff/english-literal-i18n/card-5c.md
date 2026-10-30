# 実装カード 便5c — 会社と連絡先の状態の英語を辞書の言葉にする

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 設計・訳・実装 2026-10-29「1」（選択肢の言葉は日本語にそろえる）
- 起点: 作成時の origin/main（ブランチ release/english-literal-status-options。worktree `/Users/tanizawashingo/worktrees/salesanchor/release-english-literal-status-options`。作業はこの中だけで行う）
- 設計: [design.md](design.md) §2-5・§4、現在地 [recon.md](recon.md) §4。便4 のカード [card-4.md](card-4.md) 判断4 で移した `CompanyBasicTab.tsx:92` を含む
- 対象ADR: ADR-027、ADR-144
- 調査の生出力: `/tmp/CC報告ファイル/english-literal-i18n/bin5/recon/`・`/tmp/CC報告ファイル/english-literal-i18n/bin5/opus/status_keys.txt`・`statusPresentation.ts`（行番号は ccd3f475f のもの）
- Opus の設計判断:
  - 判断1: 選択肢の表示は、会社と連絡先の入力欄の部品（`frontend/src/pages/companies/CompanyFormFields.tsx:29-32`・`frontend/src/pages/contacts/ContactFormFields.tsx:40-43`）が既に使っている `customers.status_*` にそろえる。「保留中の重複確認」の値（pending_dedup_review）は、会社の画面では `customers.status_pending_dedup`、連絡先の画面では `contacts.statusPendingDedupOption`（同じ部品の書き方）を使う
  - 判断2: 一覧の状態の札（生の値を出す4か所）は、状態の見た目の中央対応表 `frontend/src/utils/statusPresentation.ts`（SSOT）を通す。連絡先は既にある `contact` の組を使う。会社の組は無いので、`company` の組を同じ形で足し、表示の言葉は判断1 と同じ `customers.status_*` にする（会社の札の見た目は今の `status-badge status-${値}` のクラスのまま。badgeVariant は連絡先の組と同じ値を書くが、この便では札のクラスに使わない）
  - 判断3: 辞書に新しい訳は足さない。既存のキーの値も変えない
  - 未解決（PO へ）: 同じ「重複確認」の状態に、辞書の訳が2通りある（「重複確認待ち」= `customers.status_pending_dedup`・`contacts.statusPendingDedupOption`／「重複確認中」= `contacts.statusCode.pending_dedup_review`）。design.md §2-5 により、そろえる訳は PO が決める。この便ではどちらの値も変えない（今と同じ訳が出る）
  - 判断4: 保存する値（active など）は変えない。バックエンド（`backend/app/schemas/company.py:37`・`contact.py:36`）がこの文字で確かめているため

## 1. 直す所（行は ccd3f475f のもの。ずれていたら同じ文字の行を直す）

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `frontend/src/pages/companies/CompaniesPage.tsx:511-514` | `<option>` の表示が active / inactive / archived / pending_dedup_review の直書き | `t("customers.status_active")` / `_inactive` / `_archived` / `t("customers.status_pending_dedup")` |
| `frontend/src/pages/company-detail/CompanyBasicTab.tsx:89-92` | 同上 | 同上 |
| `frontend/src/pages/contacts/ContactsPage.tsx:348-350` | active / inactive / archived の直書き | `t("customers.status_active")` など |
| `frontend/src/pages/company-detail/CompanyContactsTab.tsx:199-201` | `{ value, label }` の label が直書き | 同上 |
| `frontend/src/pages/contacts/ContactEditPage.tsx:189-191` | 同上（`:192` は既に t） | 同上 |
| `frontend/src/pages/companies/CompaniesPage.tsx:408` | 札の中が `{c.status}` | `{t(getStatusPresentation("company", c.status).labelKey ?? c.status)}`（クラスは変えない） |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:96` | 同上 | 同上 |
| `frontend/src/pages/contacts/ContactsPage.tsx:396` | 札の中が `{c.status}` | `{t(getStatusPresentation("contact", c.status).labelKey ?? c.status)}`（クラスは変えない） |
| `frontend/src/pages/company-detail/CompanyContactsTab.tsx:123` | 同上 | 同上 |
| `frontend/src/utils/statusPresentation.ts` | `StatusDomain` に company が無い | `| "company"` を足し、`STATUS_PRESENTATION_MAP` に `company:` を `contact:` と同じ4つの値・同じ bucket と badgeVariant で足す。labelKey は `customers.status_active`・`customers.status_inactive`・`customers.status_archived`・`customers.status_pending_dedup`。冒頭のコメントの「11」を実際の数にする |

- `t(... ?? 値)` で値がそのまま出るのは、対応表に無い値のときだけ（既存の `getStatusPresentation` の使い方の例 `statusPresentation.ts` の @example と同じ）
- value・props・DOM・クラス名・`data-testid` は変えない

## 2. 辞書
- 触らない（判断3）

## 3. 触らない範囲
- `CompanyFormFields.tsx`・`ContactFormFields.tsx`・`MergeContactModal.tsx`・`ContactEditPage.tsx:192`
- 状態の札のクラス・バックエンド・保存する値・`scripts/`・`.github/workflows/`・stories・辞書
- 文書: design.md・recon.md

## 4. 実測（生出力は `/tmp/CC報告ファイル/english-literal-i18n/bin5c/impl/`）
- 最初に `cd frontend && npm ci`
- 残りが0: §1 の各ファイルで、`<option>` の中身・`label:` の値・札の中身に active / inactive / archived / pending_dedup_review の直書きが残らない（`sed -n` で該当行を保存して示す）
- 検査: `BASE_SHA=origin/main HEAD_SHA=HEAD node scripts/check-ui-governance.js` exit 0
- 辞書: `npm run check:i18n-missing-keys` exit 0
- 試験: statusPresentation の既存の試験があれば流し、`company` の組の4つの値の labelKey を確かめる試験を足す（既存の試験ファイルの書き方に合わせる。無ければ `statusPresentation.test.ts` を作る）。`npx vitest run src/pages/companies src/pages/contacts src/pages/company-detail src/utils`
- 全体: `npm run lint`・`npx tsc --noEmit`（既存4件だけ）・unit 全体（揺れたら揺れたファイルだけ流し直した結果も保存）

## 5. 検証
| 基準 | 検証方法 |
|---|---|
| 英語が残っていない | §4 の sed の結果 |
| 中央対応表を通る | 札の4か所が getStatusPresentation を使う（diff） |
| 既存の試験が壊れない | 対象の試験と unit 全体が通る |
| 範囲 | `git diff origin/main...HEAD --name-only` が §1 のファイル・試験・本カード・台帳だけ |
| CI | PR の必須の検査がすべて緑 |
| 画面（反映後・PO） | 会社の一覧で状態が「有効」と出る。会社の作成の選択肢が「有効・無効・アーカイブ・重複確認待ち」と出る |

## 6. 想定分岐
- 試験が active などの表示で探していて赤 → 試験の名前と失敗の文を保存し NEEDS_DECISION:
- `STATUS_PRESENTATION_MAP` の型や試験が「ドメインの数」を固定していて赤 → その行を保存し NEEDS_DECISION:
- `getStatusPresentation` が開発時に未知の値で警告を出す仕組みが試験を赤にする → 保存し NEEDS_DECISION:
- check:i18n-missing-keys が今回と関係ない所で赤（origin/main でも赤） → origin/main の結果も保存して報告。直さない
