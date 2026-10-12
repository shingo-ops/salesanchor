# design: FedEx 送料比較モーダルの入力欄の標準化（AY-2m）

recon 相互参照: docs/handoff/fedex-rate-modal-inputs/recon.md
以下は設計書 ay2m-design.md の内容をそのまま転記する。

#### AY-2m FedEx 送料比較モーダルの入力欄の標準化（2026-10-12）

mode: handoff。§AY の一行入力を金型へ移す便の続き。PO 原文（2026-10-11、本セッション）「一旦金型登録に戻るページの統合は後で行う」。GO は ADR-1003 の委任に基づき Claude Opus が発行する。

現在地（origin/main 8fa6deb41。調査全文は /tmp/CC報告ファイル/ssot-ay2m/recon-raw.md）:
- 対象は frontend/src/components/FedExRateModal.tsx の生 `<input` 4件（:176 発送元国コード、:193 宛先国コード、:210 重量 kg、:239 宛先郵便番号）と、それぞれの `<label>`（:170-175、:187-192、:204-209、:233-238）。
- 4件の input の style は px 直書き（:183,:200,:217,:246 `width: 80px|80px|100px|160px, padding: "6px 8px", border: "1px solid var(--border)", borderRadius: "4px", fontSize: "13px"`）。label の style も px 直書き（:172,:189,:206,:235 `display:block, marginBottom:4px, fontWeight:500, fontSize:13px`）。
- 入力欄を囲む枠の余白も px 直書き（:167 `marginBottom: 12px`、:168 `gap: 16px, flexWrap: wrap, marginBottom: 8px`、:232 `marginBottom: 16px`）。
- CSS ファイル・className なし（全部 inline）。Modal・Button の金型は使用済み（:20-21）。
- 使用元は見積作成 QuoteCreatePage.tsx:289 の1か所だけ。
- 試験の依存: FedExRateModal.test.tsx:73,:124,:134 は getByLabelText（ラベルの文字と htmlFor の結び付き）、:78-79 は getByDisplayValue と `input.id === "fedex-dest-cc"`。e2e の参照 0。
- 金型 frontend/src/components/TextField.tsx:57-103 の TextField は、ラベル（comp-field__label、htmlFor=id）と TextFieldControl を comp-field（縦並び、gap var(--space-1)、margin-bottom var(--space-4)）で包む。id を渡すとそのまま input の id になる（:68,:92）。style は input に素通し。
- トークン（frontend/src/tokens.css）: --input-width-weight 80px（:425、請求書・見積の明細で sm と組み合わせて使用）、--input-width-price 120px（:427）。80px・100px・160px の「国コード」「郵便番号」用のトークンは無い。

設計判断（設計者、2026-10-12）:
- 金型は TextField（ラベル付き）・大きさは標準 md にする。理由: ここは表のセルではなくモーダルの一般フォームで、PO 方針「一般フォームは標準の見た目」に当たる（AY-2k の sm は1行に7欄並ぶ表のための例外）。ラベルも金型のラベルに変わり、ラベルの px 直書き4件が消える。
- 幅は金型の外側の配置なので、style の width に残し、値はトークンにする（幅の数値は今と同じ。並びを変えない）。md は左右の余白が var(--space-3) ずつで今（8px）より広いため、文字が欄の中で切れないかを実画面で確かめる（受入）。
  - 郵便番号（160px）は、幅金型の正式な段 --field-w-sm（160px）を使う。新しいトークンは作らない。
  - 国コード（80px）と重量（100px）は、同じ値で用途が合う既存トークンが無い。既存の候補は次の理由で使わない。
    - --input-width-weight（80px）は明細の重量用で、国コードとは用途が違う。値も重量の 100px と合わない。
    - --field-w-sm（160px）・--min-width-input-sm（120px）は値が違い、並びが変わる。
  - そのため、新しいトークンを2つ登録する。
    - `--input-width-country-code:    80px;  /* 国コード入力フィールド (FedEx 見積) */`
    - `--input-width-shipping-weight: 100px; /* 発送重量入力フィールド (FedEx 見積) */`
