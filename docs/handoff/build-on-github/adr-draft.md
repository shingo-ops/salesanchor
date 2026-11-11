# ADR-（番号は空欄・PO が採番）: 本番サーバーでは組み立てず、GitHub で組み立てた完成品を会社の非公開の倉庫から指紋で受け取る

- この文書は何か（素人向け1行）: 「アプリの箱を本番で作るのをやめ、GitHub で作って会社の非公開の倉庫にしまい、本番は指紋の一致する完成品を取って並べるだけにする」と決める下書き。
- 設計: `docs/handoff/build-on-github/design.md`（現在地: `docs/handoff/build-on-github/recon.md`、目標: `docs/specs/build-on-github/kgi.md`）。

| 項目 | 内容 |
|---|---|
| ステータス | Proposed（下書き。PO の承認で Accepted） |
| 起案日 | 2026-11-04（Fable 作成・設計担当） |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-135・ADR-136（deploy.yml を含む PR の GO）、ADR-1003（GO の委譲と例外）、ADR-092（deploy の直列化）、ADR-115（自動ロールバック）、ADR-1024・ADR-1042・ADR-1052（backend の完成品を使い回す読み取り窓口）、ADR-1056（secretary-agent の箱）、ADR-1058（K8 測定で空きメモリ不足が分かった経緯）、ADR-025（secrets の扱い） |
| PO の言葉（2026-11-04） | 「そもそもサーバーの上で作り変えるのは適切？git hubで作り変えて本番反映させたほうが良いのでは？」「個人アカウントでプログラムなどは作っているので完成品は組織アカウントの非公開リポジトリに入れてほしい」 |

---

## What（何を決めたか）

- 本番サーバー prod1 の上では箱（Docker イメージ）を組み立てない。`docker compose build`・`docker build` は本番への入れ替え（deploy.yml）の手順から無くす。自動の戻し（ロールバック）でも組み立てない。
- 組み立ては公開の置き場 `shingo-ops/salesanchor` の自動作業（GitHub Actions・deploy.yml の中の build job）で行う。動く条件は main への push だけ。`pull_request`・`pull_request_target`・`workflow_dispatch`・`repository_dispatch` は付けない。
- 完成品は組織 GEN-RYU-System の倉庫（ghcr.io）に、非公開で、5 つの名前（`salesanchor-backend`・`salesanchor-frontend`・`salesanchor-gemini-egress`・`salesanchor-gha-exporter`・`salesanchor-secretary-agent`）でしまう。倉庫側のタグは commit の sha だけ（`latest` は作らない）。
- 本番は指紋（`@sha256:`）で受け取る。compose は `image: ${<名前>_IMAGE:-<今の名前>}` の形（変数と、今 prod1 で付いている名前の既定値。例 `${BACKEND_IMAGE:-astro-webapp-backend}`）だけを書き、倉庫の名前も指紋も書かない。既定値を置くのは、変数を持たない場所（CI の試験・砂場・手元の開発）で `docker compose` が止まらないようにするため（design §5-2）。本番の守りは compose ではなく deploy に一本化する: deploy が build job の出力を `.env` に書いた後、5 行が揃っていなければ箱に触る前に止まる（exit 1）。指紋の正本は prod1 の `.env` の 5 行。1 つ前は `.deploy_prev_images.env`（git に入れない）。
- 倉庫に書く鍵は classic PAT の `write:packages` だけ（`repo` は付けない・期限付き・`monthly-secret-expiry.yml` の見張りに入れる）。本番が読む鍵は別の classic PAT の `read:packages` だけで、GitHub の secret にだけ置き、入れ替えの段で `docker login` → 取得 → 同じ段で `docker logout` する（prod1 に鍵を残さない）。
- 倉庫へ push する前に、完成品の中身を走査する（名前の走査・gitleaks・履歴）。見つかれば push しない。許す例外は画面の JS に載る Firebase の web API key（`VITE_FIREBASE_API_KEY`）1 つだけで、経路と規則を 1 つに限って allowlist にする。
- 完成品を公開にする操作（GitHub の Danger Zone）は戻せないので、不可逆操作として PO 本人の確認が無ければ行わない。組織の「Package Creation」は Private にする。週 1 の見張りが非公開と 5 つの名前を確かめ、違えば Discord と fail で知らせる。
- 1 つ前の完成品へ戻すときは、控え `.deploy_prev_images.env` にある行（本番は 5 行）を `.env` に戻して `docker compose up --no-build` する。prod1 に残した完成品を使い、取り直しも組み立てもしない。片付けは現行と 1 つ前の指紋だけ残す自前の手順で行い、`docker image prune` は呼ばない。
- 最初の段として、dockerd を入れ直して（live-restore を先に有効化）メモリの基準を取り、入れ替え 1 回ごとの増え方を黒板（node-exporter の textfile）で測る。これは本番の危険操作なので PO の `!` 実行に限る。

