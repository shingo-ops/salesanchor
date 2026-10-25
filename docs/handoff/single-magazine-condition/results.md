# results: シングル系の状態「雑誌付き」（CN0027）の本番適用

設計は [design.md](./design.md)、調べは [recon.md](./recon.md)。仕入元名・原文・生出力は社外秘の保管場所（~/CC報告ファイル-keep/shime-auto-check/daily/20261025_1200/state_split/apply/）に置き、ここには件数と判定だけを書く。
実行は Opus。PO の同意票「1」（2026-10-25、ADR-1033）に基づき、台本 cond.sh の5操作を順に流した。出力の読み取りと判定も Opus。

## 手順と結果

| 段 | 何をしたか | 結果 |
|---|---|---|
| precheck | 01_precheck.sql（読むだけ） | PRECHECK_OK 8件。状態は27行、群 single は5行（id55〜59）。CN0027 は未使用。単位 17=Booklet。CHECK は single を許す。line_conditions を参照する外部キーは3本。products 1464件 |
| 状態の追加 dryrun | 02_apply.sql を ROLLBACK で流す | BEFORE_OK 2件、INSERTED 1件、CHECK_OK 7件（ほかの27行は全列同じ・CN0025 不変・products 1464件のまま）。最後は ROLLBACK |
| 状態の追加 commit | 02_apply.sql を COMMIT で流す（2026-10-25 15:24 JST） | 同じ件数のあと COMMIT。CN0027 は id=70 |
| verify | 03_verify.sql（読むだけ） | VERIFY_OK 6件。K2_OK（precheck の6行の全列 md5 が verify と一致、verify は CN0027 の分だけ1行多い7行）。products 1464件 |
| rollback dryrun | 04_rollback.sql を ROLLBACK で流す | 無効化1件、ほかの27行は全列同じ、既存 single 5行は有効のまま。CN0027 への参照は3表とも0件。削除は付けずに流したので無効化のみ。最後は ROLLBACK |

## 受入条件

| 基準 | 判定 | 根拠 |
|---|---|---|
| K1 CHOPPER's の投稿で、本付きは「雑誌付き」の完売、カードだけは「Single」の在庫として別の行になる | 次の同じ投稿の後 | 適用後の最初の同じ投稿を待つ。毎朝点検の記録と在庫行で確かめる |
| K2 試算で4つの言い方のシングル系の行が全部「雑誌付き」（45/45） | ○ | 適用前の試算（recon §5、origin/main 570d70c4a）。本番の状態の値は試算の前提と同じ（precheck の ROW と一致） |
| K3 プロモパック系の判定が変わる行0・CN0025 の全列不変 | ○ | 試算 0/968 と、CHECK_OK CN0025_unchanged・K2_OK |
| K4 言い方の無いシングル系の行の変化0・既存 single 5行の全列不変 | ○ | 試算（ほかの変わり方0）と、K2_OK・VERIFY_OK existing_single_rows 5 |
| K5 商品の件数が増えない | ○ | products 1464件（precheck・commit・verify で同じ） |
| K6 次の同じ投稿のとき、毎朝点検でこの〆の行が○ | 次の同じ投稿の後 | 毎朝点検の判定表 |
| K7 04_rollback の DRY-RUN で新しい行が無効になり、ほかは変わらない | ○ | rollback-dryrun（ROLLBACK_CHECK_OK 2件・最後は ROLLBACK） |

## 戻し方

- `bash cond.sh rollback-commit`（台本は上の保管場所）。CN0027 を無効にするだけで、行は消さない。
- 適用時点で参照は0件なので、行ごと消す `-v del=1` も選べる。ただし、解析が進むと参照が付き、消せなくなる。
- 「雑誌付き」になった解析結果は、再解析しない限りそのまま残る。