- 囲む枠の px 直書きはトークンに置き換える: :167 の 12px → var(--space-3)。:168 の gap 16px → var(--space-4)、marginBottom 8px は削除（金型の comp-field が下に var(--space-4) を持つため）。:232 の外側の div は削除し、TextField 1つにする（金型の margin-bottom var(--space-4) が今の 16px と同じ）。

AY-2m 変更契約:
1. FedExRateModal.tsx の4組（`<div>` の中の `<label>` と `<input>`）を、それぞれ1つの `<TextField>` に置き換える。
   - label={t("fedexRateModal.originLabel")} など、ラベルの文字は今と同じ t() のキー。
   - id・type・value・maxLength・min・step・placeholder・onChange は逐語で保持（属性の順も保つ）。size は渡さない（md）。
   - style は `{{ width: "var(--input-width-country-code)" }}`（:176,:193）、`{{ width: "var(--input-width-shipping-weight)" }}`（:210）、`{{ width: "var(--field-w-sm)" }}`（:239）だけにする。
   - 3つ並びの組では、外側の `<div>`（:169,:186,:203 の各ラッパー）も TextField に置き換える（TextField 自身が包みの div を持つ）。:232-248 の郵便番号の外側の div も削除し、TextField 1つにする。
   - import に `import { TextField } from "./TextField";` を追加。
2. :167 `marginBottom: "12px"` → `"var(--space-3)"`。:168 → `{{ display: "flex", gap: "var(--space-4)", flexWrap: "wrap" }}`。
3. tokens.css の --input-width-price の次の行に上記2トークンを追加する。
   - docs/adr/ADR-067-design-token-enforcement.md のトークン表に2行を追加する。書き方は AY-2k の --input-width-price と同じにする。
   - ADR-067 を変えたあと、`node scripts/generate-adr-index.js` を実行し、docs/adr/README.md に差分が出たかどうかを記録する（差分があればコミットに含める）。
   - PR 本文には、作成する時点で「### デザイントークン変更時」の節を入れ、check-new-tokens.js が求める4項目を `- [x]` で書く。「既存トークンで代替できないか確認」の項目には、上記の不採用の理由を書く。色のトークンではないので、色の項目はチェックボックスにしない（AY-2k の前例どおり）。
4. 変えないもの: FedExRateModal.tsx の :250 以降（結果の表・バッジ・エラー表示の px 直書きは次の便で扱う）と :1-159 のロジック、Modal・Button、i18n、API、試験、QuoteCreatePage、InventorySearchBar（別の便）、金型本体、backend。既存の試験が落ちたら試験を直さずに止まって報告する。
5. design.md に、AY-2l の本番反映の記録、本節、実装結果を追記。

前後表（予定。実画面で確定）:

| 対象 | 変わる項目 |
|---|---|
| 入力欄4件 | 余白 6px 8px→var(--space-2) var(--space-3)、文字 13px→var(--font-base)、角 4px→var(--comp-input-radius)、背景 var(--bg-surface)、フォーカス時の枠色。幅は今と同じ数値 |
| ラベル4件 | 文字 13px→var(--font-sm)、色→var(--text-secondary)、太さ 500 は同じ（var(--font-weight-medium)） |
| 入力欄と「見積を取得」ボタンの間 | 8px → var(--space-4)（16px） |
| その他（結果の表など） | 変化0 |

受入:

| 基準 | 検証方法 |
|---|---|
| 金型に変わる | 開発モードの build と preview（偽ログイン・API モック）で /quotes/new を開き、FedEx のモーダルを開く。幅1280・1440で変更前と変更後のスクリーンショット（DPR2）。4件の input に class comp-field__input、ラベルに comp-field__label があることを DOM で記録 |
| 文字が切れない | 発送元「JP」、宛先「USA」、重量「12.345」、郵便番号「SW1A 1AA」を入れ、各 input の scrollWidth ≤ clientWidth を前後で JSON に記録する（この4つで合否を決める。切れる場合は担当は止まって実測を報告する）。郵便番号に20文字の値を入れた結果は参考値として記録するだけで、合否に使わない |
| 並び | 3つの欄が1行に並ぶこと（3つの getBoundingClientRect の top が同じ）を前後で記録 |
| 直書き0 | 変更後の FedExRateModal.tsx の、`<Modal` の開始行から `{/* API エラー` のコメントの直前の行までの範囲で、`[0-9]+px` の一致が0件（その範囲を切り出した grep の生出力） |
| 試験 | FedExRateModal.test.tsx が無修正で全件成功。単体試験の全件成功 |
| 品質 | generate 後の tsc、lint、check:all、test:coverage（maxWorkers=1）、build、build-storybook、CI 必須がすべて成功 |
| 本番 | Deploy 成功。本番の JS か CSS に --input-width-country-code の参照がある。app と /api/health が 200 |

