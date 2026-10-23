# master-exclude-barapack: 商品 440406 の除外語「バラパック」を外す

PO 決定 2026-10-21。本番の共用商品マスタ（public.product_exclude_keywords、tenant_id なし）から 1 行を消す。値の変更のみ。コード変更なし。やり方は「手順書を作り、PO が 1 行で流す」（PO が選択肢 2 を選択）。

## 変える値

| 対象 | 項目 | 今の値 | 変更後 |
|---|---|---|---|
| 商品 440406（PM0263 / 型番 M6a / 30th CELEBRATION） | 除外語 | 52 語（「バラパック」は position 46、行 id 2000） | 「バラパック」の 1 行を外した 51 語。後ろの 6 語は position を 1 つ詰める（47〜52 → 46〜51） |

- 今の値は 2026-10-21 に reader 鍵（ADR-1024）で確認した。除外語の並び 52 語は gen_sql.py に埋め込んである。
- 除外語は 1 語 1 行の表。アプリの保存は並びを 1..n の連番で書き直すため（recon.md §2）、連番を保つよう詰める。
- 外す理由と試算は recon.md §3、戻し方は design.md を参照。

## ファイル

- `gen_sql.py`: 下の 6 つの SQL を 1 つの表から作る（DB には触れない）。`python3 -B gen_sql.py`
- `precheck.sql`: 読むだけ。440406 があること、「バラパック」がちょうど 1 行（position 46・id 2000）であること、除外語 52 語の並びを照合
- `dryrun.sql`: precheck → 変更 → postcheck → ROLLBACK（何も残らない）
- `apply.sql`: dryrun.sql と本体は同じで、最後だけ COMMIT（1 つでも失敗なら全部戻る）
- `postcheck.sql`: 読むだけ。適用後の値と audit_log の 1 行を照合
- `rollback.sql`: 「外した後」の状態のときだけ、外した行を元の id・position・updated_at で入れ直し、詰めた position を戻す。audit_log に 1 行。消す文は含まない
- `rollback_dryrun.sql`: rollback.sql の試し流し（最後だけ ROLLBACK）

実行は PO が台本（リポジトリ外・社外秘フォルダ）で行う。台本は origin/main のこのフォルダから SQL を取り、dryrun 済みの同じ sha だけ COMMIT する。

## 再解析（別手順・台本のみ）

「バラパック」を外すと、この語で外れていた投稿行が 440406 に当たる。画面に出る側の行を直すため、該当する有効な投稿の job を再解析する（台本はリポジトリ外）。対象と根拠は recon.md §4。
