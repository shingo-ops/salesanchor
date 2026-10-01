# recon: 担当者アイコン登録・英語名必須化（ADR-159 便A）

実測基準: origin/main b3235f5f8（2026-10-01）。事実のみ。

## 既存 ADR 検索（着手前）

- git grep -i "avatar\|webhook" docs/adr/ と docs/adr/FEATURE-INDEX.md を確認。担当者アイコン・英語名必須を決めた既存 ADR は無し。
- 関連: docs/adr/ADR-091 系（Discord Bot 権限。MANAGE_WEBHOOKS を将来機能として許容）、ADR-072（commit 後 reset_tenant_context）、ADR-027（i18n）、ADR-144（UI 金型ガバナンス）、ADR-067（デザイントークン）。
- 新規: docs/adr/ADR-159-staff-identity-on-discord.md（ADR-159 は origin/main・open PR で未使用を確認済み）。

## 事実（file:line はリポジトリルート相対のフルパス）

- staff 表に avatar 列なし: backend/app/services/tenant.py:586-607（CREATE TABLE staff）。phone 列も同テンプレートには無く migration で追加する慣例: migrations/083_add_staff_phone.sql
- given_name_en / surname_en は全スキーマで任意だった: backend/app/schemas/staff.py（StaffCreate / StaffUpdate / StaffProfileUpdate）
- staff の INSERT は 1 箇所のみ（招待・登録経路で英語名なしの作成は無い）: backend/app/routers/staff.py:417（create_staff）。grep "INSERT INTO staff" backend/app の実測結果は当該 1 件。
- 本人特定は primary_email 一致・ORDER BY id ASC: backend/app/routers/staff.py（get_my_staff / update_my_profile）
- 認証不要ルーターの前例: backend/app/main.py:219-232（health / auth / webhook / meta / contact / registration_tokens.public_router）
- 添付保存ルート ATTACHMENT_ROOT（既定 /data/attachments）: backend/app/routers/leads.py:1375、backend/app/discord_gateway/ticket_channel_writer.py:38。docker ボリューム attachments_data: docker-compose.yml:127
- 絶対 URL のベース設定の前例 API_BASE_URL（既定 https://api.salesanchor.jp）: backend/app/routers/invoices.py:589
- 422 でないコード付きエラー詳細の前例 detail={"code": ...}: backend/app/routers/tcg_analysis_review.py:202
- フロントの API クライアントは ApiError.responseDetail に detail を保持、multipart は api.postForm: frontend/src/lib/api.ts（ApiError / requestForm / api.postForm）
- アカウント設定のプロフィール: frontend/src/pages/account-settings/ProfileSection.tsx。スタッフ作成: frontend/src/pages/staff/StaffPage.tsx、編集: frontend/src/pages/staff/StaffEditPage.tsx
- UI ガバナンス: 禁止は生 select / 生 input（type=text|search|省略）/ 自作タブ / 色直値。type="file" は検出対象外: scripts/check-ui-governance.js:166-215、docs/CC_UI_GOVERNANCE.md
- 金型作法 Xxx.tsx + Xxx.css(var()のみ) + Xxx.stories.tsx、stories の存在は CI 検査: frontend/scripts/check-stories-count.js
- Pillow は backend/requirements.txt に未導入（本便で Pillow==12.3.0 を追加）。Dockerfile は python:3.12-slim（backend/Dockerfile:1）で manylinux wheel を利用
- migration の登録: scripts/run_all_migrations.sh（末尾に run_sql 追記が慣例）。CI の migration-test.yml は tenant_001.staff の最小スタブ（id, tenant_id, user_id, full_name, is_active …）を持ち、DO ブロックの ALTER TABLE ADD COLUMN IF NOT EXISTS はそのまま通る（スタブ変更不要）
- テスト用 staff 表は backend/tests/conftest.py の setup_test_db に集約（avatar_token 追加が必要）
- backend/tests/test_adr072_phase_2_reset_rollout.py は staff.py の reset_tenant_context 呼び出し数を固定（4 → 6 に更新が必要）

## 未確認

- 本番ボリューム attachments_data の空き容量（アイコンは 1 件あたり数 KB の想定）
- Discord 側が WebP の avatar_url を表示できること（便B の実機確認で検証）
