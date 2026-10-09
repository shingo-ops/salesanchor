<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — hide-system-admin-role

この文書は、「システム管理者」ロールを通常の会社の画面と操作から隠し、super admin だけが見られるようにする設計です。

親: [../../specs/auth-roles/README.md](../../specs/auth-roles/README.md)

**対象ADR**: ADR-147（追補する）、ADR-1007  
**recon**: docs/handoff/hide-system-admin-role/recon.md  
**仕様書**: docs/specs/auth-roles/（ideal-state.md・kgi.md）  
**日付**: 2026-10-10  
**担当**: Planner / Architect（Opus。同一 AI の自己審査）

状態: 設計案作成済み／自己審査 APPROVE（§審査）／PO 承認済み（2026-10-10 チャット：隠すこと「y」、K1〜K6 で実装に進めることに「y」）／実装着手

**着手の条件**: #4012（system_roles.py と system_key による判定）が main にマージされ、本番に出た後。本設計は #4012 の定数を使う。

---

## 目的（PO に見える変化）
- super admin でない人には、ロール一覧・スタッフ追加・スタッフ編集のどこにも「システム管理者」が出ない。API で直接付けようとしても付かない。
- super admin（PO と担当エンジニア）には今どおり出る。
- ロールそのものは消さない（5社の行と目印 admin は残る）。

## 変更前 → 変更後

| 場所 | 変更前 | 変更後（super admin でない人） | super admin |
|---|---|---|---|
| GET /roles（roles.py:151） | 全ロール | system_key が隠す一覧にあるロールを除く | 全ロール |
| GET/PATCH/DELETE と権限の GET/PUT（_get_role を使う5本） | id があれば返す | 隠すロールは「ロールが見つかりません」（404） | 今どおり |
| GET /users/{id}/roles（roles.py:481） | 全部 | 隠すロールを除く | 全部 |
| PUT /users/{id}/roles（roles.py:495） | priority だけで判定。全消し→入れ直し | 隠すロールの id は「存在しないロールID」（400）。全消しは隠すロール以外だけにする（既に持っている隠すロールを、普通の人の操作で外さない） | 今どおり |
| スタッフ追加（staff.py:545） | 同じ会社にあれば可 | 隠すロールは「指定の role_id はこのテナントに存在しません」（400） | 今どおり |
| スタッフ編集（staff.py:629） | role_id を確かめずに保存 | role_id を送ったとき、同じ会社にあり隠すロールでないことを確かめる（違えば同じ 400） | 存在だけ確かめる |
| 画面（RolesPage・StaffPage・StaffEditPage） | GET /roles を並べる | 変更なし（API が除くので自然に消える） | 変更なし |

## 実装の指示（Generator 向け）
1. #4012 の backend/app/auth/system_roles.py に、隠す目印の一覧を1か所だけ置く：`TENANT_HIDDEN_SYSTEM_KEYS = frozenset({ROLE_KEY_ADMIN})`。名前の文字列（「システム管理者」）でコードを分岐させない。
2. super admin の判定は `bool(getattr(current_user, "is_super_admin", False))`（roles.py:139 と同じ書き方）。
3. `backend/app/routers/roles.py`
   - SQL の絞り込みは `(:show_hidden OR system_key IS NULL OR NOT (system_key = ANY(:hidden_keys)))` の形で、GET /roles・GET /users/{id}/roles・PUT /users/{id}/roles の存在確認と全消しに入れる。show_hidden は super admin のとき真。
   - _get_role は system_key も読む。呼ぶ5本は、super admin でなく隠すロールなら、今の「見つからない」と同じ 404 を返す（見つからない場合と区別しない）。
   - RoleResponse に system_key を足さない（API の形を変えない。frontend/api-contract/openapi.json は変わらない）。
4. `backend/app/routers/staff.py`
   - 追加（:545-551）の存在確認 SQL に同じ絞り込みを足す。
   - 編集（:629 以降）で update_data に role_id が非 NULL で入るとき、追加と同じ確認をしてから保存する。:335 付近の別の update が role_id を書けるかを実装前に読み、書けるなら同じ確認を入れ、書けないなら触らない（どちらだったかを報告に書く）。
5. 文書
   - `docs/adr/ADR-147-common-6roles-standardization.md` に「追補（2026-10-10）：システム管理者は運営者用。super admin 以外には見せず、付けさせない。見分けは system_key=admin」を足し、`node scripts/generate-adr-index.js` を実行する。
   - `docs/ACCESS_CONTROL.md` のロール表（:29）の用途を「運営者用（super admin のみ表示・付与）」に直す。
