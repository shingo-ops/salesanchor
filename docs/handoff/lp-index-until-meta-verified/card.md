<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。 -->
# 実装カード — lp-index-until-meta-verified

**PO承認**: 2026-11-12 チャット「3. 検索に出すのは、審査が通るまでにする。審査が通ったら、検索に出ない形に戻します。」
**設計**: docs/handoff/lp-index-until-meta-verified/design.md
**土台**: origin/release/lp-index-until-meta-verified（設計コミット 8251fe1b7 の次に積む）

## §0 着手前の実物点検（違えば止めて NEEDS_DECISION:）

| 確かめること | 期待 |
|---|---|
| `sed -n 19p lp/src/layouts/BaseLayout.astro` | `  noindex = true,` |
| `sed -n 12p lp/src/layouts/LegalLayout.astro` | `const { title, description, subtitle, canonical, noindex = true } = Astro.props;` |
| `sed -n 11p lp/src/pages/404.astro` | `  description="お探しのページが見つかりませんでした。Sales Anchor のホームに戻るか、URL をご確認ください。"` |
| `sed -n 12p lp/src/pages/404.astro` | `>` |
| `sed -n 11p lp/src/pages/deletion-status.astro` | `  noindex={true}` |

## §1 変更（この3つだけ）

1. `lp/src/layouts/BaseLayout.astro:19` を `  noindex = false,` に置き換える。
2. `lp/src/layouts/LegalLayout.astro:12` の `noindex = true` を `noindex = false` に置き換える（行のほかの部分は変えない）。
3. `lp/src/pages/404.astro` の 11 行目（description 行）と 12 行目（`>`）の間に、`  noindex={true}` の1行を足す（先頭は空白2つ）。

## §2 確かめ（生の出力を返す）

1. `cd lp && npm ci && npm run build`（終了コード 0。失敗したら BLOCKED:）
2. `for f in $(find dist -name '*.html' | sort); do echo "$f $(grep -c 'name=\"robots\"' $f)"; done`
   - 期待: `dist/index.html` `dist/pricing/index.html` `dist/privacy/index.html` `dist/terms/index.html` `dist/data-deletion/index.html` が 0、`dist/404.html` と `dist/deletion-status/index.html` が 1。違えば BLOCKED:
3. `git diff --stat origin/release/lp-index-until-meta-verified` が上の3ファイルだけ（dist や node_modules が入っていないこと）。

## §3 コミット

3ファイルを名前で git add し、1コミット。文:
```
fix: Meta の審査が通るまで LP を検索に出す（noindex 既定値を false）

ADR-1044 追記（2026-11-12）。404 と deletion-status は noindex を明示で残す。

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

## §4 触らない範囲

上の3ファイル以外すべて。特に `lp/public/robots.txt`、`frontend/`、`.github/`、nginx。
