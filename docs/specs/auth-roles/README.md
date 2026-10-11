# 認証・権限・ロール（仕様書の表紙）

この文書は、アプリの「ロール（役割）」と「運営者の権限」が、誰に何を見せるべきかの表紙です。

## 概要
- テナント（各社）の中のロール（オーナー・システム管理者・マネージャーなど）と、アプリ全体の運営者（super admin）の境界を決める。
- あるべき姿: [ideal-state.md](ideal-state.md)（PO の言葉のみ）
- KGI: [kgi.md](kgi.md)

## 境界
- 対象: 各社の roles 表のロールの見せ方・付け方、super admin（public.users.is_super_admin）との関係。
- 対象外: 個々の権限キーの中身、ログイン方式、在庫の見える範囲。

## 関連
- ADR-147（共通ロールの標準）、ADR-1007（system_key と所有者・管理者の権限の計算）
- docs/ACCESS_CONTROL.md（現行のロール表）

## ぶら下がる文書（子）
- [../../handoff/hide-system-admin-role/recon.md](../../handoff/hide-system-admin-role/recon.md)
- [../../handoff/hide-system-admin-role/design.md](../../handoff/hide-system-admin-role/design.md)

## ステータス
- 2026-10-10 新規作成。あるべき姿は PO の発言（2026-10-07・2026-10-10）から転記。KGI は PO 承認済み（2026-10-10）。
