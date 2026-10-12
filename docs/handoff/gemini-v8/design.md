# 設計書：Gemini 書き写し v8 と比較試験（詳細版）

- recon: docs/handoff/gemini-v8/recon.md
- 関連ADR: ADR-1004、ADR-085、ADR-100

状態：**設計審査済み（Opus の自己審査で REVISE、修正を反映して APPROVE。§7-2 を参照）／方針は PO と合意済み（2026-10-01）／実装済み（PR #3903, Draft, GO未受領）**

根拠
- docs/handoff/line-accuracy-pages/accuracy-evidence.md
- /tmp/CC報告ファイル/accuracy-eval/gemini/
  - raw/：指示の再構成と生の出力
  - raw2/：SIG の10列の件と、列数違いの件数
- 公式資料の写し：scratchpad の thinking.txt、structured-output.txt、m31.txt、g3.txt

## 1. PO の決定（2026-10-01）
- ① 完売：Gemini は、書かれている欄にそのまま写す。数量欄の「完売」は、システムが拾う。
- ② 単位：原文に無ければ none にする。デフォルト単位は Gemini に渡さず、システムが付ける。
- ③ 状態ごとの価格行：1行を1件として分ける。商品名は見出しから写す。
- ④ 投稿全体にかかる発送の注記は写さない。
- ⑤ 範囲に見出しの行を入れない。まず全仕入元に共通のルールにし、不安定なら KMS だけのルールにする。
- ⑥ 考えた過程を見える化し、ログに残す。
- 出力は、型を指定した JSON にする。
- 温度は 1.0 で試験する。
- 一括実行は、処理済みの 345 run で打ち切った。比較試験は、この 345 run の投稿から選ぶ。

## 2. 出力の型（response_json_schema）
```json
{
  "type": "object",
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "product_name": {"type": "string"},
          "price": {"type": "string"},
          "unit": {"type": "string"},
          "quantity": {"type": "string"},
          "state": {"type": "string"},
          "ship": {"type": "string"},
          "source_line_start": {"type": "integer"},
          "source_line_end": {"type": "integer"},
          "heading_line_start": {"type": ["integer", "null"]},
          "heading_line_end": {"type": ["integer", "null"]},
          "multi_note": {"type": "string"}
        },
        "required": ["product_name","price","unit","quantity","state","ship","source_line_start","source_line_end","heading_line_start","heading_line_end","multi_note"]
      }
    }
  },
  "required": ["items"]
}
```
- 値は文字列で写す（数値に変換しない）。値の意味の判断はシステムが行う。
- 原文に値が無い欄には none を入れる。
- 範囲は行番号の整数にする。「L0003-L0005」という文字を読み取る処理が不要になる。
- multi_note は、1つの行の中に同じ種類の値が2つ以上ある場合だけ使う（例：1行に2つの価格）。それ以外は none。
- 未確認：nullable の書き方 ["integer","null"] が受け付けられるか。受け付けられなければ、見出しが無いときに 0 を入れる規約に変える。試験 T0 で確かめる。

