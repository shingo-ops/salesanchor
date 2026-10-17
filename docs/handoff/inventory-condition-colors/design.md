# 在庫表・閲覧ページ「状態」列の色分け 設計

- 区分: B（画面のみ・API/DB 変更なし）
- recon: docs/handoff/inventory-condition-colors/recon.md
- 対象ADR: ADR-1023（状態の価値順）、ADR-067（デザイントークン）、ADR-144（UI ガバナンス・金型）、ADR-027（i18n・今回は文言追加なし）

## 目的（PO の言葉）
- 「状態も色付けしたい…頻度の多いもの順に見やすい色にしたい」（2026-10-17）
- PO 決定（2026-10-17）: 「Sealed box・Case・Unsearched pack→青　Damaged sealed box・Damaged case→黄　No shrink box→別色」→「薄い紫にする」。赤は薄い赤（Badge soft の danger＝淡い赤背景）

## 変更前（recon より）
- frontend/src/features/inventory/conditionBadge.ts:7-18 は "sealed"/"damaged"/"case" の完全一致のみ。本番の実値で当たるのは Case（青）だけで、他は全て灰
- 本番頻度（2026-10-17 14:03Z・配信条件と同じ 873 行）: Sealed box 527 / Case 153 / Damaged sealed box 84 / No shrink box 43 / Damaged case 28 / Searched pack 17 / Bulk 10 / Opened box 7 / Unsearched pack 4。小文字の旧値 "sealed"/"damaged" は 0 件
- Badge の variant は neutral/info/success/warning/danger の5種（frontend/src/components/Badge.tsx:16）。紫トークン --purple-bg/--purple-text はライト frontend/src/index.css:124-125・ダーク :313-314 に既存

## 変更後
### 1. 色の割り当て（conditionBadge.ts）
trim・小文字化して完全一致（既存の判定方法を維持）。

| variant | 値（小文字で一致） | 本番件数 |
|---|---|---|
| info（青） | sealed box / case / unsearched pack | 684 |
| warning（黄） | damaged sealed box / damaged case | 112 |
| purple（薄い紫・新設） | no shrink box | 43 |
| danger（薄い赤） | opened box / opened case / searched box / searched pack / ar confirmed pack | 24 |
| neutral（灰） | 上記以外（Bulk・空など） | 10 |

- 値の集合は ADR-1023「What」4 の11値（正本は DB public.line_conditions）。旧値 "sealed"/"damaged" の割り当ては本番 0 件のため削除する
- ファイル冒頭コメントの「GAS 在庫一覧 H:1591-1605 と同じ規則」は事実でなくなるため、ADR-1023 の値と本設計への参照に書き換える

### 2. Badge に purple を足す（金型の拡張）
- Badge.tsx: BadgeVariant に 'purple' を追加、冒頭コメントの variant 一覧も更新
- Badge.css soft: `.comp-badge--soft.comp-badge--purple { background: var(--purple-bg); color: var(--purple-text); }`
- Badge.css solid: 塗り用の紫トークンが無いため、新トークンは作らず soft と同じ組（--purple-bg / --purple-text）にし、その旨をコメントで残す（現在 solid purple の利用者はいない）
- Badge.stories.tsx の AllVariantsSoft / AllVariantsSolid、frontend/src/pages/design-preview/sections/BadgeSection.tsx の variant 配列と「5種」の文言を6種に
- 新しいトークン・hex は追加しない（check-design-token-ratchet・check-new-tokens・check-dark-parity は発動しない／PASS のまま）

## 触らない範囲
- ステータス列（在庫=青文字・予約=オレンジ文字）、他の列、API、DB、locale
- 既存 variant の色トークン値（ライト info の文字コントラスト 4.01:1 は既存の値で、今回は変えない。事実として記録）
- GAS 在庫一覧（別リポジトリ・別作業。PO 判断を別途取る）

## 代替案
- 案A（価値の段で緑/黄/赤/灰）: PO が青・黄・薄紫・赤に修正したため不採用
- 9値に9色: 少数の色の目立ちが消え、新トークンが多く要るため不採用
- No shrink box を緑: 緑が黄より良く見え、ADR-1023 の価値順（Damaged sealed box 2 > No shrink box 3）と逆転するため不採用

