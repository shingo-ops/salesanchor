# 設計: 在庫表を最初からポケモンで開き、表示を早くする

- 状態: 設計案（Opus）。PO 依頼 2026-10-21（recon.md 冒頭の原文）。
- 現在地: docs/handoff/inventory-default-pokemon-tab/recon.md
- 対象 ADR: ADR-1019 項8（閲覧ページはアプリと同じ金型・同じ見え方）、ADR-1030（タブは中分類で絞る）、ADR-027（UI 文字列は t() 経由）、ADR-144（金型を使う）。新しい部品・文言・色は足さない。

## 1. 目的（PO の言葉）と成功条件
- 「ポケモンをデフォルトにして裏で全件読み取る」
- 「読み込みはタブ順にその他に統合されていないデータを優先的に読み込んでページが1秒でも早く表示されるようにしたい」

| 基準 | 検証方法 |
|---|---|
| K1 閲覧ページを開くと、PC はタブ「ポケモン」が選択中、スマホはセレクトが「ポケモン」。表はポケモンの行だけ | vitest（新規テスト）＋本番の配信 JS に変更が入っていること（deploy 後に取得して確認） |
| K2 閲覧ページで、ポケモンの行が1件も無いときは今までどおり「すべて」で開く | vitest |
| K3 シート版を開くと、タブ「ポケモン」が選択中（スマホのセレクトも「ポケモン」）。表はポケモンの行だけ | Playwright（匿名）でテスト版・本番版を開き、選択中のタブと表の行のシリーズを確認 |
| K4 シート版で、表示直後に検索欄へ打っても結果が正しい（検索用文字列を後回しにしても漏れない） | Playwright: テスト版で、表が出た直後に検索語を入れ、表示行がすべて検索語を含むこと・「すべて」タブで同じ語の件数が変更前（本番 版21）と同じこと |
| K5 シート版の更新ボタンで、選んでいたタブのまま読み直す | Playwright: ワンピースを選び更新 → ワンピースのまま |
| K6 シート版の表が出るまでの時間が、変更前より短い | Playwright（匿名 Chrome）で 変更前（本番 版21）と変更後（テスト版）を交互に5回ずつ開き、表のデータ行が出た時刻の平均を比べる。変更後の平均 < 変更前の平均 なら ○。数値はそのまま報告する |
| K7 アプリ在庫表は変えない（今もポケモンで開き、開いたタブの50件だけ読む） | 差分にアプリ在庫表のファイルが無いこと |

- 期待の大きさ: 画面側の処理 1.04秒のうち、描く行が約3分の2になる分と検索用文字列の作成を後回しにする分が減る。外枠の読み込み（2.67秒）とサーバーの応答待ち（1.85秒）は Google 側で、この変更では減らない。「1秒」に届くかは【未測定】で、K6 の実測で報告する。

## 2. 変更前 → 変更後
| | 変更前 | 変更後 |
|---|---|---|
| アプリ在庫表 | ポケモンで開く。開いたタブの50件だけ読む | 変えない |
| 閲覧ページ（PC・スマホ） | 「すべて」で開く | 「ポケモン」で開く（ポケモンの行が無ければ「すべて」） |
| シート版（PC・スマホ） | 「すべて」で開く。受信直後に全行の検索用文字列を作ってから表を描く | 「ポケモン」で開く（行が無ければ「すべて」）。表を描いた後に検索用文字列を作る。描く前に検索語が入っていればその場で作る |

## 3. 選ばなかった案と理由
- **案X: サーバー呼び出しを「主な3つ」「その他」に分ける（依頼の言葉どおりの形）。** シート版は通信量が 33KB・20ms で（recon C）、サーバーは呼ばれるたびにシートを全行読むため、分けても最初の応答待ち 1.85秒は減らず、呼び出しが1回増える。閲覧ページは応答時間が【未測定】で、分ける効果を測る手段（ログイン済みの計測）が今は無い。測れないものは変えない（変更は測ってから）。依頼の狙い「ポケモンが先に見える」は、ポケモンで開いて描く行を減らすことで満たす。
- **案Y: シート版でサーバー側の作り置き（CacheService）を使う。** 応答待ちを減らせる可能性はあるが、在庫の更新がどれだけ遅れて見えるかという事業判断を伴い、効果も【未測定】。今回は入れない（残件として記録）。

