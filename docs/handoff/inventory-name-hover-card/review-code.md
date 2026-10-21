# コード審査: inventory-name-hover-card

- 審査者: Claude Opus（同じ AI による自己審査で、独立した第二者レビューではない）
- 日時: 2026-10-20
- 対象: 作業ツリーの差分（17ファイル）と GAS stage の差分（/tmp/CC報告ファイル/inventory-name-card/impl/gas.diff）
- 判定: **REVISE → 指摘3点の修正後 APPROVE**

## 設計 §3 との照合（○＝一致）
- §3-1 トークン: ○ 色ではない2つ（`--ease-pop`・`--comp-hover-card-blur`）だけを tokens.css に足した。ADR-067 の表にも追記した。色は既存トークン（--bg-surface・--border・--text-primary・--text-secondary・--shadow-xl）だけを使い、直値はない。
- §3-2 API と動き:
  - ○ props は title・subtitle・onlyWhenClipped（既定 true）・delay（既定 150）・className。
  - ○ `[data-hover-card-clip]` の scrollWidth > clientWidth で判定する。
  - ○ 300ms の間は待たずに出して滑らせる（glide）。
  - ○ unmount で、自分が基準なら閉じる。
  - ○ クリックの処理はない。
  - ○ position:fixed で、scrollX・scrollY を足していない。
  - ○ スクロールと画面幅の変更で閉じる。
  - ○ 上に入らないときは下に出す。
- §3-3 列: ○ 両方の列で `title` 属性を外し、`data-hover-card-clip` を付けた。HoverCard で包んだ。
- §3-4 Host: ○ InventoryPage.tsx と InventoryView.tsx に1つずつ置いた。
- §3-7 記録: ○ ADR-1014 に改訂 2026-10-20（2）を追記し、前の節の反映行を「テスト版28」に直した。

## 指摘
1. **GAS（重大）**: カードの div を `</script>` の後に置いていた。script の即時実行関数は、読み込みの途中で `getElementById('hoverCard')` を読むため、まだ div が無く null になる。その結果、カードが一切動かない。
   - 原因は設計 §3-6 の「body の最後に置く」という指示の誤りで、設計の書き漏れによる。
   - 設計を訂正し、div を `<script>` より前へ移させた。
2. **試験（軽微）**: unmount で閉じる動き（即時反映で行が描き直されたときに、カードが残らないための処理）を試す試験がなかった。設計 §3-5 に (5) として追加し、実装させた。

3. **unmount で閉じない不具合（指摘2の試験で発見）**: unmount 用 effect の後片付けで `ref.current` を読んで比べていた。React は後片付けの前に ref を null にするので、比べても一致せず、カードが残っていた。
   - effect 本体で要素を取っておき、後片付けではその要素と比べる形に直させた。
   - 試験 (5) で、カードが閉じることを確かめる。

## 受け入れた逸脱
- inventoryColumns.test.tsx の「#product_id の title」試験を「title 属性なし」に書き換えた。title 属性をやめるのが本便の目的なので、受け入れる。
- 閉じた後も Host を DOM に残し、aria-hidden を付けている。フェードアウトと、次に出るときの滑りに必要なので受け入れる。
- docs/CC_UI_GOVERNANCE.md に金型の一覧が無いため、そこへの追記はしない。
- 初めて開くときは、次の順で動く。まず位置0の透明な状態で一度描く。次に useLayoutEffect で正しい位置を計算する。最後に rAF で表示する。描画の前に位置が決まるので、ちらつかない（コードから読み取った判断で、実物の目視は K6 で行う）。

## 検証（実行した事実）
- vitest: 修正前の対象3ファイルで 44 件 pass（/tmp/CC報告ファイル/inventory-name-card/impl/vitest.txt）。修正後（試験5つ目を追加し unmount の不具合を直した後）は3ファイル 45 件 pass（vitest3.txt）。eslint エラー0（lint3.txt）。
- tsc: 変更したファイルのエラーは 0 件。エラー4件は、変更していないファイルに元からあるもの（tsc.txt）。
- check:all・lint: 緑（check-all.txt・lint.txt）。

## 追補: 閲覧ページの JS 上限（design §3-8）
- CI の「Viewer bundle check」が失敗した（301.4KB、上限300KB）。§3-8 を設計し、担当に実装させた。
- 差分（/tmp/CC報告ファイル/inventory-name-card/impl2/diff.txt）を確認した:
  - ○ icons-base.tsx に、型・hi()・4アイコン・TABLE_ICONS を中身を変えずに移した。
  - ○ icons.tsx は import して再 export する。二重定義はない。使わなくなった heroicons の import は消した。
  - ○ DataTable・Drawer・Modal・Sheet の import 先だけを変えた。
  - ○ eslint の no-restricted-imports（eslint.config.js:118-139）は lucide-react だけが対象で、反しない。
- 検証（担当の実行結果）:
  - viewer は 248.0KB で合格（bundle.txt）。
  - tsc は変更したファイルで 0 件。
  - eslint は警告 0。
  - check:all は exit 0。
  - vitest: 初回は Mac の高負荷による時間切れで 37 件が失敗した。失敗した 10 ファイルを再実行すると、242/242 件が合格した（vitest-rerun.txt）。全体の判定は CI で行う。
- 判定: APPROVE
