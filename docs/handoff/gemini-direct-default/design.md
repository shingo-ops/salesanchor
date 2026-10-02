# design：Gemini 中継の既定を直接接続に戻す

- 作成：2026-10-02（Sonnet 実装担当）
- 事実の根拠：[recon.md](./recon.md)
- 関連 ADR：ADR-080（監視VPS分離・prod2 の存在根拠）、ADR-135（リリース相乗り防止・本変更のスコープ遵守根拠）
- 既存設計：[docs/handoff/gemini-egress-via-prod2/design.md](../gemini-egress-via-prod2/design.md)（追補 §12 を本変更で追記済み）

## 1. 目的（KGI）

PO 指示（2026-10-02 verbatim）：「中継ポイントは緊急時のまま残しておき、再発した場合の手段として確立しておく、設定をデフォルト仕様として中継なしに切り替える、中継ポイントを使ったprod2からの中継方法は緊急手段として次回も使えるように記録しておいてほしい」

| KGI | 判定（○×） |
|---|---|
| 既定で中継を経由しない | 反映後、`.env` に `GEMINI_PROXY_URL`/`GEMINI_GRPC_PROXY` が無い状態で、backend・celery-worker の `GEMINI_PROXY_URL` が空文字（`docker-compose config` で確認可能） |
| 抽出 attempt が成功する | 反映後、新しい抽出ジョブで `status=done` が出る（API_ERROR 増加なし） |
| 中継を緊急時に再利用できる記録が残る | `docs/runbooks/gemini-egress-emergency.md` に判定・ON/OFF手順・prod2側前提が揃っている |
| gemini-egress は起動したまま残る | デプロイ対象への登録（`.github/workflows/deploy.yml:342`）・サービス定義（`docker-compose.yml` の `gemini-egress`）を変更しない |

## 2. 対象と対象外

**対象**
- `docker-compose.yml` の backend・celery-worker の `GEMINI_PROXY_URL`/`grpc_proxy` の既定値（`${VAR-http://gemini-egress:18888}` → `${VAR-}`）
- 新規 `docs/runbooks/gemini-egress-emergency.md`（緊急手段の手順書）
- `docs/handoff/gemini-egress-via-prod2/design.md` への追補（§12）

**対象外（変更しない）**
- `gemini-egress` サービス定義（`docker-compose.yml`、`monitoring/prod1/gemini-egress/Dockerfile`）
- `.github/workflows/deploy.yml:342` の `gemini-egress` デプロイ対象登録
- prod2 側の tinyproxy・中継専用鍵・`monitoring/prod2/gemini-egress/`
- `backend/app/services/gemini_extraction_svc.py` の `_get_genai_client()` ロジック自体（空文字判定は既存のまま。変更不要と recon §2-2 で確認済み）
- 旧SDK（`google.generativeai`）→新SDK移行（別テーマ）

## 3. 変更前と変更後

```
変更前：.env に明示設定が無い場合 → docker-compose.yml のデフォルトが中継先（http://gemini-egress:18888）→ 常に中継経由
変更後：.env に明示設定が無い場合 → docker-compose.yml のデフォルトが空文字 → 直接接続
        .env に GEMINI_PROXY_URL / GEMINI_GRPC_PROXY を明示設定した場合のみ → 中継経由（緊急手段）
```

`gemini-egress` コンテナ（prod1 側）・prod2 側 tinyproxy は、どちらのケースでも起動したまま変わらない。

## 4. 検証（recon の事実に基づく）

- 新SDK（`google.genai`）：`_get_genai_client()`（`backend/app/services/gemini_extraction_svc.py:267-276`）は `if proxy_url:` で空文字を falsy 判定するため、コード変更不要で直接接続に切り替わる（recon §2-2）。
- 旧SDK（`google.generativeai`、`grpc_proxy` 依存）：本番 backend コンテナで `grpc_proxy=""` を渡した実測で成功を確認済み（recon §2-3）。
- 直接接続・中継経由どちらも成功することをデザイナーが実測済み（recon §2-4）。これにより「直接接続に戻しても壊れない」ことと「中継は今も機能する（緊急手段として有効）」ことの両方を確認している。
- 本番 `.env` に明示設定が無いことを確認済み（recon §2-1）。そのため、この変更（compose のデフォルト変更）だけで本番の挙動が直接接続に切り替わる。もし明示設定があれば、この変更だけでは切り替わらないため事前に STOP する設計だったが、該当しなかった。