## 3. 指示書 v8（下書き。extraction_prompt_config に version 2 として足す。v1 は残す）
```
あなたは書き写し担当です。判断・推測・補完・言い換え・翻訳はしません。
入力は LINE の投稿本文で、各行の先頭に行番号（例 [L0001]）が付いています。
価格が書かれた行を1件として、指定の JSON 形式で書き出してください。

【1件の決め方】
- 価格が書かれた行ごとに1件です。同じ商品の下に価格の行が複数ある場合（状態違い・梱包違いなど）は、それぞれを別の1件にします。
- 送料・転送料・連絡事項など、商品ではない行は書き出しません。

【各欄】
- product_name：その件の商品名を原文のまま写す。価格の行に商品名が無い場合は、その上にある商品名の行（見出し）から写す。
- price, quantity, unit, state：その件の行（と、その件だけに付く注記の行）に書かれている文字を、そのまま写す。書かれていなければ none。単位を推測で補わない。
- 「完売」「残りN」などは、書かれている位置の欄にそのまま写す（在庫の判定はしない）。
- ship：その件の行か、その件の見出しに書かれた発送の情報だけを写す。投稿全体の注意書き（例「14時までのご注文で当日発送」）は写さない。無ければ none。
- source_line_start / source_line_end：その件の価格の行と、その件だけに付く注記の行の範囲。商品名の見出しの行や、ほかの件の行を含めない。
- heading_line_start / heading_line_end：商品名を写した見出しの行。無ければ null。
- multi_note：1つの行の中に同じ種類の値が2つ以上ある場合（例：1行に2つの価格）だけ使い、その値を原文のまま「／」でつないで写す。それ以外は none。

【例】
原文:
[L0425] ■OP05 新時代の主役
[L0427] 22BOX@65,400円[通常品]
[L0429] 2BOX@64,200円[状態A-]
書き出し（2件）:
{"product_name":"■OP05 新時代の主役","price":"65,400円","unit":"BOX","quantity":"22","state":"通常品","ship":"none","source_line_start":427,"source_line_end":427,"heading_line_start":425,"heading_line_end":425,"multi_note":"none"}
{"product_name":"■OP05 新時代の主役","price":"64,200円","unit":"BOX","quantity":"2","state":"状態A-","ship":"none","source_line_start":429,"source_line_end":429,"heading_line_start":425,"heading_line_end":425,"multi_note":"none"}

原文:
[L0057] ワンピースBOX カートン
[L0059] OP-02  25,500円/1box
[L0061] OP-04 21,000円/1box
書き出し（2件。範囲には見出しの L0057 を含めない）:
{"product_name":"OP-02","price":"25,500円","unit":"box","quantity":"1","state":"none","ship":"none","source_line_start":59,"source_line_end":59,"heading_line_start":57,"heading_line_end":57,"multi_note":"none"}
{"product_name":"OP-04","price":"21,000円","unit":"box","quantity":"1","state":"none","ship":"none","source_line_start":61,"source_line_end":61,"heading_line_start":57,"heading_line_end":57,"multi_note":"none"}

この後に続く「仕入元の書き方」は、この仕入元がどこに何を書くかの説明です。書き写す場所を見つける参考にだけ使ってください。
```
- 仕入元の書き方から外す項目：デフォルト単位（extraction_default_unit）。②の決定による。
- 仕入元の書き方に残す項目：価格・数量・状態・発送の書式、明細行の並び、例文、区切り記号。
- 未決：例の KMS の product_name を「OP-02」にするか「ワンピースBOX カートン OP-02」にするか。原文に忠実なのは「OP-02」で、見出しの文字は heading の欄で参照できる。この案では「OP-02」を採る。

## 4. 呼び出しの設定（gemini_extraction_svc.py の call_gemini_raw_copy）
- 変更前：config={"temperature": 0}（:507）
- 変更後の案
  - temperature：指定しない（既定の 1.0）。PO の決定と、公式資料 g3.txt の推奨による。
  - response_mime_type："application/json"
  - response_json_schema：§2 の型
  - thinking_config：include_thoughts=True。thinking_level は試験 T0・T1 の結果で決める。
- 返ってきた値の扱い
  - response.text（JSON）を読む。
  - part.thought=True の部分は、考えた過程の要約として別に保存する。
  - usage_metadata は、加工せずにすべて保存する（thoughts_token_count が来るかどうかを確かめるため）。

## 5. 前処理と、受け取り後の処理
- strip_emoji：その仕入元の block_delimiter に入っている文字は消さない。行の数は変えない。
- 受け取り後は JSON として読み、件ごとに次の検査をする。違反した件は parse_error として、理由を付けて記録する。
  - 範囲が原文の行数の内側にあること
  - 範囲が見出しの範囲と重ならないこと
  - 範囲がほかの件の範囲と重ならないこと
  - 必須の欄がそろっていること
- 記録先：extraction_shadow_runs に新しい列を3つ足す（migration が必要で、GO の対象）。
  - thought_summary text
  - usage_raw jsonb
  - parse_errors jsonb
  - 試験の段階では、表に書かずファイルに出す（§6）。

