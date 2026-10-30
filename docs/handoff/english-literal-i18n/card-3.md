# 実装カード 便3 — 受信箱の英語を辞書の言葉にし、時刻の言葉を1つにまとめる

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 設計・訳・実装 2026-10-29「1」。便の順番は design.md §2-7 のとおり（便2 のあと）
- 起点: origin/main 162cb7544。ブランチ release/english-literal-inbox（worktree `/Users/tanizawashingo/worktrees/salesanchor/release-english-literal-inbox`。作業はこの中だけで行う）
- 設計: [design.md](design.md) §2-3、現在地 [recon.md](recon.md) §3-2
- 対象ADR: ADR-027（文字は t() 経由・ja.json と en.json は同じキー）、ADR-144
- 調査の生出力: `/tmp/CC報告ファイル/english-literal-i18n/bin3/`（行番号は 162cb7544 のもの）
- Opus の設計判断:
  - 判断1: 既存のキーで同じ意味のものがあれば、新しいキーを作らずそれを使う（辞書の SSOT）。使う既存キー: `dashboard.priorityFallbackLead`（リード #{{id}}）・`inbox.noLead`・`inbox.sendError.generic`・`inbox.sendError.codeSuffix`・`leads.targetTitlesPlaceholder`・`faq.title`（ja・en とも「FAQ」）・`inbox.elapsed*` の4つ
  - 判断2: 既存キーを使うことで en の文が少し変わる所がある（例: 送信失敗が「Failed to send the message. (code: X)」になる）。en も辞書の文にそろえるのが正しい（design.md §3-2「辞書の en.json の値」）。受信箱の試験は react-i18next をモックしており、これらの英語で探している試験は0件（調査 bin3）
  - 判断3: 時刻の言葉の置き場は、受信箱の共通の処理が既にある `frontend/src/pages/inbox/inbox.types.ts` の helpers（`parseDate` と同じ所）。共通の日時処理は `frontend/src/lib/`・`frontend/src/utils/` に無く、時刻の関数を使うのは受信箱だけ（調査 bin3）なので、新しい置き場を作らない
  - 判断4: 7日以上前の日付と、吹き出しにかざしたときの日時は、`en-US` 固定をやめて今の言語（`i18n.language`）で日付の形を作る。表示の項目（月・日、年・月・日・時・分の2桁）は今と同じ
  - 判断5: 「Me」（送信欄の丸い印）・「EN」（英語へ訳すボタンの文字）・「Human Agent」・「(no body)」・「Filter by Page」・「You: 」は、新しいキーを作る（§1-2）。design.md §3-4（固有名詞も t() を通す）により「EN」もキーにする
  - 判断6: stories（`*.stories.tsx`）の英語は直さない（検査の対象外・画面に出ない）。InboxProfileModal の Hot/Warm/Cold・Small/Medium/Large は便5 で扱う

## 1. 直す所（行は 162cb7544 のもの）

### 1-1. 時刻の言葉（`frontend/src/pages/inbox/inbox.types.ts`・`frontend/src/pages/inbox/InboxKartePanel.tsx`）
- `InboxKartePanel.tsx:86` の `type TFn` と `:90-101` の `elapsedLabel` を `inbox.types.ts` の helpers へ移して export する（中身は変えない）。`InboxKartePanel.tsx` は import して使う（呼び出し `:231`・`:820` はそのまま）
- `relativeTime` を次の形にする:

```ts
/** 現時刻を起点に「N 分前」等の相対表記。7日以上前は今の言語の月日。 */
export function relativeTime(iso: string | null, t: TFn, lang: string): string {
  const d = parseDate(iso);
  if (!d) return "—";
  const diffDay = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  if (diffDay < 7) return elapsedLabel(iso, t);
  return d.toLocaleDateString(lang, { month: "2-digit", day: "2-digit" });
}
```

