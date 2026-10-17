# Phase 3 設計 — deploy-keep-oneoff

**対象ADR**: ADR-092  
**recon**: docs/handoff/deploy-keep-oneoff/recon.md  
**日付**: 2026-10-17  
**担当**: Opus（設計）／Sonnet（実装）

---

## 外部・過去事例の参照と我々への応用

- 事例1: Docker Compose は `compose run` の一時コンテナに `com.docker.compose.oneoff=True` を付ける（本番で実測。recon.md）→ 我々への応用: rm -f の対象を `oneoff=False` に絞り、一時コンテナを対象から外す。
- 事例2: `docs/handoff/reextract-v6-with-v102/review-opus.md` M4 は「デプロイで別コンテナも強制削除される」と指摘し、`--name` で名前を外す運用回避を挙げた → 我々への応用: 運用回避ではなく、削除側の条件で恒久的に防ぐ。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 3か所すべてに `--filter "label=com.docker.compose.oneoff=False"` が付く | `git diff origin/main -- .github/workflows/deploy.yml` で3行の差分を目視 |
| 修正後の1行で、一時コンテナは生存し、常駐と残留は消える | 使い捨て環境で再現（verify/k2k3.log の K2 節） |
| `compose stop` / `up --remove-orphans` は一時コンテナを止めない・消さない | 同上（K3 節） |
| 本番反映中に動かした一時コンテナが生き残る | 本番反映後に Opus が実施（K4） |

---

## 技術 How・KPI

- KPI: デプロイ中に消える一時コンテナ 0 件（修正前は名前が一致する全件）。
- 技術選択: `docker ps` の `--filter` を複数並べる（AND 条件）。理由: 変更が最小で、既存の残留削除（oneoff=False の常駐・ハッシュ付き残骸）の動きは変わらない。

---

## 弊害・トレードオフ

- oneoff=True で名前が一致する古い残骸は自動では消えなくなる → 対策: 一時コンテナは `--rm` 付きで使う運用。残った場合は `scripts/f2-cleanup.sh` が古い exited を片付ける。
- 触らない範囲: deploy.yml のそれ以外の行、`scripts/`、`docker-compose.yml`。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | deploy.yml の3行に filter を追加し、コメントを付ける | Generator |
| 2 | 使い捨て環境で K2・K3 を観測 | Generator |
| 3 | PO の GO 後にマージ・本番反映、K4 を確認 | Opus |

---

## 継続

- 完了後の監視: 本番反映後の次回デプロイで、動作中の一時コンテナが残ることを確認する（K4）。
- 次フェーズへの引き継ぎ: なし
