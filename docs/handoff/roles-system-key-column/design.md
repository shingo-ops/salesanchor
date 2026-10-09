# 設計：roles.system_key の列の追加（ADR-1007 段1 の PR-1a、2026-10-05）

状態：設計案作成済み／Opus 自己審査 APPROVE（§7）／PO 承認済み（2026-10-05「system_key：はい」、ADR-1007）。migrations を含む危険な PR なので、マージには PO の「GO #番号」が要る（ADR-136）。

## 1. 目的（PO に見える変化）
- 画面の見た目は変わらない。
- 所有者と管理者の役割を、表示名ではなく変わらない目印（system_key = 'owner' / 'admin'）で見分けられるようにする。
- これは、権限をコードで計算する PR-1b の前提になる。

## 2. 現在地（recon.md の要約）
- テナントの roles の表にあるのは、name・priority・is_system だけで、変わらない目印は無い（backend/app/services/tenant.py:485-496）。
- 所有者と管理者を見分けられるのは、日本語の表示名（オーナー・システム管理者）だけである。
- テナントの表の定義は2か所にある：tenant.py（新しいテナント）と、migrations の tenant のループ（既存のテナント）。

## 3. 既存の ADR との関係
- ADR-1007 の決定4（system_key で計算する）と、実施順序の段1 にあたる。
- ADR-155 と ADR-1007 の決定1：この PR は構造の変更だけで、値を書かない。値は別の「データの変更」で入れる（docs/handoff/roles-system-key-data/）。

## 4. 変更
- migrations/20261005_150000_add_roles_system_key.sql
  - 全テナントの roles に `system_key TEXT` を足す。
  - 部分一意の索引 `uq_roles_system_key`（system_key IS NOT NULL）を作る。
  - COMMENT を付ける。
  - 何度流しても同じ結果になる（IF NOT EXISTS）。値は書かない。
- scripts/run_all_migrations.sh の末尾に登録する。
- backend/app/services/tenant.py の roles の定義に、同じ列と索引を足す（新しいテナント用）。
- 試験：backend/tests/test_roles_system_key_ddl.py
- データの変更の準備（実行しない）：docs/handoff/roles-system-key-data/
  - 既存の5社に 'owner'・'admin' を入れる。
  - 件数の照合、DRY-RUN、rollback を用意する。
- 触らない：load_user_permissions（PR-1b）、role_permissions の行、画面。

## 5. 代替案と選んだ理由
- 表示名で見分ける：名前の変更に弱く、ハードコードになる。PO が system_key を選んだ。
- migration で値も入れる：ADR-155 と ADR-1007 に反する。

## 6. リスクと対処
| リスク | 対処 |
|---|---|
| デプロイでは、コードの切り替えの後に migration が流れる（.github/workflows/deploy.yml:376, :500） | この PR のコードは、新しい列を読まない（tenant.py の定義に足すだけ）。そのため、どちらが先でも害は無い |
| 新しいテナントの定義と、既存のテナントの migration の2か所で、食い違う | 試験で、tenant.py の定義に列があることを確かめる。migration の側は CI の Migration SQL Test で確かめる |
| 一意の索引で、既存の行とぶつかる | 列は新しく足すので、値は全部 NULL である。部分一意の索引なのでぶつからない |

## 7. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| 全テナントの roles に system_key と索引がある | デプロイの後に、本番で information_schema と pg_indexes を読み取りで確かめる |
| 新しいテナントの定義に、同じ列がある | test_roles_system_key_ddl.py |
| 値の書き込みが無い | migration-guard の Check 7・8 と、差分の目視 |
| 関連の試験が通る | pytest（担当の実行では 40 passed, 9 skipped。PG の試験は CI で動く RLS_ADMIN_DATABASE_URL を使う） |

## 8. 外部・過去事例の参照と我々への応用
- 外部事例：サロゲートの目印（コードで扱う変わらない値）と、表示名を分けるのは一般的な設計である。特定の数値には依存しないため、外部の事例は挙げない。
- 過去事例：migrations/20261001_120000_add_staff_avatar_token.sql の、テナントのループで列を足す形にならった。

## 9. 維持の仕組み
- 守り手: 設計担当（Opus）。データの変更の後と PR-1b の後に、本番の読み取りで system_key の件数（5社×2）を確かめる。
