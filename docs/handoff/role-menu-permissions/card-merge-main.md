# 実装カード（追加）: 本線の取り込みでぶつかった 1 ファイルを両方残す形で直す

| 項目 | 内容 |
|------|------|
| 枝 | release/role-menu-permissions（この枝の先頭に足す。新しい枝は作らない） |
| 起点の commit | このカードを足した commit（枝の先頭） |
| 理由 | 本線に予定表の作業（PR #5261、本線の先頭 dc1fb7b5c）が入り、`frontend/src/constants/icons.tsx` の同じ場所に両方が行を足したため、GitHub で合流できなくなった。`git merge-tree` で確かめると、ぶつかるのはこの 1 ファイルだけ。`frontend/src/locales/en.json`・`frontend/src/locales/ja.json` は自動で合わさる |
| 区分 | A の続き（取り込みのみ。新しい機能は足さない） |

## 1. やること

（１）`git merge origin/main` を流す（rebase はしない。force push もしない）。
（２）`frontend/src/constants/icons.tsx` のぶつかりを、両方の行を残す形で直す。
- `@heroicons/react/24/outline` の import の並び: 本線の 3 行（`ClockIcon as ClockOutlineIcon`・`MapPinIcon as MapPinOutlineIcon`・`Bars3BottomLeftIcon as Bars3BottomLeftOutlineIcon`）と、この枝の 1 行（`SlashIcon as SlashOutlineIcon`）を全部残す。
- 他の箇所（`const ClockOutline` 等・`SCHEDULE_POPOVER_ICONS` の 3 行・`const SlashOutline`・`export { SlashOutline };`）も、両方とも残っていることを確かめる。どちらも消さない。
（３）ぶつかりの印（`<<<<<<<`・`=======`・`>>>>>>>`）が全ファイルに 0 件であることを確かめる。
（４）ja.json と en.json の鍵の数が同じで、JSON として読めることを確かめる。

触らない: 上の 1 ファイルのぶつかり以外の箇所。製品の振る舞い・試験・locale の中身を書き換えない。

## 2. 確かめ（生出力をファイルに残し、終了コードを報告する）

- `git grep -n '^<<<<<<<\|^>>>>>>>' -- frontend` が 0 件。
- `npx tsc --noEmit` exit 0。
- `npx eslint --max-warnings=0 src/constants/icons.tsx` exit 0。
- `npm run test:unit` で失敗 0 件。
- `node -e` で ja.json と en.json を読み、鍵の数を数えて一致すること。

## 3. 止まる条件

- `icons.tsx` 以外のファイルでぶつかりが出た。
- 両方を残すと型や試験が通らない。
- 本線の先頭が dc1fb7b5c から進んでいて、別のぶつかりが出た。

## 4. 記録

- merge commit は 1 つ。題「Merge origin/main into release/role-menu-permissions (keep both icon additions)」。最後の行に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- `git push origin release/role-menu-permissions`（force は使わない）。
- 最後に DONE / BLOCKED: <理由> / NEEDS_DECISION: <内容> のどれか 1 行。
