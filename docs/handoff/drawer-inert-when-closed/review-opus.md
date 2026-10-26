# review: 閉じているパネルを「無い物」として扱う（宿題 D5）の独立審査と対応

> この文書は何か（1行）: 設計担当（Opus）とは別の Opus に「**反証を探す立場**」で差分・設計書・recon を見せた
> 独立審査の結果と、設計担当がそれにどう対応したかの記録。ADR-1003 の委譲 GO の条件（Reviewer 判定）を満たすための正本。

**日付**: 2026-10-27 ／ **土台**: `release/drawer-inert-when-closed`（`origin/main` = `fbc8e3086`）

## 判定の経緯

| 回 | 判定 | 内容 |
|---|---|---|
| 1回目 | **REQUEST_CHANGES** | **ブロック1件（B-1・確実に壊れる退行）**・非ブロック7件・書類の誤り5件 |
| 対応 | B-1 を直し、守り手（C8）を新設。非ブロックは ⑫ F6〜F8 に起票。書類の誤りは訂正済み | 下の各節 |

## ブロック級（1件・直して反映済み）

### B-1 開いたときの「先頭へフォーカス」が無効化の札に弾かれ、キーボードで開いたパネルに入れなくなる

**指摘の中身**: React は同種の effect を**書いた順**に流す。初版は `useInertWhenClosed` を
「開いたら先頭へフォーカス」effect（`frontend/src/components/Drawer.tsx:81-87`・
`frontend/src/components/Sheet.tsx:62-68`）の**後ろ**に置いた通常の `useEffect` だったため、
閉→開の回に「先頭へフォーカス」→「無効化を解除」の順になり、**まだ inert な枝へ `focus()` して不発**に終わる
（HTML 標準では inert な枝はフォーカス可能領域ではなく `focus()` は何もしない）。
結果、カーソルは押したボタン（パネルの外）に取り残され、**キーボードだけで使う人は開いたパネルに入れない**。
`Drawer` 35画面・`Sheet` 2画面に効く退行だった。

**設計担当による再現（一次情報）**: 審査の指摘を鵜呑みにせず、**ブラウザの決まりを模した単体検査を新設して実測**した。
`useLayoutEffect` を `useEffect` に戻すと:

```
 FAIL  'Drawer' opens with focus inside the panel (D5-C5)
 FAIL  'Sheet'  opens with focus inside the panel (D5-C5)
 Tests  2 failed | 26 passed (28)
```

**対応（反映済み）**:
1. `useInertWhenClosed` を **`useLayoutEffect`** にした（通常の effect より先に走るので、
   **呼び出し側で何行目に書いても順序が保たれる**。呼び出し位置を動かす案より堅い）。先例 `frontend/src/components/CheckboxControl.tsx:35`。
2. **守り手 C8（D5-C5）を新設**。jsdom は `inert` を実装していないため、検査の中で**本物のブラウザの決まり2つ**
   （`inert` は属性に反映される／inert な枝では `focus()` は何もしない）を模し、順序が崩れたら赤になるようにした。
   これが無いと jsdom では永久に検出できない（審査の条件でもある）。
3. 設計 4-2 と ⑤ に理由と基準を明記。

## 非ブロック（起票して次便送り／この便で直したもの）

| 審査 | 内容 | 扱い |
|---|---|---|
| N1 | jsdom は `inert` 未実装（`'inert' in el` が false・属性にも反映されない）＝C1〜C4 が保証するのは「値を代入したこと」だけ。design ⑨ の「印が付いているかは測れる」は不正確 | **書類を訂正**（⑨）。検査ファイルの冒頭にも明記。挙動の一次情報は画面検査だけ、ただし順序だけは C8 で単体固定 |
| N2 | 「直す前は赤」の対象は C1・C4 だけでなく **C2・C3 も赤**（未設定は `false` ではなく `undefined`） | **書類を訂正**（⑤ の表） |
| N3 | `FOCUSABLE_SELECTOR` の写しが検査側に2つ。便7 の C11（定義1か所）は `src/` しか見ないので歯止めの外 | ⑫ **F6** |
| N4 | **`tests-e2e/` は既定の型検査・lint の対象外**（`frontend/tsconfig.json` の include が `["src"]`／`npm run lint` は `eslint src`）。新 spec は手で型検査して0件だが仕組みとしては野放し | ⑫ **F7** |
| N5 | 「画面検査3幅」は不正確。対象パネルは `isMobile` のときだけ存在し `gotoViewer` が 390×844 を強制するため、**3 project で同じ 390px を3回** | **書類を訂正**（③・⑤） |
| N6 | B1 の前提「10個以上」に対し実測11＝余裕1 | **書類に明記**（⑤。将来ここが赤くなる理由を残した） |
| N7 | `ready` は依存配列専用で effect 本文では使っていない | ⑫ **F8** |

## 書類の誤りの訂正（反映済み）

- `recon.md` §1: `Drawer.tsx:143` → **`:118`**（25行ずれ）。
- `recon.md` §2: オーバーレイの範囲 `:110-117` → **`:110-116`**。
- `recon.md` §3: `Drawer.tsx:105`／`Sheet.tsx:86` は土台では正しいが**実装後は `:107`／`:88` にずれる**ことを追記。
- `design.md` ⑤: 「直す前は赤」の対象（N2）と「3幅」（N5）を訂正、C8 を追加。
- `design.md` ⑨: jsdom についての表現（N1）を訂正。

## PO が明示した重点3項目への審査判定

