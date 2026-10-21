# master-keyword-fix: 共用マスタの語の修正（4件・A7 は別便）

PO 合意 2026-10-21。本番の共用商品マスタ（public.products、tenant_id なし）に語を足す。値の変更のみ。コード変更なし。

## 変える値の一覧

| 対象 | 項目 | 今の値 | 入れる値 |
|---|---|---|---|
| 作品 type_master 8982（名探偵コナン） | code_only_match | false | true |
| 商品 420439（OP-ST01 麦わらの一味） | 除外語 | STORY BOOSTER 01 / Heroic Beginnings / ガイアレッド / STORY BOOSTER / ドラゴンボール / カートン | 末尾に「Vジャンプ」を追加 |
| 商品 420450（OP-ST12 ゾロ&サンジ） | 除外語 | Raging Onslaught / ジエスモン | 末尾に「Vジャンプ」を追加 |
| 商品 420560（OP-VJ Vジャンプ付録カード） | 除外語 | なし | 「麦わらの一味3人の最強セット」「応募者全員サービス」「VJ2610」を追加 |
| 商品 440578（PM0234 インクランド探訪） | 検索ワード | インクランド探訪 / INTO THE INKLANDS インクランド探訪 | 末尾に「イングランド探訪」を追加 |
| 商品 466060（PM0370 3周年トレジャーキャンペーンパック） | 検索ワード | 3周年!ワンピースカードトレジャーキャンペーンパック / 3周年トレジャーキャンペーン / 3周年 トレジャーパック | 末尾に「トレジャーキャンペーン」を追加 |
| 商品 466060 | 除外語 | なし | 「四皇」「4周年」を追加 |

- 424595（OP-VJ2610）は変更なし。Vジャンプ系の商品は 420560 と 424595 の 2 件。
- A5（ゴールデンボックス）は触らない。
- **A7（440406 の除外語「バラパック」を外す）は別便**。除外語は 1語1行の表で、外すには行を消す文が要るため、扱いを PO 判断待ち。
- 今の値は 2026-10-21 に reader 鍵で確認。

## ファイル

- `docs/handoff/master-keyword-fix/gen_sql.py`: 下の 4 つの SQL を 1 つの表から作る（DB には触れない）
- `docs/handoff/master-keyword-fix/precheck.sql`: 読むだけ。今の値が上の表どおりか照合
- `docs/handoff/master-keyword-fix/dryrun.sql`: precheck → 変更 → postcheck → ROLLBACK（何も残らない）
- `docs/handoff/master-keyword-fix/apply.sql`: precheck → 変更 → postcheck → COMMIT（同一トランザクション。1つでも失敗なら全部戻る）
- `docs/handoff/master-keyword-fix/postcheck.sql`: 読むだけ。適用後の値が目標どおりか照合

語は末尾に足すだけで、既存行の id と position は動かさない。商品ごと・作品ごとに audit_log を 1 行ずつ書く。実行は PO が台本（リポジトリ外・社外秘フォルダ）で行う。台本は origin/main のこのフォルダから SQL を取り、dryrun 済みの同じ sha だけ COMMIT する。

## TODO

- 戻し用 SQL（rollback）は扱いを PO 確認中のため含めない。
- 再解析（対象 job 2 本）の台本は別便。
- A7 は別便。
