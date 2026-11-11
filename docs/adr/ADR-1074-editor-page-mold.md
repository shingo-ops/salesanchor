# ADR-1074: 窓いっぱいの編集画面は金型 EditorPage 1 つで描く（Google の予定の編集画面の形・塗りの欄と丸い保存はこの金型の中だけ）

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（設計案。PO の判断待ち） |
| 備考 | PO 2026-11-11「予定の詳細画面だけどGoogleカレンダーをクローンしてほしくて左側に寄せたり入力欄の角の丸みも真似てほしい、今の金型だと実現できないから別途金型を作って」。範囲は PO の選択「作るときと直すとき両方」（2026-11-11）。 |
| 起案日 | 2026-11-11 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-144（金型の決まり）、ADR-067（トークン）、ADR-027（i18n）、ADR-073（見本帳）、ADR-1060（Meet は保存のときに作る）、ADR-1051（本番の画面点検 S13）、ADR-1065（予定の画面は金型で描く）。設計: `docs/handoff/schedule-gcal-clone/design.md` §2.7・§3.19 |

---

## What（何を決めたか）

1. 窓いっぱいの編集画面の入れ物は新しい金型 `EditorPage`（`frontend/src/components/EditorPage.tsx`）1 つにする。形は Google カレンダーの予定の編集画面に合わせる: 中身は左に寄せ、上の段に ×・題名の欄・丸い保存、その下に札の上の中身（lead）、角の大きい白い札の中に絵の列と欄の行。
2. 今の金型 `FullScreenDialog`（真ん中寄せの 1 列）は消す。同じ働きの金型を 2 つ置かない（`docs/specs/design-system/design.md:32`）。振る舞い（Esc・フォーカス・portal・読み上げ）は EditorPage にそのまま移す。
3. 欄の新しい種類 `editor-filled`（角 `--radius-sm`・枠なし・塗りの地 `--comp-input-filled-bg`・高さ `--space-10`）と `editor-title`（下線だけ・`--font-2xl`）を金型 TextField・Select・Textarea に足す。使ってよいのは EditorPage の中に置く欄だけで、`frontend/src/components/editorVariantUsage.test.ts` が外での使用を CI で止める。入力欄は完全に丸いという決まり（`docs/specs/design-system/design.md:811`）の例外はこれだけ。
4. 丸い保存（Button `shape="pill"`）を使ってよい場所に金型 EditorPage を足す（`frontend/src/components/buttonShapeUsage.test.ts`）。画面のファイルには足さない。
5. 予定は作るときも直すときもこの編集画面で直す。詳しくの小窓の中で入力欄に変わる形は無くす。

## Why（なぜ）

- PO が Google の形（左寄せ・角の小さい欄）を求め、今の金型では作れないので別の金型を作るよう指示した。今の金型は中身を真ん中寄せの 1 列にするだけで、左に寄せる・札で包む・絵の列を作る口が無い（`frontend/src/components/FullScreenDialog.css:46-49`）。
- 寸法は Google の画面を窓 1279×1448 で測った値（`docs/handoff/schedule-gcal-clone/recon.md` §8.1）。比べる相手が本物なので、成功条件は「同じ位置・同じ形か」で ○× を付けられる。
- 今の金型を使うのは予定の編集 1 か所だけで、口を足して 2 つの形を持たせる理由が無い。消すことで「どちらを使うか」の迷いが残らない。
- 塗りの欄と丸い保存を全体に広げると、ほかの画面の見た目の決まり（完全に丸い欄・ログインだけの丸いボタン）が崩れる。金型の中だけに閉じ、CI の試験で外への広がりを止める。
- 直す形を小窓と全画面の 2 つ持つと、同じ項目の描き方が 2 通りになる。1 つにまとめる。

## 受け入れたリスク

- 色は Google の青ではなくアプリのトークン（ADR-067）を使う。欄の地は Google の rgb(233,238,246) に最も近い既存の `--link-active-bg`（#ebeff8）。
- 保存の高さはアプリの金型 Button の md（36px）で、Google の 40px と 4px 違う。押した欄の下線は 2px で、Google の 3px と違う。
- 招待する人・通知・繰り返し・タイムゾーン・「時間を探す」のタブ・説明の飾りの帯は、アプリに機能が無いので作らない。
- 詳しくの小窓から直すと、小窓は閉じて編集画面が開き、閉じるとカレンダーに戻る（Google と同じ）。今までの「小窓の中で直す」動きに慣れた人には変化になる。

## 戻し方

この便の PR を revert する（frontend と書類だけ。DB・移行・設定は変えない）。古い金型も revert で戻る。

## 測り方

- G58〜G64（設計 §2.7）。位置と形は本番で窓 1279×1448 の `getBoundingClientRect`・`getComputedStyle` を読み、Google の実測と並べる。
- CI: 「UI governance gate」「Lint & Dark Mode Check」・`editorVariantUsage.test.ts`・`buttonShapeUsage.test.ts`・`git grep FullScreenDialog -- frontend` が 0 件。
- 本番の画面点検 S13（ADR-1051）が、合流の後も毎日 07:00 と配備の後に合格のまま。