## Why（なぜ）

- prod1 の空きメモリが平均 19.85% で、`dockerd` 1 つが約 1.7GiB を使っている（recon §2）。入れ替えは 25 日で 1,000 回あり、その度に本番の上で組み立てている（recon §1）。本番はお客さんにアプリを出す仕事だけに戻す（PO の言葉）。
- 公開の置き場の標準の実行機は無料で、組織の非公開の置き場で組み立てると月 12 USD 分（約 2,000 分）の枠を超える見込み（design §3-4）。だから組み立ては公開の置き場で行い、完成品だけを組織の倉庫に置く。
- 倉庫の認証は GITHUB_TOKEN か classic PAT しか無く、GITHUB_TOKEN は自分の置き場に限られる（design §0 G1・G4）。組織の倉庫に書くには PAT が要る。scope を `write:packages` だけにし、期限と見張りを付けて被害の範囲を狭める。
- 指紋で受け取るのは「どの完成品が動いているか」を一義に決め、戻しを取り直し無しにするため（K3・K6）。
- 走査を push の前に置くのは、秘密の入った完成品を倉庫に残さないため。GitHub の実行機の checkout は常に clean で、prod1 の作業コピーの未追跡ファイルが混ざらない利点もある。

## リスク（記録）

- 書き込みの PAT が漏れると、持ち主が書ける完成品が上書きされ得る。本番は deploy が書いた指紋以外を動かさないので、偽物を動かすには deploy.yml の改変（PR と GO）が要る。漏れたら PO が失効して作り直す。
- 倉庫（ghcr.io）の障害では出荷できない。箱は旧のまま。緊急時だけ PO の `!` で本番の手組みを許し、K1 の例外として記録する。
- 倉庫の保管・転送は「currently free」で、有料化は 1 か月前に知らされる。知らせが来たら枠（組織 Free: 保管 500MB・転送 1GB/月）と実測を比べて対処を決める。
- 初回の切替では指紋の控えが無く、自動の戻しは効かない。時間帯を選び PO が待機する。
- VITE の値は組み立て時に固定される。値を変えるときは GitHub 側を変えて main に push する。

## Scope

- Included: deploy.yml の build job と受け取りの段、compose 6 ファイルの `image:` 化（既定値付き）と手元用の override、blue-green と app-services-plan の直し、組み立てを呼ぶ既存の試験・素振り 4 本（リハーサル・手書きミラー・blue-green の素振り・砂場の ai-reader 試験）の追随（design §12 便2 12.〜15.）、pull/rollback/prune の 3 スクリプト、倉庫の見張り、鍵 2 本と Variables、dockerd の入れ直しと黒板。frontend の層キャッシュは付けない（design §7-3）。便2 に進む前に K8 の関所（design §12 便1 の完了条件）を通す。
- Excluded: 置き場の公開をやめる件、秘書の ChatGPT 化、prod2（github-collector・recovery-check・tinyproxy の組み立て先）、nginx・certbot・redis・postgres（元々取ってくる箱）。

## 戻し方

- 便ごとに前進の PR で戻す（revert）。compose に `build:` を戻し、deploy.yml の Step 3 を `docker compose build` に戻せば今の形に戻る。`.env` の 5 行と倉庫の完成品は残しても害は無い。
- 鍵は PO が GitHub で失効する。
- 段ごとの細かい戻し方は design.md §12。

## Follow-up

- 便0〜便3 の実施と K1〜K8 の記録（design.md §10-4・§14）。
- K5 が満たせないときの原因の切り分けは別作業（design.md §19 D12）。
- `workflow-lint.yml` に「deploy.yml に build の文字列が無い」規則を足すかは PO 本人の判断（design.md §19 D13）。