## 5. 受入条件

| 基準 | 検証方法 |
|---|---|
| ① `docker-compose.yml` の backend・celery-worker の `GEMINI_PROXY_URL`/`grpc_proxy` 既定値が空文字 | `docker-compose config`（`.env` 無し）で `GEMINI_PROXY_URL: ""` / `grpc_proxy: ""` と表示される（recon §3 で確認済み） |
| ② デプロイ反映後、抽出 attempt が成功する（API_ERROR が増えない） | 本番 DB の抽出ジョブ `status` を確認（マージ後にPOまたは次便で実施） |
| ③ `gemini-egress` は起動中のまま | `.github/workflows/deploy.yml:342` に変更が無いことを diff で確認済み（本design作成時点） |
| ④ 中継を再度使う手順が記録されている | `docs/runbooks/gemini-egress-emergency.md` が存在し、症状判定・ON/OFF手順・prod2前提を含む |
| ⑤ 監視スタック整合性チェックが通る | `python3 monitoring/scripts/validate_tokens.py` / `node monitoring/grafana/generate-nav.js --check` をローカル実行して確認済み（recon §3） |

## 6. リスクと対処

| リスク | 対処 |
|---|---|
| Google の位置判定が再発し、直接接続が再び `400 User location is not supported` で失敗する | `docs/runbooks/gemini-egress-emergency.md` の手順で `.env` に2行追加 → push to main でデプロイ → 中継 ON に戻す（gemini-egress は起動済みのため追加作業不要） |
| 判定を誤り、実際には中継が必要な状態で直接接続のまま運用してしまう | recon §2-4 の実測で両経路とも成功を確認済み。反映後も抽出 attempt の成功率を監視する（既存の API_ERROR 監視、design.md（prod2版）§6 V6 と同じ見方） |
| `gemini-egress` コンテナ・prod2 tinyproxy が放置されて設定ドリフトする | 本変更では稼働を止めないため、既存の `docs/handoff/gemini-egress-via-prod2/design.md` §7 のリスク対処（restart: unless-stopped、autossh 再接続）がそのまま有効 |

## 7. 外部・過去事例

該当事例なし（理由：環境変数デフォルト値の変更という単純な設定変更であり、外部事例による裏付けを要する技術選定ではない。経路選択自体の外部事例は `docs/handoff/gemini-egress-via-prod2/design.md` §11 に記載済み）。

## 8. 維持の仕組み

- 守り手: Opus 設計担当（`docs/runbooks/gemini-egress-emergency.md` と prod2 構成を、監視VPSを変えるときに見直す）／PO（Google の位置判定が再発した場合の中継 ON/OFF 判断）
- 気づく仕組み：抽出ジョブの API_ERROR 監視（既存、`docs/handoff/gemini-egress-via-prod2/design.md` §6 V6 と同じ見方）
- 解除するきっかけ：本変更自体が「解除」（中継を既定から外す）。再度 ON にするきっかけは runbook §1 の症状発生時
- 参照パス：`docs/runbooks/gemini-egress-emergency.md`、`docs/handoff/gemini-egress-via-prod2/design.md`、`docker-compose.yml`

## 9. 標準ワークフロー確認

- 着手前に既存 ADR を検索済み（recon §1）。矛盾する ADR なし
- recon.md: フルパス:行番号で事実を引用済み
- design.md（本ファイル）: ADR 相互参照・`|基準|検証方法|` テーブル・外部事例欄・維持の仕組み（守り手含む）を記入済み