## 4. 変更内容
### 4-1. 閲覧ページ `frontend/src/pages/viewer/InventoryView.tsx`
- `:55` を次に変える（既定は MAIN_SERIES の先頭。新しい定数は作らない）:
  ```ts
  // 既定はポケモン（MAIN_SERIES の先頭）。その行が無いときは「すべて」（docs/handoff/inventory-default-pokemon-tab/design.md）
  const [tab, setTab] = useState(() =>
    data.rows.some((r) => r.series === MAIN_SERIES[0]) ? MAIN_SERIES[0] : TAB_ALL,
  );
  ```
- MAIN_SERIES が既に import されていることを確認する（`:288-` の Tabs で使用中）。
- 「表示を元に戻す」系のリセット（`InventoryView.tsx` 内に tab を TAB_ALL に戻す処理があれば）は、戻す先を同じ既定にそろえる。無ければ触らない。実装担当は grep で `setTab(` と `TAB_ALL` の全箇所を列挙して報告する。
- `ViewerApp.tsx` の読み込み、`api.ts`、バックエンドは変えない。
- テスト `frontend/src/pages/viewer/InventoryView.test.tsx`:
  - 追加 K1: ポケモンとワンピースの行がある data で描画 → PC のタブ「ポケモン」が aria-selected=true、表の行はポケモンだけ。スマホ（既存テストの isMobile の切り替え方に合わせる）で `viewer-tab-select` の value が「ポケモン」。
  - 追加 K2: ポケモンの行が無い data → 「すべて」が選択中・全行表示。
  - 既存テストで全件表示を前提にして落ちるものは、data にポケモンの行しかない場合は直さずに通るはず。落ちたものは「すべて」タブを押してから確かめる形に直し、直した箇所を全部報告する（期待値そのものは変えない）。

### 4-2. シート版 index.html（テスト・本番とも同じファイル）
作業場所: `/Users/tanizawashingo/CC報告ファイル-keep/inventory-default-pokemon/gas/stage/`（テスト）と `prod_stage/`（本番）。どちらも `inventory-tabs-attach-table/gas/verify_test_after/`・`verify_prod_after/` を丸ごと写して作る（.clasp.json を含む）。編集するのは index.html だけ。編集後に stage と prod_stage の index.html は同一にする。
1. 既定タブ: `:1000` の `var activeSeries = '';` を消し、`:1003` の MAIN_SERIES の宣言の直後に置く:
   ```js
   // 既定はポケモン（MAIN_SERIES の先頭）。その行が無ければ buildSeriesTabs が「すべて」('')に戻す
   var activeSeries = MAIN_SERIES[0];
   ```
   （コメントの「'' は「すべて」」の説明は残す）。buildSeriesTabs の既存の戻し処理はそのまま使う。
2. 検索用文字列の後回し: onDataLoaded の `SEARCH_TEXTS = ALL_ROWS.map(...)`（`:1237-1239`）を関数にする:
   ```js
   // 検索用の文字列（ALL_ROWS と同じ添字）。表を先に出すため、作るのは表示の後か、検索語が入ったとき
   function ensureSearchTexts() {
     if (SEARCH_TEXTS) return;
     SEARCH_TEXTS = ALL_ROWS.map(function(row) {
       return normalizeForSearch([row[COL.japaneseTitle], row[COL.englishTitle], row[COL.mark], row[COL.searchKeywords]].join('\n'));
     });
   }
   ```
   - onDataLoaded: ALL_ROWS を入れた直後に `SEARCH_TEXTS = null;`。`render();` の後に `setTimeout(ensureSearchTexts, 0);`。
   - render: `queryTerms` を作った直後に `if (queryTerms.length) ensureSearchTexts();`。
   - `:996` の初期値 `var SEARCH_TEXTS = [];` は `null` に変え、コメントを「null は未作成」と直す。
   - SEARCH_TEXTS を使う箇所が他に無いことを grep で確かめる（recon 時点では `:996, :1237, :1449` の3か所）。
