-- 会社と連絡先の状態の4行（設計 docs/handoff/status-ssot-contact-company/design.md §4）
-- この4行の値を書くのはこのファイルだけ。本番への投入（run-insert.sh）も、試験の準備（backend/tests/seed_data.py・便2）も、このファイルを読む。
-- 冪等: 同じ code の行があれば何もしない。書けるのは運営だけ（RLS・呼ぶ側が SET LOCAL app.is_operator='true' を付ける）。
INSERT INTO public.customer_statuses (code, name_ja, name_en, sort_order, is_active, selectable_on_create) VALUES
  ('active',               '有効',         'Active',                  10, TRUE, TRUE),
  ('inactive',             '無効',         'Inactive',                20, TRUE, TRUE),
  ('archived',             'アーカイブ',   'Archived',                30, TRUE, TRUE),
  ('pending_dedup_review', '重複確認待ち', 'Pending duplicate check', 40, TRUE, FALSE)
ON CONFLICT (code) DO NOTHING;
