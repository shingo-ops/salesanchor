# review-opus: 便9（宿題 E4）確認窓と下から出るパネルの単体テスト — 設計担当の審査記録

> この文書は何か（1行）: 便9 の実装を設計担当（Opus）が**自分で測って**審査した記録。
> 一次情報（コマンドと出力の数字）だけを載せる。**サブエージェントの報告は根拠にしない**。

**日付**: 2026-10-27 ／ **土台**: `release/modal-sheet-unit-tests`（`origin/main` = `acc8d11ca`）
設計: `docs/handoff/modal-sheet-unit-tests/design.md` ／ 調査: 同 `docs/handoff/modal-sheet-unit-tests/recon.md`

## 判定

**合格（投入可）**。ただし審査で**2件を指摘し、その場で埋めた**（下の B-1・B-2）。
製品コードの変更は**0行**なので退行の余地が無く、残る不確実は「CI で既存テストが緑か」だけ。

## 1. 審査で見つけた問題と対応

| # | 重み | 内容 | 対応 |
|---|---|---|---|
| **B-1** | **ブロック（設計の誤り）** | 設計 ⑨ に「単体テストは本物のブラウザの挙動（**フォーカスの実移動**・inert の効き）を測れない」と書いてあったが、**これは事実と違う**。jsdom は `focus()`／`document.activeElement` を実装しており、既存の `frontend/src/hooks/useFocusTrap.test.tsx`（28件）は**すでに jsdom でフォーカスを測っている**。この誤りのため、`frontend/src/components/Modal.tsx`/`frontend/src/components/Sheet.tsx` **本体にある**2つの振る舞い（**開いたら中の最初の操作へカーソルが入る** `:61-68`／**閉じたら開く前の場所へ戻る** `:50-59`）が歯止めなしで残るところだった。しかも**次の宿題 E1 はまさにこの2つを共通化して動かす便**で、歯止めの無いまま動かすことになっていた | **M12・M13・S8・S9 の4件を追加**。設計 ⑨ の記述も訂正し、本当に測れないもの（①Tab キーの既定移動 ②`inert` の効き）に書き換えた |
| **B-2** | **ブロック（検査の強さ不足）** | 設計 C3 は「空振り防止」をうたいながら、**代表4通りの壊し方**しか求めていなかった（M6・M4・S3・S7 のみ）。残り13件は「書いたが何も見ていない」でも気づけない。便6〜便8 で**空振りで緑を3便連続で踏んでいる**ので、同じ穴を残すのは筋が通らない | **22件すべてを個別に保証する形へ強化**し、24通りの壊し方で実測した（§2）。**空振り0件** |
| B-3 | 軽微（指摘のみ・直さず） | `size` は `sm` を測っていない | **直さない**。単体テストは CSS を読めないので per-size のテストが測れるのは**文字列の組み立て1行だけ**で、`md`・`lg`・`xl` の3件で足りる。4つの class が `frontend/src/components/Modal.css:42-45` にすべて定義されていることは現物を読んで確認した（`sm` も実使用あり） |
| B-4 | 軽微（`size="xl"` の追加） | `xl` は型に在り**本番3画面で実使用**（`frontend/src/components/PurchaseDetailPanel.tsx:310`・`frontend/src/components/ShippingDetailPanel.tsx:383`・`frontend/src/features/tcg-analysis-review/V102PostEditModal.tsx:219`）なのに、当初案は `lg` だけだった | **M11 を追加** |

## 2. 空振り確認（RED）— 24通りすべてで狙ったテストが赤くなった

やり方: 製品コードを**1か所だけ**一時的に壊す → **その金型のテストファイルだけ**を実行 →
失敗したテスト名を取る → `git checkout --` で復帰。**22件すべてが最低1通りで赤**になることを要求した。

| 壊し方 | 壊した所 | 赤くなるべき | 実際に赤くなった | 件数 |
|---|---|---|---|---|
| mu-M1 | `frontend/src/components/Modal.tsx` `if (!open) return null;` を無効化 | M1 | M1 | 1/10 |
| mu-M2a | `aria-modal="true"` → `"false"` | M2 | M2 | 1/10 |
| mu-M2b | `aria-labelledby` を外す | M2 | M2 | 1/10 |
| mu-M3 | 既定 `size = "md"` → `"sm"` | M3 | M3 | 1/10 |
| mu-M4 | `comp-modal-dialog--${size}` → `--md` 固定 | M4 | M4 | 1/10 |
| mu-M5 | ✕ の `onClick={onClose}` を無効化 | M5 | M5 | 1/10 |
| mu-M6 | 背景の `onClick` を `undefined` 固定 | M6 | M6 | 1/10 |
| mu-M7 | 背景の `onClick` を `onClose` 固定 | M7 | M7 | 1/10 |
| mu-M8 | 本体の `stopPropagation` を外す | M8 | **M5, M8** | 2/10 |
| mu-M9 | Esc の判定キー名を変える | M9 | M9 | 1/10 |
| mu-M10 | `footer != null` → `false` | M10 | M10 | 1/10 |
| mu-M11 | `comp-modal-dialog--${size}` → `--md` 固定 | M11 | **M4, M11** | 2/13 |
| mu-M12 | 初期フォーカス `first.focus()` を無効化 | M12 | M12 | 1/13 |
| mu-M13 | 復帰 `el.focus()` を無効化 | M13 | M13 | 1/13 |
| mu-S1 | `frontend/src/components/Sheet.tsx` を閉じているとき null を返す形に | S1 | S1 | 1/7 |
| mu-S2 | `--open` が付かない形に | S2 | S2 | 1/7 |
| mu-S3 | オーバーレイを常に描く形に | S3 | S3 | 1/7 |
| mu-S4 | オーバーレイの `onClick` を無効化 | S4 | S4 | 1/7 |
| mu-S5 | ✕ の `onClick` を無効化 | S5 | S5 | 1/7 |
| mu-S6 | Esc の判定キー名を変える | S6 | S6 | 1/7 |
| mu-S7a | `aria-modal="true"` → `"false"` | S7 | S7 | 1/7 |
| mu-S7b | `footer != null` → `false` | S7 | S7 | 1/7 |
| mu-S8 | 初期フォーカス `first.focus()` を無効化 | S8 | S8 | 1/9 |
| mu-S9 | 復帰 `el.focus()` を無効化 | S9 | S9 | 1/9 |

