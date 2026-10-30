# 実装カード 便5b — 照合の方法の言葉を1組にする

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 設計・訳・実装 2026-10-29「1」（照合は「完全一致」）
- 起点: 作成時の origin/main（ブランチ release/english-literal-match-type。worktree `/Users/tanizawashingo/worktrees/salesanchor/release-english-literal-match-type`。作業はこの中だけで行う）
- 設計: [design.md](design.md) §2-5・§4、現在地 [recon.md](recon.md) §4
- 対象ADR: ADR-027、ADR-144
- 調査の生出力: `/tmp/CC報告ファイル/english-literal-i18n/bin5/recon/`・`/tmp/CC報告ファイル/english-literal-i18n/bin5/opus/match_keys.txt`（行番号は ccd3f475f のもの）
- Opus の設計判断:
  - 判断1: 照合の方法の値の訳は、既にある `ruleManagement.matchType.*`（LITERAL 完全一致・REGEX 正規表現・DEFAULT デフォルト・RELEASE 発売日）だけを残す。PO の決定（design.md §4）の訳「完全一致」と同じ組で、ルール管理の画面（`frontend/src/pages/super-admin/components/RuleDrawer.tsx:270-273`・`RuleManagementPanel.tsx:129`）が既に使っている
  - 判断2: 足りない値 KEYWORD は、その組に `ruleManagement.matchType.KEYWORD` として足す。訳は今の `superAdmin.conditionsAdmin.fields.matchTypeKeyword` の値をそのまま写す（ja キーワード一致・en Keyword）
  - 判断3: もう2組の値の訳（`statusMaster.matchTypeRegex/Literal/Default`・`superAdmin.conditionsAdmin.fields.matchTypeKeyword/Regex/Literal/Default`）は、使う所を全部 判断1 の組に変えたあと辞書から消す。項目名の `statusMaster.matchType`・`superAdmin.conditionsAdmin.fields.matchType`（「一致タイプ」「言葉の探し方は？」）は値の訳ではないので残す
  - 判断4: 生の値の表示は、既存の書き方（`RuleManagementPanel.tsx:129` の `t(\`${f}.matchType.${row.match_type}\`, { defaultValue: row.match_type })`）にそろえる
  - 判断5: 保存する値（LITERAL など）は変えない。バックエンド（`backend/app/schemas/central_masters.py:620-653`）がこの文字で確かめているため
  - 影響: 状態マスタと条件マスタの画面で、「文字列一致」が「完全一致」に変わる（PO の決定どおり）

## 1. 直す所（行は ccd3f475f のもの。ずれていたら同じ文字の行を直す）

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `frontend/src/pages/note-master/NoteMasterPage.tsx:84-88` | ファイルの外側の定数 `MATCH_TYPE_OPTIONS`（表示が LITERAL / REGEX / DEFAULT の直書き） | 値だけの並びにし、部品の中で `label: t(\`ruleManagement.matchType.${value}\`)` を付けて `:300` に渡す |
| `frontend/src/pages/note-master/NoteMasterPage.tsx:229` | `{n.match_type}` | `{t(\`ruleManagement.matchType.${n.match_type}\`, { defaultValue: n.match_type })}` |
| `frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:81-85` | 上と同じ定数 | 上と同じ直し（使う所は `:286`） |
| `frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:193` | `{row.match_type}` | `{t(\`ruleManagement.matchType.${row.match_type}\`, { defaultValue: row.match_type })}` |
| `frontend/src/pages/status-master/StatusMasterPage.tsx:124-126` | `t(\`${f}.matchTypeRegex\`)` など | `t("ruleManagement.matchType.REGEX")` など |
| `frontend/src/pages/status-master/StatusMasterPage.tsx:197` | `{ key: "match_type", header: … }`（生の値） | 同じ列に `renderCell: (r) => t(\`ruleManagement.matchType.${r.match_type}\`, { defaultValue: r.match_type })` を足す（列の型 `DataTableColumn` の書き方は同じファイルの他の列に合わせる） |
| `frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:236-239` | `t(\`${f}.matchTypeKeyword\`)` など | `t("ruleManagement.matchType.KEYWORD")` など |
| `frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:257` | 生の値の列 | StatusMasterPage と同じく renderCell を足す |

