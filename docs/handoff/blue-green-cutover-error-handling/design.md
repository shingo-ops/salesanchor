# design: blue-green cutover Steps 4-6 エラーハンドリング修正

## recon 参照

`docs/handoff/blue-green-cutover-error-handling/recon.md`

## 対象 ADR

ADR-115（デプロイ安全策）— cutover スクリプトのエラーハンドリング強化はデプロイ安全策の一環

## KGI

Steps 4-6 で旧コンテナが存在しない場合でもスクリプトが最後まで完走し、green コンテナが正常稼働する。

| 基準 | 検証方法 |
|------|----------|
| Step 4b: 旧コンテナ不在時にスクリプトが exit しない | `docker rm -f astro-webapp-backend-1` 後に cutover を実行し exit code 0 を確認 |
| Step 6: rename 失敗時に green が `--restart unless-stopped` で稼働し続ける | rename が失敗するケースをシミュレートし green コンテナの restart policy を確認 |
| 通常フロー（旧コンテナ存在）で動作変更なし | 通常デプロイを実行し cutover が成功することを確認 |

## 設計方針

### Step 3 直後: `set +e` 追加

`trap - ERR` で ERR trap を解除しても `set -e` は残るため、Steps 4-6 の失敗でスクリプトが中断する。`set +e` を追加し、各ステップで個別にエラーを処理する方式に切替。

### Step 4b: 旧コンテナ存在確認

```bash
if docker inspect "${OLD_BACKEND}" >/dev/null 2>&1; then
  docker network disconnect "${FRONTNET}" "${OLD_BACKEND}" 2>/dev/null || echo "⚠️ already disconnected"
else
  echo "⚠️ Old backend container not found — skipping disconnect"
fi
```

`docker inspect` で存在確認 → 存在する場合のみ disconnect。disconnect 失敗（既に切断済み）も警告のみで継続。

### Step 6: rename 失敗時の fallback

```bash
if docker rename "${GREEN_BACKEND}" "${OLD_BACKEND}"; then
  docker update --restart unless-stopped "${OLD_BACKEND}"
else
  echo "⚠️ Rename failed — green container serves as '${GREEN_BACKEND}'"
  docker update --restart unless-stopped "${GREEN_BACKEND}"
fi
```

rename 失敗時は green コンテナ名のまま restart policy を設定し、サービス継続を保証。

### 最後: `set -e` 復帰

```bash
set -e  # 安全モードを復帰
```

Steps 4-6 の後に `set -e` を戻す（将来の追加コードが無防備にならないよう）。

## 外部・過去事例の参照と我々への応用

- Docker 公式: `docker inspect` でコンテナ存在確認してから操作する運用パターンは Docker CLI の標準的な防御コーディング
- 過去事例: ADR-115（2026-06-06 503 障害）— 環境差バグが CI をすり抜けて本番初めて出るケース。本修正も同様に「コンテナが存在しない」という本番固有の状態を想定した防御
- `set +e` + 個別チェックの組み合わせは bash ベストプラクティス（cleanup や post-flight 処理で `set -e` を一時解除するパターン）

## 弊害・リスク

- 通常フローへの影響なし（正常ケースでは分岐の `if` 条件が成立し従来と同じコードパスを辿る）
- `set +e` 区間中は予期しないエラーも継続する可能性があるが、Steps 4-6 は各コマンドで個別チェックしているため実用上問題なし

## 維持の仕組み

- 守り手: `set +e` + 個別エラーチェックが Steps 4-6 の各操作を保護。最後の `set -e` 復帰でそれ以降の安全を確保。
- 次回デプロイスクリプト変更時: Steps 4-6 への変更は `set +e` 区間内にあることを確認し、エラーハンドリングを継続すること