## 6. 比較試験（本番の表には書かない）
### 6-1. 道具
- 新しく backend/app/tools/prompt_ab.py を作る（読み取りだけ。PR と GO が必要）。
  - 入力
    - 対象の run id の一覧（ファイルで渡す）
    - 設定の組（v7 の現行、または v8 で、温度・thinking_level・schema の有無を変えたもの）
    - 繰り返しの回数
    - 費用の上限
  - 動き
    - 本番と同じ load_extraction_context で文脈を読み、設定の組ごとに Gemini を呼ぶ。
    - 結果は /tmp の JSONL ファイルにだけ書く。1行に、生の応答、usage_metadata、考えた過程の要約、パース結果、件ごとの検査結果を入れる。
    - DB には書かない。ただし llm_usage_events には、purpose="line_extraction_shadow"・source_ref="prompt_ab:<test_id>" で費用を記録する（purpose の追加は migration の CHECK 制約が要るため、source_ref で区別する）（ADR-1004 の台帳に合わせる。書き込みはこの1か所だけ）。
  - 費用の上限を超えたら止まる。失敗が1件でも出たら止まる。
### 6-2. 試験の順序
- T0（設定の確認・約5回）
  - 投稿1件に対して、次の5通りを流す。
    - v7 の現行（温度 0、指定なし）
    - v8 で thinking 指定なし
    - v8 で minimal
    - v8 で low
    - v8 で high
  - 確かめること
    - usage_metadata の全体
    - 考えた過程の要約が返るか
    - 各 level が受け付けられるか
    - schema と thinking を一緒に使えるか
- T1（比較・約100投稿）
  - 標本：345 run の投稿から選ぶ。
    - 課題があった仕入元（SIG、シンソク、KMS、倉田、N&U、中村、斉藤、西田）から各5件
    - 残りは md5 で無作為に選ぶ
  - 設定は2つ。
    - A：v7 の現行
    - B：v8（温度 1.0、schema あり、thinking は T0 で決めたもの）
  - B は2回流して、ぶれを測る。
- T2（判定まで通す・約50ブロック）
  - B の出力を、システムの判定（今のロジック）に通し、Opus が目視で正しいかを判定する。
  - ①・E・A などのシステム側の修正は、まだ入れない。どこまでが Gemini の改善分かを切り分けるため。
### 6-3. 測る項目と合格の目安（目安は PO が決める）
| 項目 | 測り方 | 目安（案） |
|---|---|---|
| 形式の崩れ | parse できない件、必須の欄が欠けた件 | 0件 |
| 範囲の重なり（⑤） | 件の範囲どうし、件の範囲と見出しが重なる数 | 0件 |
| 条件違いの分割（③） | シンソクなどで、価格行の数と件の数が一致するか（目視） | 95%以上 |
| 価格行の見落とし | 価格らしき行（送料行を除く）のうち、どの件にも入っていない行 | v7 より減る |
| 単位の補完（②） | 原文に無い単位を書いた件 | 0件 |
| 発送の範囲（④） | 投稿全体の注記を写した件 | 0件 |
| 2回流したときの一致 | 件の数と範囲が一致する投稿の割合 | 95%以上 |
| 費用 | 1投稿あたり（考えた分を含む） | 実測値を報告し、PO が判断する |
| 考えた過程の要約 | 返ってきた割合と、中身の例10件 | 実測値を報告する |
| 判定まで通した正答率 | T2 の目視判定 | v7 との比較を報告する |
- ⑤：範囲の重なりが2回の実行のどちらでも 0件なら、共通ルールとして採用する。重なりが出るなら、KMS だけのルールにする案に切り替える。
- 費用の見込み：T0 が約0.05ドル、T1 が約100投稿×3回で約0.6〜1ドル【推測：1件約0.002ドルから。thinking を入れると増える】。上限は 3ドルを提案する。

## 7. 進め方（PR を分ける）
1. PR-1（GO が必要）：prompt_ab の道具と、v8 の指示書の version 2（is_active は false のまま）
   - 本番の判定には使わない。
2. T0 → T1 → T2 を実行し、結果を PO に報告する。PO が合格の目安を決める。
3. 合格したら、次を順に入れる。
   - PR-2：呼び出しと受け取りの変更、migration（新しい列）
   - PR-3：システム側の判定の修正（①の完売、E の見出しを使った照合、A の短い記号、C の予約、D の単位、②のデフォルト単位の付与）

## 7-2. 自己審査（Opus、2026-10-01）：REVISE。下の修正を反映して APPROVE（T0 で確かめる項目は残る）
1. 旧方式（v6）を変えない
   - _build_supplier_context_note と strip_emoji は、v6 と共通で使っている可能性がある。
   - v8 の変更（デフォルト単位を外す、区切り記号を残す）は、v8 専用の引数か関数で行う。v6 の挙動は1文字も変えない。
   - 共通かどうかは、PR-1 の前にコードで確かめる。
