# design: 顧客情報の「新規登録」ボタンを消す

- 根拠: `docs/adr/ADR-097-sa-customer-registration-form.md` §6（2026-11-21 PO 決定「1」）・recon: `docs/handoff/company-create-button-removal/recon.md`
- 画面の決まり: `docs/adr/ADR-027-ui-internationalization.md`（文字は `t()` 経由・ja/en 同一キー。消すキーは両方同時に消す）、ADR-144（金型の部品を使う。今回は消すだけで新しい部品は足さない）。
- 関連: 要件ライブラリ（`docs/handoff/requirement-library/design.md` 便2c）。ボタンを消すのは 3 回目の 20 回測定のあとに本番へ入れる（測定の条件を変えないため）。

## 1. 目的と利用者に見える変化

- 前: 顧客情報の画面の右上に「+ 新規登録」があり、押すとリード無しで会社を作ろうとして失敗する（裏側が `lead_id` を求める）。
- 後: 顧客情報の画面に「新規登録」ボタンが無い。会社は受信箱から送る登録フォームでお客様が登録する道だけで増える。一覧・検索・行を押して開く編集・削除は今までどおり。

## 2. 対象と対象外

- 対象: `frontend/src/pages/companies/CompaniesPage.tsx`、`frontend/src/components/PageFormButtonMigration.test.tsx`、`frontend/src/locales/ja.json`・`frontend/src/locales/en.json`（使われなくなった `companies.*` キーだけ、両方同時に）。
- 対象外: 裏側の `POST /companies`、連絡先・仕入先の画面、編集 Drawer・`frontend/src/pages/companies/CompanyFormFields.tsx`、DB、本番設定。

## 3. やり方（カード: `docs/handoff/company-create-button-removal/card.md`）

- recon §2 の「はい」の行を消す。`PHONE_RE`〜`type Tab` と import は、消した後に名前ごとに grep し、定義の 1 か所しか残らないものだけ消す。
- `ContentToolbar` の `right` には何も渡さない（属性ごと外す）。
- 試験: 会社の create の組を `cases` から外す。二重送信止めの試験は contact だけにする。電話の試験は消す。代わりに「会社の画面に `companies.newCompany` のボタンが無い」試験を 1 件足す（権限は全部ありの状態で）。
- 文字: 消した後に `git grep -c 'companies\.<key>' -- frontend/src` が 0 になったキーだけ ja/en 両方から消す。

### 代わりの案と選ばなかった理由

- 権限で隠す（`customers.create` を外す）: 連絡先の新規登録も同じ権限で消えるので不可。PO の決定は「撤去」。
- ボタンを残してリード選択を足す: ADR-097 §6 が「直さない」と決めている。

## 4. リスクと対処

- 編集 Drawer が新規作成用の型や関数を共用していて壊れる → 型検査と既存の試験（編集の 3 種）で止まる。消すのは grep で定義だけになったものに限る。
- 使われているキーを消して画面に生のキー名が出る → `frontend/scripts/check-i18n-missing-keys.js` と grep 0 件の条件で止める。
- 測定中に本番へ入って測定の条件が変わる → 3 回目の 20 回測定の結果が出るまで main に合流しない。

## 5. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1 会社の画面に新規登録ボタンが無い（全権限ありでも） | 足した vitest が通る（CI の frontend 試験が緑） |
| K2 編集・取消・失敗時の保持の試験が会社・連絡先・仕入先で今までどおり通る | CI の frontend 試験が緑・`frontend/src/components/PageFormButtonMigration.test.tsx` の会社の edit の組が残っていることを差分で確認 |
| K3 型検査・ESLint・i18n の欠けの確かめが緑 | `gh pr checks` で全部 pass |
| K4 本番に入った | 合流コミットの deploy が success（`gh run list --workflow deploy.yml`） |
| K5 本番の画面コードから消えた | `https://app.salesanchor.jp/` の main の JS で `grep -o newCompany \| wc -l` が 4 → 0 |
| K6 一覧は今までどおり開く | 本番の朝の画面点検（`tests/prod-check/prod-ui.spec.ts` の会社一覧）が次の回も合格 |

## 6. 外部・過去事例の参照と我々への応用

不要。理由: 社内の決定（ADR-097 §6）どおりに画面の入口を1つ消すだけで、方式の選び方に外部の比較が要らない。

## 7. 維持の仕組み

- ADR-097 §6 と FEATURE-INDEX の会社の行の補足に「手で作る道は撤去」と書いてあり、会社のコードを読むと見張り（`.claude/hooks/requirement-context.py`）がその要旨を AI に見せる。ボタンを戻す計画はそこで止まる。
- 足した vitest が、ボタンが戻ると CI を赤にする。
- 守り手: frontend/src/components/PageFormButtonMigration.test.tsx

## 8. 審査

- 2026-11-21 Opus 自己審査: APPROVE。根拠: 消す行は recon §2 で全部 file:line を確かめた。残す機能（編集 Drawer）は別の部品を使い、試験で守られている。裏側は触らない。未解決: 型・関数の一部は「消した後の grep」で決める（カードに手順と止める条件を書いた）。
