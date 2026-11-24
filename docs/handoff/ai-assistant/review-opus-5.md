# 設計審査 5回目 — 審査役（Claude Opus・手元）

対象: HEAD a36832bd5 の design.md 第2.3版。審査日 2026-11-25。読み取りだけ。

設計審査 5回目（審査役・Opus・読み取りだけ）

判定は REVISE です。ただし直しは小さく、3か所の書き直しで済みます。
- 前回の直す点 1〜6 は、ほぼ本文に入りました（○5件・△1件）。
- 担当表の頭の欄に `/` を含む値は入ります。
- 「頭の渡し方」の作りは、Hermes の説明書と合っています。

ただし次の3つが残っています。
- 便0 の確かめ②「違う AI 会社を送ると 400 で断られる」は、説明書に根拠がありません。
- `/` で分けるときの決まりが書かれていません。
- 表題の版の番号が古いままです。

対象は worktree の HEAD a36832bd5（design.md・requirements.md）です。ファイルの書き換え・commit・push はしていません。

１：review-opus-4 の直す点 1〜6 の行方（行番号は design.md）

| # | 判定 | 根拠 |
|---|---|---|
| 1 Q8 を §0 に入れ、関係する所を Q8 どおりに直す | △ | 【事実】Q8 は :29 に入りました。:109（形がくずれたら1回だけやり直す）、:114（試し用に別に1回ログイン）、:150（§9-1 決定済み）、:107（会話を消して全文を残さない＝Q8 で PO 決定）も直っています。:16 の状態は第2.3版になりました。ただし :4 の表題が「第2.2版・草案」のままで、:16 と食い違っています |
| 2 頭の渡し方を1つの形にする | ○ | 【事実】:37 は「§5 の1つだけ」です。:98 は「model 欄に AI 会社/頭 の組を入れ、アプリが分けて送る。model_routes の別名は使わない」です。:103 は「両方付ける」です。3か所が同じ形になりました。便0 の最初の確かめは :99 にあります。ただし :99 の②は説明書と合いません（下の２） |
| 3 容器の守りを「同じ形で立つか便0 で測る」に直す | ○ | 【事実】:113 に入りました。中身は次のとおりです。<br>・root で立ち上がり、UID の付け替えと利用者の切り替えをする（docker/stage2-hook.sh）<br>・同じ形で立つかを便0 で測る<br>・立たなければ、最小の権限と理由を一覧にする<br>・Hermes が書き込む場所の一覧を取る<br>・本番の守りは PO が決める |
| 4 クラウドで Docker が使えるかの確かめ | ○ | 【事実】:112 に入りました。動かなければ止めて PO に相談します。別の入れ方には相談なしに切り替えません |
| 5 unknown_execution・消す口の通り方 | ○ | 【事実】unknown_execution は :107 に入りました（snapshot を取り直して1回だけやり直す、残れば番号を記録し K7 で確かめる）。消す口が `/p/` と部屋の鍵で通るか、ダッシュボードが要るかは :108 に、便0 の最初の確かめとして入りました |
| 6 K7 の探す範囲・K2 の数え方 | ○ | 【事実】K7 は :86 で、データの置き場全体（ログ〈agent.log など〉を含む）を grep -r で探す形になりました。K2 は :81 で、やり直し1回の後で数え、やり直した件数も別に記録する形になりました |

２：§5「頭の渡し方」と説明書・担当表の照合

出典は Context7 /nousresearch/hermes-agent（main）です。版は分かりません。

（１）説明書と合っている点
- 【事実】頼みの `model` と `provider` を両方送る形は、説明書の口の作りどおりです。
  - 出典は api-server.md「Per-request model selection」と「POST /v1/chat/completions」です。
  - `provider` は「Hermes provider slug」です。
  - provider の無い model は `/v1/chat/completions` では無視されます（`direct_model_requests: true` のときは別）。
  - :98・:103 の書き方と合っています。
- 【事実】優先の順番は「① 会話の /model → ② model_routes の別名 → ③ 頼みの model/provider → ④ 全体の既定」です（同じ所）。
  - 別名を使わず、頼みごとに新しい会話の番号を付ける（:107）ので、①と②は効きません。
  - 頼みの組（③）がそのまま効く形になります。
- 【事実】`gpt-5.6-terra` は、ChatGPT 契約の Codex 用の頭の一覧 DEFAULT_CODEX_MODELS に入っています（hermes_cli/codex_models.py）。
  - 【未確認】この契約で実際に選べるか。:114 のとおり便0 で確かめます。

（２）説明書と合わない点（新しい指摘）
- 【事実】:99 の②「違う provider を送ると 400 で断られる」は、説明書に根拠がありません。
  - 説明書が 400 と書いているのは「model_routes の別名とぶつかる provider を送ったとき」だけです。原文は "If a request sends a `provider` that conflicts with a configured `model_routes` alias, Hermes rejects the request with `400`"（api-server.md「Per-request model selection」）。
  - 設計は別名を使いません（:98）。そのため、違う provider を送ったときの動きは説明書に書かれていません。
- 【推測】違う provider を送ると、その会社の鍵が無いための失敗か、別の誤りになると読めます。説明書で確かめたものではありません。
- そのまま便0 のカードにすると、正しく動いていても「②が落ちた」と判定される恐れがあります。
- 【事実】頭の名前そのものに `/` が入ることがあります。説明書の例は `anthropic/claude-opus-4.6`・`openai/o1-2025-12-17` です（website/docs/integrations/nous-portal.md、website/docs/guides/run-hermes-with-nous-portal.md）。
  - :98 の「`/` で分けて」には「最初の `/` で分ける」の決まりがありません。
  - 今の codex の組では困りません。ただし A/B で別の会社の頭を入れるときに分け方が割れます。
