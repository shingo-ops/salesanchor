# Design: Chromatic 関連の完全撤去（設定・依存・スクリプト・ワークフロー）

- **ステータス**: Draft（①KGI起案 / ②recon確定済み / ③設計＝本書）
- **日付**: 2026-06-24
- **正本**: `docs/STANDARD-WORKFLOW.md`（矛盾時は正本優先）
- **参照 recon**: 本タスクのCC recon（file:line実引用つき）。**確定後 `docs/handoff/chromatic-full-removal/recon.md` としてコミット＋CI緑にし相互参照を確立**
- **先行の注意**: PR #2519「remove chromatic ci」は **handoff docs のみで MERGED・実装ゼロ**（chromatic.yml削除・依存除去・main.ts修正すべて未着手）。`docs/handoff/remove-chromatic-ci/design.md` は実装が伴わなかったため本書で作り直す。「在るだけ＝完了でない」の実例として記録。

> local-only注意: 本doc・recon・実装は「コミット＋CI緑」で初めて成果物。

---

## 0. 一行サマリ

Chromatic（ビジュアルリグレッションテスト）を、リポジトリ全体から完全撤去する。対象はnpm依存2件＋script / Storybookプラグイン / コメント。`UI Tests (Chromatic App)` はプラン上限で永久pending・required外で、運用上の番人として機能していない（ADR-073でも「現フェーズは手動確認で代替」と肯定済み）。docsの履歴言及は過去記録として残す。

---

## ①KGI（PO承認待ち）

**KGI（観測可能な事象）:**
```
develop で「chromatic」を全文検索したとき、実行コード・依存・設定・ワークフローの
該当がゼロになる（docs/handoff・ADRの履歴言及は除く）。
Chromatic除去後も frontend ビルド（npm run build）と storybook build が成功する。
```

**KPI（数値）:**

| KPI | 測定 | 目標 |
|---|---|---|
| 実行コード/依存/設定/workflow中のchromatic該当数 | `git grep -i chromatic -- ':!docs/'` | 0件 |
| Chromatic除去後のfrontendビルド成否 | `npm run build` | 成功 |
| Storybookビルド成否（プラグイン除去後） | storybook build | 成功 |
| package-lock.json のchromaticエントリ | grep | 0件 |

**○×最終確認:** 撤去PRマージ後、`git grep -i chromatic -- ':!docs/'` が0件 ＋ frontendビルド成功。

---

## ②recon サマリ（file:line / 要 recon.md 確定）

### 撤去対象（実体・develop に残存・全て未着手）

| 対象 | file:line | 内容 |
|---|---|---|
| ワークフロー | `.github/workflows/chromatic.yml` | Chromatic実行CI（develop に残存。#2519では削除されていない） |
| npm script | `frontend/package.json:47` | chromatic 実行script |
| npm依存 | `frontend/package.json:86` | `@chromatic-com/storybook` |
| npm依存 | `frontend/package.json:102` | `chromatic` |
| lock | `frontend/package-lock.json` | chromatic言及18箇所 |
| Storybook | `frontend/.storybook/main.ts:14` | `@chromatic-com/storybook` プラグイン登録 |
| コメント | `frontend/.storybook/main.ts:21` | Chromatic言及 |
| コメント | `frontend/src/lib/__storybook-mocks__/firebase-app.ts:1` | Chromatic言及 |
| コメント | `frontend/src/lib/__storybook-mocks__/firebase-auth.ts:1` | Chromatic言及 |

### 残すもの（過去記録・撤去しない）

- `docs/adr/ADR-073-design-system-kgi-rubric.md:77`（手動確認で代替＝Chromatic不使用を肯定。残すべき）
- `docs/handoff/**`・`docs/ai-agents/evidence-registry.md:53` 等の履歴言及（改竄しない）

### 確認済みの事実

- ruleset に Chromatic は含まれていない（#2538のPUTで確認・元から対象外）。required除去は不要。
- `CHROMATIC_PROJECT_TOKEN` は package.json:47 のscript内参照。script削除で参照が消える。GitHub secrets値は別途あなたが削除可（repo変更では触れない）。

