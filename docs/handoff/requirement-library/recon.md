# recon — 要件の書類を作業の場面で目に入れる（2026-11-21・origin/main 62f1c4c09 基準）

> この文書は何か: 今の目録・見張り・CI がどうなっているかを、ファイルの行番号つきで並べた現在地。設計の土台。
> 親: [../../specs/requirement-library/README.md](../../specs/requirement-library/README.md)／KGI: [kgi.md](../../specs/requirement-library/kgi.md)

## 1. 既存 ADR の検索結果

- `git grep -il "FEATURE-INDEX\|索引" docs/adr/` と FEATURE-INDEX「横断・運用・プロセス」節を引いた。
- 関係する決まり: **ADR-1040**（AI 向け文書を「入口→目次→章→末端」にする。doc-agenda-nav）、**ADR-121**（`docs/specs/README.md` 索引と設計仕様書の義務）。どちらも「目次を辿れる」までを決めており、**作業の場面（ファイルを開いた瞬間）で決まりを見せる仕組みは決めていない**（ADR 本文に PostToolUse・additionalContext の語なし。grep 済み・該当なし）。
- 本テーマは両者を覆さず、上に足す。

## 2. 目録（R1）の現在地

| 事実 | 根拠 |
|---|---|
| 機能→ADR 索引は手で選んだ主要 ADR だけを載せる方針 | `docs/adr/FEATURE-INDEX.md:6`「主要ドメインの正準 ADR だけを人手でキュレート」 |
| 索引は 68 行・表の行 34 | `wc -l`・`docs/handoff/requirement-library/r1_count.py` の出力 `fi_rows 34` |
| ADR ファイル（`ADR-<数>-*.md`）の番号 210 個のうち、索引が指すのは 59・**指さないのは 151** | `python3 -I docs/handoff/requirement-library/r1_count.py .` → `adr_ids 210 referenced 59 missing 151` |
| 設計仕様書のフォルダ 56 のうち、`docs/specs/README.md` に無いのは `master-ssot-migration`（既存の抜け）と本テーマ（本 PR で足す） | 同出力 `missing_in_specs_readme 2` |
| 索引から設計仕様書を指す行は 2 フォルダだけ | 同出力 `spec_dirs_referenced_from_feature_index 2` |
| 11/13 の取り違えの元: 「会社」の行は ADR-060・ADR-058 だけで、会社はリードの子と決めた ADR-097・deal-removal の設計書を指さない | `docs/adr/FEATURE-INDEX.md:28` |
| その決まりの本文 | `docs/specs/db-ssot/deal-removal/design.md:8`（§1 PO の言葉 2026-07-18）・`:62`（§4.6）・`:65`「leadは全ての親」 |
| コードも同じ決まりで動く | `backend/app/routers/companies.py:383` `create_company`・`:391`「# 便1a: lead 必須（背骨）」 |

- kgi.md 初版の「158（223 番号中）」は数え方を固定する前の手計算。本 recon からは `r1_count.py`（ファイル名 `ADR-<数>-` の番号の重複を除く）で数え、**今の値は 151** とする。

## 3. 練習問題（R2・R3・R4 補助）の現在地

- 題と数え方は [quiz.md](./quiz.md) に固定（2026-11-21）。正解の ADR 10 題中 9 題（Q4 以外）が索引に載っていない（r1_count の MISSING に 097・1076・1083・1022・1037・1032・1062・1056・1071 が入る）。
- 変更前の測定値は `quiz/before/` に置く（クラウドで流す。結果が出たら本節に書き足す）。

## 4. 見張り・CI の現在地

| 事実 | 根拠 |
|---|---|
| 着手前に索引と `git grep` で ADR を引く義務は文書にある（人と AI の注意に頼る） | `docs/STANDARD-WORKFLOW.md:25`・`:82` |
| リポジトリの見張りは SessionStart・SubagentStop・PreToolUse・UserPromptSubmit・Stop だけで、**PostToolUse（ファイルを開いた直後）の見張りは無い** | `.claude/settings.json:35`・`:64`・`:74`・`:88`・`:93` |
| 目次のたどり着き検査は CI で毎回流れる。索引の網羅は数えていない | `.github/workflows/doc-index-reachability.yml:31`→`scripts/ci/check_doc_index.py`（259 行。`UNREACHED` は `:148`） |
| `claude -p` ではリポジトリの見張り（hooks）は動き、`permissions.allow` だけが使われない | 公式 https://code.claude.com/docs/en/permissions 「What runs before you trust a folder」・https://code.claude.com/docs/en/hooks 「Workspace trust」（Context7 2026-11-21） |
| PostToolUse の見張りは `hookSpecificOutput.additionalContext` で AI に文を渡せる。入力に session_id・tool_name・tool_input が来る | Context7 `/websites/code_claude` hooks（2026-11-21） |
| クラウドで `claude` 2.1.330 が動く。ごく短い問いでも 1 回 0.179 ドルかかった | 実行記録 cse_01HHUUpSNznAhPBQRNm4C975（2026-11-21） |

## 5. 未確認

- 変更前の R2・R3・R4 補助の値（クラウドで測定中）。
- R4 本測定（見張りの記録の週次の数え）は見張りができるまで値が無い。
