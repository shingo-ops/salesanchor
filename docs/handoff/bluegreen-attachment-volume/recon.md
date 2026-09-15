# recon — backend に添付ボリュームが付かない理由

> この文書は何か（専門用語なしの1行）:
> 保管した画像が backend から見えない理由を、起動の仕組みまで遡って調べた記録。

対象ADR: ADR-091
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-03）

### 症状

配信APIが 404 を返す。

backend コンテナで ls を実行すると
No such file or directory となり、保管先のディレクトリが存在しない。

DBの行は正しく存在する。
id=4 / tenant_id=6 / lead_id=1049 / file_path=tenant_006/lead_1049/1544797944954224681.png

gateway コンテナからは同じファイルが見える。

### 設定は正しい

docker-compose.yml:113 に backend への添付ボリュームの記述がある。
2026-09-01 のコミット ca2c970f で追加された。

### backend は compose で起動していない

.github/workflows/deploy.yml は backend の切替に
scripts/blue-green-cutover.sh を呼ぶ。

scripts/blue-green-cutover.sh:80 以降が docker run で
コンテナを直接起動している。

同スクリプトの docker run に渡される volume 指定は
firebase-credentials.json の1件のみである。
添付ボリュームの指定が無い。

docker run は docker-compose.yml を読まないため、
compose 側に書いた volume 定義は反映されない。

### gateway との違い

.github/workflows/deploy.yml:335 で
gateway は docker compose up -d で起動している。
そのため compose の volume 定義が反映される。

backend だけが別経路である。

## 本便で変更する箇所

scripts/blue-green-cutover.sh の docker run に volume 指定を1行追加する。

.github/workflows/deploy.yml と docker-compose.yml は変更しない。
