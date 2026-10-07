# design: 比較試験の道具が、指示書を DB から名前で読めるようにする

この文書は何か：これから作る Gemini の指示書を、公開のリポジトリに置かずに試験できるようにする設計。
親（仕様書）：[../../specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)
現状の事実：[recon.md](./recon.md)
関係する ADR：[ADR-014](../../adr/ADR-014-inventory-management.md)（解析のロジック・プロンプトを外から見えなくする方針、`:29`）

## 1. 目的（KGI）
- PO の決定（2026-10-07）：「公開のままで進めても良い、ただし基盤となるロジックはあまり公開してほしくはないので見えないようにしたい」。続けて、本設計の方向（新しい指示書は DB にだけ置き、リポジトリには名前・指紋・数字だけ）に「y」。
- 判定：新しい指示書（`raw_copy_v101_f_a`・`raw_copy_v101_f_b` 以降）の本文が、公開リポジトリのどのファイルにも無い状態で、prompt_ab がその指示書で試験を流せる（○×）。

## 2. 現在地（事実。詳細は recon.md）
- prompt_ab は指示書を `backend/app/prompts/*.txt` からしか読めない（`backend/app/tools/prompt_ab.py:279`）。
- リポジトリは公開（recon §2）。
- 本番の解析は、もともと表 `public.extraction_prompt_config` から指示書を読む（recon §1-2）。本番が読むのは決まった名前の行だけ。

## 3. 変更（prompt_ab.py と、その試験だけ）
### 3-1. 引数 `--prompt-key` を足す
- 意味：表 `public.extraction_prompt_config` の `prompt_key` がこの名前で、`is_active = TRUE` の行の `prompt_text` を指示書にする。
- 使える `--config`：v101・v102 だけ。ほかは引数の検査で止める。
- 名前の形：`V101_PROMPT_NAME_RE`（`^raw_copy_v101_[a-z0-9_]+$`、`backend/app/services/gemini_raw_copy_v101.py:27`）に合うものだけ。こうすると、本番が使う名前（`raw_copy_extraction`・`base_extraction`・`work_id_extraction`）は読めない。
- `--prompt-name` と同時には使えない（引数の検査で止める）。
- 形の検査は `parse_args`（`:585` の近く）で行う。行が有るかは `run_ab` の中、Gemini を呼ぶ前（`:448` の位置）で、同じ `session` を使って確かめる。行が無い・無効・本文が空のときは `ValueError` で止める。

### 3-2. 読み込み
- `_load_prompt_text(config, prompt_name, prompt_key=None, session=None)` にする（`:285`）。`prompt_key` があれば、次の SQL で読む。
  ```sql
  SELECT prompt_text FROM public.extraction_prompt_config
  WHERE prompt_key = :key AND is_active = TRUE
  ```
- 既存の `--prompt-name` と既定の読み方は変えない。

### 3-3. 記録
- 結果の行（`:476`）：`prompt_name` に、`--prompt-key` のときは key を入れる。新しく `prompt_source`（`"file"` か `"db"`）と `prompt_sha256`（読んだ本文の UTF-8 の sha256）を足す。
- `--prompt-key` のときは、本文の sha256 を1行だけログに出す（本文は出さない）。`--dry-run` は今までどおり、組み立てた指示の先頭30行を画面に出す（手元の画面だけで、どこにも保存しない）。

### 3-4. 指示書を DB に入れる手順（コードではない。手元・社外秘）
- 本文は手元の社外秘フォルダ（CC報告ファイル-keep の prompts フォルダ）に key ごとのファイルで置き、sha256 を固定する。
- 書き込みは、2026-10-07 の17社のルールの書き込み（手元の社外秘フォルダの stage5 の run_write.sh）と同じ形。段階は precheck・dryrun・commit・verify・rollback。PO が `!` で実行する。
  - precheck：その key がまだ無いことを確かめる（有れば止まる）。
  - commit：`INSERT ... ON CONFLICT (prompt_key) DO NOTHING` のあと、行数が1でなければ巻き戻す。
  - verify：DB の本文の sha256 が手元のファイルと一致する。本番の3つの行（`raw_copy_extraction`・`base_extraction`・`work_id_extraction`）の本文の md5 が precheck と同じ。
  - rollback：その key の行だけを消す。
