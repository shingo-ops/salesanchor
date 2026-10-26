# recon: 閲覧ページの絞り込みを「項目をタップ → 次の画面で選ぶ」に変える（便2・現在地）

> この文書は何か（1行）: 便1で入れた「その場に全部並べる」形が使いにくいという PO の実使用の判断を受けて、メルカリと同じ「次の画面で選ぶ」形に変える前の、**現物のコードと実機で測った数字**の置き場。

**日付**: 2026-10-25
**ベース**: `origin/main` = `43e8e3ab1`
**PO 指示（原文）**: 「2で『項目をタップ → 次の画面で選ぶ』形（メルカリと同じ）に変える、使いづらい」
**PO 承認（形の決定・2026-10-25）**: 2案を図で示し「**右から入れ替わる（メルカリと同じ）**」を選択。
**前便**: `docs/handoff/viewer-inventory-mobile-filter/` （PR #4731・本番反映済み・実機確認済み）

## 1. 便1 の結果と、そこで分かった使いにくさ

便1 で「絞り込みパネルの中にチェックボックスを全部並べる」形にして本番に出した。
不具合（選択肢が見えない）は解消したが、**実機で測ると次の問題が残った**。

| 測った値 | 実測（本番・2026-10-25・CSS幅360） |
|---|---|
| 提供者の選択肢 | **42 件** |
| コンディションの選択肢 | **15 件** |
| 「提供者」の見出しの位置 | y = **100** |
| 「コンディション」の見出しの位置 | y = **2024** |
| 画面の高さ | 672 |

→ **コンディションに辿り着くまでに、提供者42件ぶん（約1900px）スクロールが要る。**
PO の「使いづらい」はこれ。測り方は `docs/handoff/viewer-inventory-mobile-filter/recon.md` 冒頭と同じ
（実機 Chrome に `adb forward` でつなぎ `Runtime.evaluate` で直読み）。

## 2. お手本（メルカリ）がこれをどう解いているか

実測は `docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md`。

| 事実 | 値 |
|---|---|
| 選択肢が多い項目（カテゴリー・ブランド・サイズ）は**次の画面に進む** | 親の行は高さ **52.7**・左にラベル・右に現在値・右端に「>」 |
| 未選択のときの現在値 | 「指定しない」 |
| 選択後の現在値 | **選んだ名前をカンマでつなぐ**（実測「IRWIN, AEG」）。件数ではない |
| 進んだ先の画面 | 上の帯 **48**（←／題／クリア）・候補を絞る検索欄 **268x48**・チェックボックスの行 **60.7〜68.7（行まるごと押せる）**・下に固定の「決定する」**268x48** |

## 3. 使える金型（ADR-144: 新しく作る前に必ず既存を確認する）

| 金型 | 場所 | 本便での使い方 |
|---|---|---|
| `Drawer` | `frontend/src/components/Drawer.tsx` | 絞り込みパネル本体。**`title` と `footer` は差し替えられるが「← 戻る」が無い**（`:138-164` のヘッダは題と「フルページで開く」と「閉じる」だけ） |
| `MultiSelect` | `frontend/src/components/MultiSelect.tsx` | 便1 で `layout="inline"` を追加済み（本番稼働中）。**選択肢の一覧はこれをそのまま使える** |
| `TextFieldControl` | `frontend/src/components/TextField.tsx` | 候補を絞る検索欄 |
| `Button` | `frontend/src/components/Button.tsx` | 「決定する」 |
| `Sheet` | `frontend/src/components/Sheet.tsx` | **今回は使わない**（下から出る・`max-height: 80dvh`。PO は「右から入れ替わる」を選択） |
| `ListRow` | `frontend/src/components/ListRow.tsx` | **使えない**。会話一覧の行（丸い画像＋2段の文字）用で、「ラベル＋現在値＋>」の形ではない |

**不足しているもの2つ**
1. `Drawer` の「← 戻る」。
2. 「ラベル＋現在値＋>」の行。→ **新しい金型は作らない**。`MultiSelect` に表示の形を1つ足して金型の中に収める（便1 で `inline` を足したのと同じやり方）。

## 4. アイコンと、閲覧ページの容量の上限（ここを外すと CI で落ちる）

| 事実 | 引用 |
|---|---|
| **閲覧ページには JS 合計 300KB の上限がある** | `frontend/scripts/check-viewer-bundle.js:21`（`const LIMIT_KB = 300;`）・`:69`（超えたら失敗）。CI は `.github/workflows/frontend-check.yml` で必ず実行する |
| そのため**閲覧ページが使うアイコンは `frontend/src/constants/icons-base.tsx` にだけ定義する**決まりがある | `frontend/src/constants/icons-base.tsx:2-3`（「閲覧ページ（JS 上限300KB）が使う最小のアイコン。**定義はここだけ**。icons.tsx が再 export する」） |
| `Drawer` 金型も `icons-base` から読んでいる（`frontend/src/constants/icons.tsx` を見ていない） | `frontend/src/components/Drawer.tsx:19`（`import { X, ArrowTopRight } from "../constants/icons-base";`） |
| `icons-base` の中身は少ない（`ArrowUp`・`ArrowDown`・`X`・`ArrowTopRight` ほか） | `frontend/src/constants/icons-base.tsx:48-52` |
| 左向き矢印（←）も右向きの「>」も **`icons-base` には無い** | 同上 |
| `frontend/src/constants/icons.tsx` 側には在るが、名前は `ICON.*` ではない | `frontend/src/constants/icons.tsx:209`（`NAV_ICONS`・`chevronDown`）・`:234`（`DashboardIcons`・`arrowRight`）・`:358`（`SCHEDULE_SETTINGS_ICONS`・`back`） |
| **`ICON` はアイコンの「大きさ」の定数**で、アイコンそのものではない | `frontend/src/constants/iconSizes.ts:5`（`export const ICON = { sm: 14, md: 16, ... }`）。生成物のため直接編集しない |
| 包み方は `hi()`（heroicons を `Icon` 型にする） | `frontend/src/constants/icons-base.tsx:8`・`:27` |

→ **足す場所は `frontend/src/constants/icons-base.tsx` 一択**。`frontend/src/constants/icons.tsx` に足すと閲覧ページが重い方のファイルを読み込み、300KB の関所に当たる恐れがある。
なお `frontend/AGENTS.md:64` の追加手順は「lucide-react で確認 → constants/icons.tsx に追加」と書かれているが、
**実際のコードは heroicons を `hi()` で包む形**（`frontend/src/constants/icons-base.tsx:8`・`:27`）で、手順書の記述は実態と合っていない。本便は実態に合わせる。

## 5. 便1 で入れた守り手（壊さないこと）

`frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts`（A4〜A13）。
本便は画面の形を変えるので、**この spec も同じ PR で直す**（`frontend/AGENTS.md`「E2E テスト更新ルール」）。
ただし次の3つは**形が変わっても守り続ける**:
- ドロワーが開いている間 `.comp-popover` が 0 件
- 選択肢の行が画面幅に収まり、高さ 44px 以上
- 2件選ぶと一覧が絞られる

## 6. 未確認（推測で埋めない）

- 進んだ先の画面で**一度に何件見えるか**は、作ってから実機で測る（お手本は約12件）。
- 「決定する」を押さずに「←」で戻ったときの扱い（便1 と同じ即時反映のままにするか）は設計で決める。
