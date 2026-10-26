# review: 宿題 C8（出口封じの1か所化＋行が消えても外へ出さない）の独立審査と対応

> この文書は何か（1行）: 設計担当（Opus）とは別の Opus に「**反証を探す立場**」で差分・設計書・recon を見せた
> 独立審査の結果と、設計担当がそれにどう対応したかの記録。ADR-1003 の委譲 GO の条件（Reviewer 判定）を満たすための正本。

**日付**: 2026-10-26 ／ **土台**: `release/viewer-focus-trap`（`origin/main` = `840eea949`）
**審査対象**: `frontend/src/hooks/useFocusTrap.ts`（新規）・同 `.test.tsx`（新規）・
`frontend/tests-e2e/visual-language/viewer-focus-trap.spec.ts`（新規）・`Drawer.tsx`／`Modal.tsx`／`Sheet.tsx` の差分・
`design.md`・`recon.md`

## 判定の経緯

| 回 | 判定 | 内容 |
|---|---|---|
| 1回目 | **REQUEST_CHANGES** | ブロック1件（B-1）・非ブロック5件・書類の行番号誤記8件 |
| 対応後 | **（下の「対応」のとおり B-1 を直し、非ブロックは ⑫ へ起票）** | 本体コードへの指摘は0件のまま |

審査は本体（`useFocusTrap.ts` と3金型の繋ぎ替え）について
「**設計どおりで、挙動の変わる範囲も主張どおり1点だけ**。壊れる呼び出し方の全数調査でも実害が出る画面は無い」と判定した。

## ブロック級（1件・直して反映済み）

### B-1 画面検査 B2 の assert が弱く、**直す前でも緑になり得た**

**指摘**: `panel.contains(document.activeElement)` だけでは不足する。本物のブラウザは
**消えた要素の位置を順次フォーカス移動の起点として覚える**ため、素の Tab でも
「消えた候補の**次の候補**」（＝同じパネルの中）へ入り得る。つまり直す前でも緑になり、
この便の主張（Tab で外へ逃げるのを止めた）を何も確かめないまま通る。便6（PR #4780）の
「空振りで緑」と同じ形。しかも C8 の起票自体が**読みによる指摘**で、
「直す前は本当に外へ出る」を本物のブラウザで測った記録はどこにも無い。

**対応（反映済み）**: 「中に居るか」ではなく**先頭／末尾そのもの**を assert する形へ変えた。
- **B2**（Tab）→ パネル内の先頭 `drawer-back` に入ったこと。先頭は消えた候補より **DOM 順で前**なので
  **前方向の素の Tab では到達できない**。
- **B2'**（Shift+Tab・新規追加）→ パネル内の末尾 `viewer-filter-apply`（footer の「決定する」）に入ったこと。
  **後方向の素の Shift+Tab では到達できない**。
- あわせて「パネル内の先頭が `drawer-back`・末尾が `viewer-filter-apply` であること」自体も assert するので、
  将来 DOM 順が変わったときに黙って緑にならず赤で気づける。
- 設計 ⑤ に理由を明記（`design.md` ⑤「B2 を『パネルの中に居る』で測ってはいけない」）。

**残る限界（正直に書く）**: この端末には Playwright のブラウザが入っていない
（`/root/.cache/ms-playwright/…/headless_shell` が無く、既存 spec も全件が同じエラーで即失敗する）ため、
**画面検査側の「直す前は赤」は手元では実測できない**。したがって
- 作りの上で「連れ戻したときだけ緑」になることを上記のとおり保証した（論理で担保）。
- 同じ論理の**単体テスト側の RED-first は実測済み**（下記）。
- 審査が併せて求めた「main（直す前）で spec を走らせた赤のログ」は、取るなら CI を1往復する必要がある。
  **PO 判断待ち**として残す（取らない場合も、赤になる理由は作りで保証されている）。

## 非ブロック（⑫ へ起票して次便送り）

| 審査の番号 | 内容 | 起票先 |
|---|---|---|
| N-1 | パネル2枚が同時に開いているとき、`document` の購読が登録順に呼ばれるため**背面のパネルが勝つ**（最前面ではない）。実在経路は `SupplierMasterPanel.tsx:298-392` のドロワー内 `:385` から `:395-441` の確認窓を開く形。直す前も同じ回は外へ出ていたため**新たに不可能になる操作は無い** | ⑫ **E6**（＋ 4-2 に限界として追記） |
| N-2 | `Drawer`/`Sheet` を**最初から `open=true` でマウントすると出口封じも初期フォーカスも付かない**（`portalTarget` の2段構えのため。既存の穴＝この便の退行ではない。現在の呼び出し元 37 ファイルはすべて安全な形） | ⑫ **E5** |
| N-3 | `C11` は `const FOCUSABLE_SELECTOR =` という**名前の完全一致**しか数えない（別名の複製は通る）／`C6` は `Modal` ではほぼ無条件に緑／テスト自身の自己除外は現状効果なし | ⑫ **E7** |
| N-4 | spec がトークン投入を写していた／幅の引数が固定値のまま可変 | **この便で直した**（`installViewerToken` を `export` して共有・引数を削除） |
| N-5 | `useFocusTrap.ts` の `active instanceof Node &&` は不要（`contains(null)` は false） | 残置（害が無く、型の読みやすさを優先） |