- 版の決まり：一度入れた key の本文は書き換えない。直すときは新しい key にする（e → f_a → f_b …）。

## 4. 触らない
- 本番の解析（v6・v7）と、その読み込み（`backend/app/services/gemini_extraction_svc.py`）。
- 表の定義（migration は作らない）。管理画面と API。`.github/workflows/deploy.yml`。
- 既存の `backend/app/prompts/*.txt`（9ファイル）と `--prompt-name`。
- 既に公開されている過去の指示書・設計書の扱い（別の判断。§7）。

## 5. 試験と受入条件
| 基準 | 検証方法 |
|---|---|
| `--prompt-key` で、DB の行の本文が指示書になる | 単体試験：偽の session が返す本文が `_load_prompt_text` の戻り値と一致 |
| 行が無い・`is_active = FALSE`・本文が空なら、Gemini を呼ぶ前に止まる | 単体試験：3つの場合で `ValueError`、Gemini の偽物が0回 |
| 本番の名前と、形の違う名前は読めない | 単体試験：`raw_copy_extraction`・`base_extraction`・`../x`・`raw_copy_v101_A` が引数の検査で止まる |
| `--prompt-name` と同時に使えない、v101・v102 以外では使えない | 単体試験：`parse_args` が止まる |
| 結果の行に `prompt_source`・`prompt_sha256`・`prompt_name`（key）が入る | 単体試験：1回分の行の3つの欄 |
| 既存の動きは変わらない | `backend/tests/test_prompt_ab.py` の既存の試験がすべて通る（CI） |
| 指示書の本文が PR に入っていない | PR の差分に `backend/app/prompts/` の変更が無い（`git diff --name-only`） |
| 本番で動く | マージ・デプロイ後に、DB に入れた key で `--dry-run` を流し、`target_count` と先頭行が出る（PO が DB に入れたあと） |

## 6. 外部・過去事例の参照と我々への応用
- 過去事例（このリポジトリ）：本番の解析の指示書は、すでに `extraction_prompt_config` に置いている（recon §1-2）。表・管理画面・読み込みの型があるので、新しい置き場所を作らずに、それを使う。
- 過去事例（このリポジトリ）：`--supplier-rules-file`（`docs/handoff/gemini-supplier-rules-file/design.md`）と同じく、試験の道具にだけ入口を足し、本番の解析は変えない。
- 外部事例：不要。公開・非公開の置き場所の選び方は、社内の既存の表を使うことで決まり、外部の数値で比べる対象ではないため。

## 7. リスクと戻し方
- リスク：DB の行を誤って書き換えると、どの本文で試験したかが分からなくなる。→ 結果の行に `prompt_sha256` を残し、手元の本文の sha256 と照合する。key の本文は書き換えない決まり（§3-4）。
- リスク：管理画面の一覧 API（`backend/app/routers/super_admin_suppliers.py:1024-1025`）は全行の本文を返す。→ super admin だけが見られる（PO と担当エンジニア）。画面は2つの key だけを表示する。公開とは違う。
- 未決：既に公開されている指示書 v8〜e・v7 の本文（migration の中）・過去の設計書をどうするか。ファイルを消しても GitHub の変更の記録には残る。本設計では扱わない。
- 戻し方：PR を revert する（`--prompt-key` が無くなるだけで、既存の動きは変わらない）。DB の行は `run_write.sh rollback` で key ごとに消す。

## 維持の仕組み
- 守り手: backend/tests/test_prompt_ab.py
- 対象: `--prompt-key` が本番の名前を読めないこと、行が無いときに Gemini を呼ぶ前に止まること、結果に `prompt_sha256` が残ること。
- 人手で守るもの：新しい指示書を `backend/app/prompts/` に足さないこと。理由：ファイルを足すこと自体を機械で止める関所は作らない（既存の9ファイルの試験が同じ場所を読むため）。調整記録（親の仕様書）の §3 に、新しい版は DB の key と sha256 だけを書く決まりを足して守る。
