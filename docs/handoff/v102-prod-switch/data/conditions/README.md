# conditions: Opened box（id=18, CN0006）の search_kw に1語追加（1回だけのデータ変更）

ADR-1007（migration に値を書かない。値は記録した SQL を1回だけ実行する）。表 `public.conditions` の構造は変えない。

## 目的
検品のために開封した旨の注記が付いた商品が、箱の状態「Opened box」ではなく FLAG_SINGLE（単品扱い）になる件を直す。
状態の語は `tcg_analyzer_svc.py` の `load_condition_entries`（is_active かつ priority>0）が `search_kw` / `exclude_kw` から読む。basis は `R{priority}:{一致した語}`。

## PO 決定（2026-10-11、PO しんごさんの言葉）
> 開封箱に検品のため追加

（「開封箱に検索ワードを追加」。追加する語は「検品のため開封済み」の1語。）

## 変更内容
- 対象: `public.conditions` の id=18（code=CN0006, canonical=Opened box）の `search_kw`（text・カンマ区切り。`tcg_analyzer_svc.py:799` 等で `split(",")`）
- 現在値（7語）: `ペリ無,ペリなし,ペリ無し,ぺりぺり無し,ぺりぺり無,検品のため一度開封済み,確認のため開封済み`
- 変更後（8語）: 末尾に `,検品のため開封済み` を足す。他の列・他の行は触らない。
- 「検品のため開封済み」は既存の「検品のため一度開封済み」の部分文字列ではない（間に「一度」が入る）ため、既存語の追加では拾えない。

## 部分一致の影響確認（本番 conditions 13行・読み取り）
- 新語を search_kw / exclude_kw に含む行: 0 件
- 新語に含まれる語、または新語を含む語（全行のカンマ区切りの各語で双方向照合）: 0 件
- 対象は id=18 のみ。

## 手順（上から順に。失敗したらそこで止まる）
1. `kw_precheck.sql`（読み取り）: `TABLE|conditions`、`ROWS|13`、`ROW18|18|CN0006|Opened box`、`EXACT_CURRENT|true`、`HAS_NEW_WORD|0`、`PRECHECK_DONE`。
2. `kw_dryrun.sql`: 更新して検査し、必ず ROLLBACK。`UPDATED|1`、`CHECK_OK 1`、`DRYRUN_OK`。
3. `kw_commit.sql`: dryrun 成功の後だけ。id=18 かつ search_kw が現在値と完全一致する時だけ更新し、件数が1でなければ失敗（COMMIT に進まない）。`UPDATED|1`、`CHECK_OK 1`、`COMMIT_DONE`。
4. `kw_verify.sql`（読み取り）: `EXACT_NEW|true`、`ROWS|13`、`VERIFY_DONE`。
5. 再解析（下記）と前後比較。

## 戻し方
`kw_rollback.sql`（追加後の値と完全一致する時だけ、現在値の7語に戻す）。`ROLLED_BACK|1`、`ROLLBACK_DONE`。

## 再解析の対象
- 注記「検品のため開封済み」を原文に含む v102 のジョブのうち PO 指定の3件（FLAG_SINGLE が各1件）: 6b415ffa / b4605ec5 / fda77ba1（完全IDは `kw_snapshot.sql`）
- 前スナップショット: `kw_snapshot.sql`（読み取り）で取得した41行（6b415ffa 13行・b4605ec5 15行・fda77ba1 13行。原文は含まない）
- 同じ語を原文に含む他のジョブが3件ある（8桁: a100097a / a1a120c6 / e370623d）。範囲に含めるかは設計者判断。

## 記録欄（設計者が実施後に記入）
### 準備（2026-10-11、実装担当）
| 項目 | 内容 |
|---|---|
| precheck | TABLE\|conditions・ROWS\|13・ROW18\|18\|CN0006\|Opened box・EXACT_CURRENT\|true・HAS_NEW_WORD\|0・PRECHECK_DONE |
| dryrun | BEGIN・UPDATED\|1・AFTER\|（8語）・CHECK_OK 1・ROLLBACK・DRYRUN_OK（dryrun 後に search_kw が7語のままであることを確認済み） |

### 本番反映
| 項目 | 内容 |
|---|---|
| 実施日時 | 2026-10-10T21:2xZ（2026-10-11 06:27 JST、kw_commit.log の更新時刻） |
| commit | BEGIN・UPDATED\|1・CHECK_OK 1・COMMIT・COMMIT_DONE |
| verify | ROW18\|18\|CN0006\|（8語、末尾が 検品のため開封済み）・EXACT_NEW\|true・ROWS\|13・VERIFY_DONE |
| 再解析 | 実施済み。再解析で状態の入れ替わりが起きた（別の件の状態が付いた）。原因は A6（reassign_ambiguous による迷う行の付け直し）。便G（release/v102-gemini-trust）で v102 では付け直しを廃止する |
| 前後比較 | 原文を含むため repo 外（手元 /tmp/CC報告ファイル/v102-kw-kenpin/diff6.txt）。原因の証拠は /tmp/CC報告ファイル/v102-swap-rca/ |