外部事例: 不要（既存の金型 TextField を前例どおり使う）。

維持の仕組み:
- 守り手: FedExRateModal.test.tsx、TextField.test.tsx、design-token-guard（check-new-tokens.js）、ui-governance、frontend-check。
- 守っていないもの: FedExRateModal.tsx の :250 以降の px 直書き、InventorySearchBar の生 input 1件、ほかの残り。
- 切戻し: 本 PR の merge commit を revert する（DB への影響なし）。

Architect 審査（AY-2m）: 1回目 REVISE（Fable、2026-10-12）。指摘への対応:
- HIGH（20文字の値を合否に使うかが不明）: 合否は4つの値で決め、20文字は参考値にした。
- MEDIUM（--field-w-sm を使わない理由が無い）: 郵便番号に --field-w-sm を採り、新しいトークンは2つにした。
- MEDIUM（直書き0 の範囲の決め方）: 範囲を行番号ではなく、目印になるコードで決めるようにした。
- MEDIUM（PR 本文のトークンの節が契約に無い）: 契約3に追加した。
- LOW（トークン名）: 重量のトークン名を --input-width-shipping-weight にした。コメントには用途を書いた。
- LOW（ADR の索引）: generate-adr-index の実行と、差分の記録を契約3に追加した。
- LOW（ダークテーマ）: 前例と同じく測らない。
Architect 審査（AY-2m）: 2回目 APPROVE（Fable、2026-10-12）。Fable は AI の審査で、PO 承認や人のレビューではない。残った指摘は LOW の2件。
- PR 本文の色の項目に「色トークンは」という文字列を含めない。AY-2k の PR #4125 と同じ書き方にする。
- 日本語のラベルは 80px より広いため、ラベルの幅で枠の幅が決まる。今も同じ決まり方なので、並びは変わらない。並びは受入の「並び」の項目で確かめる。

## 維持の仕組み
- 守り手: frontend/src/components/FedExRateModal.test.tsx（ラベルと id の結び付き）、frontend/src/components/TextField.test.tsx、frontend/scripts/check-new-tokens.js（トークン追加時の PR 本文検査）、scripts/check-ui-governance.js（生 input の検出）、.github/workflows/frontend-check.yml。
- 守っていないもの: FedExRateModal.tsx の API エラー表示以降の px 直書き、InventorySearchBar の生 input 1件。次の便で扱う。
- 切戻し: 本 PR の merge commit を revert（DB への影響なし）。

## 外部・過去事例の参照と我々への応用
外部事例: 不要。既存の金型 TextField を、前例（AY-2k #4125 の明細入力欄、AY-2e のラベル付き入力）と同じ型で使うため。前例からの応用: 新トークンを足す場合は PR 作成時点で「デザイントークン変更時」節を入れる（AY-2k で本文の後追い編集が CI に読まれなかった学び）。

## 関係する ADR
- ADR-144（UI ガバナンス）: 生 input を金型 TextField へ移す本便の根拠。docs/CC_UI_GOVERNANCE.md の「生 input 禁止」に従う。
- ADR-067（デザイントークン強制）: 幅・余白の px 直書きをトークンへ置き換え、新トークン2件を ADR-067 の表に登録。
- ADR-027（UI 国際化）: ラベル・placeholder は既存の t() キーを逐語で保持し、i18n のキーは追加・変更しない。
- 相互参照: recon は docs/handoff/fedex-rate-modal-inputs/recon.md。
