# 共有 DB の後片付けを札の外で流す試験を止める見張り — 設計

前のテーマ: docs/handoff/ci-test-shared-collisions/（design §10・recon §6-5 で、このテーマを別に回した）。

## 1. 目的（KGI・PO 2026-11-27「1」で承認）

| # | 基準 | 検証方法 |
|---|------|---------|
| G1 | 新しい見張りの試験が main で pass する | 合流後の main の Backend Tests で、その試験が passed |
| G2 | 当たった関数のうち、分類が書かれていないものが0件 | 見張りの試験の中の分類表と、機械で探した一覧の差が0（試験が自分で数える） |
| G3 | わざと札の外で後片付けをする関数を足すと、見張りが赤になる | 見張りの試験の中に、仮の文字列を読ませて落ちることを確かめる試験を置く |
| G4 | 共有 DB で札の外にあったものは、全部札の中へ移す | 分類表に「共有 DB・札の外」が0件 |
| G5 | 変えるのは試験コードだけ | `git diff --name-only origin/main...HEAD` に backend/tests/ と docs と台帳しか無い |
| G6 | passed の数は main と同じ＋見張りの分だけ。skipped は main と同じ | PR の CI の pytest の要約行を main と比べる |

分類は3つ: 使い捨て（own_database・SQLite・文字として読むだけ）／札の中（public_bootstrap_lock か同じ鍵）／直した（札の中へ移した）。

## 2. 現在地（recon.md）
- recon.md（origin/main 65934286b）: 86関数・60ファイルが当たる。A 39／B 2／C 15（CI で動く）／C-skip 21（`TEST_PG_URL` だけで動き CI では skip）／D 9。
- Opus が手元で scan.py を流し直し、同じ 86関数・60ファイルを得た（2026-11-27）。
- 前のテーマの 53ファイル・76関数は、条件を前と同じに絞ると一致する（recon §0）。

## 3. 既にある決まり（ADR）
- `git grep -il -E "bootstrap_lock|advisory_lock|xdist|後片付け" origin/main -- docs/adr` は0件（2026-11-27）。この見張りの元になる決まりは無い。手本は試験の中の見張り backend/tests/test_tenant_loop_migration_guard.py（`_REVIEWED`）。

## 4. 決めたこと（Opus の設計判断）

### 4-1. どれを「直す」か
- C の15件と C-skip の21件、合わせて36件はすべて札の中へ移す（G4 を字のとおり満たす）。C-skip は CI で流れないが、手元で `TEST_PG_URL` を共有 DB に向けると同じぶつかりが起きるため、残さない。
- D のうち、次の2件も直す（札の中へ移す）。
  - test_lead_merge_pg.py:322 `env`: `public.registration_tokens` の行を消す文（:355）は public の表を触る。`tenant_schema_lock` は別の鍵なので、:351-355 を `public_bootstrap_lock` で囲む（入れる順は tenant → public。test_permission_resolution_pg.py:98-100 と同じ順）。
  - test_priority_prospects_pg_rls.py:66: 今は無条件に skip だが、`DROP SCHEMA`（:291）を `public_bootstrap_lock` で囲む（skip を外した日にぶつからないため）。
- 直した関数は札の語を持つので、見張りの当たりから外れる。分類表には載せず、design §6 の一覧に残す。

### 4-2. 直さずに分類するもの（分類の名前）
| 分類 | 意味 | 見張りが追加で確かめること | 当てはまるもの |
|---|---|---|---|
| `own_database` | その試験が `CREATE DATABASE` した使い捨て DB か、uuid の名前で作る役割 | ファイルに `CREATE DATABASE` があるか、`pg` fixture（test_tcg_work_matching_integration.py）を import している | recon §2-1 の DB を使う A と、test_tenant_isolation_daily_check.py の2件 |
| `text_only` | SQLite・偽の session・文字として読むだけ・docstring の語 | なし（理由を書く） | recon §2-1 の残り |
| `caller_locked` | 呼び出し元が `public_bootstrap_lock` の中 | 同じファイルに `public_bootstrap_lock` がある | recon §2-2 の2件 |
| `tenant_locked` | テナント専用スキーマだけを消し、`tenant_schema_lock` の中 | 同じファイルに `tenant_schema_lock` がある | test_tenant_user_ref_guard_pg.py:121 |
| `denied_check` | 拒否される前提の文で、取引は巻き戻す（後片付けではない） | なし（理由を書く） | test_analysis_error_report_tables_rls.py:147・test_ops_incident_tables_rls.py:178・test_permissions_rls.py:64・test_tenant_payment_versioning_pg.py:199 |

