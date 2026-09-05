# 開発計画書: 商品マスタ 英語名・発売日の欠損補完（tcg_products）

- テーマ: docs/handoff/tcg-product-master-growth/
- 区分: 既存の延長・修正（STANDARD-WORKFLOW §1.8）。新規仕様書なし。親仕様: docs/specs/product-master/README.md
- 対象ADR: ADR-154（照合ロジックには触らない）
- 対象テナント: tenant_004（本番）。書き込みは migration 経由のみ
- 起草: 2026-09-06 設計パートナー / 承認: PO（決定は各ターンの合意に基づく）
- 実測の出所: カード CG-01（DB, 2026-09-06 00:58）/ CG-02（07:56 頃）/ CG-03（07:02）/ CG-04（コード, main HEAD 154e93f6, 07:38）

## 1. 目的と位置づけ

`tenant_004.tcg_products` の `english_title`（空17件）と `release_date`（空40件）を埋める。

**照合精度への効果は無い**ことを明記する。商品判定に渡る文字列は `raw_product_name` とキーワードのみで、`english_title` `release_date` は判定に使われない（recon.md §落とし穴）。本計画の効果は表示・輸出書類・新商品判定の入力品質に限られる。

## 2. KGI（全件数 296 は CG-01 手順3 実測）

| 指標 | 現在（実測） | 目標 | 備考 |
|---|---|---|---|
| english_title 空 | 17 | 0 | 4件は登録前に追確認（§4.1 の「要追確認」） |
| release_date 空 | 40 | 5 | 残5件は「発売日なし」または「無効化」。理由を §4.3 に記録 |
| 要公式確認（日付未確定） | 5 | 0 | 確認できたものから M2' で埋める。確認不能なら NULL＋理由 |
| is_active=false（対象内） | 0 | 2 | PM0241・PM0242。戻せる措置 |

## 3. 決定事項（PO合意済み・本書で正本化）

1. 英語名の表記ルール: 公式英語名があればそれを使う。無ければ販売サイト多数派の表記。**ゲーム名は付けない**（既存 PM0001〜 の書式に揃える）。
2. PM0227「3rd anniversary set」= ONE PIECEカードゲーム 日本版 3rd ANNIVERSARY SET（プレミアムバンダイ抽選・2025-08-29〜09-30 受付）。
3. 単独の発売日が存在しない商品は `release_date` を NULL のまま残し、理由を本書に1行記録する（代替日は入れない。新商品判定の誤作動を避ける）。
4. プロモ・賞品カードは**配布開始日**を発売日とする（既存 PM0271 = 雑誌発売日 2025-06-04 と整合）。
5. 日本語版に単独商品が存在しない PM0241・PM0242 は `is_active = false`（削除しない）。根拠: CG-03 で参照0件、CG-04 で候補抽出が `is_active = TRUE` に限定されていることを確認（tcg_analyzer_svc.py L63/L149/L174/L192）。
6. ロルカナは全て日本語版として扱う（PO明言）。

## 4. 対象一覧

### 4.1 english_title 登録 17件（M1）

出典の種類: 公式=メーカー公式サイト / 多数派=海外販売サイトの慣用表記 / 定訳=長年の慣用（追確認要） / 訳案=設計パートナー訳（追確認要）

| code | japanese_title | english_title（登録値） | 出典 |
|---|---|---|---|
| PM0219 | ストームエメラルダ | Storm Emeralda | 多数派 |
| PM0220 | アビスアイ | Abyss Eye | **要追確認**（確認1件のみ） |
| PM0221 | ワイルドブレイズ | Wild Blaze | **要追確認**（定訳・未検索） |
| PM0222 | OP16 決戦の刻 | The Time of Battle | 公式（英語版名） |
| PM0223 | 遊戯王 LIMIT OVER COLLECTION THE HEROES | Limit Over Collection -The Heroes- | 公式（KONAMI アジア） |
| PM0224 | 遊戯王 LIMIT OVER COLLECTION THE RIVALS | Limit Over Collection -The Rivals- | 公式（KONAMI アジア） |
| PM0225 | UNION ARENA 勝利の女神NIKKE【PC02BT】 | Precious Booster Pack Goddess of Victory: NIKKE [PC02BT] | 多数派 |
| PM0226 | FB-09 | DUAL EVOLUTION [FB09] | 公式（商品名が英語） |
| PM0227 | 3rd anniversary set | 3rd Anniversary Set | 公式表記由来 |
| PM0228 | 葬送のフリーレン 新装版 | Frieren: Beyond Journey's End (New Edition) | **要追確認**（「新装版」の訳は訳案） |
| PM0260 | BEYOND THE BRAVE | Beyond the Brave | 公式 |
| PM0261 | QUARTER CENTURY LIMITED PACK | Quarter Century Limited Pack | 公式 |
| PM0262 | QUARTER CENTURY TRINITY BOX | Quarter Century Trinity Box | 公式 |
| PM0263 | 30th CELEBRATION | 30th Celebration | 公式 |
| PM0264 | FUTURISTIC BOX | 30th Celebration Futuristic Box | 公式 |
| PM0265 | 30th CELEBRATION プレミアムデッキセット | 30th Celebration Premium Deck Set Espeon & Umbreon | 公式（ポケモン英名） |
| PM0271 | ONE PIECE magazine 別冊 Focus on ONE PIECE FAN LETTER 付録プロモ | ONE PIECE magazine Special Issue Focus on ONE PIECE FAN LETTER Promo Card (P-096) | **要追確認**（訳案） |

### 4.2 release_date 登録 30件（M2）

出典: 公式=メーカー公式 / 複数=独立した2サイト以上 / 単一=1サイトのみ（登録前に再確認推奨）

| code | japanese_title | release_date | 出典 |
|---|---|---|---|
| PM0231 | ビクティニ レッドプロモ（BWR争奪戦 優勝プロモ） | 2025-06-14 | 公式（配布開始日・決定4） |
| PM0232 | 物語のはじまり | 2025-01-25 | 公式X |
| PM0233 | フラッドボーンの渾沌 | 2025-03-22 | 複数 |
| PM0234 | インクランド探訪 | 2025-05-17 | 公式（ディズニーストア） |
| PM0235 | 逆襲のアースラ | 2025-07-12 | 複数 |
| PM0236 | 星々の輝き | 2025-09-06 | 単一 |
| PM0237 | 大いなるアズライト | 2025-10-31 | 単一 |
| PM0239 | ジャファーの王権 | 2026-02-21 | 公式X |
| PM0243 | 未知なる彼方へ! | 2026-05-08 | 複数 |
| PM0246 | LEGACY OF DESTRUCTION | 2024-01-27 | 公式 |
| PM0247 | INFINITE FORBIDDEN | 2024-04-27 | 複数 |
| PM0248 | RAGE OF THE ABYSS | 2024-07-27 | 複数 |
| PM0249 | SUPREME DARKNESS | 2024-10-26 | 単一 |
| PM0250 | ALLIANCE INSIGHT | 2025-01-25 | 複数 |
| PM0251 | DUELIST ADVANCE | 2025-04-26 | 単一 |
| PM0252 | DOOM OF DIMENSIONS | 2025-07-26 | 公式 |
| PM0253 | BURST PROTOCOL | 2025-10-25 | 単一 |
| PM0254 | BLAZING DOMINION | 2026-01-24 | 単一 |
| PM0255 | CHAOS ORIGINS | 2026-04-25 | 公式 |
| PM0256 | QUARTER CENTURY CHRONICLE side:UNITY | 2024-02-23 | 公式 |
| PM0257 | QUARTER CENTURY CHRONICLE side:PRIDE | 2024-03-23 | 公式 |
| PM0258 | QUARTER CENTURY DUELIST BOX | 2023-12-23 | 公式 |
| PM0259 | QUARTER CENTURY ART COLLECTION | 2025-02-22 | 公式 |
| PM0260 | BEYOND THE BRAVE | 2026-07-18 | 公式 |
| PM0261 | QUARTER CENTURY LIMITED PACK | 2024-11-16 | 単一（受注品・出荷日） |
| PM0262 | QUARTER CENTURY TRINITY BOX | 2024-12-21 | 単一 |
| PM0263 | 30th CELEBRATION | 2026-09-16 | 公式 |
| PM0264 | FUTURISTIC BOX | 2026-09-16 | 複数 |
| PM0265 | 30th CELEBRATION プレミアムデッキセット | 2026-09-16 | 複数 |
| PM0266 | OP-17 | 2026-08-22 | 単一 |

### 4.3 release_date を NULL のまま残す 5件（理由記録・決定3）

| code | japanese_title | 理由 |
|---|---|---|
| PM0229 | レトロカード バルク | バルク品。発売日の概念なし（PO明言） |
| PM0240 | 物語のおもいで | 単独販売なし。第7弾・第8弾ボックス購入特典プロモパック（タカラトミー公式記載） |
| PM0241 | WHISPERS IN THE WELL | 日本語版に単独商品なし（公式商品情報に非掲載）。M3 で is_active=false |
| PM0242 | WINTERSPELL | 同上。M3 で is_active=false |
| PM0245 | ハイペリアシティ | 第14弾・未発売（公式非掲載）。analysis_results 参照5件あり＝取引対象として稼働中のため有効のまま維持 |

### 4.4 要公式確認 5件（M2' で別途）

| code | japanese_title | 現状 |
|---|---|---|
| PM0227 | 3rd anniversary set | 抽選受付 2025-08-29〜09-30 は確認。お届け月は未確認 |
| PM0230 | トライアルデッキ 【推しの子】 | 未調査 |
| PM0238 | アーケイジアと魔法の島 | 2025年12月下旬まで絞れたが日付未確定（公式ページ取得失敗） |
| PM0244 | ヴァインズ・アタック! | 予約サイトで 2026-07-17。公式未確認 |
| PM0267 | ONE PIECE magazine Vol.21 特集ヒロインズ 021 付録プロモ | 未調査 |

## 5. 実装単位（migration 3本・1本1目的）

各 migration は**自分の対象 code の範囲だけ**を検証する。テーブル全体の件数一致チェックは書かない（落とし穴）。全SQLは `tenant_004.` を明示する。

- **M1**: `UPDATE tenant_004.tcg_products SET english_title = ... WHERE code = ...` ×17。事前条件: 対象17code で `coalesce(english_title,'') = ''` が17件。事後条件: 同0件。
- **M2**: `release_date` UPDATE ×30。事前条件: 対象30code で `release_date IS NULL` が30件。事後条件: 同0件。
- **M3**: `UPDATE ... SET is_active = false WHERE code IN ('PM0241','PM0242')`。事前条件: 対象2code で is_active=true が2件。事後条件: is_active=false が2件。
- **M2'**（後日）: §4.4 で確定した分のみ。

要追確認4件（§4.1）が確認できない場合は M1 から除外し、KGI 未達分として本書 §2 を更新する。

## 6. 発見事項（本計画では触らない）

- `category_class` が空文字 `''` の商品が **31件**（CG-03 手順9）。NOT NULL 列に空文字が入っている。別計画で扱う。
- `tcg_products` を参照する FK が information_schema 上で各テーブル2行ずつ出力された（CG-02 手順5）。制約の二重定義か結合の重複か未確認。
- main 作業ツリーに `git status --porcelain` 367行の未コミット/未追跡（CG-04 手順3）。PR作成は worktree 起点とする。
- `tcg_product_master_svc.py:368` に商品マスタへのアプリ側 INSERT 経路が存在する。本計画では使わない（書き込みは migration のみ）。

## 7. 手順

1. 本書を PR で正本化（PO GO）
2. design.md（docs/handoff/tcg-product-master-growth/）に M1〜M3 の SQL 案と検証クエリを記載 → PO GO
3. 要追確認4件・要公式確認5件の裏取り（設計パートナーが外部確認 → 結果を design.md に反映）
4. M1・M2・M3 を別PRで作成（各PRカードに `.pr-number` 書き込みを含める）
5. QA実行: tenant_006 に TCG テーブルが存在するかを先に実測。無ければ migration 内の事前・事後条件クエリで代替
6. PO GO → 本番適用 → 事後条件の生出力で KGI 達成を確認し本書 §2 を更新

## 8. 未確認事項（正直に）

- tenant_006 に TCG テーブルが存在するか（未実測）
- `is_active=false` 商品の管理画面上の見え方（未確認）
- 「単一」出典の日付11件は登録前に2つ目の出典で裏取りする
