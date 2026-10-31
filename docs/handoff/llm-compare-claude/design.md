# 解析AIを Claude Haiku・Sonnet に替えたときの精度比べ — design

状態: 設計案 第3版（Opus）。第1版 REVISE → 第2版 条件付き APPROVE（2026-10-30、reviewer Opus）→ 第3版で条件(a)と(b)〜(e)を反映。設計審査済み。PO 承認済み（2026-10-30、提示した計画と §4・§8-1・§8-3・§9 の PO 判断3点を含めて選択肢「1」）。道具の作成は、試験に使う手元の社外秘データ（f_ct の写し）をクラウドに置かないため、§9 と同じ理由で手元で行う。調査は recon.md（同じフォルダ）。

## 1. 目的
今の解析AI（Gemini gemini-3.1-flash-lite）が受け持つ「書き写し」を、Claude Haiku と Claude Sonnet（claude CLI、サブスク）に同じ条件で解かせ、正答率・トークン量・時間・費用・回数の上限の差を数で並べる。本採用は決めない。並べた結果を見て PO が次を決める。

## 2. 対象と対象外
- 対象: 正解表 gold_v1 の100投稿（1494行）。Gemini 1種と Claude 2種の計3種。
- 対象外: 本番の解析の切り替え（LINE_ANALYSIS_ENGINE は触らない）。Codex・Grok。tenant001/004 だけ読める入り口（段階2、別設計）。サーバーで Claude を動かすこと。製品コードの変更。

## 3. 同じ条件にそろえる表
| 条件 | Gemini | Claude Haiku / Sonnet | そろえ方・残る差 |
|---|---|---|---|
| 指示書 | f_dm（DB id=397、sha256 84afd2e4…8b0c） | 同じ | Gemini に実際に渡した文字列を残し、その同じ文字列を Claude に渡す（§5-1） |
| 原文・仕入元の決まり | build_prompt_v8 が組み立てた1本（`--config v102` で旧7欄を外す。本番 line_analysis_v102_svc.py:199-202 と同じ） | 同じ1本 | 同じ日に組み立てた1本。sha256 を全件照合 |
| 答えの形 | response_schema = V102_RESPONSE_SCHEMA | `--json-schema` に同じ定義 | 定義（gemini_raw_copy_v101.py:106-107）を JSON に書き出して渡す。CLI が追加の制約を求めて定義を変えたら「残る差」に記録 |
| 考える量 | thinking_level high（prompt_ab は "HIGH" に直して渡す :648-649。前回の f_dm 試験と同じ） | `--effort high` | 名前をそろえる。中身の同等は保証できない |
| temperature | 未指定（既定） | 変える口が無い | 両方とも既定。そろえられない |
| 道具・追加の指示 | なし | `--tools ""` `--setting-sources ""` `--strict-mcp-config` `--no-session-persistence`。`--bare` は使わない（API の鍵だけになりサブスクで動かない、help.txt:41-50） | Claude の土台 約600トークンは残る |
| system の指示 | なし | `--system-prompt "与えられた指示に従い、指定の JSON だけを返してください。"` 固定 | CLI 既定の長い指示を入れないため |
| やり直し | `--retry-transient 3`（本番は即時のやり直し line_analysis_v102_svc.py:495-523） | なし（失敗で停止） | 残る差として記録 |
| 後段（決まりの処理） | fhd_snapshot.py convert | 同じ | 3種の答えを1回の起動でまとめて convert（同じ読み取り・同じマスタ、fhd_snapshot.py:236-277）。prompt_ab の v102_items は使わない |
| 採点 | score_v102.py | 同じ | 同じ gold_v1.tsv（sha256 照合）・同じ score_v102.py（commit 固定） |
| トークンの数え方 | 入力 = prompt_tokens、出力 = candidates_tokens、考えた分 = thoughts_tokens | 入力 = input + cache_creation + cache_read、考えた分 = thinking_tokens、出力 = output_tokens（thinking が output の内数かは手順（４）で確かめ、二重に数えない） | 表に定義を書いて並べる |
| 時間 | elapsed_sec（後段の計算とやり直しの待ちを含む） | 壁時計（起動 約8秒を含む）と duration_ms | 中身の違いを表に注記 |
| 実施日 | 同じ日 | 同じ日 | — |
| 回数 | 3回 | 1回 | Gemini は3回でばらつき幅を出す。Claude はサブスクの残りを守るため1回 |

