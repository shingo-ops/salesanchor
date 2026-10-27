# recon: v102 の既定の指示書を raw_copy_v101_f_dm に切り替え

関連 design: `docs/handoff/v102-prompt-fdm/design.md`

## 事実（根拠つき。基準は origin/main 77b40a1ae8fcbd57c01e9385b95ef3856d6e3584）

- 既定の指示書を決めるのはコードの定数: `backend/app/services/line_analysis_v102_svc.py:95`（`V102_ENGINE_VERSION = "v102-f_ct"`）、`backend/app/services/line_analysis_v102_svc.py:97`（`V102_PROMPT_KEY = "raw_copy_v101_f_ct"`）。
- 指示書は `backend/app/services/line_analysis_v102_svc.py:500-501` で extraction_prompt_config を prompt_key と is_active=TRUE で毎回引く（キャッシュなし。`backend/app/services/line_analysis_v102_svc.py:143-146`、`:174-183`）。
- f_ct を固定値で書いている行（変える行）:
  - `backend/app/tools/prompt_ab.py:15`、`backend/app/tools/prompt_ab.py:626`
  - `backend/tests/test_line_analysis_v102_pg.py:115`
  - `backend/tests/test_line_analysis_v102_svc.py:72`、`:74`、`:87`、`:312`
  - `backend/tests/test_prompt_ab.py:105`、`:689`、`:690`、`:693`、`:698`、`:928`
  - `docs/specs/line-analysis-tuning/README.md:19`（「既定は f_ct」）
- 定数を名前で使う行（定数に追随するので触らない）: `backend/app/tools/prompt_ab.py:78`、`:323`、`:493`、`backend/app/tools/reextract_v6_with_v102.py:217`、`backend/tests/test_line_analysis_v102_pg.py:169`。
- 残ってよい f_ct の文字（触らない）: `scripts/accuracy/` の各行（fetch_snapshot.py:5,26 ほか。scripts/ は危険パスで別便）、`backend/tests/test_v102_value_overrides.py:232`、`:353`（効くのは `v102:` の接頭辞だけ。`backend/app/services/line_analysis_v102_svc.py:159-160` の startswith）、`docs/specs/line-analysis-tuning/README.md:39`（#4128 の履歴の行）。
- 名前で固定していない読み手: `backend/app/services/v102_unit_price_check_svc.py:25,62`（`v102%`）、`backend/app/services/v102_transcription_svc.py:58,74`（`v102:%`）。

## 本番 DB 事前確認（読み取り鍵・2026-10-27 04:47 UTC）

```
133|raw_copy_v101_f_ct|True|1|5469|fe50593fa362da213e33663f85110381a6f3f97465553443e87ae0f0df8515fd
397|raw_copy_v101_f_dm|True|1|7773|84afd2e4e0094b542d5f1dada1fef39290aa6d997135296e78601fc945ac8b0c
377|raw_copy_v101_f_hd|True|1|6886|0ea18ba069dadf0b20060a4cbe5f5e41024d824aba890cc5840926c77cb833aa
```
（列: id / prompt_key / is_active / version / 字数 / 本文の sha256。本文そのものはリポジトリに置かない。f_dm の sha は試験の判定で使った値と一致）

## 既存 ADR 検索

- 指示書の既定 key を定めた ADR は無い（前回 `docs/handoff/v102-prompt-fct/recon.md` の検索結果と同じ。ADR-085 は指示書の DB 管理の関連のみ）。
- GO と マージの手順: ADR-1003（PO の委任に基づく Claude Opus の GO 発行）、`docs/adr/ADR-136-cc-bot-github-identity.md`（GO 記録の形）、ADR-135（main にマージ＝本番投入可）。
- 関連の正本: `docs/specs/line-analysis-tuning/README.md`

## #4128 との1対1の対応表

行番号は「#4128 の親での行→今回の行」（77b40a1ae 時点）。

| ファイル:行 | #4128 の変更 | 今回の変更 |
|---|---|---|
| `backend/app/services/line_analysis_v102_svc.py:51→95` | V102_ENGINE_VERSION f_c→f_ct | f_ct→f_dm |
| `backend/app/services/line_analysis_v102_svc.py:53→97` | V102_PROMPT_KEY f_c→f_ct | f_ct→f_dm |
| `backend/app/tools/prompt_ab.py:14→15` | docstring の既定 key f_c→f_ct | f_ct→f_dm |
| `backend/app/tools/prompt_ab.py:588→626` | --prompt-name の help の既定 key f_c→f_ct | f_ct→f_dm |
| `backend/tests/test_line_analysis_v102_pg.py:108→115` | version の前方一致 f_c→f_ct | f_ct→f_dm |
| `backend/tests/test_line_analysis_v102_svc.py:71→72` | build_prompt_version の引数 f_c→f_ct | f_ct→f_dm |
| `backend/tests/test_line_analysis_v102_svc.py:73→74` | key の期待値 f_c→f_ct | f_ct→f_dm |
| `backend/tests/test_line_analysis_v102_svc.py:86→87` | V102_PROMPT の期待値 f_c→f_ct | f_ct→f_dm |
| `backend/tests/test_line_analysis_v102_svc.py:281→312` | 偽の prompt_version f_c→f_ct | f_ct→f_dm |
| `backend/tests/test_prompt_ab.py:104→105` | コメント内の key f_c→f_ct | f_ct→f_dm |
| `backend/tests/test_prompt_ab.py:688→689` | V102_PROMPT の期待値 f_c→f_ct | f_ct→f_dm |
| `backend/tests/test_prompt_ab.py:689→690` | DB 読みの key 引数 f_c→f_ct | f_ct→f_dm |
| `backend/tests/test_prompt_ab.py:692→693` | prompt_name の期待値 f_c→f_ct | f_ct→f_dm |
| `backend/tests/test_prompt_ab.py:697→698` | ValueError の match f_c→f_ct | f_ct→f_dm |
| `backend/tests/test_prompt_ab.py:927→928` | prompt_name の期待値 f_c→f_ct | f_ct→f_dm |
| `docs/specs/line-analysis-tuning/README.md:19` | 「試作版で採用確定の指示書」の行の既定の書き換え（f_c→2026-10-11 以降は f_ct） | 「既定は f_dm（…切り替えまでは f_ct）」に書き換え |
| `docs/specs/line-analysis-tuning/README.md:39→40` | #4128 の行を足した（f_ct の行） | #4128 の行は書き換えず、直後に f_dm の行を足した。測定の宿題の書き添えは **1対1の外の追加** |

- コードの変更行は #4128 と今回で同じ15行（1対1）。
- #4128 にあって今回に無い行: `docs/handoff/v102-prompt-fct/` の design.md・recon.md の新規作成（今回は `docs/handoff/v102-prompt-fdm/` に別途ある）。
- 今回にあって #4128 に無い行: なし（README の測定の宿題の書き添えのみ1対1の外）。
