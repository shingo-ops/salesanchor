# 設定配線SSOT（config-delivery-ssot）— 設計仕様書（表紙）

> この文書は何か（専門用語なしの1行）:
> アプリを動かすための設定値が、どこに1つだけ書かれ、どうやって全部の部品に届くかを決める設計テーマ。

- あるべき姿（POの言葉のみ・正本）: [ideal-state.md](./ideal-state.md)
- KGI: [kgi.md](./kgi.md)
- 親: なし（独立トップレベル）
- 関連: [secrets-permission-ssot/README.md](../secrets-permission-ssot/README.md)（鍵と持ち主の台帳。本テーマは鍵に限らない設定全般を扱う） / [process-hardening/README.md](../process-hardening/README.md)（守り手の自動ガード化）
- ステータス: あるべき姿確定・KGI確定 2026-09-06

## なぜ既存で足りないか

`secrets-permission-ssot` のあるべき姿は「全ての鍵とその持ち主」を対象とする（ideal-state.md 原文）。
本テーマが扱う `TCG_AUTO_ANALYZE`（業務のON/OFF）や `TCG_SCHEMA`（スキーマ名）は鍵でも権限でもない。
原文を設定全般へ読み広げることはPOの言葉の書き換えにあたるため、独立テーマとして新設する。

## 子文書リンク一覧

- [ideal-state.md](./ideal-state.md)
- [kgi.md](./kgi.md)
- recon.md: [../../handoff/config-delivery-ssot/recon.md](../../handoff/config-delivery-ssot/recon.md)
- design.md（今後作成）
