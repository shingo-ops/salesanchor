# Design: FedEx Pickup API carrierCode 修正

## 参照

- recon: docs/handoff/fedex-pickup-carriercod-fix/recon.md
- ADR-125（FedEx Rates/Ship/Pickup API 基盤実装）

## 方針

FedEx Pickup API v1 の正式仕様に合わせてペイロード構造を修正する。Sandbox 実機テストで 2 回 HTTP 200 確認済みのため、修正内容は確定。

## 変更設計

### create_pickup() ペイロード構造変更（`backend/app/services/fedex_ship.py:233-262`）

```
旧: pickupRequestDetail: { carrierCode, packageCount, totalWeight, ... }
新: トップレベルに carrierCode / totalWeight / packageCount を配置
    originDetail: { pickupAddressType, pickupLocation, packageLocation, readyDateTimestamp, customerCloseTime }
```

追加フィールド:
- associatedAccountNumberType: キャリアコードに対応（FDXE→FEDEX_EXPRESS, FDXG→FEDEX_GROUND）
- packageLocation: "FRONT"（FedEx API v1 必須）
- customerCloseTime 正規化: HH:MM 入力を HH:MM:SS に自動変換

## 検証基準

| 基準 | 検証方法 |
|---|---|
| Sandbox で HTTP 200 が返る | pickupConfirmationCode が含まれるレスポンスを確認 |
| carrierCode がトップレベルに存在する | `backend/tests/test_fedex_ship.py` アサーション |
| HH:MM → HH:MM:SS 変換が正しい | ユニットテスト |
| associatedAccountNumberType が正しくマッピングされる | ユニットテスト |

## 外部・過去事例

- FedEx Pickup API v1 公式仕様: carrierCode はトップレベル必須フィールド（旧 v0 では pickupRequestDetail 内だった）
- Sandbox 実機確認 2 回: pickupConfirmationCode "3075" (2026-06-11), pickupConfirmationCode "3084" (2026-06-12)