## リスクと対処
- 青が隣のステータス列「在庫」の青文字と同じ系統 → PO 承知の上の決定（2026-10-17）。在庫は文字色のみ、状態は背景付きの札で形が違う
- BadgeVariant を import する他の5ファイル → 型の拡張のみ。Record<BadgeVariant, …> の網羅型があれば tsc が知らせるため、tsc 結果で確認する

## 受入条件
| 基準 | 検証方法 |
|---|---|
| ADR-1023 の11値と Bulk・空・null がそれぞれ上表の variant になる | conditionBadge.test.ts を全値の it.each に更新して vitest pass |
| 在庫表・閲覧ページのセルが新しいクラス（comp-badge--info 等）で描かれる | viewerColumns.cells.test.tsx 等の期待値更新後 vitest pass |
| purple soft の文字コントラストが 4.5:1 以上 | recon の計算値（ライト 6.28・ダーク 7.39） |
| hex・新トークンの増加なし | check-design-token-ratchet.sh / check-new-tokens.js / check-dark-parity.js pass |
| i18n・lint・型 | check-i18n-missing-keys.js / eslint / tsc（既存エラー件数が増えない） |
| 本番反映 | デプロイ success と配信物に comp-badge--purple が含まれること。画面の見え方は PO 目視 |

## 外部・過去事例の参照と我々への応用
- 過去事例: #4480 は「在庫・予約」列（#4484 で見出しを「ステータス」に変更）の文字色のため、frontend/src/tokens.css にトークン2つ（--offer-instock-text / --offer-preorder-text）を新設した → 我々への応用: 今回は既存の --purple-bg / --purple-text（frontend/src/index.css:124-125, :313-314）が使えるため新設せず、既存の Badge 金型を拡張して色を付ける
- 外部事例: 視覚探索の pop-out（Treisman & Gelade 1980）と色覚多様性への配慮（文字を必ず併記・WCAG 1.4.1）を配色の考え方に用いた → 我々への応用: 状態の文字は常に表示し、色だけで情報を伝えない。出典の書誌は原典照合未実施。数値で効果を主張する事例は用いない

## 維持の仕組み
- 守り手: frontend/src/features/inventory/conditionBadge.test.ts（vitest・CI）が全値と色の対応のずれを止める。hex 直書きは CI の design-token-ratchet と ADR-067 チェックが止める
- 状態の値と色の対応は conditionBadge.ts 1か所（在庫表・閲覧ページの両方が呼ぶ）。試験が全値の対応を固定する
- 状態の値が ADR-1023 で増減したら、本ファイルの表と conditionBadge.ts と試験を同じ PR で直す

---

## 追補1（2026-10-17）: バッジをやめて文字色にする

### PO の言葉
- 「バッジの色ではなく文字に色を付けられる？ばっじなしで」
- Opus の確認「傷あり（Damaged）はライトでは茶色、ダークでは黄色で文字色にしてよいか」→ PO「y」（2026-10-17）

### 変更前（#4485 マージ後の origin/main 4a6d72e53）
- frontend/src/features/inventory/inventoryColumns.tsx:114 と frontend/src/pages/viewer/viewerColumns.tsx:70 は `<span className="inventory-cell__nowrap"><Badge variant={conditionBadgeVariant(it.condition)}>` で状態を札で描く
- 隣のステータス列は文字色だけ（inventoryColumns.tsx:63-69、viewerColumns.tsx:39-41、inventoryColumns.css:23-29）

### 変更後
- 状態列は Badge を使わず、文字だけを色付きで描く: `<span className={"inventory-cell__nowrap inventory-cell__condition--" + conditionBadgeVariant(it.condition)}>{状態}</span>`（在庫表・閲覧ページとも）
- frontend/src/features/inventory/inventoryColumns.css に文字色のクラスを足す（既存トークンを参照・新トークンなし・hex なし）
  - `.inventory-cell__condition--info    { color: var(--info-text); }`（青: Sealed box / Case / Unsearched pack）
  - `.inventory-cell__condition--warning { color: var(--warning-text); }`（ライト茶 #744210・ダーク黄 #fde68a: Damaged sealed box / Damaged case）
  - `.inventory-cell__condition--purple  { color: var(--purple-text); }`（紫: No shrink box）
  - `.inventory-cell__condition--danger  { color: var(--danger-text); }`（赤: Opened* / Searched* / AR confirmed pack）
  - neutral はクラスに規則を書かず、普通の文字色のまま（Bulk など）