## 書類の誤りの訂正（8件・反映済み）

- `recon.md` §2 の「集め方」3件（`Drawer.tsx:221-228`→`221-229`、`Modal.tsx:167-174`→`167-175`、
  `Sheet.tsx:175-182`→`175-183`）＝`getFirstFocusable` の閉じ括弧まで含める。
- `design.md` 4-3 の3件（`:212-228`→`212-229`、`:158-174`→`158-175`、`:166-182`→`166-183`）。
- `recon.md` §4 `InventoryView.tsx:183-200`→**184-199**（依存配列の行は 199。183 は `prevDrawerOpenRef` の宣言）。
- `recon.md` §3 `InventoryView.tsx:94-99`→**94-101**（`providerOptions` 94-97／`conditionOptions` 98-101）。

いずれも**主張そのもの（事実関係）は正しい**ことを審査が確認している。事実誤認は0件。

## 審査が「調べたが問題なかった」と確認した主な点

- 挙動が変わるのは「現在地がどこでもないときの Tab」**1点だけ**。`inPanel` が true の分岐は旧 `Drawer.tsx:107-125` と論理が完全一致。
- `FOCUSABLE_SELECTOR`／`getFocusableElements`／`getFirstFocusable` は**値・順序・`[aria-hidden='true']` 除外まで3金型の旧実装と一字一句同じ**。
- 公開プロパティの増減なし＝呼び出し元（`Drawer` 35／`Modal` 43／`Sheet` 2）の書き換えは **0**。
- `Modal` はポータル先が `document.body` 直書き（`Modal.tsx:150`）＝2段構えが無いので `open={true}` 固定の5件は N-2 の穴に当たらない。
- ドロワーの中から `Popover` を開く経路は**現状どの画面にも無い**（閲覧ページのスマホ経路は `MultiSelect layout="row"/"inline"` で Popover を通らない）＝「別の要素に居るときは何もしない」枝が意図どおり効く。
- **`document` の keydown で Tab を見ている箇所はリポジトリ全体で `useFocusTrap.ts:55` の1本だけ**＝`preventDefault` の競合先が無い。
- 単体テストの前提 assert は本当に前提を固定している（C2/C3 はイベント後に候補を取り直すので消えた行を数え込まない）。
- spec の呼び順（`setViewportSize`→`addInitScript`→`clock.install`→`goto`）・`fastForward` の相手（`useViewerAutoRefresh.ts:17-23` の `setInterval`）・testid が本物の `<input type="checkbox">` に届くこと（`MultiSelect.tsx:103`→`CheckboxControl.tsx:38-45`）・`page.clock` が実在する版（1.59.1）であること。
- `page.clock` は**このリポジトリで初使用**。万一 viewer の起動経路がタイマーに依存していると「本当の失敗ではない赤」になり得るので、**CI 1往復目は件数の行まで自分で読む**。

## 設計担当が自分で測った一次情報（コマンドと出力の件数行）

```
$ npx vitest run src/hooks/useFocusTrap.test.tsx
 Test Files  1 passed (1) /  Tests  20 passed (20)

# RED-first: 連れ戻す枝を一時的に外して再実行（＝直す前の挙動）
 Test Files  1 failed (1) /  Tests  6 failed | 14 passed (20)
   赤の内訳 = C2・C3 × Drawer/Modal/Sheet（連れ戻しに関する検査だけが赤く、他は緑）
# 枝を戻して再実行 → Tests  20 passed (20)

$ npm run generate:api-types && npx tsc --noEmit        → TSC_EXIT=0（0件）
$ npm run check:all                                     → CHECKALL_EXIT=0（lint 0 error・警告59件は既存）
$ npx eslint --max-warnings=0 <この便で触った src の5ファイル>  → 合格（pre-commit と同じ厳しさ）
$ npx vite build --manifest && node scripts/check-viewer-bundle.js
 viewer JS: 2 ファイル, 合計 260.7 KB（上限 300 KB） → ✅ PASSED
   便6 時点の実測 266.7KB から **約6KB 減**（複製を消した分）
$ E2E_NO_WEBSERVER=1 npx playwright test --list --project=vl-{mobile-390,tablet-768,desktop-1280}
 viewer-focus-trap が各 project で 3 件ずつ収集（B1・B2・B2' × 3幅 = 9件）
$ npm run test:unit（全体）
 1742 passed / 3 failed → その3件だけを単独で回すと 11 passed（全部緑）。
 2回の全体実行で赤の顔ぶれが毎回違う＝この端末が遅いための時間切れで、本便とは無関係
```

**走らせていないもの**: 画面検査（この端末に Playwright のブラウザが無い＝環境制約。CI が唯一の一次情報）。

## 対象 ADR

- **ADR-1003**: 委譲 GO の条件として Reviewer の判定が必要 → 本書がその記録。
- **ADR-144 §4**: 金型新設には当たらない（`.tsx`＋`.css`＋`.stories.tsx` を伴う部品ではない）＝審査も妥当と判定。
