# 実装カード 段階3 便9 — 読み込み系の部品・画面に残る直書きの言葉を辞書の言葉にする

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 方針 2026-10-23「1」、設計 2026-10-24「1」、英語の直書きの直し方 2026-10-27「1」（全部直す）
- 起点: origin/main 8cf4c84d6。ブランチ release/loading-english-literal（手元で design.md・本カード・台帳を commit 済みのものを push してある。その上に積む）
- 根拠: 事前調査（2026-10-26 クラウド・読み取りのみ。origin/main 447a60e46）。部品の英字の直書き10か所はどれも画面での使用 0件、Spinner の既定値が出る所も 0件。いまの画面に英語は出ていない。画面の「...」2か所と見本ページの日本語5か所は出ている
- 対象ADR: ADR-027（文字は t() 経由）、ADR-144（金型を使う）
- 実行場所: クラウド。push までを行う。PR は手元で作る（scripts/agent-hooks/cloud/rules.md）
- Opus の設計判断:
  - 判断1: 使われていない部品も直す。理由: 今後その部品を使ったときに英語が出るのを防ぐ（PO 選択肢1の原文）
  - 判断2: ProgressBar の 'Done' は既存の common.done（済／Done）を使い、キーを足さない。理由: 意味が同じで、辞書を分散させない
  - 判断3: お客さまの情報の欄（InboxKartePanel）は、文字を持つ span ごと `<LoadingBlock size="sm" inline />` に替え、外側の2つの div（data-testid 付き）は残す。理由: LoadingBlock の外枠は div なので、span の中に入れると入れ子の決まりに反する。段階2 規則E（枠の div は残す）に合う
  - 判断4: 左のメニュー（DesktopShell）は、枠の div.sidebar-loading-dot を残し、中の文字だけを `<LoadingBlock size="sm" inline />` に替える。段階2 規則F（枠の div 自身が文字を持つときは枠を残して文字だけ替える）
  - 判断5: 画面から Spinner を直接呼ばない。今の main で pages・features・components（loading と Button を除く）に Spinner の直接 import は 0件。この形を崩さない
  - 判断6: 英字の直書きを見つける検査は今回は作らない。理由: 直した後の部品の中の英字直書きは 0 になり、eslint の no-japanese-literal と同じ型の英字版は誤検知（クラス名・型名・URL）を見分ける設計が別に要る。今回の範囲を広げない

## 1. 直す所
(1) frontend/src/components/loading/ の部品（useTranslation を使う。LoadingBlock.tsx と同じ書き方）
| ファイル:行 | 今 | 後 |
|---|---|---|
| SaveIndicator.tsx:15 | `<Spinner size="sm" label="Saving" /> Saving` | label と本文の両方を `t('common.saving')` |
| SaveIndicator.tsx:21 | `Saved` | `t('common.saved')` |
| ProgressBar.tsx:51 | `{done ? 'Done' : label}` | `{done ? t('common.done') : label}` |
| Drawer.tsx:32 | `aria-label="Close"` | `aria-label={t('common.close')}` |
| Skeleton.tsx:27・45・66 | `aria-label="Loading"` | `aria-label={t('common.loading')}` |
| SplashScreen.tsx:15 | `aria-label="Loading"` | `aria-label={t('common.loading')}` |
| Spinner.tsx:26 | 既定値 `label = 'Loading'` | 既定値を外し、L31 で `label ?? t('common.loading')` を使う |
- 行番号がずれていたら中身で探す。中身が表と違えば BLOCKED:（ファイル・行・中身）
(2) 画面
- frontend/src/components/DesktopShell.tsx:222-223 `<div className="sidebar-loading-dot">...</div>` → `<div className="sidebar-loading-dot"><LoadingBlock size="sm" inline /></div>`（判断4。LoadingBlock は "./loading" の barrel から import）
- frontend/src/pages/inbox/InboxKartePanel.tsx:770-772 `<span className="right-panel-value">...</span>` → `<LoadingBlock size="sm" inline />`（判断3。外側の div.karte-performance-section と div.right-panel-row は残す。LoadingBlock は既に L15 で import 済み）
(3) 見本ページ frontend/src/pages/design-preview/sections/ButtonSection.tsx（1回目の BLOCKED を受けて直した。判断7）
- :73 `<Button variant="primary" loading>保存中...</Button>` → children を `{t("common.saving")}`
- :74 `<Button variant="secondary" loading>読み込み中</Button>` → children を `{t("common.loading")}`
- このファイルには useTranslation が無い。`import { useTranslation } from "react-i18next";` を既存の import の並びに足し、コンポーネントの先頭で `const { t } = useTranslation();` を足す
- 同じファイルの :53 の説明文・:71 の行ラベルの「読み込み中」、BadgeSection.tsx の「処理中」、ほかの日本語は変えない（判断7）
- 判断7（Opus、1回目の BLOCKED のあと）: 見本ページは eslint.config.js:246-252 で「日本語表記を許可」と決めた例外のページで、日本語は 407 行ある。事前調査の5か所は読み込みに関わる言葉だけを数えたもので、ページ全体の数ではなかった。直すのは、読み込み中の見本として金型 Button の loading に渡している言葉2か所だけにする。BadgeSection の「処理中」は状態バッジの見本（対応済み・保留中・要対応・未分類と並ぶ）で読み込みの表示ではないため、外す。辞書のキーは足さない

