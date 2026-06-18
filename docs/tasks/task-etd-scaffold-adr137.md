# Task: ETD骨格コード実装（CTS非依存分）— ADR-137 基盤

**ブランチ**: feature/morimoto/etd-scaffold-adr137  
**担当**: Hikky-dev  
**起案日**: 2026-06-18  
**状態**: ECC Clarify 待ち（C-Q1: FedEx Trade Documents Upload API エンドポイント確認待ち）

## 目的

ADR-137（Proposed）のうち、CTS回答・Shingo GOに依存せず先に書ける骨格を実装する。
「CTS回答が来たらJ3のフィールドを埋めてフラグONするだけ」=発射準備完了の状態にする。

## ゲート（厳守）

- migration は作成のみ・deploy未wiring・未適用（G1/G2はShingo GO後の別PR）
- J3（etdDetail）のフィールドは確定しない。C-Q6（CTS回答）待ちのためdormant実装
- 機能はフラグでデフォルトOFF。本番フロー無影響
- author=shingo-cc、PR body非パス識別子はバックティックで囲まない

## スコープ

| # | 内容 | 状態 |
|---|---|---|
| S1 | migration ファイル作成（J1・適用しない） | 待機 |
| S2 | レターヘッド/署名アップロード BE+エンドポイント（J2a） | **C-Q1待ち** |
| S3 | ETD書類登録UI（J4・既定非表示） | 待機 |
| S4 | etdDetail dormant 追加（J3・CTS待ち） | 待機 |
| S5 | poka-yoke ガード（使い捨てdocId再利用禁止） | 待機 |

## Clarify ブロック

### C-Q1: FedEx Trade Documents Upload API エンドポイント

既存外部調査では `POST /ship/v1/shipments/images` を示唆。
しかし Eva (APAC) は「Trade Documents Upload API をAPIキーに追加」と言及しており、
Ship API とは別の独立したAPIである可能性が高い。

**公式ドキュメントで確認すべき内容**:
- エンドポイントURL（`/ship/v1/shipments/images` か `/documents/v1/etds/upload` 等か）
- imageType パラメータ名（LETTER_HEAD か LETTERHEAD か）
- リクエスト形式（multipart/form-data か base64 JSON か）
- レスポンスの docId フィールド名

**影響**: S2 の API コントラクト確定に必要。コードは書けるがSandbox疎通前に確認要。

## 参照

- ADR-137: docs/adr/ADR-137-fedex-etd-paperless-trade.md
- recon: docs/handoff/etd-scaffold-adr137/recon.md
- design: docs/handoff/etd-scaffold-adr137/design.md
