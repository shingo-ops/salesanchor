# Phase 3 設計 — FedExRateModal 見積書作成ページ導線接続

**対象ADR**: ADR-125
**recon**: docs/handoff/fedex-modal-connection/recon.md
**日付**: 2026-06-10
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 該当なし：今回は既存の FedExRateModal コンポーネントと QuoteCreatePage を接続する UI 配線のみ。新規APIや外部サービスの追加はなく、外部事例の参照は不要と判断。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 見積書作成ページの送料欄横に「FedEx見積もり」ボタンが表示される | 目視確認 / `data-testid="fedex-estimate-btn"` の存在 |
| ボタン押下で FedExRateModal が開く | ユニットテスト `FedExRateModal.test.tsx` |
| モーダル内に宛先国コード入力欄が表示される | ユニットテスト: `getByLabelText("Destination country code")` |
| モーダル内に重量入力欄が表示され、totalWeight が初期値として入る | ユニットテスト: `weightKg prop is used as initial weight value` |
| 重量を手動変更すると変更後の値で API が呼ばれる | ユニットテスト: `edited weight is sent to the API, not the original prop` |
| 料金選択で送料欄に金額が自動入力される | ユニットテスト: `selecting a rate calls onSelectRate` |
| FedEx 未連携時は設定ページ誘導リンクが表示される | ユニットテスト: `shows settings link when live_error includes the not-connected marker` |
