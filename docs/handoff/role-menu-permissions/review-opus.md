# 役割の画面をメニューごとの3択にする — Opus 審査記録

| 項目 | 内容 |
|------|------|
| 区分 | A（新しい部品 `SegmentedToggle` と新しい正本 `menuPermissions.ts` を含むため） |
| 設計審査 | design.md §10（自己審査 APPROVE）・§11（クラウド Opus 設計審査 APPROVE、高 0・中 4・低 3 を反映済み） |
| 実装 | クラウド Sonnet、commit `9080e14444efd81dc73d4b80c1bf8bcfd7c5b9db`（2026-11-07 11:18 UTC push） |
| 実装の確かめ | Opus が手元で差分全文を読んだ（同じ AI による確かめで、独立した審査ではない。マージ前に別の reviewer を通す） |

## 1. 実装役の報告（クラウドで実行・Opus は記録を読んだだけ）

- `tsc --noEmit` exit 0（生成物 `src/api/generated/schema.d.ts` を作ってから。生成物は git 管理外）。
- 単体試験 7 ファイル・74 件すべて通過。
- `npm run check:all` exit 0。変更したファイルに関する警告 0 件。
- 変更ファイルだけ `eslint --max-warnings=0` exit 0。
- `check-ui-governance.js`（BASE=`177ae7fe3` HEAD=`9080e1444`）exit 0「新規ハードコードなし」。
- `build-storybook` exit 0。

## 2. Opus が差分を読んで確かめたこと

- 変更ファイルは card-impl.md §2 の表の 16 件だけ（`git diff --stat 177ae7fe3 HEAD`）。
- サーバー・DB・`migrations/`・`deploy.yml`・`scripts/` の変更なし。
- 保存は今までどおり許可 id の一覧を丸ごと送る。行の外の許可（画面に出ない `menu.*` を含む）は `applyState` が変えない。
- メニューを出す条件: `canSeeMenu` の試験で、置き換え前の式と全メニュー・全組み合わせ（無し・1つずつ・全部）が一致。
- 色・寸法は `var()` だけ。文字は `t()` で、`ja.json` と `en.json` に同じ 17 鍵を足した。

## 3. カードとの差（実装役が報告済み・Opus 判断で受け入れ）

- `MobileShell.tsx` は `usePermissions()` の `hasAny` を使わず、`hasPermission` から同じ意味の `hasAny` を作った。既存の試験が `hasPermission` だけを差し替えているためで、意味（どれか1つ持てば真）は同じ。受け入れる。

## 4. 残すもの（今回はしない・design.md §9 の次の課題）

- `pages-layout.css` の `.permission-group*` と、使わなくなった言葉の鍵（`roles.categoryPagePerm` など）の片付け。
- 管理センターの入口を出す条件を正本から作ること。

## 5. 判定

- APPROVE（PR 作成へ進む）。マージ前に新しく立てた reviewer（Opus）の判定を取る。
