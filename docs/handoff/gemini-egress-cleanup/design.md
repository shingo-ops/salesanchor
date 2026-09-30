# design: gemini-egress 片付け（PR-4）

## 目的

PR-4「片付け」カードに沿って、残骸削除・ドキュメントと実物の差分記録・誤ったモデル名の docstring 修正を行う。挙動は一切変更しない。

recon: docs/handoff/gemini-egress-cleanup/recon.md
対象ADR: ADR-080（追記対象・決定は変更しない）, ADR-113（標準開発フロー・2モード運用に従い本 recon/design を作成）

## 対象と対象外

**対象:**
- `monitoring/prod2/gemini-egress/tunnel/Dockerfile` の削除
- `monitoring/prod2/gemini-egress/README.md` の残骸記述の更新（削除済みである旨）
- `docs/handoff/gemini-egress-via-prod2/design.md` の残骸記述に削除記録を追記
- `docs/adr/ADR-080-monitoring-vps-separation.md` に「実物との差分」追記節（決定は変更しない）
- `backend/app/services/gemini_extraction_svc.py` の docstring/コメント（5, 15, 377行目）のモデル名表記修正

**対象外:**
- `monitoring-tunnel.service`（systemd unit）自体の作成・リポジトリ管理化 — 未決のため今回は着手しない
- ADR-080 の決定内容（本文）— 変更しない、追記のみ
- `_GEMINI_MODEL` 定数の値・実行コードのロジック — 変更なし

## 変更前後

### 1. `monitoring/prod2/gemini-egress/tunnel/Dockerfile`
- 変更前: リポジトリに存在（未使用、compose から外されていた）
- 変更後: `git rm` で削除

### 2. `monitoring/prod2/gemini-egress/README.md:56`
- 変更前: 「`tunnel/`（Dockerfile）は 2026-09-30 の方式変更で使わなくなった。compose からは外してある。削除は、あとの片付けの便で行う。」
- 変更後: 「`tunnel/`（Dockerfile）は 2026-09-30 の方式変更で使わなくなり、同日の片付け PR で削除した。」

### 3. `docs/handoff/gemini-egress-via-prod2/design.md:99`
- 変更前: 末尾が「…動作には影響しない。」で終わっていた
- 変更後: 「…動作には影響しない。→ 2026-09-30 の片付け PR（release/gemini-egress-cleanup）で削除済み。」を追記

### 4. `docs/adr/ADR-080-monitoring-vps-separation.md`
- 変更前: ファイアウォール直接スクレイプ前提の決定文のみ
- 変更後: 決定文はそのまま。末尾に「## 追記（2026-09-30）：実物との差分（観測事実の記録。決定の変更ではない）」節を追加し、実際は `monitoring-tunnel.service` による autossh トンネル方式であること・unit がリポジトリに無いこと・どちらを正とするか未決であることを記録。
- `docs/adr/README.md` は `node scripts/generate-adr-index.js` で再生成（自動反映のみ、手動編集なし）。

### 5. `backend/app/services/gemini_extraction_svc.py`
- 5行目: `Gemini 3.6 Flash で LINE メッセージから商品明細を抽出する。` → `Gemini（モデルは _GEMINI_MODEL を参照）で LINE メッセージから商品明細を抽出する。`
- 15行目: `  - モデル: gemini-3.6-flash / temperature=0` → `  - モデル: _GEMINI_MODEL / temperature=0`
- 377行目: `    モデル: gemini-3.6-flash（GAS 側デフォルトと同一）` → `    モデル: _GEMINI_MODEL`（「GAS 側デフォルトと同一」の記述も削除。現在の `_GEMINI_MODEL` は `gemini-3.1-flash-lite` であり GAS 側デフォルトと同一とは限らないため、誤解を招く記述を残さない判断）
- `_GEMINI_MODEL` の値そのもの（282行目）は変更していない。

## 影響範囲

- 実行コードの変更なし。docstring・コメント・ドキュメントのみの変更。
- `monitoring/prod2/gemini-egress/docker-compose.yml` は変更しない（既に `tunnel` サービス定義なし）。
- 削除される `tunnel/Dockerfile` を参照している CI・デプロイ設定は無い（`docker-compose.yml` に記載なし、他ファイルからの参照も grep で0件）。

## 戻し方

- 本 PR を revert する。
- `tunnel/Dockerfile` は git 履歴に残るため、必要であれば `git show <この変更前のコミット>:monitoring/prod2/gemini-egress/tunnel/Dockerfile` で復元可能。

## 検証

| 基準 | 検証方法 |
|------|---------|
| `tunnel/` が git 管理から消えている | `git ls-tree -r --name-only HEAD -- monitoring/prod2/gemini-egress/` に `tunnel/Dockerfile` が出ない |
| ADR-080 に追記節がある | `grep -n "追記（2026-09-30）" docs/adr/ADR-080-monitoring-vps-separation.md` がヒット |
| `backend/app/services/gemini_extraction_svc.py` に `3.6-flash` が残っていない | `grep -n "3.6-flash" backend/app/services/gemini_extraction_svc.py` が0件 |
| 既存テストが緑 | `python3 -m pytest tests/test_tcg_gemini_extraction.py -q`（backend/ 配下） が pass |
| ADR index が最新 | `node scripts/generate-adr-index.js --check` が成功 |

## 外部・過去事例の参照と我々への応用

該当なし（理由：記録と残骸削除のみで挙動を変えない片付け作業のため、外部事例の調査対象ではない）。

## 維持の仕組み

- 守り手: .github/workflows/adr-index-check.yml（ADR ファイル変更時に `node scripts/generate-adr-index.js --check` を CI で強制。インデックス整合性のみ機械検査。ADR-080 本文の追記が今後消えないかどうかは人のレビューで守る）
- ADR-080 の追記節により、次に監視VPS周りを触る人が「実物は ADR と違う」ことを ADR 本体から知れる（別ドキュメントに埋もれない）。
- `_GEMINI_MODEL` を参照する記述に変えたことで、今後モデルを変更しても docstring が自動的に古くならない（定数名を指すだけで値を書き写さない）。
- `monitoring-tunnel.service` をリポジトリで管理するかどうかは未決のまま。次にこの領域を触る便で改めて判断が必要（本 PR のスコープ外）。
