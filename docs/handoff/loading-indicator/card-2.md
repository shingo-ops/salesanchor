# 実装カード: 段階2 便1 金型 LoadingBlock の新設と検査

- PO承認: 2026-10-22 PO「金型を変更したら全部切り替わるようにしたほうが良い」「確立したなら進める」（ADR-144 §4 の金型新設の許可として扱う）。設計: design.md §段階2・recon.md §段階2。
- 担当: Sonnet（実装）／Opus（審査・合流）
- 区分: 画面と検査の変更（migrations / deploy.yml / 本番 scripts を含まない）
- worktree: /Users/tanizawashingo/worktrees/salesanchor/release-loading-state-mold（毎回この絶対パスへ cd）

## 作るもの・変えるもの（これ以外は触らない）
1. frontend/src/components/loading/LoadingBlock.tsx（新規）
```tsx
import { useTranslation } from 'react-i18next';
import { Spinner } from './Spinner';
import type { SpinnerSize } from './Spinner';
import './LoadingBlock.css';

export interface LoadingBlockProps {
  /** Accessible label. Default: t("common.loading"). */
  label?: string;
  size?: SpinnerSize;
  /** Inline (no padding) for use inside a row or form. */
  inline?: boolean;
  className?: string;
}

/** The single loading indicator for areas that are fetching data. */
export function LoadingBlock({ label, size = 'md', inline = false, className }: LoadingBlockProps) {
  const { t } = useTranslation();
  const cls = ['sa-loading-block', inline ? 'sa-loading-block--inline' : '', className].filter(Boolean).join(' ');
  return (
    <div className={cls}>
      <Spinner size={size} label={label ?? t('common.loading')} />
    </div>
  );
}
```
   - `useTranslation` の import 元は、frontend/src/components/ConfirmModal.tsx の import 行に合わせる（違えばそちらに従い報告）。
2. frontend/src/components/loading/LoadingBlock.css（新規。var() だけ。直値・px 禁止）
```css
.sa-loading-block {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  color: var(--text-muted);
}
.sa-loading-block--inline {
  display: inline-flex;
  padding: 0;
  vertical-align: middle;
}
```
3. frontend/src/components/loading/LoadingBlock.stories.tsx（新規。frontend/src/components/Callout.stories.tsx 等の既存 stories の書き方に合わせる。Default・Small・Inline・CustomLabel の4つ）
4. frontend/src/components/loading/LoadingBlock.test.tsx（新規。i18n を `import i18n from '../../i18n'` し beforeEach で `changeLanguage('en')`。import の相対パスは ProductMasterPanel.test.tsx:6 を見て合わせる）
   - 既定: `getByRole('status', { name: 'Loading...' })` があり class に `sa-spinner sa-spinner--md`、外側 div の class が `sa-loading-block`
   - `label="X"` で name が X
   - `size="sm"` で `sa-spinner--sm`
   - `inline` で外側に `sa-loading-block--inline`
   - status が1つだけ（`getAllByRole('status').length === 1`）
5. frontend/src/components/loading/index.ts に2行追加（Spinner の export の直後）
```ts
export { LoadingBlock } from './LoadingBlock';
export type { LoadingBlockProps } from './LoadingBlock';
```
6. frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx
   - 変更前 :285 `{loading && <Spinner size="md" label={t("common.loading")} />}`
   - 変更後 `{loading && <LoadingBlock />}`
   - :19 の import を `import { LoadingBlock } from "../../../components/loading";` に変える（Spinner をこのファイルで他に使っていなければ。使っていれば並べて import し報告）。