## 4. 成功の決め方（PO 承認済みの線を一つに決める）
Haiku と Sonnet は別々に判定する。「Gemini 平均」は Gemini 3回の率の単純平均。

| 基準 | 合格の式 | 検証方法 |
|---|---|---|
| 正答率 | E1・E2(AI段)・E3(AI段) の率がすべて Gemini 平均以上、かつ C1 読み落とし件数と余分件数がともに Gemini 平均以下 | score_v102.py の出力（:299-300 ほか）を並べた表。Gemini は3回の最小〜最大も併記 |
| 参考 | 判定に使わない | A1〜A5・E2/E3 システム段・A4 を同じ表に並べる |
| サブスクで動く | Claude 100件すべて rc=0・is_error=false、かつ実施前に環境変数 ANTHROPIC_API_KEY と ANTHROPIC_AUTH_TOKEN がどちらも空（CLAUDE_CODE_OAUTH_TOKEN はサブスクの鍵なので、あってよい）、かつ `claude auth status` がサブスクのログイン | 実施ログ（値は伏せる） |
| 回数の上限 | N = 本番の直近7日の purpose='line_extraction' の1日平均件数（本番の送り直しも1件に数えるので、N は実際より少し大きく出る＝判定が厳しくなる側）。100件連続で上限の返事0件、かつ「100件の所要時間 ÷ 100 × N ≦ 24時間」で合格。N > 100 のときは「上限に当たらず1日分を回せる」ことは今回の試しでは証明できないので「未確定」とし、N件を連続で回す追試を PO に相談 | 読み取りの窓口で N を数える。実施ログ |
| 1件の時間 | 判定に使わない（並べるだけ） | 中央値と最大 |
| トークン量 | 判定に使わない（並べるだけ） | §3 の定義で3種の合計と1件平均 |
| 費用（円） | Claude の追加費用（今の契約のまま回せたら0円、上の契約が要るならその月額の差）≦ Gemini の直近30日の purpose='line_extraction' の cost_usd の合計を円にした額 | 読み取りの窓口と llm_budget.py の式。為替の値と日付を書く。参考に Claude の total_cost_usd（定価換算）も並べる |
| 本番の解析結果に書いた件数0件 | 100件の job に結び付く extraction_items と analysis_results の行を、実施の直前と直後に全列まるごと md5 にして一致（時刻の列の有無に頼らない）。かつ llm_usage_events の source_ref LIKE 'prompt_ab:llmcmp-%' の行数 = Gemini の呼び出し回数 | 読み取りの窓口で実施の直前（手順（２））と直後（手順（７））に1回ずつ |

使用量の記録帳（llm_usage_events）には Gemini の分が最大300行書かれる（prompt_ab.py:596-600）。PO の線「本番に書いた件数0件」をこの形で読むことは、実施前に PO の承認を得る（§8-1）。

## 5. 変更前後と作るもの
製品コード（backend/・frontend/・migrations/・本番の deploy）は変えない。試験用の道具を scripts/accuracy/llm_compare/ に新しく置く（本番には配られない。CI では走らない）。

