<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。 -->
# 実装カード — lp-footer-operator-ja

**PO依頼**: 2026-11-12 チャット「フッター内の会社情報を日本語にしてくれ」
**設計**: docs/handoff/lp-footer-operator-ja/design.md
**土台**: origin/release/lp-footer-operator-ja（設計コミットの次に積む）

## §0 着手前の実物点検（違えば止めて NEEDS_DECISION:）

`sed -n 38,46p lp/src/components/Footer.astro` の出力が次と完全に一致すること。

```
          Operator
        </h4>
        <ul class="space-y-2 text-sm">
          <li>HIGH LIFE JPN</li>
          <li>Representative: Shingo Tanizawa (谷澤 伸吾)</li>
          <li>8-312 Ryokuyoudai, Kuwabara, Okazaki, Aichi 444-2141, Japan</li>
          <li>〒444-2141 愛知県岡崎市桑原町字緑陽台8番地312</li>
          <li>Invoice Registration No. (適格請求書発行事業者登録番号): T3810449547408</li>
          <li>Phone: +81 90-6072-7767</li>
```

## §1 変更（`lp/src/components/Footer.astro` の 38〜46 行を次に置き換える。他は変えない）

```
          運営者
        </h4>
        <ul class="space-y-2 text-sm">
          <li>屋号：HIGH LIFE JPN</li>
          <li>代表者：谷澤 伸吾</li>
          <li>所在地：〒444-2141 愛知県岡崎市桑原町字緑陽台8番地312</li>
          <li>適格請求書発行事業者登録番号：T3810449547408</li>
          <li>電話番号：090-6072-7767</li>
```

コロンは全角「：」。インデントは元と同じ空白。

## §2 確かめ（生の出力を返す）

1. `cd lp && npm ci && npm run build`（終了コード 0。失敗したら BLOCKED:）
2. `grep -rc -e Ryokuyoudai -e 'Representative:' dist --include=*.html | grep -v ':0$'` が何も出さない
3. `grep -c -e '代表者：谷澤 伸吾' -e '所在地：〒444-2141' -e '適格請求書発行事業者登録番号：T3810449547408' -e '電話番号：090-6072-7767' dist/index.html` が 1 以上（4語それぞれ `grep -c` で確認）
4. `git diff --stat origin/main -- lp` が `lp/src/components/Footer.astro` の1ファイルだけ、6 insertions / 7 deletions

## §3 コミット

`fix(lp): フッターの運営者情報を日本語表記にする`（末尾に Co-Authored-By 行）。push は `git push -u origin release/lp-footer-operator-ja`。
