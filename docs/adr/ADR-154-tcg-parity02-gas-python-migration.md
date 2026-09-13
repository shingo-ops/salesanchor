# ADR-154: TCG PARITY-02 — GAS Phase 3 解析パイプラインを Python サーバーへ移植する

| 項目 | 内容 |
|------|------|
| ステータス | Accepted |
| 作成日 | 2026-09-03 |
| 起案 | しんごさん（PO） |
| 関連 | docs/handoff/parity02-phase-d-integrate/ |

---

## ひとことで

GAS で動いている TCG 仕入れ解析 Phase 3 を Python（FastAPI）サーバーへ完全移植し、
`analyze_extraction_job` が GAS の実行順序を 100% 再現できる状態にする。

## 背景

- GAS（Google Apps Script）実装は実行速度・保守性・テスト可能性の観点から制約が大きい。
- Python 側 `analyze_extraction_job` は既存だが、GAS Phase 3 の後処理（正規化ルール・注記マスタ・ステータスマスタ・unit 復旧・condition 再計算）が未実装だった。
- 本番データで GAS 実測と Python の condition_canonical 分布を照合したところ、99.32%（1615/1626）の一致率にとどまっていた。

## 決定

1. 正規化ルール（C-1）、注記マスタ（C-7）、ステータスマスタ（Status）、unit 復旧 E3a/E5、unit 未解決フラグ E3b、condition 逆引き E4 を Python に実装する。
2. 各マスタテーブル（tcg_normalization_rules / tcg_note_master / tcg_status_master）不在時は graceful fallback で従来動作を維持する。
3. ENGINE_VERSION を `name-first-v2` に統一する。
4. GAS Phase 3 の実行順序（正規化 → 照合 → E3a → E5 → E3b → E4）を Python で完全再現する。

## 検証基準

| 基準 | 検証方法 |
|------|---------|
| condition_canonical 分布が GAS 実測と 100% 一致 | dry_run_parity02_phase_e.py でオフライン比較 |
| E3a: unit 復旧 11件（GAS 実測と完全一致） | stats["e3a_recovered"] = 11 |
| E3b: unit_unresolved フラグ > 0 | stats["e3b_flagged"] > 0 |
| E4: 0件（現データで対象なし） | stats["e4_resolved"] = 0 |
| 既存テスト全 PASS | pytest -x -q |


---

## 追加決定案（2026-09-10・文書レビュー中）: 作品をまたぐ誤商品判定の防止

本節は提案であり、上記Acceptedの移植履歴を遡って変更しない。

### What

`name-first-v3-work` では作品の原文根拠と既存work_idを商品候補の制約に使う。作品不明の場合は型番語だけの自動確定を止める。同じ明細の商品名・状態・備考を商品除外語の対象にし、通常バトルコレクションへ「コロ」を追加する。原文抽出は作品名と根拠位置を追加した9列とし、旧7列データは保持する。

### Why

2026-09-10の本番read-only調査で、ガンダム系→ワンピースの保存誤判定29行（有効原文4行）、限定版→通常版4行（すべて無効原文）を確認。後者の1行は限定版表記が備考だけにあり、商品名だけの除外では止まらない。最新商品296件・作品11件を照合し、作品IDの仕組み自体は既存であることを確認した。GASと同じ誤判定を再現することは、人の正解との一致を保証しない。

### Scopeと既存契約との関係

v2のGAS一致は移植当時の検証として保存する。v3の商品判定は本件の受入基準を正とし、GASとの完全一致を要求しない。数量・価格・単位・状態の処理順序の変更は含まない。既存解析の一括更新、新商品登録、配信・本番反映は本提案に含めない。

設計: docs/handoff/tcg-product-master-growth/design-keyword.md §10
根拠: docs/handoff/tcg-product-master-growth/recon.md §2026-09-10本番DB読み取り調査
承認状態: POの実装依頼とGOは受領済み。本追加決定案の文書承認・マージは未完了。


## 追加決定案（2026-09-12）: 商品参照に基づく作品IDのみのGemini判断

状態: PO目的/境界/条件付き実行依頼を受領、方式は本PRで審査。詳細は[design-keyword §16](../handoff/tcg-product-master-growth/design-keyword.md)、実物は[recon末尾](../handoff/tcg-product-master-growth/recon.md)。

### What

Geminiへ有効商品と作品の対応表を渡し、既存原文9列に作品UUIDのみを追加する。商品IDや状態等を判断させない。推定値は原文と別保存し、参照版・IDを検証して従来の商品照合へ渡す。旧7/9列は従来方式を維持。配信はneeds_review=falseの行に限定する。

### Why

本番の型番投稿19明細で商品確定0、作品見出しの完全一致拒否とOP-13辞書の漢字差を確認。有効293商品の作品参照欠落0、8作品への対応表は存在する。現在のGeminiには商品対応を渡さず、型番からの作品判断を禁止していた。本案は作品IDだけを例外にし、過去の別作品EB01誤一致を否定試験に残す。19件全ての正解確定・精度向上を事前に証明したものではない。

PO指示によりテスト時のGemini実呼出し0。事前は機械契約を模擬/実DBで検証し、本番後の固定原文に対する正誤比較で採用/配信を決める。旧判断を自動上書きしない。実装承認と番号付きマージGO、本番品質合格を区別する。


### Why追補: 2026-09-13 行番号契約の修正

PR3441の本番反映後、最新取込の1投稿がinvalid product source spanで拒否された（保存0）。旧promptにはL0001-L0002形式例があり、新promptにはないことを実物照合した。実際の失敗応答は未保存であり表記の特定原因は未確認。既存の厳格な位置検査を維持し、出力例と入力角括弧を除く規則を新promptへ明示する。p2で版を記録しp1保存済み判断も同じ参照SHA検査で受理する。異常診断には長さと文字種booleanだけを残し原文は追加保存しない。外部事例により成功とは主張しない。詳細/受入基準/自己審査は[設計§16.12](../handoff/tcg-product-master-growth/design-keyword.md)、実測はreconの本番停止記録。PO「進めてくれ」で修正着手承認、本番効果の合格は未判定。


### Why追補: 保存済み明細IDで作品判断だけを比較する案

本番p2で行番号受理1件を確認したが、価格記号とメモ範囲の2差分が発生しRAW一致条件で停止した。再抽出の揺れを作品判断の評価に混ぜないため、既存762固有明細IDとRAWを固定し、Geminiには転記ITEM_IDと判断WORK_IDの2列だけを求める。602既特定/160未特定を別集計し、純粋な商品照合関数とREAD ONLYで比較する。既存全再解析は内部commit3か所があり比較に使わない。詳細・代替案・自己審査は[設計§17](../handoff/tcg-product-master-growth/design-keyword.md)。読取比較設計のみAPPROVE、判断の正式保存/全再解析/配信はREVISE。POは方式見直しを承認、実装・結果採用の承認と区別する。