### 5-1 Gemini を解かせ、渡した文字列を残す: `capture_prompt_ab.py`（新規）
- 本番サーバーの別の箱の中で動かす。prompt_ab は `from app.services.gemini_raw_copy_v8 import build_prompt_v8, call_gemini_raw_copy_v8`（prompt_ab.py:47-49）で読み込み、モジュール内の名前で呼ぶ（:555）。差し替えるのは `app.tools.prompt_ab.call_gemini_raw_copy_v8`。gemini_raw_copy_v8 モジュール側を差し替えても効かない。
- 包み: 元の関数を呼び、**成功して返った後だけ**、同じ引数で build_prompt_v8 を呼んで文字列を保存する（一時的な失敗のやり直し :550-573 では保存しない）。保存名は `<test-id>_<通し番号 4桁>_<sha256>.txt`、index は `<test-id>.index.tsv`（通し番号, sha256, 文字数）。test-id ごとに別名なので、続きを別の test-id で流しても上書き・重複しない。
- 起動の引数: `--config v102 --runs-file /fhd/llmcmp/runs.txt --out-dir /fhd/llmcmp/out --test-id llmcmp-g1 --prompt-key raw_copy_v101_f_dm --thinking-level high --retry-transient 3 --repeat 3 --max-cost-usd 5.00`。必須の引数（prompt_ab.py:624-634）をすべて含む。
- 照合: JSONL の成功行の数 = 保存した文字列の数（エラー行 :576-582 は除く）。JSONL の並びは「投稿ごとに repeat 1→2→3」（:516-523）なので、Claude に渡す100本は **JSONL の repeat 欄が 1 の行**で選び、その job_id と同じ通し番号の文字列を使う。repeat 1 と 2・3 の文字列の sha256 が投稿ごとに同じであることも確かめる。
- 途中で止まったら（前回は503続きで265回目に停止、RESULT-20261027.md:3）: 未完了の job だけの runs ファイルで test-id `llmcmp-g2` として続きを流し、JSONL を結合する。
- 費用: 前回の実績 314回で約3.83USD（1回 約0.012USD）。300回の見込み 約3.6USD。上限 5.00USD。prompt_ab は「超えた後に止まる」（:208-215）。上限で止まり3回そろわなかったら、そろった回数で採点し、回数を表に書く（1回もそろわない投稿は C1 に数えられる :210-214）。

### 5-2 Claude を解かせる: `run_claude.py`（新規、手元の Mac で動かす。理由は §9）
- 入力: 取り寄せた文字列と index、JSONL（repeat=1 の job_id 対応）、モデル名（haiku / sonnet）。
- 1件ごとに `claude -p --model <m> --effort high --output-format json --json-schema <v102_response_schema.json の中身> --tools "" --setting-sources "" --strict-mcp-config --no-session-persistence --system-prompt "与えられた指示に従い、指定の JSON だけを返してください。"`。文字列は標準入力で渡す。cwd は空の一時フォルダ。1件の時間切れ 600秒。
- 順番に1件ずつ。rc≠0・is_error=true・時間切れのどれかで、理由を問わず即停止し、時刻と件数を記録する（待って再開しない）。
- 1件ごとに、modelUsage の中身が指定したモデル1種だけで、AI への呼び出しが1回だけ（usage.iterations が1件）であることを確かめる。違えば停止。
  - num_turns は、`--json-schema` を付けると 2 になる（2026-10-31 実測。作りものの短い文で、付けると num_turns=2・iterations 1件・structured_output あり、付けないと num_turns=1。生出力 /tmp/CC報告ファイル/llm-compare/probe-turns/）。このため num_turns は「structured_output があるときは 2、無いときは 1」を正常とし、それ以外は停止する。
- 出力: Gemini の JSONL と同じ欄（job_id, repeat=1, config="claude-<m>", response_text, usage_raw, elapsed_sec, errors）＋ Claude の生 JSON 全文。response_text に入れる欄（result か structured_output か）は手順（４）の結果で決め、カードの記録に書く。
- 実施前に記録: claude --version、§4「サブスクで動く」の確認（値は伏せる）。

