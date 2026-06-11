# SA-02 段階2 設計: meta_messages → conversation_logs 移行

> ADR-096 参照: conversation_logs を全会話ログの SSOT にする（SA-02 KGI G1）

## What（何をするか）

`meta_messages`（Messenger/Instagram/Discord 受信履歴 = 旧保存先）のデータを
`conversation_logs`（ADR-096 SSOT = 新保存先）にコピーする。

**移行後の状態**:
- `meta_messages`: 変更なし（並走期間は残す）
- `conversation_logs`: meta_messages 由来の行 + 手動記録（段階3）+ 新規受信（段階1）が混在

## Why（なぜ必要か）

- 段階1（PR #1932）で新規受信は `conversation_logs` に入るようになったが、**既存データ（highlife-jpn本番の蓄積分）は `meta_messages` に残っている**
- `v_company_stats` が `conversation_logs` を参照しているため、移行しないと `conversation_count=0` / `last_conversation_at=NULL` のまま
- G1「3ヶ月分の会話ログが conversation_logs に集約される」の実現に必須

## 設計決定

| 決定 | 内容 | 理由 |
|------|------|------|
| meta_messages は削除しない | コピーのみ | 安全なロールバックのため |
| 冪等性 | `external_message_id` UNIQUE + ON CONFLICT DO NOTHING | 再実行可能 |
| message_id なし行 | 合成キー `meta_legacy:{id}` | 古いレコードも移行できる |
| company_id 導出 | `companies WHERE lead_id = mm.lead_id` | leads に company_id 列なし（SSOT は companies.lead_id） |
| contact_id | NULL | meta_messages に contact 情報なし |
| is_manual | false | 自動取り込み行として区別 |

## 検証基準

| 基準 | 検証方法 |
|------|---------|
| coverage 100% | `verify_sa02_stage2_count_check.py` で gap=0 |
| ロールバック可能 | `is_manual=false AND external_message_id LIKE 'meta_legacy:%' OR IN (mm.message_id)` で特定・削除できる |
| 冪等 | 再実行後も件数が変わらない（ON CONFLICT DO NOTHING） |

## 外部事例

- Stripe の `charges` → `payment_intents` 移行: 旧テーブルを削除せず新テーブルにコピー、IDマッピングで冪等性確保（同パターン）
- GitHub issues → discussions 移行: 合成IDで重複防止

## 本番実行チェックリスト（Shingo GO後）

- [ ] VPS上で `--dry-run` を実行し件数を確認
- [ ] `--tenant-id 1`（テスト用テナント）で試し実行
- [ ] 検証スクリプトで確認
- [ ] 全テナントに本実行
- [ ] 検証スクリプトで coverage 100% を確認
- [ ] `v_company_stats` の conversation_count が 0 以外になっていることを会社詳細ページで確認
