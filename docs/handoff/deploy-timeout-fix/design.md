# 設計 — deploy-timeout-fix

**対象ADR**: ADR-115  
**recon**: docs/handoff/deploy-timeout-fix/recon.md  
**日付**: 2026-06-12  
**担当**: Morimoto

---

## 外部・過去事例の参照と我々への応用

- **GitHub Actions 公式ドキュメント**: ポーリングパターンとして「sleep + curl + retry ループ」を推奨。単発チェックは非推奨とされている。→ 応用: Step 6 の単発チェックをリトライループに変更。
- **Docker 公式 HEALTHCHECK**: コンテナの健全性確認には `retries` + `start_period` を組み合わせるパターンが標準。→ 応用: 外部チェック (Step 6) も同様に margin を持たせた上限時間でリトライする設計に統一。
- **過去障害 (ADR-115 起票の直接原因)**: SA-18 Phase2 デプロイで 60s rollback check が backend 起動完了を待てず「rollback failed」扱いになった。→ 今回はその 60s の根拠なし設定を実測値 (120s) に基づいて修正。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| Step 6 が "waiting (N/36)" ログを出力してからパスする | 検証用 PR (README trivial 変更) を作成してデプロイを実行し、CI ログで確認 |
| デプロイ成功時に Discord ロールバック通知が来ない | Discord #deploy-notifications チャンネルで通知なしを確認 |
| デプロイ後に API が 200 を返す | `curl https://api.salesanchor.jp/api/health` → `{"status":"ok"}` を確認 |
| 真の障害時（本当に起動失敗）は依然としてロールバックが発動する | 手動確認不要（ロールバックロジックは変更していない。単にタイムアウト値を延長のみ） |

---

## 修正方針の比較と決定

### 比較した3案

| 案 | 内容 | 効果 | リスク | 実装量 |
|----|------|------|--------|--------|
| **(a) タイムアウト延長** | Step 6 単発→リトライ(180s)・rollback 60s→180s | false-positive ほぼ根絶 | 障害時の判定が3分遅れる（許容） | 小（2箇所） |
| (b) 事前ビルド（CI→registry→VPS pull） | VPS ビルド時間を削減 | ビルド時間短縮のみ（起動時間は変わらない） | Registry セットアップ必要・大改修 | 大 |
| (c) deploy job 非致命化・別 job でポーリング | deploy job 常に成功扱い | ロールバック制御が複雑化 | rollback タイミング不明確 | 中 |

### 決定: 案 (a) のみ採用

**理由**:
- 根本原因が「waiting time < actual startup time」という単純な不一致であるため、値の修正が最小・最直接の解決策
- 案 (b) は startup 時間そのものに手を入れないため根本解決にならない
- 案 (c) は rollback の安全策としての役割を損なう

### 数値の根拠

```
実測 backend 起動: ~120s
安全マージン: 60s（実測の +50%）
設定値: 180s = 120s + 60s
```

---

## 弊害・トレードオフ

- **ジョブ時間の増加**: 本当に障害発生時にロールバック判定まで最大 180s 余分にかかる（旧 60s との差: +120s）。許容範囲。
- **誤 pass リスク**: 180s 以内に起動するが不安定な状態でパスする可能性。対策: `/api/health` は DB・Redis・Celery 全てチェックするため不完全起動では 200 を返さない。

---

## 計画票

| ステップ | 内容 | 状態 |
|---------|------|------|
| 1 | deploy.yml Step 6 単発チェック → 36×5s リトライループ | ✅ 完了 (commit f8fbac90) |
| 2 | rollback stabilize 12×5s → 36×5s | ✅ 完了 (commit f8fbac90) |
| 3 | actionlint 検証（既存 SC2155 も修正） | ✅ exit 0 確認済み |
| 4 | 検証 deploy（README trivial 変更 PR） | PR #1978 マージ後に実施 |

---

## 継続

- 完了後の監視: 次回デプロイの CI ログで `waiting (N/36)` が出てパスすることを確認
- 将来検討: backend 起動時間が伸びた場合は 180s を再評価（現時点では 120s + 60s margin で十分）