### 5-3 採点用の形にする
- 3種（Gemini 3回分・Claude 2種）の JSONL を本番サーバーの箱へ置き、**1回の起動で全部まとめて** fhd_snapshot.py convert（読み取りのみ。既存の道具を scripts/accuracy/llm_compare/ に写して sha256 を記録）で TSV にする。
- `split_snapshot.py`（新規、手元）: convert の出力（先頭に tag・repeat・source_message の3列＋14列、fhd_snapshot.py:241, :267）を、(tag, repeat) ごとに別フォルダ、その中で投稿ごとの <投稿id>.tsv に分け、先頭3列を落とす（score_v102.py の --snapshot-dir の形 :18-21）。

### 5-4 並べる: `summarize.py`（新規、手元）
- score_v102.py の出力（Gemini 3回・Claude 2種）、トークン量、時間、費用、§4 の合否を1枚の表（CSV と Markdown）にする。

### 5-5 起動の台本（新規）
- `vps_run_gemini.sh`、`vps_convert.sh`、`fetch_results.sh`: PO が ! で打つ台本。箱は RUNBOOK_fdm.md と同じく `docker compose run --rm --no-deps -T --name llmcmp-<id> -v /home/ubuntu/fhd-test/llmcmp:/fhd/llmcmp -e PYTHONPATH=/app celery-worker python /fhd/llmcmp/capture_prompt_ab.py …`。ファイルを直接動かすと /app が読み込み先に入らない（backend/Dockerfile:4 は WORKDIR /app、PYTHONPATH の設定なし）ので、`-e PYTHONPATH=/app` を必ず付け、ファイルの先頭でも sys.path に /app を足す。capture_prompt_ab.py は差し替えの後に `app.tools.prompt_ab.main(argv)` を呼ぶ。**健康診断の上書き（no-health.yml、RUNBOOK_fdm.md:12-17）を必ず付ける**（付けないと本番の警報が鳴る恐れ）。起動前に healthcheck と /bin/true を確かめ、120秒で健全にならなければ docker stop。道具は /fhd/llmcmp/ に置いて動かす（作業場所 /app は書けない）。

## 6. 手順（人の ! 実行の部分は PO）
（１）準備（AI）: 道具と台本を作り審査を通す。gold_v1.tsv と score_v102.py の sha256 を記録。V102_RESPONSE_SCHEMA を JSON に書き出す。
（２）job id の対応（AI、読み取りの窓口）: 100投稿の source_message_id → extraction_jobs.id。1投稿に1件でなければ止まる。N（§4）と直近30日の Gemini 費用もここで数える。
（３）Gemini（PO が ! で実行）: vps_run_gemini.sh。取り寄せ。
（４）Claude 1件の試し（AI、手元）: haiku で1件。確かめる: `--tools ""` と `--json-schema` を一緒に使えるか／答えが result と structured_output のどちらに入るか／呼び出しが1回か（iterations 1件。num_turns は §5-2 の決まり）／thinking_tokens > 0 か（--effort high が効くか）／thinking が output の内数か／標準入力で渡せるか／定義に追加の制約を求められないか。どれかが不可なら止めて設計へ戻す。
（５）Claude（AI、手元）: haiku 100件 → sonnet 100件。（３）と同じ日、作業の少ない時間帯。
（６）変換（PO が ! で実行）: vps_convert.sh。取り寄せ。
（７）採点と表（AI、手元）: split → score_v102.py → summarize.py。§4 の「本番の解析結果に書いた件数0件」を数える。
（８）片付け（PO が ! で実行）: 取り寄せと sha256 照合が済んだら、本番サーバーの /home/ubuntu/fhd-test/llmcmp/ を消す（仕入元の文字列を本番サーバーに残さない）。手元の記録は ~/CC報告ファイル-keep/llm-compare-20261030/ に残す。

## 7. 影響範囲
- 本番の解析・画面・DB の解析結果: 変えない。
- 本番サーバー: 別の箱を一時的に動かす（過去の f_dm 試験と同じ）。Gemini を最大 約300回呼ぶ（見込み 約3.6USD、上限 5.00USD）。
- 使用量の記録帳 llm_usage_events: 最大 約300行増える（purpose=line_extraction_shadow）。
- PO の Claude サブスク: haiku・sonnet 各100回の分を使う。その間、PO 自身や他の作業の Claude が上限に当たる恐れがある（§8-2）。

