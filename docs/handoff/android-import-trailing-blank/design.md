# design: Android 取込で本文末尾の空行を除き、同じ投稿の2通目を作らない（便TB）

参照: docs/handoff/android-import-trailing-blank/recon.md、docs/handoff/android-import-trailing-blank/card-TB.md、ADR-158。

## 1. 目的（PO の言葉、2026-10-12）
- 「本文の最後の空行を取り除いてから比べるようにすれば、2通目は作られません。…この修正は進められます。→進めてくれ」

## 2. 変更
| 場所 | 変更前 | 変更後 |
|---|---|---|
| 本文の正規化（tcg_line_import_svc.py normalize_message_body・_TRAILING_BLANK_CHARS） | 無し | 本文末尾の「改行と、その後ろの空白だけの行」を除く。最後の内容行の行末空白・先頭・途中は変えない |
| 保存（_write_source_messages の entry ごとの先頭） | build_provider_entries の raw_text・sha256 をそのまま保存 | 正規化した本文と、その sha256 で保存・判定（元の entry は書き換えない） |
| 再利用判定（同 :391-404） | raw_sha256 と raw_text の完全一致 | raw_text が一致、または保存済み本文の末尾空行を除いたものが一致 → reused（既に "\n" 付きで保存された 87件も同じ投稿と見なす） |
| データ | — | 変更しない（UPDATE・DELETE・migration なし） |

## 3. 受入条件
| 基準 | 検証方法 |
|---|---|
| T1 末尾の空行だけが違う本文は reused、1文字でも違えば新規 | 実 PG テスト（backend/tests/test_tcg_import_progress_pg.py、CI pytest-run で実行） |
| T2 正規化は末尾の空行だけを除く（8ケース）、保存値は正規化後 | テスト（backend/tests/test_tcg_line_import.py） |
| T3 SQL の文字集合と Python の文字集合が一致 | テスト test_reuse_sql_blank_set_matches_python_set |
| T4 本番反映後、反映時刻以降に作られた「前の行＋末尾 "\n" だけ」の2通目が 0組（取込が少なくとも10回走った時点で測る）、import_jobs の失敗増加なし | 本番読み取り |

## 4. 代替案
- Android パーサで本文を rstrip: 最後の内容行の行末空白（既存 70件）も消え、次の取込で別物と判定され2通目が出る → 末尾の空行だけを除く。
- 保存済みの "\n" 付き 87件を UPDATE で揃える: 本番データの書き換えが要り、superseded の関係も崩れうる → 判定側で吸収し、データは触らない。
- 再利用判定を sha256 だけで: 末尾の差を吸収できない → 本文の比較に寄せる。

## 5. リスクと対処
- 既存の2通目（24組）はそのまま残る（同じ時刻の2行。数量・価格は同じ）→ 本便では消さない（データは変えない）。
- regexp_replace は channel・line_posted_at で絞った行にだけかかる → 負荷は小さい。

## 6. 戻し方
- PR を revert（データ変更なし）。

## 外部・過去事例の参照と我々への応用
- 外部事例: 使わない（LINE 書き出しの空行の扱いに合わせた社内の取込の比較方法で、比べられる公開の実測が無いため）。
- 過去事例: 便SU（#4149）の再解析で、同じ時刻の2行の現行入れ替わりの過半がこの形だった → 取込の時点で2通目を作らない。

## 維持の仕組み
- テスト（正規化8ケース・保存値・SQL と Python の文字集合の一致・実 PG の再利用判定）が CI で毎回走る。
- 守り手: CI（backend/tests/test_tcg_line_import.py、backend/tests/test_tcg_import_progress_pg.py）