| 重点 | 判定 | 根拠（審査が現物で確認） |
|---|---|---|
| **推測禁止・一次情報** | △→対応済み | recon・design は現物を開いた跡があり、下請け調査の誤り2件（35ファイル／`inert` の可否）を訂正済み。残っていた行番号誤り2件と jsdom の表現は本審査で訂正 |
| **配線・DB の SSOT／データ入力を分散させない** | **○** | 追跡差分は4ファイル・CSS 0行。**backend・migrations・API・辞書(i18n)・DB は1行も触っていない**。新しい状態の持ち場所も増えていない（`inert` は `open` から導出するだけで入力口ではない）。公開プロパティ増減0＝呼び出し37ファイルの書き換え0 |
| **トークン・ハードコード禁止** | **○** | `git diff --stat` に `.css` は1本も無く CSS は本当に0行。`tokens.css` 不変。本体コードに px・色・ms の直値0・新トークン0。ADR-067 は対象外、ADR-144 §4（金型新設）にも当たらない |

## 審査が「調べたが問題なかった」と確認した主な点

- **呼び出し元全数**（`Drawer` 35／`Sheet` 2）を見て、**閉じている間に中身を操作している画面は0件**。
  programmatic な `.click()` はファイル選択とダウンロード用のみ、`.focus()` は確認窓の初期フォーカス
  （`useInboxState.ts:855-860`・閉じている間は通らない）と開いたドロワー内（`InventoryView.tsx:194,197`）だけ。
- **最初から `open=true` でマウントする形**でも `ready` 引数が効いて `inert=false` になることを実測（便7 の E5 は不変）。
- **閉じるときのフォーカス復帰**は復帰→無効化の順で壊れない（実測）。
- **閉じている間の寸法測定**は `inert` が描画・レイアウトを変えないため不変。既存 spec の寸法測定は
  すべて `--open` 付きに絞られているので無関係（6本の spec を全部確認）。
- **既存 e2e が閉じたパネルの中身を掴んでいる箇所は無い**。
- **Playwright（1.60.0）の読み取り系 assertion は `inert` を無視する**ので、既存検査が壊れる経路は無い。
- **B2 の「DOM 順で後ろ」前提は成立**: ポータル先は `document.body`（`Drawer.tsx:67`）で閉じた2枚は `#root` の後ろ。
  スマホのカード表示にフォーカス対象は無い（`onRowClick`・`selectable` 未使用）ため、外側は約6個＝押下回数は約9回。
- **B1 の前提の数**（閉じたパネル2枚・focusable 合計11＝絞り込み9＋シリーズ2）は現物と一致。
- `Modal` が対象外という判断（`frontend/src/components/Modal.tsx:86` で閉じると null）は正しい。

## 設計担当が自分で測った一次情報（コマンドと出力の件数行）

```
$ npx vitest run src/hooks/useFocusTrap.test.tsx          （直し込み・最終）
 Test Files  1 passed (1) /  Tests  28 passed (28)

# RED-first 1: useInertWhenClosed の呼び出しを2金型から外す（＝直す前）
 Tests  6 failed | 20 passed (26)   赤 = D5-C1・C2・C3 × Drawer/Sheet

# RED-first 2: useLayoutEffect を useEffect に戻す（＝審査 B-1 の状態）
 Tests  2 failed | 26 passed (28)   赤 = D5-C5 × Drawer/Sheet

$ npm run generate:api-types && npx tsc --noEmit            → TSC_EXIT=0（0件）
$ npm run check:all                                         → 終了0（警告59件は既存ファイル由来）
$ npx eslint --max-warnings=0 <触った src の4ファイル>        → 合格（出力なし）
$ npx vite build --manifest && node scripts/check-viewer-bundle.js
 viewer JS: 2 ファイル, 合計 260.8 KB（上限 300 KB） → ✅ PASSED
$ E2E_NO_WEBSERVER=1 npx playwright test --list --project=vl-{mobile-390,tablet-768,desktop-1280}
 drawer-inert-closed が各 project で 3 件ずつ収集（B1・B2・B3 × 3 = 9件）
$ git status --short | grep -cE "\.css|locales|backend/|migrations/|\.github/"  → 0
```

**走らせていないもの**: 画面検査（この端末に Playwright のブラウザが無い＝環境制約。CI が唯一の一次情報）。
審査も同じ制約下で、B1〜B3 の赤緑はコードからの論理判定と、ブラウザの決まりを模したプローブに基づく。

## 設計担当が自分で見つけて直した点（審査より前）

- **画面検査 B2 の「Tab を20回」は空振りになり得た**。閉じたパネルは `document.body` の末尾に描かれる＝
  DOM 順で画面の部品より後ろにあるため、手前の部品が20個より多いと**閉じたパネルまで届かないまま
  「入った回数0」が成立**し、直す前でも緑になる。**「閉じたパネルの外の要素数＋3回」**に変更し、
  「外側を使い切った次の1回は必ず閉じたパネルに入る」＝**直す前は赤**が作りで保証される形にした（design ⑤）。
- 下請け調査の誤り2件（`Drawer` を45ファイルと報告→実測35／「React 18 では `inert` が使えない」→
  JSX 属性としては不可だが DOM の性質としては可）を実測で訂正した。

## 対象 ADR

- **ADR-1003**: 委譲 GO の条件として Reviewer の判定が必要 → 本書がその記録。
- **ADR-144**: §4（金型新設）には当たらない（金型の内部のみ・公開面は不変）。
  結論部 `:79`「金型変更時は PO 目視依存」に対し、**PO 決定で目視は閲覧ページのみ**（design ② に記録）。
- **ADR-067**: CSS を1行も触らないため対象外。