6. 触らない：frontend（文字列の追加なし＝i18n の追加なし）、migrations、roles の行のデータ、オーナーの扱い、load_user_permissions、cache.py。

## 外部・過去事例の参照と我々への応用
- 外部事例：該当なし。理由：特定の数値に依存しない、権限による一覧の絞り込みの一般的な形であり、他社事例を根拠にする判断が無い。
- 過去事例：運営者メニューは is_super_admin の人だけに出す（`frontend/src/components/DesktopShell.tsx:372`）。同じ「運営者だけに見せる」をロールにも当てる。ただし画面だけで隠すと API から見えるため、API で除く。

## 代替案と選んだ理由
- 画面だけで隠す：API を直接呼べば見え、付けられる。採らない。
- ロールを消す：#4012 の権限の計算と ADR-1007 の目印が使う。新しい会社を作るたびにまた作られる。PO の依頼は「表示させない」。採らない。
- 名前で見分ける：名前を変えると壊れ、ハードコードになる。system_key で見分ける。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| K1: super admin でない人の GET /roles に「システム管理者」が無い | CI pytest（新しい試験 backend/tests/test_roles_hidden_system_admin.py） |
| K2: スタッフ追加・編集のロール選択に出ない | 同上（GET /roles）と Evaluator（Playwright で一般ユーザーのロール一覧・スタッフ追加の選択肢に無いこと） |
| K3: super admin でない人が PUT /users/{id}/roles・スタッフ追加・スタッフ編集で付けようとすると 400、_get_role の5本は 404 | CI pytest（同上） |
| K3b: 普通の人が PUT /users/{id}/roles をしても、相手が既に持つ隠すロールは外れない | CI pytest（同上） |
| K4: super admin は一覧に出て、付けられる | CI pytest（同上） |
| K5: ほかのロールの見え方・付け方は変わらない | 既存の `backend/tests/test_roles.py` と CI 全体 |
| K6: 本番の5社の「システム管理者」1行ずつと system_key=admin が残る | デプロイ後の本番読み取り（5行） |
| API の形が変わらない | CI「API contract is up to date」 |

## 弊害・トレードオフ
- スタッフ編集に role_id の存在確認が新しく入る → 今まで通っていた「存在しない role_id の保存」が 400 になる。正しいデータを守る向きの変化なので受け入れる。
- super admin が一般の会社のユーザーとして「システム管理者」を付けた場合、スタッフ一覧のロール名の列（staff.py の LEFT JOIN）には名前が出る。今は持つ人 0 人。kgi.md の設計送り事項に記録。
- 本番で PO（super admin）が画面を見ても違いは見えない → 画面の確認は Evaluator の一般ユーザーで行う。

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 0 | #4012 のマージと本番反映、本番で権限の数（所有者 123・管理者 122）が変わらないことの確認 | Opus |
| 1 | PO が KGI と実装に y | PO |
| 2 | 実装カードどおりに実装・試験（TDD）。security-reviewer と code-reviewer | Sonnet |
| 3 | CI 緑、Evaluator（Playwright） | Sonnet / Opus 確認 |
| 4 | マージ・デプロイ・K6 の本番読み取り | Opus |

## 継続
- 完了後の監視：新しい会社を作ったとき、隠す目印の付いたロールが一般ユーザーに出ないことを、試験が毎回確かめる。
- 次フェーズへの引き継ぎ：スタッフ一覧のロール名の扱い（設計送り）、super admin 3 人の確認（別件）。

## 審査（Opus 自己審査。独立した第二者レビューではない）
- 判定：APPROVE（設計として実装可能。着手は #4012 の本番反映と PO の y の後）
- 根拠：見える場所3画面と付ける経路3つを recon の行番号で特定し、全部が API を通るので API だけの変更で足りる。見分けは目印で、名前を使わない。API の形を変えない。
- 未解決：なし（super admin 3 人の確認は本設計の外）。

## 維持の仕組み
- 守り手: backend/tests/test_roles_hidden_system_admin.py（実装時に作る。CI の pytest で毎回動く）
- 対象: 隠す目印のロールが、super admin でない人の一覧・付与の経路に戻ってこないこと
- 関所なしの場合: 試験ができるまでは人手で守る（設計担当 Opus）