## 2. 試験
- frontend/src で、上の部品・画面の試験と stories のうち、'Loading'・'Saving'・'Saved'・'Close'・'Done'・'...'・「処理中」の文字を期待しているものを git grep で探し、すべて列挙する
  - 例: components/loading/Spinner.test.tsx（Spinner の既定 label、SaveIndicator の saving/saved）
- 期待を、試験の i18n 設定で実際に出る言葉にそろえる（試験の setup が ja か en かを先に確かめ、その言語の辞書の値を使う。既存の試験の書き方に合わせる）。label を明示して渡している試験（label="Fetching" 等）は変えない
- 足す試験: Spinner に label を渡さないと aria-label が common.loading の値になる、SaveIndicator の saving/saved の文字が辞書の値になる、の2点（既存の Spinner.test.tsx に足す）
- DesktopShell・InboxKartePanel に読み込み中の試験があれば、「...」の期待を role="status" の有無に替える。無ければ足さない（報告だけ）

## 3. 実測（生出力は /tmp/CC報告ファイル/loading-english-literal/impl/。無ければ作る。主要な結果は報告に書く）
- 直書き 0: `git grep -nE "\"(Loading|Saving|Saved|Close|Done)\"|'(Loading|Saving|Saved|Close|Done)'" -- frontend/src/components/loading` が試験・stories 以外で 0
- 画面の「...」0: DesktopShell.tsx と InboxKartePanel.tsx の読み込み中の枝に `...` の文字が無い
- 見本ページ: `git grep -nE "loading>(保存中\.\.\.|読み込み中)</Button>" -- frontend/src/pages/design-preview` が 0
- 辞書: ja.json・en.json は変えない（git diff に出ない）。viewer 辞書は判断8の3キーだけ足す

## 3-2. 閲覧ページの辞書（2回目の NEEDS_DECISION を受けて足した。判断8）
- frontend/src/locales/viewer/ja.json と viewer/en.json の "common" に、次の3キーを足す（値は本体辞書と同じ文字にする）
  - ja: `"saving": "保存中..."`・`"saved": "保存しました"`・`"done": "済"`
  - en: `"saving": "Saving..."`・`"saved": "Saved"`・`"done": "Done"`
  - 足す前に本体の frontend/src/locales/ja.json・en.json の common.saving・common.saved・common.done の値を読み、上と違えば本体の値を使い、違いを報告する
- 判断8（Opus）: check-i18n-missing-keys.js:22-26 は「閲覧ページの入口から import をたどって届く金型の t() は、本体辞書と viewer 辞書の両方に要る」と決めている（ADR-1019 の閲覧ページ専用辞書）。viewer 辞書には既に金型用の common.close・common.loading が同じ形で入っている。今回 SaveIndicator・ProgressBar が t() を使うようになり、同じ仕組みで3キーが要るようになった。既存の仕組みに従うだけで、新しい置き場は作らない。本体辞書（ja.json・en.json）は変えない

## 4. 触らない範囲
- loading/Drawer と components/Drawer の重複（別件。loading/Drawer は使用 0件のまま残す）
- 検査スクリプト（判断6）、CSS（.sidebar-loading-dot の規則も消さない）、金型の props・見た目
- 上の表に無いファイル。本体辞書（ja.json・en.json）。viewer 辞書は §3-2 の3キー以外

## 5. 文書
- docs/handoff/loading-indicator/design.md の 3-7 残件に、手元で足した「便9（card-20）」の行がある。中身を変えない
- 本カードは手元で commit 済み。中身を変えない

## 6. 検証
| 基準 | 検証方法 |
|---|---|
| 直書きの言葉 0 | §3 の3つの grep が 0 |
| 型 | `cd frontend && npm run generate:api-types && npx tsc --noEmit` 0 件（schema.d.ts は .gitignore:128 で除外された生成物。CI の frontend-check.yml:30 も tsc の前に生成する。2回目の4件はこれを生成していなかったため） |
| lint | `npx eslint` を変えたファイルにかけ、警告 0 |
| 辞書 | `node scripts/check-i18n-missing-keys.js` exit 0、ja/en キー数一致 |
| 試験 | `npx vitest run --project unit src/components src/pages/inbox src/pages/design-preview` pass（§2 の修正込み） |
| UI ガバナンス | `BASE_SHA=8cf4c84d6 HEAD_SHA=HEAD node scripts/check-ui-governance.js` exit 0 |
| 範囲 | `git diff origin/main...HEAD --name-only` が §1 のファイル・§2 で直した試験・§3-2 の viewer 辞書2つ・design.md・card-20.md・台帳だけ |
| 本番（手元で確かめる） | 合流と本番反映のあと、配信 JS で左のメニューとお客さまの情報の欄の読み込み中の枝が sa-loading-block の呼び出しになっている |

## 7. 想定分岐
- 試験の i18n が初期化されておらず t() がキーそのものを返す → 期待をキー文字列にそろえる（既存の試験がそうしていればそれに倣う）。どちらとも決まらなければ NEEDS_DECISION:
- LoadingBlock を DesktopShell の barrel から import すると循環 import の警告が出る → `./loading/LoadingBlock` から直接 import する。それでも出るなら BLOCKED:
- §2 で英語を期待する試験が 15 ファイルを超える → 直さずに一覧を NEEDS_DECISION:
- UI ガバナンス検査が赤 → どの種別が増えたかを報告して BLOCKED:（ui-allow で逃げない）
- §1 の行番号・中身が実物とずれている → 中身で探して一致すればその行を直し、ずれを報告する。中身が見つからなければ BLOCKED:
