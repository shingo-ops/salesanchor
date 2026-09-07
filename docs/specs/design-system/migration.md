# 移行計画（design-system・PO承認済 2026-07-06改訂）

> この文書は何か（専門用語なしの1行）: 散らかった今の画面を、1ヵ所直せば全ページ変わる理想形へ、壊さず順番に寄せる工事計画。

親: [README.md](README.md)／理想: [design.md](design.md)／現状実測: [recon.md](../../handoff/design-system-recon/recon.md)・[網羅recon full-recon.md](../../handoff/design-system-recon/full-recon.md)
PO承認: 2026-07-05初版／2026-07-06改訂（網羅reconで色の真数36・表28件・関所隙間5つが判明し便構成を再編）

## 1. 方針の柱（5本）
1. 関所ファースト（領域ペア版）: 掃除の前に蛇口を閉める。ただし既存debtを一度に全部failさせると全並行便が詰まるため、便0bラチェットと同じ「増分のみ阻止（A案）」で、各領域を掃除し終えた直後にその領域の関所を建てる。掃除と関所を領域ごとにペアにする。
2. 同値置換: 色の集約は値を変えず名前に置き換えるだけ。見た目の質の変更は移行完了後の別テーマ。移行とデザイン変更を混ぜない。
3. 小口バッチ: 部品の金型寄せは1便5〜8ファイルに分割し各バッチで画面確認。
4. 部品台帳が分母: KGI①の分母は §4 の部品台帳の行数（満数方式）。
5. 現物照合（便1破棄の教訓）: reconの数字は必ず3検品（ノイズ除外・既存ADR照合・KGI定義照合）を経てから設計に使う。

## 2. 便構成と受入基準
| 便 | 内容 | 前提 | 受入の芯 |
|---|---|---|---|
| 便0 | 関所ラチェット新設＋部品台帳棚卸し（完了・#2806/#2801） | − | 上限=現状値でfail稼働（済） |
| 便0.5 | 用途トークン新設: 本物色36の受け皿をADR-067準拠で index.css の :root/:root.force-dark に定義（詳細は [design.md §5.3.1](design.md) 参照） | 便0 | 新設トークンがdark-parity通過・36件の対応表確定 |
| 便1a | 色の同値置換①: calendars.config.ts 21件→用途トークン参照 | 便0.5 | config内の生hex 0・visual gate(schedule)一致 |
| 便1b | 色の同値置換②: RolesPage.tsx 13＋schedule-owner 1＋Dashboard 1＝15件 | 便0.5 | 該当生hex 0・見た目一致 |
| 便1c-guard | 色掃除領域に関所: TS色定数の増分をfailさせるガード追加（領域ペア） | 便1a/1b | TS色リテラル増分でfail稼働 |
| 便2 | 素の<table> 28件→DataTable金型（小口バッチ） | 便0.5 | 素の<table>残存0 |
| 便2-guard | 表領域に関所: 素の<table>新規をfail（領域ペア） | 便2 | 素の<table>増分でfail稼働 |
| 便5 | 骨格: 素の<h1> 6件→PageLayout・骨格CSS 2系統→1系統 | 便0 | 素の<h1>残存0・骨格1系統 |
| 便5-guard | 骨格領域に関所: 素の<h1>新規をfail（領域ペア） | 便5 | 素の<h1>増分でfail稼働 |
| 便6 | 空状態独自3件→EmptyState・検索欄/テキスト書式の共通化 | 便0.5 | 空状態独自0・検索/書式1定義 |
| 便6-guard | 空状態・visual範囲の関所拡張（inbox/Karte以外へvisual gate拡張の可否をrecon） | 便6 | 隙間の縮小を実測 |
| 便7 | カタログ満数＋KGI③波及実測（部品定義1件変更→使用全ページ反映を実証） | 便2〜6 | KGI③④の◯/◯判定 |

## 3. ラチェット運用
- 色ラチェット: .github/workflows/design-token-guard.yml（便0bで新設・稼働中）
- hex上限の推移（真の分母ベース）: 36（便0.5時点）→ 便1a後に config分減 → 便1b後 0
- 領域ペア関所（便1c-guard/便2-guard/便5-guard/便6-guard）は各領域の掃除完了直後に増分阻止で追加
- 正当な例外は許可リストで管理（変更はPO承認必須）

## 4. 部品台帳（KGI①の分母の源泉・満数方式）
| # | 部品 | 金型（1ヵ所定義） | 現状（網羅recon実測 cbaee61） | 直書き残存の測り方 |
|---|---|---|---|---|
| 1 | プルダウン | components/Select.tsx | 採用19・pages自前<select>は別途 | pages配下<select>出現数 |
| 2 | 検索欄 | components/InventorySearchBar.tsx | 採用11・共通化弱い | placeholder=検索/type=search |
| 3 | ボタン | components/Button.tsx | 採用7 | ^\.btn 定義CSS数 |
| 4 | アイコン | constants/icons.tsx + iconSizes.ts | 採用27 | アイコン供給源 |
| 5 | テキスト書式 | 共通金型なし（便6で新設） | 43ファイル分散・未集約 | toLocaleDateString等 |
| 6 | ページ骨格 | components/PageLayout.tsx | 採用62・素の<h1> 6・骨格CSS 2系統 | pages配下<h1>数・骨格CSS系統数 |
| 7 | カード | components/Card.tsx | 採用2・独自CSS 0 | pages配下 .card |
| 8 | データ表 | components/DataTable.tsx | 採用22・素の<table> 28 | pages配下<table> |
| 9 | バッジ | components/Badge.tsx | 採用2・独自CSS 0 | pages配下 .badge |
| 10 | 空状態 | components/EmptyState.tsx | 採用1・独自3 | pages配下 empty-state/EmptyState |

## 5. 手当て漏れ対応表（網羅reconで露見・全て便に割当済）
| 露見した差分 | 現状 | 担当便 |
|---|---|---|
| 素の<table> | 28件 | 便2＋便2-guard |
| 素の<h1> | 6件 | 便5＋便5-guard |
| 空状態独自 | 3件 | 便6 |
| TS色定数の関所穴 | ガード無し | 便1c-guard |
| visual gateがinbox/Karteのみ | 他画面穴 | 便6-guard(拡張可否recon) |
| 検索欄・テキスト書式の共通化弱 | 未集約 | 便6 |

## 6. ADR整合（設計トラック内で扱う）
- ADR-067（色SSOT・:root/:root.force-dark・直書き禁止）: 便0.5でトークン正本化、便1a/1bで直書き解消。
- ADR-073（KGI 100%ルーブリック・中）: 本移行完了でKGI①〜⑤達成を目指す。設計トラック内。
- ADR-144（pages/生UI増殖防止・高）: 便2/便5/便6の金型寄せ＋領域ペア関所で対応。設計トラック内。

## 7. 弊害・トレードオフ（空欄不可）
1. 領域ペア関所は便数が増える（guard便が4つ）。ただし各領域を閉じてから次へ進むので逆流ゼロ。
2. 便0.5の用途命名は判断作業。既存用途名パターンに倣い、生値命名（便1旧版の失敗）は繰り返さない。
3. config.ts 21件は表示専用と確認済（JS分岐依存なし）だが、便1aは念のためvisual gate(schedule)で確認。
4. visual gateがinbox/Karteのみ＝他画面の掃除は自動検知外。便で手動画面確認を補う。
5. 便数が多く完了まで時間がかかる。安全優先の意図的選択。

## 8. 外部・過去事例
ラチェット漸減方式はESLint警告削減等の定石。前例ADR-067。

## 9. 受入基準
便別受入は§2。テーマ完了は kgi.md ①〜⑤が○（⑥達成済）。KGI③実証は便7。

## 10. 接触面分析（6面走査）
①人: PO承認＋各便の画面確認。②エージェント: select系並行便と便1系の衝突は該当時に状態実測。③機械: 領域ペア関所を順次新設。④データ: 影響なし。⑤本番: 便0.5〜6はUI直結（同値置換で緩和）。⑥外部: 影響なし。

## 維持の仕組み
- 守り手: design-token-guard.yml/check-design-token-ratchet.sh（便0b稼働中）＋領域ペア関所（便1c/2/5/6-guardで順次）＋部品台帳満数方式
- 対象: 生値ベタ書き・部品重複定義・台帳未登録の新部品・素の<table>/<h1>/空状態の新規
- 未確立（正直な明記）: 領域ペア関所は各guard便完了まで人が守る。
