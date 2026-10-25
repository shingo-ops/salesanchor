# review-opus: 閲覧ページ在庫表 スマホ絞り込み（便1）の独立審査

> この文書は何か（1行）: 設計を別の Opus に「反証を探す立場」で審査させた結果と、指摘への対応の記録（ADR-1015:2・:30）。

**日付**: 2026-10-25
**審査の指示**: 承認ありきにせず反証を探すこと／`file:line` を全数で抜き取り検証すること／`MultiSelect` の呼び出し元を全数 grep すること／CI 設定を一次ファイルで読むこと／推測で書かないこと
**初回の結論**: **CHANGES-REQUESTED**（指摘9件＋検査漏れ9件）
**改訂後の状態**: 全12項目に対応済み（下表）。中核の因果は反証できず維持。

## 1. 中核の因果は反証されなかった

審査は「一覧（z-index 50）が絞り込みパネル（301）の裏に回る」という結論に対し、4系統の反証を試して**すべて不成立**と報告した。

| 反証の筋 | 結果 |
|---|---|
| DOM の親子関係（本当に body 直下の兄弟か） | 兄弟で正しい（`frontend/src/components/Drawer.tsx:50`・`:117`／`frontend/src/components/Popover.tsx:147-156`） |
| 祖先がスタッキングコンテキストを作っていないか | `transform`/`opacity` は両者自身に付くだけ。祖先は body/html で共通 |
| DOM の挿入順で前面に出ないか | 両者とも positioned ＋ z-index 指定ありなので順序ではなく z-index が勝つ |
| `pointer-events` / `overflow` が先に効いていないか | popover は `pointer-events: auto`（`frontend/src/components/Popover.css:23`）＝「押せない」のではなく「見えない」 |

**審査後に、設計者が実機（本番ページ・Chrome 156）で DevTools 経由で直接測り、確定させた。**
`popover_z=50` / `drawer_z=301` / `drawer_bg=rgb(255,255,255)` / `drawer_box=0,0,360,672` / `popover_opacity=1` / `option_count=43`。
＝ 選択肢は 43 件ちゃんと描かれており、不透明な白のパネルに完全に覆われている。

## 2. 指摘と対応（全12項目）

| # | 指摘 | 深刻度 | 対応 |
|---|---|---|---|
| 1 | 再発防止の AC「ドロワーの中に `.comp-popover` が 0 件」は、portal 構造上**修正前でも常に真**＝不具合を1つも検出しない | 重大 | **A8 を書き換え**：「ドロワーが開いている間、`document` 全体で `.comp-popover` が 0 件」（design §⑤・§⑪） |
| 2 | RED-first が CI 設定で成立しない（`concurrency: cancel-in-progress: true` で1本目の実行が打ち切られる／トリガーが `pull_request` 単独） | 重大 | **手順を4段階で固定**（design §4-4）。1本目だけ push → PR を開く → 集約ジョブ `visual-language` の結論を待つ → **赤の実行 URL を PR 本文に残す** → 2本目を push。必須チェック名も `visual-language`（集約側）に訂正 |
| 3 | 第3の原因の見落とし：`position: fixed` の置き場に `window.scrollY` を二重加算 | 重大 | **実機で裏取りして確定**（400px 下げると一覧が y=550／正しくは150）。recon §3-3 に原因③として追記。本便では直さず **C4** に送る（金型を使う全画面に波及するため）。あわせて **A11**（スクロール後に開く経路）を新設 |
| 4 | `--dropdown-max-h`（200px）の inline での扱いが未記載。実際は入れ子スクロールになる | 中 | 実機で **中身1279px に対し表示200px＝43件中約6.6件**と判明。**inline では打ち切りを付けず**ドロワー本文のスクロールに任せる（design §4-2）。**A10**（20件以上の fixture で最後の1件まで見える）を新設 |
| 5 | `min-width` を popover 限定にする手段が未指定。子孫セレクタは詳細度が上がる | 中 | **修飾クラス方式に固定**（`--popover` を TSX が付ける。design §4-2 の表） |
| 6 | 区分 B-1 が規程の文言に厳密には合わない（`docs/` と `.claude-pipeline/` を含む）。①と⑥が自己矛盾 | 中 | **PO に2択で確認し「1」を受領（2026-10-25）**＝1本の PR で進め、PR 本文に「B-1相当・PO 確認済み」と明記。あわせて「今は無い状態を作る＝A」への反論を design §1-2 に明記 |
| 7 | 44px の根拠トークンが二重（`--field-h-lg` と `--size-icon-btn-lg`） | 中 | **`--size-icon-btn-lg`（`frontend/src/tokens.css:163`・WCAG 2.5.5 の注記あり）に一本化** |
| 8 | お手本との対応づけが誤り（「前者を採る」の前者は横並びボタンで、チェックボックス一覧は後者の中身） | 中 | design §⑨ を訂正。**本便が作るのは第3の形**（後者の中身を画面を増やさず置く）と明記 |
| 9 | `frontend/src/pages/viewer/InventoryView.tsx:352` の二重ガード／`:353` と非対称 | 軽 | §4-3 の PC／ドロワー分割で解消すると明記 |
| 10 | 引用の行ずれ2件 | — | `frontend/src/components/Drawer.css:30`→**`:31`**、`:105-112`→**`:109-112`** に訂正。`ADR-140 §63`→**`:63`（受け入れ基準 G4 行）**と表記を訂正 |
| 11 | e2e のモックキーが未記載 | 軽 | **`"GET /viewer/inventory"`** を design §4-5 に明記（`frontend/src/pages/viewer/api.ts:8` ＋ `frontend/tests-e2e/utils/api-mock.ts:33`・`:66`） |
| 12 | 検査漏れ9件（スクロール経路／`scrollWidth`／PC の一覧幅／選択肢が多い fixture／condition 2種以上／初期フォーカス／暗いテーマ 等） | — | **A7・A10・A11・A12・A13・A14・A16 を新設**。fixture の形（仕入元20件以上・コンディション2種以上・行50件以上）を §4-5 に固定 |

## 3. 審査が確認した事実（そのまま採用）

- **`MultiSelect` の呼び出し元は製品コード6・テスト2・Storybook 1 の全9か所**。既定 `"popover"` なら全数不変（design §4-6 に転記）。`frontend/src/pages/inbox/SalesFormMultiSelect.tsx` は金型を使わない別部品で無関係。
- **閲覧ページの e2e は書ける**。`frontend/viewer/index.html` が存在し、`frontend/src/pages/viewer/ViewerApp.tsx:60` は `readToken()` の有無だけで分岐するため `addInitScript` で足りる。アプリ本体の Firebase バイパスは不要。
- `detect-changes` のフィルタは `frontend/**`（`.github/workflows/e2e.yml:52-53`）なので、1本目が `frontend/tests-e2e/` だけでも画面検査は走る。
- `frontend/src/components/Popover.css:7-12` の `.comp-popover-overlay` は `frontend/src/components/Popover.tsx` が一度も描画しない**死んだ CSS**（C5 に記録）。
- 審査記録の置き場は ADR-1015:30 に従い review-opus.md（`docs/handoff/devflow-autonomy-b/design.md:68` の review-fable.md とは食い違うが、ADR-1015:15 により ADR を優先）。

## 4. 判定

上記1〜12の対応をもって **APPROVE 相当**とする。
ただし本記録は設計者（Opus）が自分の設計への指摘に対応したものであり、**対応後の再審査は受けていない**。
実装後、PR の Reviewer・Evaluator と PO の実機確認で確かめる。
