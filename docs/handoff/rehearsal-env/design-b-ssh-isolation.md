# design.md — 対策B：本番SSH鍵の隔離（エージェントの素手の本番アクセス遮断）

- 対応recon: docs/handoff/rehearsal-env/recon.md
- PO決定（2026-06-13）: B を先行実装。A（staging正式化）/ D（CI dry-run）は後日判断。

## ゴール
エージェント（Terminal CC / Hikky-dev CC ほか自動プロセス）が、人間の明示操作なしに
本番 VPS（49.212.137.46 / 49.212.160.98）へ無制限 SSH できない状態にする。
正規のデプロイ・監視経路は一切壊さない。

## 実装内容

### 1. 鍵の棚卸しと経路特定（最初に・変更前に）
- id_ed25519（無制限）と salesanchor-claude（ForceCommand制限付き）が
  それぞれどのマシンのどのパスにあり、どの ssh config エントリ/プロセスが使うかを列挙。
- deploy パイプライン（GitHub Actions 自ホストランナー）が本番接続に使う鍵を特定し、
  本変更の影響を受けないことを確認（受ける場合は設計を止めて報告）。
- 監視系（Uptime Kuma 等）・Suttan の手動運用経路も同様に確認。

### 2. エージェント経路の制限付き鍵への一本化
- エージェントが参照する ssh config（該当ホストのエントリ）を salesanchor-claude
  （ForceCommand制限）に切替。
- ForceCommand の許可コマンド一覧を確認し、正当な自動運用（デプロイ後smoke等）に
  必要十分か検証。不足があれば許可リストの追加案を報告（勝手に広げない）。

### 3. 無制限鍵の隔離
- id_ed25519 を既定の参照パスから退避（例: ~/.ssh/manual-only/ へ移動＋ssh configから除去、
  またはパスフレーズ付与）。人間が意図して指定しない限り使われない状態にする。
- 削除はしない（緊急時の人間用として保全）。退避場所と使用手順を docs に記載。

### 4. 検証（受け入れ条件）
- [ ] エージェントのシェルから ssh ubuntu@49.212.137.46 での任意コマンド
      （例: psql 直叩き相当）が拒否されること（実証ログ添付）
- [ ] ForceCommand 許可内の操作は従来どおり成功すること
- [ ] 次回の通常デプロイ（blue-green）が無変更で成功すること（パイプライン無影響の実証）
- [ ] 監視・アラートが継続稼働していること
- [ ] CLAUDE.md の「VPS直作業禁止」に「（技術的にも制限付き鍵のみ）」の旨を追記し、
      無制限鍵の所在と人間用手順への参照を記載

## 注意
- 本変更はリポジトリ外（各マシンのSSH設定）が主体。変更前に現状をバックアップし、
  ロールバック手順（退避した鍵と config を戻す）を design 内に明記してから着手。
- 切替直後に本番障害対応が必要になった場合に備え、人間用の無制限鍵手順を先に文書化してから
  エージェント経路を切り替える（順序厳守）。

---

## 棚卸し結果（2026-06-13 実施）

| 鍵ファイル | コメント | ubuntu アクセス | 制限 |
|---|---|---|---|
| `~/.ssh/id_ed25519` | tanizawashingo@sakura-vps | **可・無制限** | なし |
| `~/.ssh/salesanchor-claude` | claude-code-reader | 可 | ForceCommand のみ |
| `~/.ssh/salesanchor_vps` | claude-code | 不可（permission denied） | - |

- `~/.ssh/config` は**存在しない**（SSH デフォルト動作で `id_ed25519` が優先使用される）
- deploy.yml: `secrets.SSH_PRIVATE_KEY`（github-actions-deploy）を使用 → ローカル鍵変更の影響**なし**
- ForceCommand 許可コマンド: `docker stats --no-stream; free -h; df -h; uptime`（監視のみ）
  - エージェントが SSH 経由で必要とする正当な操作はすべて GitHub Actions 経由のため、
    ForceCommand の追加拡張は不要

---

## 緊急時の人間用アクセス手順（ロールバック前提）

本番障害対応など人間が無制限アクセスを必要とする場合:

```bash
# 退避先から id_ed25519 を指定して接続
ssh -i ~/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46

# または一時的に config を上書きして接続
ssh -o IdentityFile=~/.ssh/manual-only/id_ed25519 -o IdentitiesOnly=yes ubuntu@49.212.137.46
```

退避先: `~/.ssh/manual-only/id_ed25519`（鍵本体は削除しない）

---

## ロールバック手順

変更後に問題が発生した場合:

```bash
# 1. config を削除（エージェント経路の制限解除）
rm ~/.ssh/config

# 2. 退避した鍵を元に戻す
cp ~/.ssh/manual-only/id_ed25519 ~/.ssh/id_ed25519
cp ~/.ssh/manual-only/id_ed25519.pub ~/.ssh/id_ed25519.pub
chmod 600 ~/.ssh/id_ed25519

# 3. 疎通確認
ssh ubuntu@49.212.137.46 "echo OK"
```

---

## 方針変更（2026-06-13 PO 決定）

初期設計では VPS 側 `authorized_keys` の人間鍵（`hitoshi@Hs-MacBook-Pro.local`）にも
ForceCommand を追加する案を提案したが、PO 判断により**採用しない**。

**確定方針**:
- 人間の鍵（`hitoshi@...`、`shingo-macbook-primary` 等）は VPS 側で変更しない。無制限のまま温存。
- エージェントの制限はマシン側（`~/.ssh/config` + 無制限鍵の退避）で完結させる。
- エージェントが無制限鍵を使えるのは、人間の明示許可（都度・タスク単位）がある場合のみ。

**Hikky-dev Mac（`hitoshi@Hs-MacBook-Pro.local`）への対応**:
- VPS 側 authorized_keys は変更しない
- Suttan 本人に自マシンでの鍵隔離を依頼（本ドキュメントの「Suttan 依頼文」参照）
- Suttan が作成したエージェント用制限付き鍵（例: `hikky-claude-restricted`）の公開鍵を
  受領後、VPS `authorized_keys` に ForceCommand 付きで**追記のみ**（既存行を変更しない）

**Suttan への依頼手順（b: 公開鍵を受領後の VPS 側作業）**:
```bash
# バックアップ
ssh -i ~/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46 \
  "cp ~/.ssh/authorized_keys ~/.ssh/authorized_keys.bak.$(date +%Y%m%d%H%M%S)"

# 追記（<PUBLIC_KEY> を実際の公開鍵バイトに置換）
ssh -i ~/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46 \
  "echo 'command=\"docker stats --no-stream; free -h; df -h; uptime\",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty <PUBLIC_KEY> hikky-claude-restricted' >> ~/.ssh/authorized_keys"

# 追記後の該当行を表示して実証
ssh -i ~/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46 \
  "grep 'hikky-claude-restricted' ~/.ssh/authorized_keys"
```