2. 倉田型の書き方
   - 状態の行（例「シュリ無し」）が価格の行（例「ボックス/¥12,000」）の前にあり、その後に「残り170」が続く書き方がある。
   - 指示書に、その件だけに付く注記の行は前の行も含むことを明記する。倉田型を3つ目の例として足す。
   - T1 では、倉田の分割の正解率を別に測る。
3. 費用の台帳
   - prompt_ab の費用は llm_usage_events に記録する。
   - purpose に新しい値を入れてよいか（制約や列挙の有無）を、ADR-1004 とコードで確かめる。新しい台帳は作らない（SSOT）。
4. migration
   - 新しい列を足す migration は、deploy.yml への登録が必須（backend/CLAUDE.md）。
   - 列の追加だけにする（additive-only）。
5. 費用の上限
   - 試験の上限 3ドルは、PO の承認事項とする。試験を流す前に承認を得る。

## 8. 未確認の事項と、それぞれを確かめる段階
- thoughts_token_count が空になる理由 → T0
- このモデルで使える thinking_level → T0
- schema と thinking を一緒に使えるか → T0
- nullable の書き方が受け付けられるか → T0
- SIG で10列になった原因 → JSON にすると形式の問題としては消える。考えた過程の要約で、何が起きたかが見えるかを T0・T1 で確かめる。
- 今のシステムに、raw_unit が none のときデフォルト単位を付ける処理があるか → PR-3 の前に、コードで確かめる。

## PR-1 の受け入れ基準
| 基準 | 検証方法 |
|---|---|
| v6 と本番 v7 の関数・ファイルが1文字も変わっていない | git diff origin/main -- backend/app/services/gemini_extraction_svc.py backend/app/services/extraction_shadow_svc.py の出力が空 |
| 既存の試験が無変更で通る | backend/tests/test_tcg_gemini_extraction.py と backend/tests/test_extraction_shadow_svc.py を pytest で実行し全件 pass |
| v8 の入力整形・仕入元ルール・受け取り後の検査・呼び出し設定が設計どおり | backend/tests/test_gemini_raw_copy_v8.py が全件 pass |
| 費用の上限・失敗1回で停止・dry-run で Gemini を呼ばない・v7 は既存関数を呼ぶ | backend/tests/test_prompt_ab.py が pass。台帳の source_ref 合計だけは共有の pg fixture のため CI で確認 |
| 台帳以外の DB に書かない・migration を足さない | PR の変更ファイル一覧に migrations/・deploy.yml が無いこと |
| 起動時の確認が働く | python -m app.tools.prompt_ab --help が通り、SDK に項目が無ければ版を表示して終了コード 2 |

## 外部・過去事例の参照と我々への応用
- 外部：Gemini 公式資料（本設計の根拠に挙げた thinking.txt・structured-output.txt・g3.txt の写し）。型指定 JSON（response_json_schema）、thinking の設定、温度の既定値 1.0 の推奨は、これらに基づく。応用：§2・§4。使える組み合わせかどうかは公式資料だけでは確定しないため、試験 T0 で実機確認する（§8）。
- 過去事例（社内）：過去ジョブに新方式を一括で流す道具 app/tools/shadow_backfill.py（費用の上限・失敗1回で止まる・台帳の費用で見張る）。応用：prompt_ab は同じ止め方を採り、結果は本番の表でなく JSONL に出す（§6-1）。

## 維持の仕組み
- 守り手: .github/workflows/process-artifacts-gate.yml
- 対象: PR-1 の道具（比較試験）が本番の v7 経路・旧方式 v6 の関数を変えないこと。変えていないことは、PR 本文に貼る `git diff origin/main -- backend/app/services/gemini_extraction_svc.py backend/app/services/extraction_shadow_svc.py` が空であることと、既存の試験（backend/tests/test_tcg_gemini_extraction.py、backend/tests/test_extraction_shadow_svc.py）が無変更で通ることで確かめる。
- 関所なしの場合: v8 の指示書ファイル（backend/app/prompts/raw_copy_v8.txt）を採用後に DB へ移して削除する段取りは、関所がないため人手で守る（PR-2 の設計で扱う。理由：採用の判断が試験結果次第で、いつ起きるか未定のため）。
