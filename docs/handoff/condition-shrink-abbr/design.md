# design: 状態の略語を足す前の試し（本番を変えずに 134 投稿をやり直して前後を比べる）

状態: 設計審査済み（Opus 自己審査、§9）。PO 実装承認 2026-11-09（「1」）。根拠は recon.md（同じフォルダ）。

## 1. 目的と成功条件

- 目的: 状態の語 5 つ（シュリあり／シュリンク有り／シュリンク有／有〆／有り〆）を本番の状態の表に足したとき、何が良くなり何が悪くなるかを、足す前に全部数える。語ごとに「足す／足さない」を PO が表で決められるようにする。
- 対象: 2026-10-10 以降の v102 の投稿のうち原文に上の語を含む 134 投稿・6,513 件（recon §3-4）。
- 対象外: 本番の状態の表を変えること（試しの結果で PO が決めた後、別便で ADR-1007 の 5 つの SQL の手順）。指示文・Gemini・製品コード（backend/app）の変更。

| 基準 | 検証方法 |
|---|---|
| K1 揺れ 0: 語を足さないやり直しを 2 回流し、全列・全件で差 0 | 差の道具の summary.tsv が全列 0、件の数が両方同じ |
| K2 語が効いている: 語を全部足した回で、状態の根拠に足した語が出る件が 1 件以上 | 差の道具の「足した語が根拠に出た件の数」が 1 以上（0 なら差し替えが効いていない＝試しは無効） |
| K3 漏れなく一覧: どれかの列が変わった件・件の数が変わった投稿を全部、原文の行と並べて出す | changed_any.tsv の行数＝summary の「どれかの列が変わった件」の数。post_counts.tsv に件の数が違う投稿が全部 |
| K4 本番に書かない: 試しの前後で、134 投稿の解析結果の行数と最終更新時刻が同じ | 読み取り専用の鍵で試しの前と後に同じ問い合わせを流し、出力が一字一句同じ |
| K5 費用 0 円: Gemini を呼ばない | 道具の最初で Gemini の呼び出しを「呼ばれたら止まる」に差し替える（既存）。止まった件 0 |
| K6 判定: 変わった件を Opus が原文で 1 件ずつ「良くなった／悪くなった／意味は同じ」に分け、語の組ごとに表にする | 表の合計が K3 の件数と一致。PO は「悪くなった 0 の組だけ足す」を表で判断できる |

## 2. やり方（変更前後）

- 変更前: やり直しの道具（recon §3-2）は状態の語を差し替える口を持たず、差の一覧は状態が変わった件だけ。
- 変更後: 製品コードは変えず、新しい台本を 2 つと、本番で流す台本を 1 つ足す（§8 のカード）。
  - 語を足す台本: 状態の表を読んだ直後に、記憶の中だけで指定の行の語に指定の語を足し、除外語用の語も作り直してから、既存の道具でやり直す。取引は読み取り専用にする（書けば DB が拒む）。
  - 差の台本: どれかの列が変わった件と、件の数が変わった投稿を全部出す。Mac で動く（本番のコードを読まない）。
  - 本番で流す台本: PO が `!` で実行。本番 worker と別の箱で、6 回を順に流す。
- 6 回の中身:

| 回 | 足す語 |
|---|---|
| base1 | なし |
| base2 | なし（K1 の揺れの確かめ） |
| A | シュリあり |
| B | シュリンク有り・シュリンク有 |
| C | 有〆・有り〆 |
| ALL | 5 つ全部 |

- 比べ方: base1 と base2（K1）、base1 と A・B・C・ALL（K2・K3）。組ごとに分けるのは、どの語が良く／悪く効いたかを分けるため。

## 3. 影響範囲

- 本番の DB: 読むだけ（取引を読み取り専用にする・1 投稿ごとに rollback・K4 で確かめる）。
- 本番のサーバー: 別の箱で動く。本番 worker は止めない。健康診断の上書きを付ける（付けないと本番の警報が鳴る。recon §3-3）。置き場は `/home/ubuntu/fhd-test/condwords`。取り寄せ後、中身の JSONL を消す。
- 製品コード・CI 設定・本番のデータ: 変えない。

## 4. 代替案

| 案 | 採否と理由 |
|---|---|
| A 語を本番に足して朝の点検で 14 日見る | 採らない。悪くなった件がお客さんの在庫表に出てから分かる |
| B 行の判定だけを写した試算（実施済み 169 行） | 不十分。件の商品・値段・まとまりへの影響が分からない |
| **C 既存の道具に台本を足して本番の写しの上でやり直す（この設計）** | 採る。本番と同じコードで、費用 0 円、本番を変えない |
| D 製品コードのやり直しの道具に口を足してデプロイ | 採らない。デプロイが要り、製品コードに試し専用の口が残る |

## 5. リスクと対処

- 差し替えが効かない → K2 で 0 なら試しは無効として止める。
- 件の位置がずれて全部が「変わった」に見える（行の役割が変わり件が増減する）→ post_counts.tsv で件の数が違う投稿を別に出し、その投稿は Opus が原文で前後を丸ごと見比べる。
- 重くて本番が遅くなる → 別の箱で 1 回ずつ順に流す。前例どおり、止めたいときは箱を止める一行を台本が表示する。
- 社外秘の文字列 → 出力は `/Users/tanizawashingo/CC報告ファイル-keep/shime-auto-check/multistate/abbr/replay/` に置き、PR に載せない。本番の置き場の JSONL は取り寄せ後に消す。