**NOT-RED / エラー: 0件**（22件すべてが保証された）。

**2件赤くなった2通りの理由**（どちらも製品は正しい。テストの作りの説明がつく）:
- **mu-M8**: 本体の伝播止めを外すと、✕ の押下が**背景にも届く**ので `onClose` が2回呼ばれ、
  M5 の「**1回**だけ」も崩れる。M5 が「1回」を測っている証拠でもある。
- **mu-M11**: M4（`lg`）と M11（`xl`）は**同じ1行**（`comp-modal-dialog--${size}`）を見ているので、
  その行を固定すると両方赤くなる。B-3 で `sm` を足さないと判断した根拠そのもの。

## 3. 測った数字（一次情報）

| 測ったこと | コマンド | 結果 |
|---|---|---|
| 新テストの件数と結果 | `npx vitest run src/components/Modal.test.tsx src/components/Sheet.test.tsx` | **Test Files 2 passed (2) / Tests 22 passed (22)**（Modal 13・Sheet 9） |
| 型検査 | `npx tsc --noEmit` | **終了0・出力なし** |
| デザインシステム一括検査 | `npm run check:all` | **終了0**（lint は 0 errors / 59 warnings＝すべて既存ファイル） |
| pre-commit と同じ厳しさ（新2本だけ） | `npx eslint src/components/Modal.test.tsx src/components/Sheet.test.tsx --max-warnings=0` | **終了0**（警告0） |
| 製品コードの変更 | `git status --porcelain` / `git diff --stat` | **`M` 表示0件・diff 空**＝追跡ファイルの変更0（新規4つの `??` のみ） |
| 全体回し（新テストあり） | `npx vitest run --config vitest.unit.config.ts` | 1775件（既存1753＋新規22）／**失敗1件** `frontend/src/pages/super-admin/components/SoldOutResultsPanel.test.tsx` |
| 全体回し（新テストあり・別の回） | 同上 | 1769件／**失敗3件** |
| **全体回し（新テストを外して）** | 2本を退避して同上 | 1719件／**失敗5件** |
| 落ちた1本を単独で | `npx vitest run src/pages/super-admin/components/SoldOutResultsPanel.test.tsx` | **9件すべて緑** |

### 既存テストの不安定さは本便と無関係（機械で示した）

**新しいテストを外した方が失敗が多い（5件 > 1件）**。落ちるのは毎回違い、
`OrderLeadButtonMigration`・`InventoryPage.noechopatch`・`InventoryPage.tablelayout`・
`NeedsReviewTabsPanel.timing`・`SoldOutResultsPanel` といった**`Modal`/`Sheet` と無関係な画面**のテストで、
**単独で回すと緑**。この端末の遅さ（全体1回に 666〜900 秒、うち環境準備 1665 秒）による時間切れ。
→ **「手元で全体緑」は合格基準に置けない**。判定は CI の必須チェック `Frontend unit tests（内部）`。
設計 ④-4 に表で記録し、⑫ G6 に起票した。

## 4. 境界の確認（やっていないこと）

- 製品コード（.tsx・.css）は**1行も変えていない**（上の表で機械的に確認）。
- 既存の `frontend/src/components/Drawer.test.tsx`（10件）・`frontend/src/hooks/useFocusTrap.test.tsx`（28件）は**触っていない**。
- 文言・辞書・トークン・DB・API・`.github/` は触っていない。
- **PO が触る所は無い**（見た目・操作が一切変わらないため、実機の目視確認は不要）。

## 5. 次の便への申し送り（設計 ⑫ に反映済み）

- **G6**（新規）: 既存5本がこの端末で時間切れで落ちる。CI で緑かを本 PR の必須チェックで確認する。
- **G7**（新規・下調べ済み）: **初期フォーカスと復帰の複製は2金型ではなく3金型**。
  `frontend/src/components/Drawer.tsx:63,72-76,85` にも同じものがある。**復帰の塊（`frontend/src/components/Modal.tsx:50-59`＝`frontend/src/components/Sheet.tsx:50-59`）は差分0＝完全に同一**、
  初期フォーカスの塊は**変数名（`dialog`／`panel`）とコメントだけ違う**（`diff` で実測）。
  本便で歯止めができたので **E1（共通化）は安全に着手できる**。
- G1（E6＝2枚開いているとき最前面が勝つ）→ G2（C-tap＝浮かぶ選択肢44px）→ G3/G4 → G5（D2＝メルカリの表示サイズ感）。
