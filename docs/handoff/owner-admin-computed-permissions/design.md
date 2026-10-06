# 設計：所有者と管理者の権限の計算と、テナント作成の完全化（ADR-1007 段1 の PR-1b、2026-10-05）

状態：設計案作成済み／Opus 自己審査 APPROVE（§7）／PO 承認済み（2026-10-05「権限の計算：はい」「system_key：はい」、ADR-1007）。認可のコードを変える危険な PR なので、マージには PO の「GO #番号」が要る（ADR-136）。

**マージの条件（必須）**：PR-1a（#3986）が本番に出て、データの変更（既存の5社に system_key）を流した後でしか、マージしない。理由は §6 の1行目。

## 1. 目的（PO に見える変化）
- 画面の見た目は変わらない。
- 所有者は全部の権限、管理者は system.manage 以外の全部の権限を、権限の表から毎回計算する。今後権限を足しても、配る手順なしで届く。
- 新しく作ったテナントが、デプロイ（migration の流し直し）を待たずに、完全な設定になる。
  - 表計算の連携の段階は B
  - システム管理者はシステムの役割
  - 目標の権限がある
  - system_key がある

## 2. 現在地（recon.md の要約）
- 権限の確かめは load_user_permissions の1か所で行い、ユーザーの役割の付与の和集合を使う（backend/app/auth/dependencies.py:486-546）。画面のメニューも /me/permissions を通じて同じ結果を使う。
- 所有者と管理者の付与は、毎回流れる migration 025 が後から配っている。
- テナントの作成（backend/app/services/tenant.py）は、次の状態で作っていて、migration 080・023・075 が次のデプロイで直している。
  - phase が 'A'
  - システム管理者の is_system が False
  - goals の付与が無い
- 所有者と管理者の役割は、画面や API から付与を直せない（roles.py:393-398）。

## 3. 既存の ADR との関係
- ADR-1007 の決定3（テナントの作成の完全化）・決定4（権限の計算）と、実施順序の段1 にあたる。
- ADR-155：値を migration で扱わない。この PR は migration を足さない（列は PR-1a で入る）。

## 4. 変更
- 新規：backend/app/auth/system_roles.py
  - ROLE_KEY_OWNER・ROLE_KEY_ADMIN・SYSTEM_MANAGE_KEY の定数を置く。除く権限の名前は、ここだけで定義する。
  - compute_permission_keys：保存済みの付与に、所有者・管理者の計算結果を union で加える純粋な関数。
- backend/app/auth/dependencies.py の load_user_permissions
  - 今の付与の和集合の問い合わせは、そのまま残す。
  - ユーザーの役割の system_key を読み、owner か admin があれば、public.permissions の全件から計算した集合を union で加える。
  - users.role='admin' の予備の扱いは変えない。
- backend/app/services/tenant.py
  - 作成時に system_key を書く（既にあれば上書きしない）。
  - システム管理者を is_system=True にする。
  - spreadsheet_phase を 'B' にする。
  - goals.view・goals.edit を付与する。
  - 'system.manage' の直書きを、定数にする。
- 試験
  - backend/tests/test_system_roles.py：DB なしで純粋な関数とテナントの定義を確かめる。8つの場面と、テナントの作成の状態。
  - backend/tests/test_permission_resolution_pg.py：本物の load_user_permissions を、CI で動く RLS_ADMIN_DATABASE_URL の PG で確かめる。所有者・管理者・CS、管理者＋system.manage を付与した別の役割（union）、新しく足した権限が行なしで届くこと、作成の状態。
- 触らない
  - 画面（RolesPage など）
  - 在庫の見える範囲の router
  - roles.py
  - 既存の role_permissions の行（残し、所有者・管理者の計算には使わない）
  - migration 023・025・075・080（段3 で扱う）
  - cache.py

## 5. 代替案と選んだ理由
- 付与を1行ずつ持つ今の形：権限を足すたびに配る手順が要る。025 の流し直しへの依存も残る。PO が計算の形を選んだ。
- 表示名で見分ける：名前の変更に弱く、ハードコードになる。PO が system_key を選んだ。
- 管理者には、ほかの役割の付与も含めず、決まった集合だけを返す：今の「役割の付与の和集合」という動きと変わってしまう。そのため union にした（Opus が今の動きに合わせて決めた）。

## 6. リスクと対処
| リスク | 対処 |
|---|---|
| デプロイでは、コードの切り替えが migration より先に動く（.github/workflows/deploy.yml:376, :500）。system_key の列が無いうちにこのコードが動くと、権限を確かめるすべての問い合わせが失敗する（500） | PR-1a が本番に出て、列があることを読み取りで確かめ、データの変更を流した後でしか、この PR をマージしない（PR の本文に明記） |
| この PR は PR-1a の上に積んでいて、PR-1a の差分を含む | PR-1a を先にマージする。その後に main を取り込むと、この PR の差分はこの PR の分だけになる |
| 権限の結果は5分間使い回される（cache.py:18 の TTL 300秒） | 切り替えの後、最大5分で新しい計算になる。結果は今と同じ集合（所有者 123・管理者 122）なので、ずれは起きない |
| 1回の確かめで、問い合わせが最大2本増える（キャッシュが無いとき） | 小さな表への問い合わせである。キャッシュで吸収する |
| 計算の結果が今と違ってしまう | 本番の所有者 123・管理者 122 は、計算の結果と同じ。切り替えの後に読み取りと画面で確かめる |

## 7. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| 所有者は全部、管理者は system.manage 以外の全部の権限。ほかの役割の付与は union で残る | test_system_roles.py（手元で通る）と、test_permission_resolution_pg.py（CI） |
| 新しく足した権限が、role_permissions の行なしで所有者と管理者に届く | test_permission_resolution_pg.py（CI） |
| 新しいテナントが phase B・is_system・goals・system_key を持つ | test_system_roles.py と、test_permission_resolution_pg.py |
| ふつうの役割の結果が変わらない | 同上と、既存の test_roles.py |
| 関連の試験が通る | pytest（担当の実行では 53 passed, 10 skipped） |
| 本番で、所有者と管理者の権限の数が変わらない | 切り替えの後、/me/permissions の件数を読み取りで確かめる |

## 8. 外部・過去事例の参照と我々への応用
- 外部事例：決まった役割（所有者・管理者）の権限をコードで決め、カスタムの役割だけを表で持つのは、役割による権限の管理（RBAC）で一般的な形である。特定の数値には依存しないため、外部の事例は挙げない。
- 過去事例：権限の和集合で判定する今の作り（Discord 方式、dependencies.py:495）を変えずに、所有者・管理者の分だけを計算で足した。

## 9. 維持の仕組み
- 守り手: 設計担当（Opus）。権限を足したときに、所有者と管理者に届くことを、CI の PG の試験で毎回確かめる。
- 除く権限の名前は、system_roles.py の定数の1か所に限る。
