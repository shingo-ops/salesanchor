# design: 受信箱の登録フォームで会社を作る（ADR-097 §3 の実装）

- 根拠: `docs/adr/ADR-097-sa-customer-registration-form.md` §3（41 行「既存リード情報＋顧客入力B/D ＝ 同期した顧客マスタを自動生成」）・§4（営業担当などの CRM 属性は担当者が後付け）・§6（会社を作る道は登録フォームだけ）。recon: `docs/handoff/register-form-create-company/recon.md`。
- 関連 ADR: ADR-126（請求先名・担当者名の扱い）、ADR-127（登録リンクの段階）、ADR-072（commit 直後に `reset_tenant_context()`）、ADR-1076（会社の状態は `public.customer_statuses` が正本。定数 `STATUS_ACTIVE` を使う）。
- PO 決定: 2026-11-22 チャット「1」（「決まりの書類のとおり、登録フォームが送られたときに、リードの情報から会社を自動で作るようにする」への回答）。

## 1. 目的と利用者に見える変化

- 前: 会社がまだ無いリードに登録リンクを送り、お客様が送信すると「会社情報が見つかりません」で止まる。画面の「新規登録」ボタンは撤去済みなので、新しいお客様の会社を作る道が無い。
- 後: お客様が送信すると、そのリードの会社が無ければその場で 1 件作り、続けて今までどおり請求先・配送先・担当者を入れる。会社がすでにあるリードは今までと同じ動き（会社を作らない）。

## 2. 対象と対象外

- 対象: `backend/app/routers/registration_tokens.py` の `register_customer` だけ。試験を 1 ファイル足す（`backend/tests/test_public_register_company.py`）。
- 対象外: DB の形（migration なし）・フロント（文字も足さない）・住所追加と請求先変更の 2 つの道（会社がある前提のまま）・`POST /companies`・リンクの発行（`create_token`）。

## 3. やり方（カード: `docs/handoff/register-form-create-company/card.md`）

1. トークンを確かめた後、同じリードの会社作りが 2 本同時に走らないように、PostgreSQL のときだけ `SELECT id FROM leads WHERE id = :lead_id FOR UPDATE` でリードの行を押さえる（`is_postgresql(db)` が偽の試験用 SQLite では押さえない）。リードが無ければ今の `company_not_found` と同じ 404。
2. 今の `SELECT id, billing_display_name FROM companies WHERE lead_id = :lead_id` で会社を探す（`ORDER BY id LIMIT 1` を足して、昔の重複があっても 1 件に決める）。
3. 無ければ作る:
   - `name` = リードの `company_name`（前後の空白を除いて空でなければ）→ だめならリードの `customer_name` → だめなら送られた `billing_display_name`。3 つとも空なら 422 `company_name_required`（画面は請求先名が空だと送らないので、ふつうは起きない）。本番の 51 件中 50 件が `companies.name = leads.company_name = leads.customer_name`（recon §3）なので、この順は今のデータの作られ方と同じ。
   - `company_code` は前例（`backend/app/routers/companies.py:401` と 455-459 行）と同じく、仮に `CO-PEND-<8桁>` で入れて、作った直後に `CO-{id:05d}` へ直す。
   - `status` = `STATUS_ACTIVE`（`app.services.customer_statuses`）。`sales_rep_id` などの CRM 属性は入れない（ADR-097 §4: 担当者が後付け）。
   - `tenant_id` はトークンから決めた値（フォームの値は使わない。ADR-097 実装上の注意）。
   - 請求先名の控え（担当者名が空のときに使う）は、作った会社では送られた `billing_display_name` を使う。
4. その後の処理（請求先名の保存・住所・担当者・トークンの使用済み・commit・`reset_tenant_context`）は今のまま。どれかで失敗すれば同じ取引の中なので会社も残らない。
5. 会社を作った回だけ、commit の後に `invalidate_dashboard_cache(tenant_id)` を呼ぶ（`POST /companies` と同じ。数の画面に新しい会社を出すため）。

### 代わりの案と選ばなかった理由

- リンクを発行するときに会社を作る: お客様が送らなかったリンクでも会社が増える。ADR-097 §3 は「送信」で作ると決めている。
- `companies.lead_id` に重複を止める決まりを足す: migration になり、昔の重複の有無を本番で確かめる手間が要る。今回は行を押さえる方法で同時の 2 本を止める。決まりを足すかは別の件（§9）。
- 監査ログを書く: 今の送信の道は監査ログを書いていない（`record_audit_log` は `user_id` が必須で、公開のフォームには利用者がいない）。誰がいつ送ったかは `public.registration_tokens` の `used_at` と `lead_id` で追える。

## 4. リスクと対処

- 同じリンクを 2 回同時に送られて会社が 2 件できる → 手順 1 のリードの行の押さえで後の 1 本は前の 1 本の commit を待ち、そのあと会社を見つけて作らない（使用済みのトークンは住所の既定の重複で 409 になる今の動きのまま）。
- 名前が空で DB の NOT NULL に当たって 500 → 手順 3 の順で決め、全部空なら 422 で止める。
- 会社がすでにあるリードの動きが変わる → 試験 K2 で今までどおりを確かめる。

## 5. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1 会社の無いリードでフォームを送ると 200 になり、会社が 1 件でき、名前がリードの名前・番号が `CO-` の 5 桁・請求先と配送先と担当者がその会社に付く | 足した pytest（CI の backend 試験が緑） |
| K2 会社のあるリードでは会社が増えず、今までどおり住所と担当者が付く | 足した pytest |
| K3 リードの `company_name` が空なら `customer_name` を名前にする | 足した pytest |
| K4 型・lint・ほかの試験がすべて緑 | `gh pr checks` で fail 0 |
| K5 本番に入った | 合流コミットの deploy.yml が success |
| K6 本番で道が通る | 本番の会社の無いリードは 5 件のまま（読むだけで数える）・本番の `GET /api/v1/public/register?token=x` が 403 `invalid_token`（道が生きている）。実際の送信は、PO が次に新しいお客様へリンクを送ったときに会社が 1 件増えることで確かめる（AI は本番のフォームを送らない） |

## 6. 外部・過去事例の参照と我々への応用

不要。理由: 社内の決定（ADR-097 §3）どおりに、同じファイルにある前例（`POST /companies` の番号の付け方・行の押さえ方）を使うだけで、方式の比較が要らない。

## 7. 維持の仕組み

- 足した pytest が、会社を作る行を消すと CI を赤にする。
- ADR-097 §3・§6 が正本。FEATURE-INDEX の会社の行から見張り（`.claude/hooks/requirement-context.py`）が要旨を AI に見せる。
- 守り手: backend/tests/test_public_register_company.py

## 8. 審査

- 2026-11-22 Opus 自己審査: APPROVE。根拠: 変える行は recon §2 で file:line を確かめた。会社の必須の欄は DDL（`backend/app/services/tenant.py:200-230`）で確かめた。名前の順は本番の 51 件で確かめた。migration・フロント・危険なパスは無い。未解決: なし（§9 は別の件）。

## 9. 別の件として残すもの（今回はしない）

- 決まりを読まなかった 1 回（Q10-1）の原因: FEATURE-INDEX 80 行（失敗時の文の行）の「コードの場所」に `frontend/src/features/discord-connect/discordConnectError.ts` が無い（ADR-1071 の 44 行には書いてある）。この便の合流の後に目次へ 1 行足す。
- `companies.lead_id` に重複を止める決まりを足すか。
