# recon — 存在しないモジュールの参照

> この文書は何か（専門用語なしの1行）:
> 画像送信が失敗する理由を調べたら、無い場所から部品を借りようとしていた記録。

対象ADR: ADR-091
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-04）

### 症状

受信箱から画像を送ると、画面に送信できませんでしたと表示される。
Discord のチャンネルには画像が届いている。

サーバーのログに次が記録されている。

ModuleNotFoundError: No module named app.tenant

発生箇所は backend/app/routers/leads.py:2397 である。

### 誤った参照は3箇所

backend/app/routers/leads.py:1448
backend/app/routers/leads.py:1516
backend/app/routers/leads.py:2397

いずれも存在しないモジュールから reset_tenant_context を読み込もうとしている。

git grep で backend 配下を全件調べた結果、この3箇所のみである。
他のファイルには無い。

### 参照先は存在しない

backend/app/tenant/ はリポジトリに0件である。
本番のコンテナでも No such file or directory となる。

### 正しい定義

backend/app/auth/dependencies.py:317 に定義がある。

引数は db と tenant_id の2つで、誤った参照側の呼び出しと同一である。
したがって読み込み元を変えるだけでよい。

### 他の箇所は正しく参照している

backend/app 配下で reset_tenant_context を参照する箇所は212件ある。
leads.py の3箇所を除き、すべて app.auth.dependencies から読み込んでいる。

### 混入の経緯

git log で追跡したところ、次の3つのコミットで混入している。

- Discord への画像送信を実装した回
- 添付URLの再取得に Discord 分岐を追加した回
- Meta受信画像のサムネ表示を追加した回

1516行と1448行は呼ばれる頻度が低いため表面化していなかった。

## 本便で変更する箇所

backend/app/routers/leads.py の3箇所の読み込み元を
backend/app/auth/dependencies.py に変える。

引数は変更しない。
