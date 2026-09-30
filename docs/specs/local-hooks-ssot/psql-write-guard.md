# psql-write-guard 実装記録（2026-09-04）

> この文書は何か（専門用語なしの1行）:
> CCが本番DBに直接SQLを書き込めないようにした仕組みと、その実装記録。

親: [local-hooks-ssot/](./README.md)
日付: 2026-09-04
PO: しんごさん（GO受領）
実装: shingo-cc

---

## 1. 背景（CC_TASK_GUARD-01）

2026-09-03 21:37: CCが GO 発行前に本番DBへ NR0136 を直接投入。

```
ssh ubuntu@49.212.137.46 "docker exec -i astro-webapp-postgres-1 psql -U jarvis -d jarvis_db" < /tmp/adr136_test_data.sql
```

`agent-danger-hook.sh` はコマンド文字列の中身で判定しているため、
**SQLをファイルに入れてパイプ/リダイレクトで渡す形式は検知できなかった。**

翌日、`migration 20260903_160000` の「135件ちょうど」チェックが 136件で失敗→デプロイ停止。

---

## 2. 実装内容

### 対象ファイル
- **`~/.claude/scripts/agent-danger-hook.sh`**（リポジトリ外・直接適用）
- バックアップ: `~/.claude/scripts/agent-danger-hook.sh.bak-20260904T083141`

### 追加したブロック（hookの先頭部分に追加）

#### A. SalesAnchorスコープ判定
```bash
REMOTE_URL=$(git -C "$PWD" remote get-url origin 2>/dev/null || true)
if [[ "$REMOTE_URL" == *"shingo-ops/salesanchor"* ]]; then
  SALESANCHOR_SCOPE=1
else
  SALESANCHOR_SCOPE=0
fi
```

#### B. 本番DB書き込みブロック（対策A）

検知パターン（正規表現）:

| パターン | ブロック理由 |
|---------|------------|
| `ssh\b.*\bpsql\b.*<\s*\S` | SSHでpsqlにファイルをredirect |
| `ssh\b.*\bpsql\b.*-f\s+\S` | psqlに-fでファイル指定 |
| `\|\s*...\bpsql\b` | パイプでpsqlに流し込み |
| `docker.*exec.*-i.*psql.*<\s*\S` | docker execでpsqlにstdin |
| `docker.*exec.*psql.*-f\s+\S` | docker execで-fファイル指定 |
| `-c "INSERT/UPDATE/DELETE/..."` | -cオプションで書き込みSQL直接 |

許可:
- `-c "SELECT ..."` → exit 0（読み取りは許可）

#### C. permit経由での解除（対策B）

```bash
bash scripts/permit-danger.sh "psql write"
```

`agent-danger-hook.sh` がワンタイムチケット（30分・1回消費）を確認し、
チケットがあれば実行を許可してチケットを削除する。

---

## 3. テスト結果（実測）

```
=== 1: ssh psql -c SELECT (通るべき) ===
STATUS: PASS(allowed)

=== 2: ssh psql < file (ブロックすべき) ===
STATUS: BLOCKED(exit=2)
STDERR: 🚫 BLOCKED [psql-write-guard]: ...
   検知パターン: ssh+psql < file

=== 3: cat file | psql (ブロックすべき) ===
STATUS: BLOCKED(exit=2)
STDERR: 🚫 BLOCKED [psql-write-guard]: ...
   検知パターン: pipe to psql

=== 4: crm-app (他リポジトリ・ブロックされないべき) ===
STATUS: PASS(allowed)

サマリー: 4/4 OK
```

テストスクリプト: `/tmp/hook_test.py`

---

## 4. 適用範囲

- **適用**: `shingo-ops/salesanchor` リポジトリ内での作業
- **除外**: `GEN-RYU-System/crm-app` 等の他リポジトリ（git remote URLで判定）

---

## 5. 戻し方

```bash
chmod u+w ~/.claude/scripts/agent-danger-hook.sh
cp ~/.claude/scripts/agent-danger-hook.sh.bak-20260904T083141 \
   ~/.claude/scripts/agent-danger-hook.sh
chmod a-w ~/.claude/scripts/agent-danger-hook.sh
```