7. scripts/check-ui-governance.js
   - `countLoadingText(content)` を countRadio の直後に追加。正規表現 `/\bt\(\s*["'`]([A-Za-z0-9_.]*[Ll]oading[A-Za-z0-9_.]*)["'`]\s*\)/g`。一致ごとに、一致位置より前の直近の `{` を探し、その直前（空白を除く）の文字が `=` なら数えない（prop の値）。`hasUiAllowBefore(lines, lineIdx)` が真なら数えない。
   - countAll に `loadingText: countLoadingText(content)` を加える。
   - 赤のときの表示文言は既存の radio の文言の並びに合わせ「読み込み中の文字だけの表示 → `<LoadingBlock>` を使うこと」。
   - 冒頭コメントの検査項目一覧があれば1行足す。
8. scripts/tests/test-ui-governance.js に試験を追加（既存の assert 形式）:
   - `<p>{t("common.loading")}</p>` → 1
   - `{loading ? <div className="loading">{t("schedule.loading")}</div> : null}` → 1
   - `<LoadingBlock label={t("schedule.loading")} />` → 0
   - `<Button loadingText={t("common.loading")}>` → 0
   - `// ui-allow: 理由 (#4624)` の次行の `<p>{t("common.loading")}</p>` → 0
   - `{t("common.save")}` → 0
   - countAll の戻りに loadingText がある
9. docs/CC_UI_GOVERNANCE.md の禁止事項の表に、radio の行の直後へ1行:
   `| 読み込み中の文字だけの表示（例 `<p>{t("common.loading")}</p>`）| `<LoadingBlock>`（components/loading）を使うこと。見た目は金型1か所で変わる |`
10. docs/handoff/loading-indicator/ の recon.md・design.md・card-2.md は Opus が書いた。そのまま commit に含める。.claude-pipeline/active-work.d/ に本ブランチの1件を既存の書式で追加する。

## 触らない範囲
- 他の 141 件の読み込み中表示、ボタン内の三項、保存・送信系、Spinner.tsx・Skeleton・SplashScreen・DataTable、ja.json/en.json、components.css の `.loading`。

## 想定分岐（合わなければ止めて NEEDS_DECISION）
- 既存の pages/ で countLoadingText の BASE と HEAD の差が NeedsReviewTabsPanel 以外で出る → 止めて報告（本便で増える所は無いはず）。
- NeedsReviewTabsPanel の既存試験が class 名の完全一致などで落ちる → 試験側を直さず止めて報告。
- stories の書き方が Storybook のビルドで型エラー → 既存の stories に合わせて直し、報告。

## 検証（生出力は /tmp/CC報告ファイル/loading-stage2-bin1/ へ）
| 基準 | 検証方法 |
|---|---|
| 金型の試験 | `npx vitest run src/components/loading` 全緑 |
| 要確認画面 | `npx vitest run src/pages/super-admin/components/NeedsReviewTabsPanel` 全緑 |
| 検査の試験 | `node scripts/tests/test-ui-governance.js` 全緑 |
| 検査本体 | `BASE=origin/main node scripts/check-ui-governance.js`（既存の起動方法に合わせる）緑 |
| 規約 | eslint 0・tsc 新規エラー 0・i18n ja/en 差 0・`grep -nE "#[0-9a-fA-F]{3,6}\|[0-9]+px" LoadingBlock.css` 0 件 |

## 戻し方
この PR の revert。

## 追補1（2026-10-22 Opus。審査の差し戻しへの対応）
- 事実: 閲覧ページは Button.tsx → `./loading` の一括 export を通じて LoadingBlock に届く。閲覧ページの辞書 frontend/src/locales/viewer/ja.json・en.json に `common.loading` が無く、`node scripts/check-i18n-missing-keys.js` が exit 1（/tmp/CC報告ファイル/loading-stage2-bin1/reviewer/i18n-missing-keys.txt）。設計で入れ忘れた。
- 決定: viewer の ja.json・en.json の `common` に `"loading"` を足す。値は本体の辞書と同じ（ja `読み込み中...`／en `Loading...`）。閲覧ページも将来 LoadingBlock を使うため、Button の import を変える案（金型の一括 export を迂回する）は採らない。
- 変更: frontend/src/locales/viewer/ja.json・en.json の `common` に1行ずつ（`close` の直後）。
- 検証: `node scripts/check-i18n-missing-keys.js` exit 0 ／ 既存の i18n 検査（check:all にあるもの）緑。
