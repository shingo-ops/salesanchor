# recon 便4: 登録ドロワーの 5 欄を金型 SelectControl にする（画面のみ）

> 親の書類: [recon.md](recon.md)（docs/handoff/format-work-parent/recon.md）。この書類は便4 の現在地だけ。
> 基準: origin/main 44c34a488（PR #4642 取り込み後）。worktree release/format-work-bin4 の実物を読んだ結果。

## 1. 金型 SelectControl（frontend/src/components/Select.tsx）
- options の型は `SelectOption = {value: string, label: string, disabled?}`（frontend/src/components/Select.tsx:20-24）。
- props: options・size・fullWidth・placeholder・appearance（frontend/src/components/Select.tsx:26-32）。disabled・value・onChange は素の select の props をそのまま受ける（frontend/src/components/Select.tsx:34-37）。onChange は素の ChangeEvent<HTMLSelectElement>。
- 実体は frontend/src/components/Select.tsx:64-114。placeholder は value="" の option として出る（:101-105）。options の描画は :106-108。
- design.md が「Select.tsx:42」と書いた onChange の行は誤り。:42 は `children?: never` で、onChange の実物は :34-37 の native props 経由。

## 2. 今の SearchSelect（frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx）
- 定義 :54-91（TextFieldControl + datalist、打った名前が候補と一致した時だけ id を返す）。使用 :215-219 の 5 箇所（細分類だけ key=`format-${work_id}`）。
- setValue :119-130。作品を変えたときの細分類リセットは :125（formatAfterWorkChange、frontend/src/features/tcg-product-import/productDetailModel.ts:92-93）。細分類の絞り込みは formatOptionsFor（同 :88-89）。作品未選択なら空配列。
- 周りの欄の形: `<label className="pmd-field">` + TextFieldControl（:220-235）。.pmd-field は frontend/src/features/tcg-analysis-review/supplier-detail-view.css:164-170。SearchSelect 専用のクラスは無い。
- 選択肢の型は LookupOption = {id, name}（frontend/src/features/tcg-analysis-review/reviewActions.ts:75）。取得元は GET /tcg/products/registration-form（backend/app/services/tcg_product_master_svc.py:191 以降）で、今のまま使う。

## 3. 前例
- SelectControl の前例: frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:312（options に {value,label}、value は String、onChange は e.target.value）。design.md は :332 と書いたが実物は :312。この前例の外枠は pmd-field ではなく form-group。

## 4. 文言・datalist・SearchSelect の今の使用（K8 の基準）
- `git grep -n searchSelectPlaceholder frontend/src`: ProductMasterDrawer.tsx:79、ja.json:4923、en.json:4923 の 3 行のみ。他の使用なし。
- `git grep -n datalist frontend/src`: ProductMasterDrawer.tsx:86、:88 の 2 行（便4 前）。
- `git grep -n SearchSelect frontend/src`: ProductMasterDrawer.tsx:54、:215-219（便4 前）。

## 5. 既存試験（frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx）
- 書き直し対象: `input[list]`（:62）、placeholder の検証（:82、:156）、`.pmd-field input` の個数 9（:89）、`input:not([list])`（:108）、`#lookup-product_format_id option`（:130）。

## 6. 候補件数の上限
- 中分類は public.type_master 18 行（docs/handoff/format-work-parent/design.md §2、docs/handoff/format-work-parent/raw/q07_constraints.txt）。
- 他の 4 欄（大分類・製造元・商品分類・細分類）は、取得元のコード（backend/app/services/tcg_product_master_svc.py:238-275）に LIMIT が無く、件数の上限をコードから確かめられなかった。design.md の「最大 18 件」は中分類にだけ言える。細分類は 28 行（docs/handoff/format-work-parent/recon-bin3b.md §2）で、作品で絞ると更に少ない。他の 3 欄の件数は未確認。
