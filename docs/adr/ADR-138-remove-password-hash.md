# ADR-138: password_hash 列廃止

**ステータス**: Accepted  
**決定日**: 2026-06-12  
**決定者**: Shingo（PO）  
**実装**: PR #2067

---

## 背景

`public.users.password_hash` 列は bcrypt ハッシュを格納していたが、  
ログイン認証は Firebase Authentication が全担当しており、DB のハッシュは  
認証フローのどこでも読み取られていない（`verify_password` は未呼び出し）。  
不要なパスワードハッシュを保持し続けることは攻撃面の無駄な拡大となる。

## 決定

`public.users.password_hash` 列を物理削除する。

- コード側: `hash_password` / `verify_password` 関数、`UserRegister.password` フィールド、  
  各スクリプトの INSERT/UPDATE 対象列をすべて除去
- DB 側: `ALTER TABLE public.users DROP COLUMN IF EXISTS password_hash`（冪等 migration）

## 結果

- ハッシュ漏洩リスクがDB構造から消える
- `UserRegister` スキーマからパスワードフィールドが消え、登録フローが Firebase 専一になる
- `bcrypt` ライブラリの不要な依存が解消される（requirements は別 PR で整理）

## デプロイ保証

通常 CI/CD パイプラインでは blue-green cutover（deploy.yml:322）が先行し、  
`run_all_migrations.sh`（deploy.yml:423）はその後に実行される。  
DROP COLUMN 実行時点で新コード（`password_hash` 参照なし）がすでに稼働しているため  
500 エラーウィンドウは発生しない。

## 関連

- recon: `docs/handoff/password-hash-removal/recon.md`
- 設計: `docs/handoff/password-hash-removal/design.md`
