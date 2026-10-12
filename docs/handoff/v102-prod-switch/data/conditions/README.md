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

---

# conditions: 状態「Error」(CN0012) の1行追加（便ER・1回だけのデータ変更）

ADR-1007（migration に値を書かない）。表 `public.conditions`（実体は `line_conditions` の単純 view）の構造は変えない。

## 目的
v102 が状態を決められなかった件（`resolve_condition_v2` の最終フォールバック。basis `R4:単位既定:単位不明`）を、状態「Error」にして理由 `condition_unknown` を付け、必ず要確認に回す。

## PO 決定（2026-10-11）
> 状態が判断できなかった場合は状態はErrorにして理由を添えて要確認に回すようにしたい

語で単品と分かった件（PSA・鑑定・プロモ・単品・枚など。basis `R1:…`）は今の FLAG_SINGLE のまま。

## 変更内容
- 1行追加: code=CN0012, canonical=Error, app_kubun='', is_active=true, priority=99, search_kw='', exclude_kw='', match_type=KEYWORD, effect=EXCLUDE。
- id は identity（`public.conditions_id_seq`、last_value 25）が振る。INSERT に id を書かない（明示すると sequence が進まず、次に画面から足す行が主キー重複で失敗する）。本番の予想は 26。コードは code='CN0012' で引き、id に依存しない。
- priority 99・search_kw 空なので照合には当たらない（`match_keyword` は search_kw が空なら当たらない）。`load_condition_entries`（priority>0）には入るので、コードが code で引ける。
- **effect='EXCLUDE' の意味 = 「配信しない状態」**（今まで全13行 OUTPUT で、どこからも読まれていなかった列）。配信 SQL（`cr.effect`）・状態の選択肢・〆の引き継ぎがこれを読む。

## 手順（上から順に。失敗したらそこで止まる）
1. `er_precheck.sql`: `TABLE|conditions`、`ROWS|13`、`CN0012_ROWS|0`、`ERROR_CANONICAL_ROWS|0`、`EXCLUDE_ROWS|0`、`PRECHECK_DONE`。
2. `er_dryrun.sql`: 追加して検査し、必ず ROLLBACK。`INSERTED|1`、`CHECK_OK 14`、`CHECK_OK 1`、`DRYRUN_OK`。
3. `er_commit.sql`: dryrun 成功の後だけ。`INSERTED|1`、`CHECK_OK 14`、`CHECK_OK 1`、`COMMIT_DONE`。
4. `er_verify.sql`: `ROWS|14`、`CN0012|（identity の id・予想 26）|…`、`EXCLUDE_ROWS|1`、`VERIFY_DONE`。
5. コードのデプロイ（この行が先、コードが後。行が無いうちは従来どおり FLAG_SINGLE＋condition_unknown に倒れる）→ 再解析と前後比較。

## 戻し方
`er_rollback.sql`（code='CN0012' の1行だけ削除）。**戻す前に**コードを戻して再解析し、`analysis_results.condition_id` が CN0012 の id を指す行を無くすこと（参照が残っていると失敗する）。

## 記録欄（設計者が実施後に記入）
| 項目 | 内容 |
|---|---|
| precheck |  |
| dryrun |  |
| commit |  |
| verify |  |