- 部品の外の定数を部品の中で使う形にするとき、毎回の描画で並びを作り直すなら `useMemo(..., [t])` にする（同じファイルに useMemo の例があればそれに合わせる）
- value・props・DOM・クラス名・`data-testid` は変えない

## 2. 辞書（`frontend/src/locales/ja.json`・`frontend/src/locales/en.json`）
- 足す: `ruleManagement.matchType.KEYWORD`（ja キーワード一致・en Keyword）
- 消す: `statusMaster.matchTypeRegex`・`statusMaster.matchTypeLiteral`・`statusMaster.matchTypeDefault`・`superAdmin.conditionsAdmin.fields.matchTypeKeyword`・`…matchTypeRegex`・`…matchTypeLiteral`・`…matchTypeDefault`（ja・en とも）
- 消す前に、`git grep -nE "matchTypeRegex|matchTypeLiteral|matchTypeDefault|matchTypeKeyword" -- frontend/src ':!frontend/src/locales'`（試験・stories も含む）が §1 の直しのあと0行であることを確かめる。1行でも残れば消さずに NEEDS_DECISION:
- 残す: `statusMaster.matchType`・`superAdmin.conditionsAdmin.fields.matchType`（項目名）と `ruleManagement.matchType` の既存の4つの値

## 3. 触らない範囲
- `RuleDrawer.tsx`・`RuleManagementPanel.tsx`（既に判断1 の組）
- バックエンド・保存する値・`scripts/`・`.github/workflows/`・stories
- 文書: design.md・recon.md

## 4. 実測（生出力は `/tmp/CC報告ファイル/english-literal-i18n/bin5b/impl/`）
- 最初に `cd frontend && npm ci`
- 残りが0: §2 の grep が0行。`MATCH_TYPE_OPTIONS` の並びに表示の英語（`label: "LITERAL"` など）が残っていないことを `git grep -n "label: \"\(LITERAL\|REGEX\|DEFAULT\)\"" -- frontend/src` で0行
- 訳が1組: ja.json で値が「文字列一致」のキーが0件、「完全一致」の照合の値のキーが `ruleManagement.matchType.LITERAL` の1つ（`superAdmin.knowledge.patternTypes.exact` は別の用途なので数えない。python で数えて保存）
- 検査: `BASE_SHA=origin/main HEAD_SHA=HEAD node scripts/check-ui-governance.js` exit 0
- 辞書: `npm run check:i18n-missing-keys` exit 0。2つの JSON が読める
- 試験: `npx vitest run src/pages/note-master src/pages/status-master src/pages/super-admin`
- 全体: `npm run lint`・`npx tsc --noEmit`（既存4件だけ）・unit 全体（揺れたら揺れたファイルだけ流し直した結果も保存）

## 5. 検証
| 基準 | 検証方法 |
|---|---|
| 英語が残っていない | §4 の grep が0行 |
| 訳が1組 | §4 の数え方の結果 |
| 辞書のキーがそろう | check:i18n-missing-keys exit 0 |
| 既存の試験が壊れない | 対象の試験と unit 全体が通る |
| 範囲 | `git diff origin/main...HEAD --name-only` が §1 のファイル・辞書2つ・本カード・台帳だけ |
| CI | PR の必須の検査がすべて緑 |
| 画面（反映後・PO） | 状態マスタの一覧で「一致タイプ」の列が「完全一致」「正規表現」と日本語で出る |

## 6. 想定分岐
- 試験が消すキー名や LITERAL の表示で探していて赤 → 試験の名前と失敗の文を保存し NEEDS_DECISION:
- §2 の grep が0行にならない → 消さずに NEEDS_DECISION:
- `DataTableColumn` に renderCell が無い・形が違う → 同じファイルの他の列の書き方を保存し BLOCKED:
- check:i18n-missing-keys が今回と関係ない所で赤（origin/main でも赤） → origin/main の結果も保存して報告。直さない
