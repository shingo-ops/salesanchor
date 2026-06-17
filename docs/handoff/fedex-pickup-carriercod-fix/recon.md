# Recon: FedEx Pickup API carrierCode 修正

## 対象 ADR

ADR-128（FedEx Ship API / Pickup API 実装）

## 現在地

### 修正ファイル

- `backend/app/services/fedex_ship.py:233-262` — `create_pickup()` ペイロード構造
- `backend/tests/test_fedex_ship.py` — Pickup API ペイロードアサーション追加

### 問題の根拠

FedEx Pickup API v1 の実仕様と実装の乖離を Sandbox 実機テストで確認（2026-06-11/12）。

| フィールド | 旧実装（バグ） | 新実装（正） |
|---|---|---|
| `carrierCode` | `pickupRequestDetail` 内 | トップレベル |
| `totalWeight` | `pickupRequestDetail` 内 | トップレベル |
| `packageCount` | `pickupRequestDetail` 内 | トップレベル |
| `customerCloseTime` | `"HH:MM"` 形式 | `"HH:MM:SS"` 形式（HH:MM 入力は自動変換） |
| `associatedAccountNumberType` | なし | トップレベルに追加 |
| `packageLocation` | なし | `originDetail` 内に追加 |
| キー名 | `pickupRequestDetail` | `originDetail` |

### 関連する ADR 調査

- `docs/adr/ADR-128-fedex-ship-implementation.md` — Ship/Pickup API 実装 ADR（存在確認済み）
- Sandbox 実機テスト確認: `pickupConfirmationCode: "3075"` (2026-06-11), `pickupConfirmationCode: "3084"` (2026-06-12)
