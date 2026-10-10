# super admin の初期化と取り消し（手動の SQL。PO の合意があるときだけ）

この文書は何か（1行）: 新しい環境で、アプリの運用者の権限（users.is_super_admin）を、デプロイの自動書き込みではなく、PO の合意のもとで手動の SQL で付ける・外す手順。

親: docs/handoff/neutralize-value-migrations-3c/design.md、recon.md。根拠: ADR-1007 決定1（値の変更の手段のうち「PO 合意の 1 回だけのデータ変更」）。

## 方針（PO 2026-10-07）
- users.is_super_admin は、**アプリの運用者の権限**。**PO と、担当エンジニアだけ**に付ける。**一般のテナントのユーザーには、決して付けない**。
- 以前は migrations/064_add_users_is_super_admin.sql が、デプロイのたびに、指定のメール 1 件のユーザーを super_admin に戻していた（人が外しても戻る）。段3c で、この書き込みを外した。以後、**デプロイでは is_super_admin を書き換えない**。
- アプリ（backend/app、scripts）に、is_super_admin を TRUE にする経路は無い（段3c の確認）。付与できるのは、この文書の手順だけ。

## いつ使うか
- 新しい環境（dev・CI の検証用・新しい本番）で、運用者が /super-admin 配下の操作（operator）を必要とするとき。
- 運用者の追加・交代・取り消しのとき。

## 手順（付与）
1. **PO の合意を、文章で得る**（誰に付けるか。users.id と、理由）。担当エンジニアの追加は、PO の明示の合意が要る。
2. 対象の確認（読み取りだけ。メールは全文を出さない）:
   - `SELECT id, left(email,1) || '***@' || split_part(email,'@',2) AS masked_email, tenant_id, role, is_active, is_super_admin FROM public.users WHERE id = <対象の id>;`
   - 対象が、PO か担当エンジニア本人の users 行であること（PO が目で確認する）。一般のテナントのユーザーでないこと。
3. PO の「psql write」チケット（scripts/permit-danger.sh "psql write"。1 回限り・30 分）を得る。
4. DRY-RUN: 変更する行を先に表示する（書き込みなし）: `SELECT id, is_super_admin FROM public.users WHERE id = <対象の id>;`
5. COMMIT（1 文だけ）: `UPDATE public.users SET is_super_admin = TRUE WHERE id = <対象の id> AND is_super_admin = FALSE RETURNING id;`（件数 1 を確認）
6. 記録を残す（docs/handoff/<topic>/ に、日付・users.id・PO の合意の文・実行者。**メールは書かない**）。
7. 確認: 同じ SELECT で TRUE になったこと。次のデプロイの後も、値が変わらないこと（段3c 以降は、デプロイが書き戻さない）。

## 手順（取り消し）
- 付与と同じ手順で、`SET is_super_admin = FALSE` にする。**取り消しは、次のデプロイで戻らない**（064 の再付与を外したため）。

## してはいけないこと
- migration・スクリプトに、メールや id を書いて、自動で付与すること。
- 一般のテナントのユーザー（role が admin や user のテナント側のユーザー）に付けること。
- PO の合意と psql write チケットなしで実行すること。

## 現在の状態（2026-10-07、本番の読み取り）
- users 10 人のうち is_super_admin が TRUE は 3 人。PO が、3 人の身元（users.id、マスクしたメール、テナント）を確認する（この文書にはメールを書かない）。
