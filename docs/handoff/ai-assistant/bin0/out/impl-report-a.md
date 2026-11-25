受領確認: card-bin0a を読んだ

# 便0-A 実装報告（2 回目の流し）

## 流した手順

- 1（作業場所）: `new-worktree.sh release/ai-assistant-bin0 --claude` で作成（起動の失敗は無視）。`git switch -C … origin/release/ai-assistant-bin0` で合わせ、`git log --oneline -1` = `35fc65dd3` が origin と一致（○）。事前確認: `git config user.name` = `Claude`・`origin/main` = ea800930e（○）。
- 2（Docker・完成品）: `dockerd` 起動・`docker info` 通過。digest 固定で pull（1 回 429 を受け、同じ digest でやり直して成功）。`hermes --version` = `Hermes Agent v0.23.4`（○）。
- 3（ソース確かめ）: S1〜S12 を読んだ（`probe-a-20261125.md` 表 1・生の行は `raw/3-grep.txt`）。S6 は会話そのものを消す口（API 側の説明は hard delete・1 トランザクション・記録ファイルも消す）で、止まる条件には当たらない。ただし消す本体の実装は読めていない（型の定義だけ）ので、行が実際に消えるかは便0-B の K7 の探しで確かめる。未確認: S7（`response_format` はソースに 0 件）・S8（既定は空・実物は未）・S9（候補のみ）・S10（記録の返り形）・S12（部屋ごとの見込み）。
- 4（道具）: `coordinator-soul.md`・`config.yaml`・`setup_profiles.sh`・`run_bin0.py`・`test_run_bin0.py`・`k3-answers.json`・`k4-cases.json`・`k8-cases.json`・`README.md` を `docs/handoff/ai-assistant/bin0/` に置いた。
- 5（本物の Hermes・ログイン無し）: P1〜P9 を流した（表 2）。P2 3 部屋 200・P3 鍵なし/別の部屋 401・P4 無い部屋 404・P5 無い番号は部屋の鍵で 404・鍵なし 401・P6 最大 251.3 MiB（アイドル）・P9 状態 200 のまま `finish_reason=error`。P7 は `--tmpfs /run:exec` と `SETGID・CHOWN・SETUID・FOWNER` の 4 権限で立った。
- 6（pytest）: 9 passed（`raw/6-pytest.txt`・1 回目で全部通った）。`backend/uv.lock` はできていない。
- 7（仕上げ）: 7a 触ったのは `docs/handoff/ai-assistant/bin0/` の中だけ（外 0 件・○）。7b 鍵の値は bin0/ の中に 0 件（○）。7c の commit と 7d の push・sha の照合は、この報告のあとに行い、結果は最後の返事に書く。

## カードと違った所・気づき

- P7: `--tmpfs /run` だけでは `noexec` で s6 が起動しない（終了コード 126）。`/run:exec` に変えた。権限の問題ではないので権限は戻していない。
- P9: ログイン無しの chat は誤りの状態ではなく HTTP 200・`finish_reason=error`・usage 0 で返る。台本はこれを `finish_error` として数える（`run_bin0.py` の `chat`）。便1 でアプリが呼ぶときも、状態だけで成否を決めない注意が要る。
- P6: 10 秒おきの 6 回ではなく、`docker stats` の連続出力（約 2 秒おき・62 秒・123 サンプル）で取った。sleep で待たないため。値はログイン無しのアイドル。会話を流している間の最大は便0-B。
- `setup_profiles.sh`: 容器の中の hermes 利用者は `/tmp/bin0-secrets`（root・700）を読めないため、鍵は 600 の環境変数ファイルで渡し、終わったら消す形にした。
- `git config user.name` は `Claude`（カードの想定と違う。PR は作らないので支障なし）。

## 止められた命令と見張りの文面

- Bash の検索命令に SQL の削除の文を含む文字列を入れたところ、見張りが止めた: `BLOCKED(cloud): 'DELETE FROM' は不可逆操作です。クラウドでは行えません。手元で PO の承認を得て実行してください。`。同じ検索は言い換えて流し直していない。S6 の確かめには、別の動作としてファイルの該当範囲を Read で読んだ（`persistence/conversation/sessions.py:1025-1064`）。
- 同じ種類で、`rm -rf` を含む命令も 1 回止められた（`BLOCKED(cloud): 'rm -rf' は不可逆操作です`）。`rm` を使わず、別の新しいディレクトリに取り直した。

## K3 で迷った件

- **i7**（みどり屋さんの請求）: 会社名が「みどり屋」か「みどり屋さん」か文から決められないので `company_name` を入れていない（単価 1500 だけ入れた）。Opus が PR で確かめてから測る。
- 他に迷った件は無い。i3 は「（北風商会）」を会社名とした。i8 の単価は書かれていないので null。i4 の期日は fixed_now の年（2026）で `2026-11-30`。e2・e3・e7 は終わりの時刻が文から決まらないので `end` を入れていない。e5 は `is_all_day` だけ。

## 後片付け

- 試しの容器（`bin0-src`・`bin0-run`・`bin0-hard`）と volume `bin0-data` は消した。`/tmp/bin0-secrets/`（クラウドの中・commit 対象外）は残る。無名の volume が 1 つ残っている（1 回限りの `docker run --rm` の置き土産）。

DONE: 本 commit（sha は push 後の最後の返事に書く）
