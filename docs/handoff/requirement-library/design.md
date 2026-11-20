# design — 要件の書類を作業の場面で目に入れる（草案 2026-11-21・審査前）

> この文書は何か: R1〜R4 を合格させる作り方・測り方・守り続ける仕組み。実装カードの元。
> 親: [../../specs/requirement-library/README.md](../../specs/requirement-library/README.md)／現在地: [recon.md](./recon.md)／KGI: [kgi.md](../../specs/requirement-library/kgi.md)／練習問題: [quiz.md](./quiz.md)

## 1. 目的と利用者に見える変化

- 目的: AI が機能に触る前に、その場所の決まり（ADR・設計書）を必ず目にする。決まりと食い違う計画を「不具合」と取り違えない（11/13 の会社の新規登録の件）。
- 変化前: 決まりは索引を自分で引けば見つかる。索引は主要 ADR だけ（151 個が載っていない。recon §2）。
- 変化後: (1) すべての ADR が索引に載るか、載せない理由が書かれる。(2) AI が決まりのあるファイルを開くと、その場で「この場所の決まり」が1回だけ示される。(3) 要件の書類を読まずに「不具合」と結論しかけたら、止めて読ませ、記録に残す。

## 2. 対象と対象外

- 対象: `docs/adr/FEATURE-INDEX.md`（表に「コードの場所」列と除外表を足す）、新しい CI 検査、`.claude/hooks/` の見張り 2 本と `.claude/settings.json` の登録、練習問題の測定。
- 対象外: 製品コード・DB・画面・ADR 本文・`workflow-lint.yml`。

## 3. 作り方（便ごと。各便のあと練習問題で測る）

### 便1 目録を漏れなくする（R1）

- 索引の各表に列「コードの場所」（`backend/app/routers/companies.py` のような glob。複数は `、`）を足す。
- 151 個の ADR を、(a) 既存の行に足す、(b) 新しい行を作る、(c) 末尾の新節「索引に載せない ADR」に「番号｜理由（置き換え済み・手順だけ・取り消し等）」で載せる、のどれかにする。11/13 の件は (a) で「会社」の行に ADR-097 と `docs/specs/db-ssot/deal-removal/design.md` を足す。
- 新しい検査 `scripts/ci/check_feature_index.py`: r1_count.py と同じ数え方で、索引にも除外表にも無い ADR 番号と、`docs/specs/README.md` に無い設計仕様書のフォルダを出し、1 件でもあれば失敗。`doc-index-reachability.yml` の run に1行足す（新しい必須チェックは作らない）。
- 試験: 抜けを1件わざと作った見本で失敗し、今の版で成功する。

### 便2 開いた瞬間に決まりを見せる（R2・R3）

- `.claude/hooks/requirement-context.py`（PostToolUse、対象 `Read|Edit|Write|MultiEdit`）: tool_input の file_path を索引の「コードの場所」と照らし、当たった行の「正準 ADR と設計書のパス」を `hookSpecificOutput.additionalContext` で返す。
- 同じ行は1つの会話で1回だけ（`$CLAUDE_PROJECT_DIR` 外の一時置き場に session_id ごとの印）。当たらなければ何も返さず、失敗しても作業を止めない（終了コード 0）。
- 文の形:「この場所には決まりがあります: ADR-097（会社はリードの子）。計画の前に docs/specs/db-ssot/deal-removal/design.md を読んでください。」

### 便3 読まずに「不具合」を止める（R4）

- `.claude/hooks/requirement-bug-claim.py`（Stop）: transcript_path を読み、最後の返事に「不具合・バグ」があり、その会話で `docs/adr/` か `docs/specs/` を1度も読んでいなければ、1回だけ `decision: block` で「要件の書類を読んでから判定してください」と返す（`stop_hook_active` が真なら止めない）。
- 止めた回を1行ずつ記録（日時・会話の番号・最初の 40 字）。R4 は週1回この記録の行数を数える。記録の置き場と週次の数え方は便3のカードで決める（agent-console の週次点検に1行足す案）。

## 4. 合格の判定

|基準|検証方法|
|---|---|
| R1 索引にも除外表にも無い ADR・設計仕様書 0 | CI `check_feature_index.py` が成功（PR の検査結果）と `r1_count.py` の missing 0 |
| R2 20 回中 18 回以上で正解の書類を開く | 便2のあと quiz を流し `count.py` の `R2` 値 |
| R3 決まりに触れずに反する計画 0 | 同じ 20 回の答えを quiz.md §2 の表で Opus が判定（`r3-judgement.md`） |
| R4 読まずに「不具合」0 | 便3の見張りの記録を週1回数える（本測定）。補助に count.py の `R4aux` |
| 見張りが作業を壊さない | 見張りの試験（当たる・当たらない・壊れた入力で終了コード 0） |

## 5. 代わりの案と選んだ理由

- 案A CLAUDE.md に全 ADR の一覧を入れる → 90 行の上限（`frontend/scripts/check-claude-size.js`）と ADR-1040 の「入口は短く」に反する。不採用。
- 案B 索引だけ直して見張りを作らない → 今も「引く義務」はあるのに引かれなかった（recon §4）。R2 が上がらない見込みが高いので、便1のあと測って確かめる。
- 案C（採用）索引を正本にし、見張りはその索引を読むだけ。決まりの置き場は索引1か所のまま（データを分散させない）。

## 6. 危ないことと対処

- 見張りの文が多すぎて邪魔 → 同じ行は会話で1回・当たったときだけ。
- 「不具合」の語は正しい不具合報告にも出る → 止めるのは「決まりの書類を1度も読んでいない」ときだけ・1回だけ。
- 索引の「コードの場所」が古くなる → 便1の CI で、glob が1つのファイルにも当たらない行を失敗にする。
- 戻し方: 便ごとに PR を分ける。見張りは `.claude/settings.json` の登録を外す revert で消える。

## 7. 外部の事例

- 確かめたもの: Eliav（指示を作業の場面に近づけると従う率が上がる趣旨）。出典と数は proposal 原稿の表を Opus が読んで確認済み。
- まだ確かめていないもの: CybeDefend・Vercel・Lance Martin・Coombs・Rulestack の数。**本設計の合格の根拠には使わない**。根拠は自分の練習問題の前後比較だけ。

## 8. 守り続ける仕組み

- 新しい ADR を足すと、索引に行か除外表が無ければ CI が落ちる（便1）。
- 見張りの記録は週1回数える（便3）。数え忘れは agent-console の週次点検で見る。
- 練習問題（quiz）は残し、索引や見張りを変えたら流し直す。

## 9. 審査

- 状態: 草案。クラウドの設計審査（architect）待ち。結果は本節に APPROVE／REVISE／REJECT・根拠・未解決で書き足す。
