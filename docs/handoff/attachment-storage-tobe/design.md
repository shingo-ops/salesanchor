# 設計 — 添付ファイル保管のTo-Be策定

> この文書は何か（専門用語なしの1行）:
> 顧客から届いた画像を自社サーバーに保管する仕組みの作り方を、実装できる細かさまで決めた文書を作るための設計。

対象ADR: ADR-091
recon: docs/handoff/discord-attachment-refetch/recon.md
親テーマ: docs/specs/attachment-storage/README.md

## 1. あるべき姿

顧客が送った画像やファイルが、いつ見返しても受信箱に残っている。
Meta以外のどのチャネルで受けても同じように扱われる。
顧客との関係が終われば、その画像も消える。
サーバーを圧迫しない上限がある。

## 2. recon（実測・2026-09-01）

- backend コンテナの Mounts は空配列。ファイルを書いてもデプロイで消える。
- postgres は永続ボリューム astro-webapp_postgres_data に載っている。
- docker-compose.yml のトップレベル volumes は 5 個（postgres_data / pgadmin_data / redis_data / caddy_data / caddy_config）。
- backend サービス定義に volumes セクションは存在しない。
- リード削除は論理削除であり物理削除しない（backend/app/routers/leads.py:1234 付近）。
- StaticFiles / mount は 0 件。静的配信の既存設定は存在しない。
- テナント別テーブルの一括作成は migrations/20260814_120000_create_tenant_link_templates.sql に実例がある。
- prod1 の空き 28GB、prod2 の空き 166GB。
- 既存の添付は全テナント合計 3 件（tenant_006 のみ）。

## 3. design（技術How）

本便では実装を行わず、設計文書のみを作成する。

作成:
- docs/specs/attachment-storage/to-be.md（理想の設計図）
- docs/handoff/attachment-storage-tobe/design.md（本ファイル）

触らない範囲: backend / frontend / migrations / scripts / .github / docker-compose.yml。

## 4. 外部・過去事例の参照と我々への応用

Discord 公式は添付CDN URLに有効期限を設け、期限後はアプリ側が
新しいCDN URLを取得し直す必要があると説明している。
LINE 公式ドキュメントもユーザー送信コンテンツは一定期間後に自動削除されると明記している。

あるOSS実装では Telegram / Feishu / DingTalk / iMessage が添付をローカル保存しているのに
Discord だけがCDN URLを直接使っており、一貫性がないとして不具合起票されている。

我々への応用: プラットフォーム側は添付を恒久保持しない。
CRMとして履歴を残すには自社保存が必要であり、他実装でも標準の対処である。
本設計はその定石に従う。

## 5. 弊害・トレードオフ

- 弊害: 本便は文書のみのため、KGI 7項目はいずれも未達である。実装は後続5便で行う。
- 弊害: 設計を固定することで、実装中に判明した事実で設計を変える際に
  再度PRが必要になる。ただし合意止まりを避ける効果の方が大きいと判断する。
- トレードオフ: 5便に分割するため、全体の完了までターン数が増える。
  インフラとDBを混ぜないことによる安全性を優先する。

## 6. 受入基準

| 基準 | 検証方法 |
|---|---|
| to-be.md が origin/main に存在する | git show refs/remotes/origin/main:docs/specs/attachment-storage/to-be.md が非空 |
| PO決定11件が漏れなく記載されている | to-be.md の決定表の行数が 11 |
| 実装の分割が5便で記載されている | to-be.md の分割表の行数が 5 |
| 実装コードを含まない | git diff --numstat に backend / frontend / migrations / docker-compose.yml が現れない |
| KGI 7項目との対応が取れている | to-be.md 内に KGI4 / KGI5 / KGI6 への言及が存在する |

## 7. 維持の仕組み

- 守り手: 人手で守る
- 理由: 本便は文書のみで、機械検査できる振る舞いを持たない。
  正本の書き換えは process-artifacts gate がPR経由を強制するため無断変更は防がれる。
- 対象: 設計がPO合意なく書き換えられること。
