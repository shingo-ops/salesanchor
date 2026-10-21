# 実装カード: 読み込み中の表示を動く印に（段階1 要確認画面だけ）

- PO承認: 2026-10-22 PO「1」（要確認画面で先に試し、良ければ全部に広げる）。本カードは段階1のみ。
- 担当: Sonnet（実装）／Opus（審査・合流）
- 区分: 画面だけの変更（migrations / deploy.yml / 本番 scripts を含まない）

## 目的（○×）
要確認画面（LINE解析 → 要確認タブ）で一覧の取得中、「読み込み中...」の文字の代わりに、金型の回る丸（Spinner）が出る。

## 現在地（origin/main・調査 /tmp/CC報告ファイル/loading-indicator-recon/）
- frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:284 `{loading && <p role="status">{t("common.loading")}</p>}`
- 金型: frontend/src/components/loading/Spinner.tsx:6-32（props: size / label など。role="status" と aria-label を自分で付ける。label 既定 'Loading'）。index.ts から export。
- アニメーション: frontend/src/loading-animations.css:66-103（トークン --duration-spinner = tokens.css:135）。prefers-reduced-motion で停止（:543-551）。
- 今の利用は Button.tsx:68 の1か所だけ。

## 変更（この1行だけ）
変更前:
```tsx
{loading && <p role="status">{t("common.loading")}</p>}
```
変更後:
```tsx
{loading && <Spinner size="md" label={t("common.loading")} />}
```
import は既存の import 群の並びに合わせて `import { Spinner } from "../../../components/loading";`（index.ts の export 名を実物で確認すること。Spinner が index.ts から出ていなければ `../../../components/loading/Spinner` を使い、報告に書く）。

- label は必ず t("common.loading")（ADR-027。既定の 'Loading' 英語直書きを画面に出さない）。
- 色・大きさ・余白の直値・style 属性・新しい CSS を足さない（ADR-067/ADR-144）。Skeleton は aria-label="Loading" が英語直書き（Skeleton.tsx:27）なので今回は使わない。

## 触らない範囲
- 上記1行と import 1行以外の NeedsReviewTabsPanel.tsx。
- ほかの約50か所の「読み込み中」表示、金型 components/loading/ の中身、DataTable、ja.json/en.json（キーは既存の common.loading を使う）。
- docs/CC_UI_GOVERNANCE.md への決まりの追記（段階2で行う）。

## 想定分岐（実物を見て判断。合わなければ止めて Opus へ NEEDS_DECISION）
- 試験が `getByText("読み込み中...")` 等の文字で読み込み中を探している場合: 文字は aria-label になるので `getByRole("status", { name: ... })` に直す。直すのは NeedsReviewTabsPanel*.test.tsx の該当行だけ。行と変更前後を報告。
- 計時（useReviewTiming）の試験が role="status" の有無に依存していたら、変更せず止めて報告。
- ReviewCsvPanel など同じ画面の別部品にも role="status" があり、試験の getByRole("status") が複数一致して落ちる場合: name 指定で絞る。

## 検証
| 基準 | 検証方法 |
|---|---|
| 読み込み中に回る丸が出る | vitest で loading 中に `role="status"` かつ name=common.loading の訳語の要素があり、class に sa-spinner を含む（試験を1件追加してよい: NeedsReviewTabsPanel.view.test.tsx） |
| 文字の「読み込み中...」の p 要素が無い | 同じ試験で `<p>` の読み込み中文字が無いこと |
| 既存の試験が通る | `npx vitest run src/pages/super-admin/components/NeedsReviewTabsPanel` 全緑 |
| 規約 | eslint 0・UIガバナンス検査緑・i18n ja/en 差 0 |
| 本番 | 合流・反映後、PO が要確認画面で目視（「再読み込みしてから」） |

## 戻し方
この PR の revert。