- `formatAbsolute(iso)` を `formatAbsolute(iso: string | null, lang: string)` にし、`toLocaleString("en-US", …)` の `"en-US"` を `lang` にする（項目はそのまま）
- 呼び出しを直す: `InboxConversationRows.tsx:128` と `InboxMessageThread.tsx:636` は `relativeTime(x, t, i18n.language)`、`InboxMessageThread.tsx:564` は `formatAbsolute(msg.created_at, i18n.language)`。`i18n` は `useTranslation()` から取る（`InboxMessageThread.tsx:101` に例がある。Rows は `:45` の `const { t } = useTranslation();` を `const { t, i18n } = useTranslation();` にする）
- 上の関数を他で呼んでいる所が増えていたら、同じように直す（`git grep -n "relativeTime\|formatAbsolute\|elapsedLabel" frontend/src` で全部確かめる）

### 1-2. 英語の直書き

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `InboxConversationList.tsx:175` | `aria-label="Filter by Page"` | `aria-label={t("inbox.filterByPage")}` |
| `InboxConversationListMobile.tsx:198` | `aria-label="Filter by Page"` | `aria-label={t("inbox.filterByPage")}` |
| `InboxConversationRows.tsx:123` | `` `Lead #${conv.lead_id}` `` | `t("dashboard.priorityFallbackLead", { id: conv.lead_id })` |
| `InboxThreadHeaderMobile.tsx:116` | `` `Lead #${selectedLeadId}` `` | `t("dashboard.priorityFallbackLead", { id: selectedLeadId })` |
| `InboxConversationRows.tsx:133` | `You: ` | `{t("inbox.youPrefix")}` |
| `InboxMessageThread.tsx:563` | `` `Send failed: ${msg.error_code}${msg.error_message ? ` — ${msg.error_message}` : ""}` `` | `` `${t("inbox.sendError.generic")}${t("inbox.sendError.codeSuffix", { code: msg.error_code })}${msg.error_message ? ` — ${msg.error_message}` : ""}` `` |
| `InboxMessageThread.tsx:569` | `"Human Agent"` | `t("inbox.humanAgentLabel")` |
| `InboxMessageThread.tsx:574` | `Send failed ({msg.error_code})` | `{t("inbox.sendError.generic")}{t("inbox.sendError.codeSuffix", { code: msg.error_code })}` |
| `InboxMessageThread.tsx:614` | `"(no body)"` | `t("inbox.noBody")` |
| `InboxMessageThread.tsx:777` | `Me` | `{t("inbox.meAvatar")}` |
| `InboxMessageThread.tsx:831` | `EN` | `{t("translation.outbound.buttonShort")}` |
| `InboxPage.tsx:100` | `FAQ` | `{t("faq.title")}` |
| `InboxProfileModal.tsx:176` | `placeholder="Pokemon, One Piece, ..."` | `placeholder={t("leads.targetTitlesPlaceholder")}` |
| `useInboxState.ts:389` | `"Lead not found."` | `t("inbox.noLead")` |
| `useInboxState.ts:797` | `e.message \|\| "Send failed"` | `e.message \|\| t("inbox.sendError.generic")` |

- `t` が無いファイル・関数では `useTranslation()` から取る。`useInboxState.ts` は `:209` の `t` を使う（`:389`・`:797` がその関数の中にあることを確かめる。外なら BLOCKED:）
- `useCallback` などの依存の配列に `t` が要る所は足す（lint の react-hooks の警告を0にする）

### 1-3. 辞書（`frontend/src/locales/ja.json`・`frontend/src/locales/en.json`。既存のキーは変えない）

| キー | ja | en |
|---|---|---|
| inbox.filterByPage | ページで絞り込む | Filter by Page |
| inbox.youPrefix | あなた:  | You:  |
| inbox.humanAgentLabel | ヒューマンエージェント | Human Agent |
| inbox.noBody | （本文なし） | (no body) |
| inbox.meAvatar | 自分 | Me |
| translation.outbound.buttonShort | EN | EN |

- `inbox.youPrefix` の値は末尾に半角空白を1つ付ける（今の「You: 」と同じ）
- 閲覧ページは受信箱を読み込まない（調査 bin3）ので、閲覧ページの辞書は触らない

