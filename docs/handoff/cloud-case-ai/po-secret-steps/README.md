# 事例 AI の窓口: PO の秘密の置き方（台本 2 本）

どちらも PO が Mac で `bash` で実行する（secrets 変更のため PO 本人の GO が前提）。B のパスワードは VPS の新しい env ファイル（権限 600）にだけ書かれ、A の値は GitHub secret と Mac の Keychain にだけ置かれる。どちらも画面・引数・記録には出ない作りにしてある。

## 順番

1. **A** `bash docs/handoff/cloud-case-ai/po-secret-steps/a-github-token.sh`
   - CASE_AGENT_TOKEN を作り、GitHub secret と Mac の Keychain（service=salesanchor-case-agent-token）に置く。既にあれば止まる（上書きしない）。
   - Keychain にも置く理由: GitHub の secret は後から読み出せないため、次の段で claude.ai の環境に同じ値を入れるときに使う控え。
2. **B** `bash docs/handoff/cloud-case-ai/po-secret-steps/b-db-password.sh`
   - VPS の上で ai_reader_cloud のパスワードを作り、`/home/ubuntu/.config/salesanchor/ai-reader-cloud.env`（権限 600）に置く。新しい env が既にあれば止まる。途中で失敗しても、新しい env が無ければもう一度実行してよい。
3. **デプロイ**
   - deploy.yml の起動条件は `push: branches: [main]` のみで `workflow_dispatch` は無い（.github/workflows/deploy.yml:3-6）。`gh workflow run` は使えない。
   - 次に本線（main）に何かが入ったときのデプロイで、ai-reader-cloud-http の容器が起きる（deploy.yml:536-551）。
4. **確かめ**
   - A・B が出す ○/× がすべて ○。
   - デプロイ後、deploy の「Start ai-reader-cloud-http」の手順に警告（::warning::）が出ていない。
   - DB 接続の確かめは、デプロイ後に窓口の容器から行う（B は postgres 容器内の接続を確かめに使わない。ループバック宛 host は trust のため scram の確かめにならない: docs/handoff/ai-readonly-db-path/recon.md:40）。

## 途中で止まったとき

A・B とも、止まった場所の名前（「失敗: 「…」」の 1 行）と、そのあとに出る ○/× の両方で選ぶ。A は正常終了でも失敗でも最後に ○/× が出る。

- A で GitHub secret が ○・Keychain が × のとき（「失敗: 「Keychain への登録」」など）: A をもう一度流すと「既にあります」で止まる。`gh secret delete CASE_AGENT_TOKEN -R shingo-ops/salesanchor` で secret を消してから A を流し直す（値は作り直されるので、前の値は使わない）。
- A で GitHub secret が × のとき（「失敗: 「鍵の生成」」「失敗: 「GitHub secret への登録」」など）: そのまま A を流し直してよい（Keychain が ○ なら先に `security delete-generic-password -s salesanchor-case-agent-token` で消す）。
- B で「失敗: 「4. ...」」のとき: 新しい env はまだ無いので、そのまま B を流し直してよい（パスワードは作り直される）。
- B で「失敗: 「5. ...」」のとき: 新しい env が無ければ、そのまま B を流し直してよい。
- B で「失敗: 「6. 確かめ」」のとき: 新しい env はもう在る。B をもう一度流すと「既にあります」で止まる。直すには「戻し方」の手順で新しい env を消してから B をやり直す。

## 戻し方

- GitHub secret: `gh secret delete CASE_AGENT_TOKEN -R shingo-ops/salesanchor`
- Keychain: `security delete-generic-password -s salesanchor-case-agent-token`
- VPS: `/home/ubuntu/.config/salesanchor/ai-reader-cloud.env` を消し、DB で `ALTER ROLE ai_reader_cloud PASSWORD NULL`（VPS 変更は作業ごとに PO の GO）
