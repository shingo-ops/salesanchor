# ADR-137: FedEx ETD / Paperless Trade 連携

## ステータス
**Proposed**（APAC一次回答 受領 2026-06-16 / ローカルCTSによるフィールド確定 待ち）

- Label Validation とは**分離**（Validation は ETD 非依存で先行・PDF/A4。#2322 マージ済 2026-06-17）
- 本ADRは Eva（FedEx APAC API Support）の一次回答を反映済。**確定（Accepted）は、ローカル Customer Technology Specialist による C-Q6（フィールド配線）確認後**とする。

## 背景 / Context
SalesAnchor は FedEx Ship API 連携済（Rates: ADR-125 / Ship・Pickup 実装済 / Label Validation ウィザード: ADR-129）。本ADRは国際出荷のペーパーレス化（ETD = Electronic Trade Documents / Paperless Trade）対応を定義する。

2026-06-16 に FedEx APAC API Support（Eva）へ Q1–Q6 を照会し一次回答を受領。フィールド配線等の細部は「ローカル CTS に繋ぐ」と案内されたため、**確定事実**と**CTS確認待ち**を分離して管理する。

## APAC一次回答（2026-06-16 / Eva）＝確定事実
| Q | 照会 | 回答（確定） | 設計への反映 |
|---|---|---|---|
| Q1 | ETD は Label Validation に必須か | **必須ではない**。Validation はテストラベル提出＋カバーシートで完結。レーザー印刷は PDF で可（ZPL/EPL は熱転写時のみ） | Validation を ETD から**分離**。PDF/A4 で先行。**U1 解決** |
| Q2 | Paperless Trade 有効化の手順 | アカウント設定の有効化は不要。**API キーに Trade Documents Upload API を追加**すれば自動有効化 | G3 を「Developer Portal でキーに当該 API を追加」に簡素化 |
| Q3 | 書類は1回登録・再利用か毎回か | **2系統**。レターヘッド/署名画像＝**1回アップロードして docId 再利用**。出荷ごとの自前書類＝**毎回アップロード・docId 使い捨て（2回目の出荷へ流用不可）** | J1/J2 を2系統に分離。前者のみ DB 保存・再利用 |
| Q4 | docId の有効期限 | レターヘッド/署名の docId は**無期限** | リフレッシュ機構 不要。**U4 解決** |

## CTS確認待ち（APACでは未回答 / ローカルCTS経由）
| # | 内容 | 影響 |
|---|---|---|
| C-Q5 | ETD 対応の origin/destination 国リスト | 対応国の出荷可否判定 |
| C-Q6 | ETD インボイス提出に必要な Ship API フィールドの正確な組み合わせ（`shippingDocumentSpecification` / `etdDetail` / `requestedDocumentCopies` / `uploadedDocuments`）＋ `stampType`（INCLUSIVE/EXCLUSIVE） | **J3 のコード確定。本ADR確定の最終ゲート** |
| C-Q7 | ETD 固有のエラーコード・リトライ・レート制限 | エラーハンドリング設計 |

→ **解除アクション**: FedEx Sales Rep 経由でローカル Customer Technology Specialist をアサイン（別途メール送付）。

## 決定 / Decision
| # | 内容 |
|---|---|
| J1 | `fedex_etd_images` テーブル新設。**レターヘッド/署名画像 専用**（1回登録・再利用・無期限）。`UNIQUE(tenant_id, image_type, environment)`。出荷ごとの自前書類は本テーブルに**保存しない**（使い捨てのため） |
| J2 | レターヘッド/署名: 1回アップロード→docId を DB upsert。出荷ごとの自前書類（インボイス等）: 出荷時に Trade Documents Upload API でアップロードし、docId は単発使用・**永続化しない** |
| J3 | `fedex_ship.py:112-133` の requested_shipment に `etdDetail` 追加（未登録テナントはオプショナルで従来通り動作）。**正確なフィールド集合は C-Q6（CTS）確定後に確定** |
| J4 | Label Validation ウィザードタブ内に「ETD 書類登録」UI（レターヘッド＋署名＋環境セレクタ） |

## Shingo GO 必須 / 危険変更
| # | 変更 | GO条件 |
|---|---|---|
| G1 | `migrations/YYYYMMDD_add_fedex_etd_images.sql` 追加 | Shingo「GO: Shingo YYYY-MM-DD」（テーブルは Q3/Q4 で確定済のため CTS 非依存。**適用のみ** GO 待ち） |
| G2 | `deploy.yml` migration ステップ追記 | G1 と同一PR |
| G3 | FedEx 側 Paperless Trade 有効化 ＝ **Developer Portal で API キーに Trade Documents Upload API を追加** | Shingo 直接操作（アカウント設定の有効化は不要） |
| G4 | 本番切替 | Sandbox PASS ＋ Shingo 確認 |

※ `etdDetail` のコード追加（J3）は通常PR・危険変更なし。

## 実装フェーズ
- **E1a**: APAC 一次回答 → 受領済（2026-06-16）
- **E1b**: ローカル CTS による C-Q6 フィールド確定 → **待ち**（Sales Rep 経由で依頼）
- E2: migration / Shingo GO（G1・G2）
- E3: BE（J1・J2。J3 は E1b 後に確定）
- E4: FE（J4）
- E5: Sandbox 確認
- E6: 本番 FedEx 設定（G3・Shingo 直接）
- E7: 本番デプロイ（G4）

## 未解決（Shingo判断）
- **U2**: 本ADRの正式起案タイミング → 本更新で **Proposed として起案**、CTS 確定後に Accepted へ昇格
- **U3**: ADR 番号 = **ADR-137**（現最終 ADR-136 の次）。正式追加時に `node scripts/generate-adr-index.js` で索引再生成
- **U5**: Label Validation 本番申請タイムライン → **ETD と分離して即提出可**（PDF＋カバーシート、3営業日）

## Consequences
- Validation と ETD を分離したことで、Validation は本日時点で提出可能（外部クロック：審査3営業日）。
- ETD は骨格（J1/J2/J4・G3）を **CTS 非依存で先行実装**でき、J3 のフィールド確定のみ CTS 待ち。
- レターヘッド/署名は無期限・再利用 → テナント単位の1回登録 UX が成立。出荷書類は使い捨てのため、**誤って再利用しないガード（poka-yoke）を実装で担保**すること。