### 1-4. 試験
- `frontend/src/pages/inbox/inbox.types.test.ts` を新しく作る（無ければ）。`vi.useFakeTimers` で今の時刻を固定し、`i18n`（`frontend/src/i18n`）の本物の `t` を使って次を確かめる:
  - ja: 30秒前「たった今」・5分前「5分前」・3時間前「3時間前」・2日前「2日前」
  - en: 5分前「5m ago」
  - 10日前: `relativeTime(iso, t, "ja")` が `d.toLocaleDateString("ja", { month: "2-digit", day: "2-digit" })` と同じ・`"en-US"` でも同じく一致
  - `formatAbsolute(iso, "ja")` が `toLocaleString("ja", …同じ項目)` と一致。null は「—」
- 既存の受信箱の試験はモックのまま通ることだけ確かめる（期待値を書き換えない）

## 2. 触らない範囲
- 受信箱の props・DOM・クラス名・`data-testid`・style
- `*.stories.tsx`・閲覧ページ（viewer）とその辞書
- InboxProfileModal の Hot/Warm/Cold・Small/Medium/Large（便5）
- `scripts/`・`.github/workflows/`・バックエンド
- 文書: design.md・recon.md・本カード

## 3. 実測（生出力は `/tmp/CC報告ファイル/english-literal-i18n/bin3/impl/`。主な結果は報告に書く）
- 最初に `cd frontend && npm ci`
- 残りが0: `git grep -nE "Filter by Page|Lead #|You: |Send failed|Human Agent|\(no body\)|Lead not found|\"en-US\"|just now|m ago|h ago|d ago" -- frontend/src/pages/inbox ':!*.stories.tsx' ':!*.test.*'` が0行。`>Me<`・`>EN<`・`>FAQ<` 相当（前後の空白・改行込み）が該当行に残っていないことを `sed -n` で見る
- 検査: `BASE_SHA=origin/main HEAD_SHA=HEAD node scripts/check-ui-governance.js` exit 0。受信箱の .tsx に `countEnglishUiLiteral` をかけ、stories と便5 の Hot/Warm/Cold・Small/Medium/Large 以外が0件
- 辞書: `cd frontend && npm run check:i18n-missing-keys` exit 0。2つの JSON が読める
- 試験: `npx vitest run src/pages/inbox` と新しい試験
- 全体: `npm run lint`・`npx tsc --noEmit`（便2 で api/generated/schema が無いための4件が出たなら、その4件だけであることを変更前と比べて示す）・unit の試験全体

## 4. 検証
| 基準 | 検証方法 |
|---|---|
| 英語が残っていない | §3 の grep が0行・countEnglishUiLiteral の残りが判断6の分だけ |
| 辞書のキーがそろう | check:i18n-missing-keys exit 0 |
| 時刻の言葉が ja と en で正しい | §1-4 の試験が通る |
| 既存の試験が壊れない | 受信箱の試験・unit 全体が通る |
| 範囲 | `git diff origin/main...HEAD --name-only` が受信箱の対象ファイル・新しい試験・辞書2つ・本カード・台帳だけ |
| CI | PR の必須の検査がすべて緑 |
| 画面（反映後・PO） | 受信箱の会話一覧の時刻が「5分前」のように日本語で出る。名前の無い相手が「リード #番号」と出る |

## 5. 想定分岐
- 受信箱の試験で、モックの `t` がキー名を返すために赤 → 試験の名前と失敗の文を保存し NEEDS_DECISION:（期待値を自分で書き換えない）
- `relativeTime`・`formatAbsolute` を受信箱の外でも呼んでいた → 呼び出し元の一覧を保存し NEEDS_DECISION:
- `useInboxState.ts:389`・`:797` が `t` の届かない所にある → BLOCKED:
- lint の react-hooks で依存の警告が出て、依存を足すと再描画の回数が変わるおそれがある所 → その行を保存し NEEDS_DECISION:
- check:i18n-missing-keys が今回と関係ない所で赤（origin/main でも赤） → origin/main の結果も保存して報告。直さない
