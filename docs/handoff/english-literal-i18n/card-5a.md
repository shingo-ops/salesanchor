# 実装カード 便5a — 見込み客の温度と規模の言葉を1組にする

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 設計・訳・実装 2026-10-29「1」（温度は 高/中/低、規模は 小/中/大）
- 起点: 作成時の origin/main（ブランチ release/english-literal-lead-options。worktree `/Users/tanizawashingo/worktrees/salesanchor/release-english-literal-lead-options`。作業はこの中だけで行う）
- 設計: [design.md](design.md) §2-5・§4、現在地 [recon.md](recon.md) §4
- 対象ADR: ADR-027、ADR-144
- 調査の生出力: `/tmp/CC報告ファイル/english-literal-i18n/bin5/recon/`・`/tmp/CC報告ファイル/english-literal-i18n/bin5/opus/`（行番号は ccd3f475f のもの）
- Opus の設計判断:
  - 判断1: 便5 は3つに分ける（5a 温度と規模・5b 照合の方法・5c 会社と連絡先の状態）。触る辞書の区分と画面が別々で、1つずつ反映して確かめるため（design.md §2-7「1便ずつ」）
  - 判断2: 温度は既にある `leads.temperature_*`（ja 高/中/低）、規模は `leads.estimatedScale_*`（ja 小/中/大）だけを残す。受信箱の右の欄（`frontend/src/pages/inbox/InboxKartePanel.tsx:656-658`・`:686-688`）が既に使っている組で、PO の決定（design.md §4）の訳と同じ
  - 判断3: もう1組の `leads.temp_*`（ja も Hot/Warm/Cold）と `leads.scale_*`（ja も Small/Medium/Large）は、使う所を全部 判断2 の組に変えたあと、辞書から消す（同じ値の訳を1組にする。design.md §5「訳が1つ」）
  - 判断4: 一覧の生の値（`LeadsPage.tsx:486`）は、既存の書き方（`frontend/src/components/MergeContactModal.tsx:233` の `t(\`…${値}\`, { defaultValue: 値 })`）にそろえる。新しい対応表は作らない
  - 判断5: 保存する値（Hot/Warm/Cold・Small/Medium/Large）は変えない。バックエンド（`backend/app/schemas/lead.py:47-56`）がこの文字で確かめているため

## 1. 直す所（行は ccd3f475f のもの。ずれていたら同じ文字の行を直す）

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `frontend/src/pages/inbox/InboxProfileModal.tsx:222-224` | 表示が `Hot` / `Warm` / `Cold` の直書き | `t("leads.temperature_hot")` / `_warm` / `_cold` |
| `frontend/src/pages/inbox/InboxProfileModal.tsx:233-235` | 表示が `Small` / `Medium` / `Large` の直書き | `t("leads.estimatedScale_small")` / `_medium` / `_large` |
| `frontend/src/pages/leads/LeadEditPage.tsx:236-238` | `t("leads.temp_hot")` など | `t("leads.temperature_hot")` など |
| `frontend/src/pages/leads/LeadEditPage.tsx:247-249` | `t("leads.scale_small")` など | `t("leads.estimatedScale_small")` など |
| `frontend/src/pages/leads/LeadsPage.tsx:386-388` | `t("leads.temp_hot")` など | `t("leads.temperature_hot")` など |
| `frontend/src/pages/leads/LeadsPage.tsx:397-399` | `t("leads.scale_small")` など | `t("leads.estimatedScale_small")` など |
| `frontend/src/pages/leads/LeadsPage.tsx:486` | `l.temperature \|\| "-"` | `l.temperature ? t(\`leads.temperature_${l.temperature.toLowerCase()}\`, { defaultValue: l.temperature }) : "-"` |

- value（保存する値）・props・DOM・クラス名・`data-testid` は変えない

## 2. 辞書（`frontend/src/locales/ja.json`・`frontend/src/locales/en.json`）
- 消す: `leads.temp_hot`・`leads.temp_warm`・`leads.temp_cold`・`leads.scale_small`・`leads.scale_medium`・`leads.scale_large`（ja・en とも）
- 消す前に、`git grep -nE "leads\.temp_|leads\.scale_|temp_\\$\{|scale_\\$\{" -- frontend/src ':!frontend/src/locales'`（試験・stories も含む）が §1 の直しのあと0行であることを確かめる。1行でも残れば消さずに NEEDS_DECISION:
- `leads.temperature_*`・`leads.estimatedScale_*` の値は変えない
- 閲覧ページの辞書は触らない

## 3. 触らない範囲
- `frontend/src/pages/inbox/InboxKartePanel.tsx`（既に判断2 の組）
- バックエンド・保存する値・`scripts/`・`.github/workflows/`・stories
- 文書: design.md・recon.md

## 4. 実測（生出力は `/tmp/CC報告ファイル/english-literal-i18n/bin5a/impl/`）
- 最初に `cd frontend && npm ci`
- 残りが0: §2 の grep が0行。`git grep -nE ">(Hot|Warm|Cold|Small|Medium|Large)<" -- frontend/src/pages/inbox/InboxProfileModal.tsx` が0行（前後の空白・改行込みを `sed -n '218,240p'` で見て示す）
- 訳が1組: ja.json で値が「Hot」「Small」の leads.* のキーが0件、「高」「小」の温度・規模のキーが `leads.temperature_hot`・`leads.estimatedScale_small` の1つずつ（python で数えて保存）
- 検査: `BASE_SHA=origin/main HEAD_SHA=HEAD node scripts/check-ui-governance.js` exit 0。InboxProfileModal の countEnglishUiLiteral が6件減って0件
- 辞書: `npm run check:i18n-missing-keys` exit 0。2つの JSON が読める
- 試験: `npx vitest run src/pages/leads src/pages/inbox`。`LeadsPage.tsx:486` の表示の試験を1つ足す（`l.temperature` が "Hot" で ja の本物の i18n なら「高」、null なら「-」。既存の LeadsPage の試験ファイルに足すか、無ければ部品を描かずに済む形で。描く準備が大きすぎるなら足さずに理由を報告）
- 全体: `npm run lint`・`npx tsc --noEmit`（既存4件だけ）・unit 全体（揺れたら揺れたファイルだけ流し直した結果も保存）

## 5. 検証
| 基準 | 検証方法 |
|---|---|
| 英語が残っていない | §4 の grep が0行 |
| 訳が1組 | §4 の数え方の結果 |
| 辞書のキーがそろう | check:i18n-missing-keys exit 0 |
| 既存の試験が壊れない | leads・inbox の試験と unit 全体が通る |
| 範囲 | `git diff origin/main...HEAD --name-only` が §1 のファイル・辞書2つ・試験・本カード・台帳だけ |
| CI | PR の必須の検査がすべて緑 |
| 画面（反映後・PO） | 見込み客の一覧と編集画面で、温度が 高/中/低、規模が 小/中/大 と出る |

## 6. 想定分岐
- 試験が `leads.temp_*`・`leads.scale_*` のキー名や Hot などの表示で探していて赤 → 試験の名前と失敗の文を保存し NEEDS_DECISION:（期待値を自分で書き換えない）
- §2 の grep が0行にならない → 消さずに NEEDS_DECISION:
- check:i18n-missing-keys が今回と関係ない所で赤（origin/main でも赤） → origin/main の結果も保存して報告。直さない