## 8. リスクと対処（PO の判断が要るものを含む）
1. 【PO 判断】「本番に書いた件数0件」の読み方: 使用量の記録帳に最大約300行書く。解析結果には書かない。→ 承認時に確認する。
2. サブスクの上限: sonnet の途中で上限に当たると、ほかの作業も止まる。→ 作業の少ない時間に回す。上限の返事で即停止し、その件数を結果として記録する。
3. 【PO 判断】社外秘の文字列を Anthropic へ送ること: 仕入元の文字列 100件×2モデル分を、サブスク経由で Anthropic に送る。→ 承認時に確認する。
4. 社外秘の置き場: 組み立てた文字列・答えは ~/CC報告ファイル-keep と本番サーバーの箱の中だけ（実施後に消す、§6（８））。PR・チャット・ボードに載せない（ADR-1045 の見張りが働く）。design.md 末尾の結果欄に書くのは集計値だけ（投稿 id・仕入元名・誤りの一覧は書かない）。
5. 同じ条件にできない点（temperature、考える量の中身、Claude の土台 約600トークン、やり直しの決まり、時間の中身）: 表に「そろえられなかった点」として書く。
6. --json-schema が大きな入力で守られない: 手順（４）で止める。

## 9. 代替案と選んだ理由
- A（採用）Gemini は本番サーバーの箱で prompt_ab、Claude は手元の Mac で同じ文字列: 鍵を動かさない。Gemini の呼び方が本番と同じ関数。前例と手順書がある。
  - 【PO 判断】手元の Mac で試験を動かすことは、PO 決定「実装と試験はクラウドで動かす」（2026-10-26）の例外になる。理由: (a) 今回測るのは「PO のサブスクで Claude を回したとき」で、そのログインがあるのは手元の Mac と PO のスマホだけ、(b) 仕入元の文字列を新しいクラウドに置かない。
- B 手元の Mac で Gemini も直接呼ぶ: 本番に何も書かない。ただし Gemini の鍵を Mac に置く必要があり、呼び方を作り直すので本番との差が入る。
- C Claude をクラウドで回す: サブスクのログインをクラウドに置く道が未確立。仕入元の文字列をクラウドに置く。不採用。
- D 10/20 の写し（f_ct）を使う: 指示書が今の本番と違うので「同じ条件」にならない。不採用。

## 10. 戻し方
- 製品は変えないので戻すものは無い。試験の道具は scripts/accuracy/llm_compare/ を消せば消える。本番サーバーの箱は `docker stop`、置いたファイルは §6（８）で消す。

## 11. 維持する担当・仕組み
- 一回きりの試し。結果（集計値だけ）は ~/CC報告ファイル-keep/llm-compare-20261030/ と、この design.md の末尾の結果欄に残す。続けるかは結果を見て PO が決める。

## 12. 外部事例
- 使わない。理由: 判断の根拠はこの会社の正解表で実際に回した数で作る指示（PO「エビデンス確立して答えてくれ」）であり、他社の数は条件が違って比べられないため。