- 【未確認】:99 の③「model だけ送ると部屋の既定の頭に落ちる」について。
  - 説明書の書き方は「Global gateway config / environment defaults」です。
  - 部屋ごと（multiplex の profile ごと）の既定になるのかは、書かれていません。

（３）担当表の model 欄に `/` を含む値が入るか（実物）
- 【事実】入ります。`ai_job_choices.model` は `TEXT NOT NULL` で、値の決まりがありません。
  - 置き場は migrations/20261103_120000_create_ai_job_assignments.sql:30 です。
  - CHECK は job_key（:32）と provider（:33）だけです。
- 【事実】後の migration にも、model の決まりを足すものはありません。
  - `ai_job_choices` を触る migration は 4本です（20261024_100300・20261103_120000・20261111_120000・20261113_100000）。grep で確かめました。
  - migrations/20261024_100300_create_ai_cloud_views.sql:25 にも「値の決まりが無く自由に入る列」とあります。
- 【事実】使用の台帳の model 列も `TEXT NOT NULL` で、決まりはありません（migrations/20260930_150000_create_llm_usage_events.sql:31）。
- 【事実】アプリ側（backend/app/services/ai_assignment.py:17-38）は provider と model を読んで返すだけで、形は確かめていません。
- 【事実】provider に `hermes` を入れるには、:33 の CHECK を広げる migration が要ります。:97 のとおりです。

３：その他の新しい食い違い
- 【事実】:4 の表題が「第2.2版・草案」です。:16・:158 は第2.3版です。
- 【事実】:76 は「今の秘書は本番にしか無いので、その回だけ本番を読む許可を PO に取る」と書いています。
  - Q8（requirements.md:40）で、本番を読むことは承認済みです。
  - :139・:150 は「その日の同意票を1回取る」と書いています。
  - 中身は食い違いませんが、:76 だけ「許可を取る」と読めます。直さなくても進められます。
- 【未確認】台帳の model 列に何を書くかは決まっていません（組のまま、分けた頭、それ以外）。:53 は「どの頭」とだけ書いています。便1 の設計で決めれば足ります。

４：便0 の実装カードを書けるか
- 【事実】入っている材料
  - 確かめの段に入れる項目は、本文に止めどころと一緒に書かれています。前回の (a)〜(i) に当たるものは、:99・:107-114・:86・:88 にあります。
  - 合格の線 K1〜K9 は :80-88 で、PO 承認済み（Q8）です。
  - 担当は :140、場所の後片付けは :140 にあります。
- 足りないもの
  - (1) :99 の②の期待値。説明書の根拠がある形に直すか、合否に使わない観察の項目にする。
  - (2) model 欄の分け方（最初の `/` で分ける）。
  - (3) 前回の (j)、同じ日に今の秘書を測る台本と、Hermes 側の新しい台本。
    - 【事実】カードの中で作る物として書けば足ります。設計の本文に要る物ではありません。
    - 今の秘書の側は docs/handoff/secretary-rulebook/bin0/run_baseline.py を使い回せます（前回の審査で確かめ済み）。

(1) と (2) を直せば、カードは書けます。

５：判定

REVISE です。今回は軽い直しです。直した後の確かめは、差分を見るだけで足ります。

直す点
1. :99 の②「違う provider を送ると 400 で断られる」を直す。
   - 説明書の 400 は、model_routes の別名とぶつかったときだけです（api-server.md「Per-request model selection」）。
   - 「違う provider を送ったときの動きを記録する（合否には使わない）」か、項目を外す。
   - 止めどころは①のままにする。
2. :98 に分け方の決まりを足す。「最初の `/` で分け、前を provider、後ろを model とする」。
   - 理由は、頭の名前に `/` が入る例が説明書にあるためです（nous-portal.md の `anthropic/claude-opus-4.6`）。
   - あわせて :99 の③の「部屋の既定」を、「全体または部屋の既定（どちらかは便0 で記録）」に直す。
3. :4 の表題を第2.3版に直す。
   - できれば :76 の「本番を読む許可を PO に取る」も、「Q8 で承認済み・その日の同意票を1回取る」にそろえる。

PO が決めること
- 決めることはありません。上の 1〜3 は、説明書と本文の書き方を合わせる直しです。PO の決定（Q1〜Q8）は変わりません。

出典のファイル
- 審査対象:
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/ai-assistant/design.md
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/ai-assistant/requirements.md
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/ai-assistant/review-opus-4.md
- 確かめた実物:
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/migrations/20261103_120000_create_ai_job_assignments.sql:26-36
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/migrations/20261024_100300_create_ai_cloud_views.sql:25-26
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/migrations/20261111_120000_add_codex_secretary_choices.sql:5
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/migrations/20260930_150000_create_llm_usage_events.sql:31
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/backend/app/services/ai_assignment.py:17-38
  - /Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/backend/app/services/llm_budget.py:180-185
- Hermes の説明書（Context7・main）:
  - website/docs/user-guide/features/api-server.md（「Per-request model selection」「POST /v1/chat/completions」）
  - hermes_cli/codex_models.py（DEFAULT_CODEX_MODELS）
  - website/docs/integrations/nous-portal.md
  - website/docs/guides/run-hermes-with-nous-portal.md