## 6. 維持する担当・仕組み

- 台本は `scripts/accuracy/condition_words/` に置き、今後ほかの語を足す前にも同じ手順で使う（語と行の code を引数で渡す）。試験は同じフォルダの pytest（DB 不要）。
- 結果と判定の表は REPORT.md（朝の点検の記録）に 1 行で場所を残す。

## 7. 外部事例

- 使わない。理由: 自社の保存済みの答えを同じコードでやり直す比較で、外の事例は判断の根拠にならない。

## 8. 実装カード（クラウドの Sonnet 向け・PO の実装承認の後に渡す）

0. 受領確認の 1 行。`git fetch origin && git checkout -B release/condition-abbr-trial origin/release/condition-abbr-trial`（無ければ origin/main から作る）→ `git log --oneline -1`。
1. 読む（変えない）: `backend/app/tools/v102_replay_diff.py` 全部、`backend/app/services/line_analysis_v102_svc.py:217-241`、`backend/app/services/extraction_judgement_svc.py:262-275`、`backend/app/services/gemini_raw_copy_v102_product_first.py` の `with_cond_terms`、`scripts/accuracy/llm_compare/vps_convert.sh` 全部。
2. 新設 `scripts/accuracy/condition_words/replay_words.py`:
   - `add_words(masters, adds: dict[str, list[str]]) -> dict`: 新しい masters を返す（元は変えない）。cond_entries のうち code が adds にある行だけ、新しい辞書で search_kw の末尾に `,語` を足す（既にある語は足さない）。`masters["product_first"]` は `with_cond_terms(masters["product_first"], build_cond_terms(新しい cond_entries))` に置き換える。adds の code が cond_entries に無ければ ValueError。
   - 入口 `python replay_words.py --posts F --out JSONL [--add CODE=語,語]`（`--add` は 0 回以上）: 接続は `v102_replay_diff.main` と同じ `_get_sync_session`。最初に `SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY` を流す。`svc.load_v102_masters` を「元の関数の結果に add_words をかけたもの」に差し替えてから `v102_replay_diff.replay(session, posts, out)` を呼ぶ。標準出力に統計と、足した後の各 code の search_kw の md5 を出す。errors が 0 でなければ終了コード 1。
3. 新設 `scripts/accuracy/condition_words/diff_any.py`（app を import しない）: `python diff_any.py BEFORE AFTER --out-dir D --words 語,語`。キーは（post_id, index）。出力: `summary.tsv`（列ごとの差の件数・どれかの列が変わった件の数・前だけ・後だけ・後で condition_basis に --words のどれかを含む件の数）、`changed_any.tsv`（post_id・index・変わった列の名前・変わった列の前の値と後の値を JSON で）、`post_counts.tsv`（件の数が前後で違う投稿の post_id・前の数・後の数）。
4. 新設 `scripts/accuracy/condition_words/vps_replay.sh`（PO が `!` で実行。AI は実行しない）: `run <出力フォルダ> <origin/main の40桁sha> <posts.txt>` と `fetch <出力フォルダ>`。vps_convert.sh と同じ止め（deploy 中・HEAD 不一致・出力の上書き）、同じ健康診断の上書き・別の箱・`-e PYTHONPATH=/app`・裏で動かす形。置き場 `/home/ubuntu/fhd-test/condwords`。§2 の 6 回を順に流す（CN0003 に足す）。fetch は JSONL・標準出力・標準エラーを取り寄せ、その後で本番側の JSONL を消す。
5. 新設 `scripts/accuracy/condition_words/test_condition_words.py`（DB 不要・架空のデータ）: add_words が指定の code の行だけ変える／元の masters を変えない／同じ語を二重に足さない／cond_terms に新しい語が入る／無い code で ValueError。diff_any が小さな JSONL 2 つで summary・changed_any・post_counts を期待どおり出す。
6. `ruff check scripts/accuracy/condition_words/` と `cd backend && python -m pytest -q ../scripts/accuracy/condition_words/test_condition_words.py`（場所が合わなければリポジトリの設定に合わせ、出力を貼る）。
7. `git add` は §2〜§5 の 4 ファイルだけ（名前を並べる）。commit 文 `test(accuracy): 状態の語を足した前後を本番を変えずに比べる台本`、末尾に空行と `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。push 先 `release/condition-abbr-trial`。
8. 合格基準（出力を貼り、判定は Opus）: ruff `All checks passed!`／pytest failed・error 0／`git diff --stat origin/main..HEAD` に出るのは §2〜§5 と本設計の文書だけ／`git diff origin/main..HEAD -- backend` が空。
9. 止まる条件: 1 の読んだ中身がカードと違う（関数の名前・引数が無い等）とき、推測で直さず `NEEDS_DECISION:` で止まる。

## 9. 設計審査（Opus 自己審査・独立の審査ではない）

- 判定: APPROVE（実装可能）。
- 根拠: 語の流れが cond_entries 1 か所に集まっていることを recon §3-1 で確かめた。既存の道具の差し替えの口（`svc.load_v102_masters` をモジュール経由で呼ぶ、v102_replay_diff.py:103）が使える。本番で流す形は前例（vps_convert.sh）どおり。受入条件はどれも数か○×で判定できる。
- 未解決: 所要時間は未測定（§5 で止め方を用意）。K1 で揺れがあれば、揺れる列を外して比べるかを PO に戻す。
