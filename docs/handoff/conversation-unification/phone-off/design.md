# 連絡手段の名簿から「電話」「対面」を全社で外す（設計）

- 状態: 設計案（Opus 作成）。PO の依頼 2026-11-08「3」（全社の名簿から外す）に基づく
- 親テーマ: 会話の一本化（docs/handoff/conversation-unification/design.md）

## 1. 目的と利用者に見える変化

- 変更前: 受信箱の「手動記録」のチャネル欄、リードのチャネル欄、管理画面「連絡手段」に「電話」「対面」が出る（全社共通の行 id=10 phone・id=11 in_person）
- 変更後: 全社で「電話」「対面」が出なくなる。WhatsApp ほか 4 行はそのまま

## 2. 成功条件（○×で判定）

| 基準 | 検証方法 |
|---|---|
| K1 名簿の共通行のうち使える行が messenger・instagram・discord・whatsapp の 4 行だけ | reader 鍵で `SELECT id, platform, is_active FROM ai_ro.public__channel_masters ORDER BY id` → id 10・11 が is_active=false、7・8・9・12 が true |
| K2 共通行の総数は 6 のまま（行を消さない） | 同上の行数 = 6 |
| K3 リードで phone・in_person を使っている件数が 0（外しても保存が壊れない） | 5 社の leads.channel_type 集計 = 0（実施前後） |
| K4 会話の数（meta_messages）が前後で同じ | 5 社の meta_messages 件数を実施前後で比べ差 0 |
| K5 戻すと元の形に戻る | rollback.sql の検査（id 10・11 が true）を dryrun 内で確認 |

## 3. 現在地（観測事実・2026-11-08 09:45 JST・reader 鍵）

- 名簿: id 10 phone 電話 manual is_active=true / id 11 in_person 対面 manual true / id 12 whatsapp manual true（/tmp/CC報告ファイル/conv/ch-m.txt）
- 会社ごとの設定: tenant 1・master 10・is_hidden=false の 1 行だけ（ch-s.txt）
- leads.channel_type が phone/in_person: 5 社とも 0 行（pi-q1.txt）
- meta_messages.platform が phone: tenant 004 の 1 行（id 109・本文「Codex translation smoke 2026-06-18 21:00 JST」＝試験の記録）。in_person 0（pi-q2.txt）
- conversation_logs.channel_type が phone: tenant 004 の 1 行（id 6・同じ試験記録の元）（pi-q3.txt）

## 4. コードの実物（origin/main）

- 「外す」の既存の表し方は `is_active = false`: backend/app/routers/conv_logs.py:585-615（会社の行の削除は is_active=false にする）
- 名簿の読み出しは全部 is_active=true で絞る: backend/app/services/channel_masters.py の list_channels（画面一覧・選択欄）・get_channel（記録の作成 conv_logs.py:212、リード保存 leads.py:205）・conversion_items・platforms_by_store
- 言語判定 backend/app/services/lang_judge.py:33-37 は is_active を見ずに is_verbatim=FALSE の行で除外。行を残すので判定は変わらない（K4 系の数が変わらない根拠）
- phone・in_person の値を直書きしたコードは無い（git grep。ChannelTypeCombobox.stories.tsx:11-12 は見本データ、ja.json の contactChannels.channels.phone は別機能「連絡先リンク」）
- 値は migration で書かない決まり（ADR-1007・backend/tests/test_value_migrations_neutralized.py）。前例 docs/handoff/conversation-unification/data-store/ と同じ「手順一式を PO 権限の鍵で流す」形にする

## 5. やること（対象）

- docs/handoff/conversation-unification/phone-off/ に run.sh と precheck・dryrun・commit・verify・rollback の SQL を置く（data-store/ と同じ形）
- commit: `UPDATE public.channel_masters SET is_active=false, updated_at=now() WHERE id IN (10,11) AND tenant_id IS NULL AND platform IN ('phone','in_person') AND is_active=true;` の後、共通行で is_active=true が 4 行・総数 6 行でなければゼロ除算で止める
- rollback: 同じ 2 行を is_active=true に戻す

## 6. 対象外

- 行の削除（DELETE）・会社ごとの設定行（tenant 1 の 1 行）の削除: 戻せなくなるのでしない
- 試験の記録 1 件（tenant 004）: そのまま残す（試験の記録で、外しても表示は残る）
- コード・画面の部品・文言の変更: 不要（名簿の値だけで画面が変わる＝配線の正本は名簿 1 か所）
- 会社が自分で「電話」を足し直すこと: 管理画面の追加（conv_logs.py:503-530）で会社用の行として足せる。これは会社の判断として許す

## 7. 代替案

- A 画面で隠す（会社ごとの is_hidden）: 会社の数だけ行が増え、正本が分かれるので不採用
- B 行を消す: 戻せず、会社ごとの設定行の外部キーにも当たるので不採用
- C is_active=false（採用）: 既存の「外す」と同じ意味・1 文で戻せる

## 8. リスクと対処

- 外した手段のリードが保存できなくなる → 現在 0 件（K3）。値を変えないリード保存は leads.py:202 の既存値の通し道で通る
- 本番の書き込み → lock_timeout 5s・数の検査が合わないと COMMIT に届かない・rollback を用意

## 9. 維持する仕組み

- 名簿の正本は public.channel_masters の 1 か所。画面は名簿を読むだけなので、足す・外すは今後も名簿の値の手順で行う

## 10. 外部事例

- 不要: 既存の表の 1 列を既存の意味で切り替えるだけで、外の事例が判断を左右しない