## 13. 実装カード（PO 承認後に Sonnet へ渡す）
- 作るファイル: scripts/accuracy/llm_compare/{capture_prompt_ab.py, run_claude.py, split_snapshot.py, summarize.py, fhd_snapshot.py（写し・sha256 を README に記録）, v102_response_schema.json, vps_run_gemini.sh, vps_convert.sh, fetch_results.sh, README.md}
- 触らない: backend/, frontend/, migrations/, .github/, scripts/accuracy/score_v102.py, 本番の設定。
- 守ること: §5-1 の差し替え先（prompt_ab 側の名前）／成功後だけ保存／test-id ごとの別名／§5-2 の停止条件と確かめ／`--bare` 不使用／§5-3 の一括 convert と split の分け方／§5-5 の健康診断の上書き。
- 試験（手元）:
  - split_snapshot.py: 手元の f_ct の写し（~/CC報告ファイル-keep/accuracy-gold-20261020/sample/snapshot/ の100ファイル）に tag="f_ct"・repeat=1・source_message=<投稿id> の3列を先頭に付けて1本の TSV にしたものを入力にし、分けた結果が元の100ファイルとバイト単位で一致すること。
  - summarize.py: 上で分けたフォルダを score_v102.py にかけた出力を入力にし、~/CC報告ファイル-keep/accuracy-gold-20261020/score/ の f_ct の採点結果と数が一致すること（どのファイルと比べたかを報告に書く）。
  - capture_prompt_ab.py: prompt_ab の call_gemini_raw_copy_v8 を偽の関数に差し替えた単体試験で、成功時だけ保存・失敗時は保存しない・別 test-id で名前が重ならないこと。
  - run_claude.py: claude を偽の命令に差し替えた単体試験で、rc≠0・is_error・時間切れ・別モデル混入で止まること。

## 結果（実施後に記入。集計値だけ）

実施: 2026-10-30〜31。対象100投稿（正解表 gold_v1 の1480行）。Gemini 3回・Haiku 1回・Sonnet 1回。集計は summarize.py（出力は手元の非公開の置き場。仕入元の文面はここに載せない）。

| 項目（判定に使う） | Gemini 1/2/3回目 | Gemini平均 | Haiku | Sonnet |
|---|---|---|---|---|
| E1 違う件数（率） | 29 / 30 / 37 | 32.0（97.8%） | 53（96.4%） | 29（98.0%） |
| E2(AI段) 違う件数 | 3 / 2 / 3 | 2.67 | 3 | 3 |
| E3(AI段) 違う件数 | 2 / 2 / 2 | 2.0 | 2 | 1 |
| C1 読み落とし | 2 / 2 / 2 | 2.0 | 2 | 2 |
| 余分 | 0 / 1 / 1 | 0.67 | 0 | 0 |

| 項目（参考） | Gemini 1/2/3回目 | Haiku | Sonnet |
|---|---|---|---|
| 入力トークン | 611038 / 611038 / 611038 | 873779 | 871674 |
| 出力トークン | 52174 / 52856 / 50837 | 416581 | 92031 |
| 考えたトークン | 386062 / 383518 / 386334 | 367035 | 44762 |
| 1件の時間 中央値・最大（秒） | 14.5・46.6 / 14.8・48.4 / 14.9・41.4 | 21.5・124.0 | 17.8・61.1 |
| 合計時間（秒） | 1612.5 / 1574.5 / 1593.0 | 2711.8 | 2040.1 |
| 定価換算（実際の請求ではない） | - | 0.365 USD | 4.07 USD |

判定（§4 の式のまま）:
- Haiku: 正答率 不合格（E1 が Gemini 平均を下回る）。サブスクで動く 合格（100/100）。回数の上限 合格（N=99、約0.7時間）。費用 合格（追加0円 ≦ Gemini 直近30日 40.6629 USD＝6353円、為替 156.23円/USD・2026-09-17 の値。10/31 の値は見つからなかった）。
- Sonnet: 正答率 不合格（E2 が 3件で Gemini 平均 2.67件を下回る。差は1件未満で、Gemini 自身の3回の幅 2〜3件の中。E1・E3・余分は Gemini 平均より良い）。サブスク・回数の上限（約0.6時間）・費用は合格。
- 本番の解析結果に書いた件数0件: 合格（extraction_items・analysis_results 各1492行の md5 が実施前後で一致。記録帳の行 300 ＝ Gemini 呼び出し 300、2.425979 USD）。

実施中の直し: 変換の箱を本番 worker と分けた（81f2b533f。2回 rc=137 で終わらされたため）。採点で Gemini 2回目に在庫の値 none が1件あり、score_v102.py に --a4-extra-system を足して NG として数えた（3c45eba71、試験18件合格）。
