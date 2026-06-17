# 設計 — FedEx Label Validation 通常フロー PDF/A4 一本化

**対象ADR**: ADR-129  
**recon**: docs/handoff/fedex-sandbox-label-validation-smoke/recon.md  
**日付**: 2026-06-17  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 該当なし：今回は既実装（PNG/ZPL追加 PR #2300）の逆操作（運用方針に合わせた除去）であり、
  外部事例を参照して設計するものではない。
  Shingoさんの確定運用方針（A4通常プリンター・熱転写ラベル不使用）に基づく簡素化。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| PDF ラベルが 4 サービス分（IP / IE / IPE / FICP）発行される | `pytest tests/test_shipping_lv.py -v`（8件 PASS） |
| PNG / ZPL ボタンが通常 UI に表示されない | Playwright または手動: FedexLabelValidationTab Step 2 を確認 |
| 既存 PDF 発行が他形式の失敗に巻き込まれない | `pytest tests/test_fedex_ship.py tests/test_shipping_lv.py -v`（22件 PASS） |
| TypeScript 型エラーなし | CI: `tsc --noEmit` |
| `lvStep2DownloadPng` / `lvStep2DownloadZpl` キーが ja.json / en.json から除去済み | CI: i18n キー整合チェック |
| `fedex_ship.create_shipment()` の低レイヤー互換（label_image_type / label_stock_type）は保持 | `pytest tests/test_fedex_ship.py -v` |

---

## 技術 How・KPI

- **KPI**: pytest 22件 PASS（`test_fedex_ship.py` 14件 + `test_shipping_lv.py` 8件）
- **方針**: PR #2300 で追加した PNG/ZPL を除去して PDF × 4呼び出しに戻す。
  低レイヤー（`fedex_ship.create_shipment`）の引数は将来の開発検証用に保持する。
- **i18n**: `lvStep2DownloadPng` / `lvStep2DownloadZpl` を ja/en 両ファイルから削除。
  `lvStep2Desc` を「PDF/A4通常プリンター」向け説明に更新（ADR-027）。

---

## 弊害・トレードオフ

- **PNG/ZPL 発行機能の除去**: 熱転写ラベルプリンター利用ユーザーが今後現れた場合は
  再実装が必要。ただし現在の運用方針では不使用であるため、通常フローからは除外が正当。
  低レイヤー互換を保持することで再実装コストを最小化する。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `LVSampleResult` から png/zpl フィールド削除 | Generator |
| 2 | `lv_issue_sample_labels()` を PDF × 4 に簡素化・`_lv_issue_zpl_with_fallback()` 削除 | Generator |
| 3 | `FedexLabelValidationTab.tsx` から PNG/ZPL ハンドラー・ボタン削除 | Generator |
| 4 | ja/en ロケールから PNG/ZPL キー削除・説明文更新 | Generator |
| 5 | `test_shipping_lv.py` を PDF専用テストに置換 | Generator |
| 6 | `checklist.md` / `recon.md` を PDF/A4 一本化方針に更新 | Generator |

---

## 継続

- 本番 FedEx Label Validation 申請後、PDF/A4 での申請が完了したことを確認する
- 熱転写ラベル対応が必要になった場合は `fedex_ship.create_shipment(label_image_type="ZPLII")` から再実装可
