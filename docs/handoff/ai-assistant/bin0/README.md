# 便0 の試しの道具（便0-A で置いた分）

- 設計: [../design.md](../design.md) §4・§5・§8。カード: [../card-bin0a.md](../card-bin0a.md)。ソースの確かめと本物のログイン無しの確かめ: [out/probe-a-20261125.md](out/probe-a-20261125.md)。
- 完成品: `nousresearch/hermes-agent@sha256:ef0650d523ee1b5ab32c779acabc446d9936869a9932591553688a62bcf0c42f`（v0.23.4）。別の版に替えない。
- 鍵は `/tmp/bin0-secrets/`（chmod 700）のファイルにだけ置く。画面・報告・commit に値を出さない。

## 置いたもの

| ファイル | 役目 |
|---|---|
| config.yaml | Hermes の設定（multiplex・道具なし・覚え書き off・振り返り off・切り替え off） |
| coordinator-soul.md | まとめ役の人格 |
| setup_profiles.sh | 3 部屋（coordinator・calendar・invoice）を volume に作る。係の人格は secretary-agent/prompt.txt を作るときに写す |
| run_bin0.py | 束を流す台本（K1〜K3・K5・K9 の材料・K4・K8） |
| test_run_bin0.py | 台本の確かめ（偽の Hermes・9 件） |
| k3-answers.json・k4-cases.json・k8-cases.json | 正解表・K4 の頼み 15 件・K8 の頼み |

## 便0-B で流す命令（PO が居るとき）

以下の `D` は上の完成品の digest 付きの名前、`S=/tmp/bin0-secrets`。

1. **鍵を作る**（未作成なら）: `mkdir -p $S && chmod 700 $S && for r in default coordinator calendar invoice; do openssl rand -hex 32 > $S/key-$r; done`。`keys.json`（部屋名→鍵の JSON）と `default.env`（`API_SERVER_ENABLED=true`・`API_SERVER_HOST=0.0.0.0`・`API_SERVER_KEY=<key-default>`）は 600 で作る。
2. **部屋を作る**: `docker volume create bin0-data` → `bash docs/handoff/ai-assistant/bin0/setup_profiles.sh bin0-data`（標準出力の `prompt_txt_sha256` を記録）。
3. **起動**（本番に近い守り）: `docker run -d --name bin0-run --read-only --cap-drop ALL --cap-add SETGID --cap-add CHOWN --cap-add SETUID --cap-add FOWNER --security-opt no-new-privileges:true --tmpfs /tmp --tmpfs /run:exec --env-file $S/default.env -v bin0-data:/opt/data -p 127.0.0.1:8642:8642 $D gateway run`。`curl http://127.0.0.1:8642/health` が 200 になるまで確かめる。（`/run` は `:exec` が要る。無いと s6 が起動しない。実測は probe の表 2・P7。）
4. **ログイン**（試し用に 1 回・device code・PO が打つ）: `docker exec -it -u hermes bin0-run hermes auth add openai-codex`。部屋ごとか全体かは便0-B の最初に確かめる（S12。部屋ごとなら `hermes -p <部屋> auth add openai-codex` を 3 部屋に流す）。
5. **最初の確かめ**（design.md §5「頭の渡し方」①〜③・`response_format`・使った量の読み先 K9・記録から道具の実行を読む道 K4）は、未確認の項目として便0-B の最初に 1 件ずつ流して記録する。
6. **台本**: `cd backend && PYTHONPATH=. uv run --no-project --with httpx==0.28.1 --with pydantic==2.10.6 --with jsonschema==4.23.0 python ../docs/handoff/ai-assistant/bin0/run_bin0.py --target hermes --set main --model openai-codex/gpt-5.6-terra --keys-file $S/keys.json > out/main.tsv 2> out/main.err`。続けて `--set k4`・`--set k8`。決まり帳つきで比べるときは `--rules docs/handoff/secretary-rulebook/bin2/dummy-rules.json`。
7. **K6（メモリ）**: 台本を流している間、別の端末で `timeout 600 docker stats bin0-run --format '{{.MemUsage}}'`（約 2 秒おきに出る）を取り、最大を記録する。10 秒おきの代わりに 2 秒おきで測る（便0-A で確かめた形）。
8. **K7（残らない）**: 台本のあと `docker exec bin0-run grep -rIl -F -f <頼みの文のファイル> /opt/data`（頼みの文は 1 行 1 件のファイルにして容器の外から渡す。結果は件数だけ記録する）。
9. **今の秘書**（同じ日・本番を読む日の同意票のあと）: `--target secretary --url <秘書の URL> --model <今の model>`。
10. **後片付け**: `docker rm -f bin0-run`・`docker volume rm bin0-data`・`/tmp/bin0-secrets/` の鍵のファイルを消す（消す前に PO の確認）。

## 便0-B の最初に確かめる（便0-A では未確認）

- ①組で送ると返事の model と Hermes の記録がその頭になる（止めどころ）・②違う provider の動き・③model だけ送ったときの落ち先
- `response_format` を読むか（ソースに 0 件。実物で）
- K9: 返事の使った量と Hermes の記録の突き合わせ（候補: `GET /health/detailed` の metrics と、会話の行の input_tokens・output_tokens）
- K4: `GET /p/<部屋>/api/sessions/<番号>/messages` の返り形（台本は role=tool か tool_calls ありを数える。形が違えば `-`）
- `hermes auth add openai-codex` が部屋ごとか全体か（S12）
- DELETE が会話の文を実際に消すか（K7 の探しで確かめる）