3. それ以外（Code.js、appsscript.json、タブの見た目、スマホのセレクトの並び）は変えない。

## 5. 影響範囲
- 閲覧ページ: InventoryView の初期 state だけ。URL・API・作り置き・権限に変更なし。
- シート版: 画面の初期タブと検索用文字列を作る時機だけ。サーバー（Code.js）・シート・配信の列は変えない。
- アプリ在庫表・バックエンド・DB・migration・deploy.yml: 変更なし。
- 「その他」の判定・主な3つの定義は既存の1か所ずつ（閲覧 `viewerFilter.ts:227`、GAS `index.html:1003`）を使い、増やさない。

## 6. リスクと対処
| リスク | 対処 |
|---|---|
| 「すべて」で開くと思っている利用者が戸惑う | PO 依頼どおり。タブは1回押せば「すべて」に戻せる |
| 検索用文字列ができる前に検索されて結果が漏れる | render で検索語があれば先に作る（K4 で確認） |
| 更新ボタンで読み直したとき古い検索用文字列が残る | onDataLoaded で毎回 null に戻す |
| GAS の反映で別の変更を上書きする | PO 実行の台本で、push 前に pull して基準（版31/版21）と同一か・公開中の版が 31/21 かを確かめ、違えば止める（前回の deploy_both.sh と同じ形） |
| clasp の認証切れ（2026-10-21 Opus の読み取り pull で invalid_rapt） | PO が台本を実行する前に `clasp login` が必要。台本の冒頭で案内する |

## 7. 戻し方
- 閲覧ページ: PR を Revert。
- シート版: テスト `clasp redeploy <TEST_ID> -V 31`、本番 `clasp redeploy <PROD_ID> -V 21`（台本に書く）。

## 8. 実装と反映の順番
1. Sonnet: 4-1 を実装、vitest（InventoryView 全件）・build・lint・check:all を通す。4-2 の stage/prod_stage を作り編集、`node --check` 相当の構文確認（index.html の script 部分を取り出して確認）と、編集前後の diff を保存。clasp は実行しない。
2. Opus: コード審査（APPROVE を review-code.md に記録）。
3. PR（閲覧ページ）→ CI → マージ → deploy → K1 の配信 JS 確認。
4. PO が `!` で台本1 `/Users/tanizawashingo/CC報告ファイル-keep/inventory-default-pokemon/po_run_test.sh` を実行（`clasp login` の案内 → permit-danger → テスト版だけ反映）。
5. Opus: テスト版で K3〜K5、テスト版（新）と本番（旧 版21）を交互に測って K6。どれかが × なら本番には出さず、テスト版を版31に戻す台本を用意して止める。
6. 全部 ○ なら PO が `!` で台本2 `po_run_prod.sh`（本番だけ反映）を実行。Opus が本番で K3・K5 を確認。
- K6 を反映前に測る理由: 本番を反映すると「変更前」が無くなるため。

## 9. 維持の仕組み
- 既定タブは MAIN_SERIES[0] に従うので、主な3つの並びを変えたら既定も一緒に変わる（閲覧 `viewerFilter.ts:227`、GAS `index.html:1003` の既存の相互参照コメントのとおり両方直す）。
- 閲覧ページの既定は vitest K1/K2 が守る。シート版はテストの仕組みが無いため、この設計と GAS の版番号の記録（ADR-1014 の版の記録欄）で追う。

## 10. 外部事例
- 該当事例は使わない。理由: 判断の根拠は本番での実測（recon C の内訳）で足り、外部の数値を当てはめると「通信量が小さい GAS」という条件が合わない。

## 11. 残件（今回やらない）
- 閲覧ページの表示時間の測定（ログイン済みで測る手段が要る）と、その結果しだいでの分割読み込み。
- シート版のサーバー側作り置き（案Y）。