- 値と色の対応の正本は conditionBadge.ts のまま（関数名・表は変えない。冒頭コメントだけ「Badge の variant」から「状態の色の種類（文字色のクラス名にも使う）」に直す）
- Badge 金型の purple variant（#4485 で追加）は残す。状態列では使わなくなるが、金型の6種目として stories・design-preview に載っており、削除は別判断

### 読みやすさ（WCAG コントラスト比・通常行の背景に対して。生出力 /tmp/CC報告ファイル/condition-text-color/4-5-contrast.txt）
| 色 | ライト（#ffffff） | ダーク（#1e293b） |
|---|---|---|
| 青 --info-text | 5.42 | 8.11 |
| 茶/黄 --warning-text | 8.30 | 11.75 |
| 紫 --purple-text | 8.40 | 8.28 |
| 赤 --danger-text | 7.53 | 10.11 |
- 既知の弱点（事実として記録・今回は変えない）: ライトの青はマウスを乗せた行 4.40・選択行 4.01（ステータス列の在庫の青と同じ値）

### 触らない範囲
- 色の割り当て（どの値が何色か）、ステータス列、トークン値、API・DB、GAS 在庫一覧

### 受入条件
| 基準 | 検証方法 |
|---|---|
| 状態列に Badge（comp-badge）が描かれず、値ごとに inventory-cell__condition--{info,warning,purple,danger,neutral} の span になる | inventoryColumns.test.tsx・viewerColumns.cells.test.tsx・InventoryPage.tablelayout.test.tsx の期待値更新後 vitest pass |
| hex・新トークンの増加なし | check-design-token-ratchet.sh / check-dark-parity.js pass |
| 型・lint | tsc（既存4件から増えない）・eslint・stylelint pass |
| 本番反映 | デプロイ success と配信物に inventory-cell__condition--warning の CSS が含まれること。見え方は PO 目視 |

### 維持の仕組み（追補1）
- 守り手: 上記3つの試験（vitest・CI）が状態列のクラスを固定する。値と色の対応は conditionBadge.test.ts が固定する


---

## 追補2（2026-10-18）: Case だけを緑にする

### PO の言葉
- 「Caseは緑に出来る？」→ Opus「Case だけ緑の文字（既存の色を使う）にしてよいか。Sealed box・Unsearched pack は青のまま」→ PO「y」（2026-10-18）

### 変更前（#4490 マージ後の origin/main）
- frontend/src/features/inventory/conditionBadge.ts で `case "case"` は Sealed box・Unsearched pack と同じ `"info"`（青）を返す
- frontend/src/features/inventory/inventoryColumns.css に `.inventory-cell__condition--success` の規則は無い

### 変更後
- conditionBadge.ts: `"case"` だけを `"success"` を返す分岐へ移す（"sealed box"・"unsearched pack" は `"info"` のまま。"damaged case"・"opened case" は変えない）
- inventoryColumns.css に1規則を足す（既存トークン参照・新トークンなし・hex なし）
  - `.inventory-cell__condition--success { color: var(--success-text); }`
  - --success-text はライト #22543d（frontend/src/index.css:57）、ダーク #bbf7d0（同:250）で定義済み
- 'success' は Badge の既存 variant 名（BadgeVariant）にあるため、関数の戻り値の型は変わらない

### 触らない範囲
- Case 以外の値の色、ステータス列、トークン値、Badge 金型、API・DB、GAS 在庫一覧

### 受入条件
| 基準 | 検証方法 |
|---|---|
| Case が success、Sealed box・Unsearched pack が info のまま、他の値は不変 | conditionBadge.test.ts の対応表更新後 vitest pass |
| 在庫表・閲覧ページで Case の span が inventory-cell__condition--success になる | 状態列の試験（Case を使うものがあれば期待値更新）vitest pass |
| hex・新トークンの増加なし | check-design-token-ratchet.sh / check-dark-parity.js / check-ui-governance.js pass |
| 型・lint | tsc（既存4件から増えない）・eslint・stylelint pass |
| 本番反映 | デプロイ success と配信物 CSS に inventory-cell__condition--success が含まれること。見え方は PO 目視 |

### 維持の仕組み（追補2）
- 守り手: conditionBadge.test.ts が値と色の対応を固定し、CI（vitest）で毎回確かめる