### 4-3. 札で囲むときの決まり（実装カードに写す）
（１）消す文の取引の確定（commit）まで、札の中で終える。札を出てから確定する形にしない。
（２）札の中から、札を取る関数（`public_bootstrap_lock` を使う関数・`bootstrap_public_products` など）を呼ばない。別の接続で同じ札を待ち、自分で止まる。
（３）札は tenant → public → 2147483647 → `public.products` の順で取る。逆にしない。
（４）同期の engine（test_purge_expired_inventory_offers.py だけ）は、同じ接続で `pg_advisory_lock(20260623, 1)` を取り、finally で外す（数は rls_bootstrap の定数を import して使う）。
（５）囲む前に、その関数の呼び出し元を全部読む。呼び出し元が既に札の中なら囲まずに止める（BLOCKED）。

## 5. 見張りの形
- 新しいファイル backend/tests/test_shared_db_cleanup_lock_guard.py（静的・DB を使わない）。手本は test_tenant_loop_migration_guard.py。
- scan.py と同じ探し方を関数 `_scan_source(rel, text)` にする。見張り自身のファイルは読まない。
- `_REVIEWED: dict[str, tuple[str, str]]`。鍵は `ファイル::関数名`（行番号は使わない。行がずれても落ちないため）。値は（分類, 理由）。
- 試験は4つ。
  - 当たりが表に無い → 落ちる（G2）。
  - 表にあるが当たらない → 落ちる（表の掃除）。
  - 分類ごとの追加の確かめ（§4-2 の表）が合わない → 落ちる。
  - 仮の文字列（札なしで public の行を消す関数）を `_scan_source` に読ませると当たる。札の語を足すと当たらない（G3）。

## 6. 直す一覧（38件）
recon §2-3 の15件・§2-4 の21件・§4-1 の2件。直す案は recon の「直す案」の列のとおり。

## 7. 対象外
- `public.` を付けない行削除だけの40関数（recon §4）。テナントの表の後片付けで、別のテーマ。今回は数を残すだけ。
- 製品コード・migration・CI 設定・rls_bootstrap.py。

## 8. 危うさと対処
| 危うさ | 対処 |
|---|---|
| 囲んだ札の中で同じ札を取り、自分で止まる | §4-3（２）（５）。CI の Backend Tests が時間切れなら分かる |
| 札の順が逆で待ち合いの輪 | §4-3（３） |
| C-skip は CI で流れず、直しが正しいか CI で分からない | 形を他と同じにする。G6 で skipped の数が変わらないことを見る。中の動きは未確認と PR に書く |
| 札で囲んで試験が遅くなる | 後片付けだけを囲む。Backend Tests の時間を main と比べて PR に書く |

## 9. 戻し方・測り方・維持
- 戻し方: PR を revert する（試験コードと docs だけ）。
- 測り方: G1〜G6 の表のとおり。
- 維持: 見張りの試験が、新しく足した札なしの後片付けを CI で落とす。分類を足すときは理由を書く（書くまで落ちる）。

## 10. 外部事例
- 該当なし。理由: 試験の中の分類表と見張りは、このリポジトリの test_tenant_loop_migration_guard.py が既にある手本で、外の事例より直接の根拠になる。PostgreSQL の advisory lock の仕様は前のテーマで確かめた（ci-test-shared-collisions design）。

## 11. 審査（Opus・同じ AI の自己審査）
- 結論: APPROVE（設計合格）。
- 根拠: 当たり86件はすべて §4-1 か §4-2 のどちらかに入る（A 39・B 2・D のうち7件が §4-2、C 36件と D 2件が §4-1）。G1〜G6 はどれも CI の結果か差分で ○× が決まる。触る範囲は試験コードと docs だけ。
- 残る点: C-skip 21件の直しは CI で流れないため、動きを確かめられない（§8）。