---

## ③設計（技術How・Generatorは判断ゼロ）

### 変更1: ワークフロー削除 — 実施不要
`.github/workflows/chromatic.yml` は develop に存在しないことを確認済み
（`git ls-files` / `git show origin/develop`、recon.md「ワークフロー実在確認」参照）。
過去に削除済みのため、本撤去では対象外。

### 変更2: `frontend/package.json`
- `:47` の chromatic script 行を削除
- `:86` の `@chromatic-com/storybook` 行を削除
- `:102` の `chromatic` 行を削除

### 変更3: `frontend/package-lock.json`
- `npm install` でlockを正規再生成（手編集禁止）。chromatic 2パッケージのエントリ除去。

### 変更4: `frontend/.storybook/main.ts`
- `:14` の `@chromatic-com/storybook` プラグイン登録を削除
- `:21` のコメントから Chromatic 言及を除去（モックは残す・文言のみ）

### 変更5: モックコメント（任意・実害なし）
- `firebase-app.ts:1` / `firebase-auth.ts:1` のコメントから Chromatic 語を除去（モック実体は残す）

### 触らない範囲
- `docs/**` の履歴言及、ADR-073:77。
- Storybook本体・モックの実体（Chromaticプラグインだけ抜く）。

### KPI（=KGI検証）
- `git grep -i chromatic -- ':!docs/'` が 0件
- `npm run build` 成功 / storybook build 成功
- package-lock.json に chromatic 0件

### 弊害対策
- **Storybookを壊さない**: Chromaticは「Storybookのスナップショットをクラウド比較」するツール。Storybook本体・モックは残し、Chromaticプラグインと依存だけ抜く。撤去後 storybook build で起動を確認。
- **lockの整合**: package-lock.json は手編集せず `npm install` で再生成（18箇所手削除は壊す）。
- **ビルド回帰**: 撤去後 `npm run build` 成功を確認。
- **secrets**: `CHROMATIC_PROJECT_TOKEN` のsecrets値はrepo変更で消えない。あなたが設定画面で削除（任意）。

### 計画
- 1PRで変更1〜5（撤去は不可分・中途半端だと半分残る）。ビルド確認を受け入れ基準に。

### 指差呼称・削除宣言（今日作ったガード対応）
- PR番号≥2600なら③触るファイル宣言・②削除宣言が必須。
  - 触るファイル: chromatic.yml / package.json / package-lock.json / main.ts / firebase-app.ts / firebase-auth.ts
  - 削除するファイル: chromatic.yml（git rm）。package.json等も行削除でnumstat削除>0になるため deleteFiles に含める
- PR番号<2600なら猶予でスキップ（宣言は書く方が望ましい）。

### 継続・再発防止（＋外部・過去事例）
- **直接の教訓**: PR #2519 が「設計書だけMERGED・実装ゼロ」で「削除済み」と誤認されていた＝正本「在るだけ≠完了」の実例。本撤去は `git grep 0件＋ビルド成功`の実証で完了を定義し、同じ誤認を防ぐ。
- **外部事例**: 不要ツール・死んだ依存の残置は Knight Capital「死んだコードの残置」と同型リスク。完全撤去で技術的負債を断つ。

---

## 関所・承認（process-artifacts gate）
- 変更は `.github/workflows/` `frontend/`＝user-impact/real-code中心。`scripts/`は触らない。`.github/workflows/chromatic.yml`削除がdangerous判定に当たるかは実装時に確認（deploy.yml以外のworkflowはreal-code扱い＝recon既出）。
- recon を `recon.md` としてコミット＋CI緑にし本design と相互参照。

## 受け入れ基準

| 基準 | 検証方法 |
|------|------|
| `git grep -i chromatic -- ':!docs/'` が0件 | grep |
| frontend `npm run build` 成功 | CI/ローカル |
| storybook build 成功 | ビルド |
| package-lock.json に chromatic 0件 | grep |
| docs/ADRの履歴言及は保持 | 目視 |
| CI全緑 | CI |
