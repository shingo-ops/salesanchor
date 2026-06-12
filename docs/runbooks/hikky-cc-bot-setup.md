# Runbook: hikky-cc ボットアカウント セットアップ

> **根拠**: ADR-136 / Shingo決定 2026-06-12  
> **目的**: CC（Claude Code）の GitHub 操作を `shingo-ops` と分離し、Shingo（PO）が CC 作成 PR を承認できる体制を確立する。

---

## 全体の流れ

```
[人間] hikky-cc アカウント作成 & PAT発行
  ↓
[人間] .claude-access.env に PAT を書く
  ↓
[CC]  gh auth 切り替え & 動作確認
  ↓
[人間] テスト PR を shingo-ops で Approve → 確認
  ↓
完了
```

---

## Part 1: 人間がやる手順（Shingo）

### Step 1: hikky-cc アカウント作成

1. **ブラウザで `https://github.com/join` を開く**
2. メールアドレスを入力（例: shingo+hikky-cc@your-domain.com）
3. ユーザー名に `hikky-cc` と入力
4. パスワードを設定（強いもの・パスワードマネージャー推奨）
5. 「Create account」をクリック
6. メール認証を完了する

> ⚠️ **注意**: GitHub 無料プランで OK。個人メール+エイリアスでも可。

---

### Step 2: salesanchor リポジトリに hikky-cc を招待

1. **ブラウザで `https://github.com/shingo-ops/salesanchor/settings/access` を開く**
   - 「Settings」タブ → 「Collaborators and teams」
2. 「Add people」ボタンをクリック
3. 検索欄に `hikky-cc` と入力 → ユーザーを選択
4. 権限を **「Write」** に設定
5. 「Add hikky-cc to this repository」をクリック
6. hikky-cc のメール受信箱で招待メールを確認 → 「Accept invitation」リンクをクリック

---

### Step 3: Fine-grained PAT 発行（hikky-cc アカウントで実施）

1. **hikky-cc アカウントでログイン**（Step 1 で作ったアカウント）
2. **`https://github.com/settings/personal-access-tokens/new` を開く**
   - プロフィール右上 → Settings → Developer settings → Personal access tokens → Fine-grained tokens → 「Generate new token」
3. 以下の通り設定:

| 項目 | 値 |
|------|-----|
| Token name | `salesanchor-cc-bot-2026` |
| Expiration | **1 year**（最長）|
| Resource owner | `hikky-cc`（デフォルト） |
| Repository access | **Only select repositories** → `shingo-ops/salesanchor` |

4. **Permissions（Repository permissions）** を以下に設定:

| 権限 | レベル |
|------|--------|
| Contents | **Write**（git push に必要） |
| Pull requests | **Write**（PR 作成・編集に必要） |
| Metadata | **Read**（必須・自動） |
| Actions | **Read**（CI ステータス確認に必要） |
| Issues | **Write**（issue 作成に必要） |
| Secrets | **Read** のみ（Write 不要） |

5. 「Generate token」ボタンをクリック
6. **表示されたトークン文字列（`github_pat_...`）をコピー**（この画面を閉じると二度と見えない）

---

### Step 4: .claude-access.env に PAT を保存

CC に渡すため、ローカル専用ファイルに書く（**git追跡・チャット記載禁止**）:

```bash
# ターミナルで実行（~/ = ホームディレクトリ）
echo 'HIKKY_CC_PAT=github_pat_ここにコピーしたトークンを貼り付け' >> ~/.claude-access.env
chmod 600 ~/.claude-access.env
```

> 確認: `cat ~/.claude-access.env | grep HIKKY_CC_PAT` でトークンが見えれば OK。

---

### Step 5: CC に切り替えを依頼

CC（このチャット）に以下のメッセージを送る:

```
.claude-access.env に HIKKY_CC_PAT を書いた。hikky-cc に gh 認証を切り替えて、テスト PR で確認して。
```

---

## Part 2: CC がやる手順（Claude Code）

> ⚠️ **前提**: Part 1 が完了し、`~/.claude-access.env` に `HIKKY_CC_PAT` が書かれていること

### Step 6: gh auth を hikky-cc に切り替え

```bash
# PAT 読み込みと gh 認証切り替え
source ~/.claude-access.env
echo "${HIKKY_CC_PAT}" | gh auth login --hostname github.com --with-token

# 確認
gh auth status
# → "Logged in to github.com account hikky-cc" と表示されれば OK
```

### Step 7: テスト PR 作成

```bash
cd ~/worktrees/salesanchor/<任意のworktree>
# 空コミットでテストブランチ作成・PR起票
git checkout -b test/hikky-cc-auth-check
git commit --allow-empty -m "test: hikky-cc 認証チェック用テストPR（クローズ予定）"
git push origin test/hikky-cc-auth-check

gh pr create \
  --base develop \
  --title "[TEST] hikky-cc 認証確認 — クローズ予定" \
  --body "hikky-cc アカウントでの PR 作成確認テスト。Shingo が shingo-ops で Approve できることを確認後クローズ。"
```

### Step 8: 結果確認・報告

1. Shingo（shingo-ops）がテスト PR を Approve → Approve できれば成功
2. テスト PR をクローズ: `gh pr close <PR番号>`
3. テストブランチ削除: `git push origin --delete test/hikky-cc-auth-check`
4. 確認結果を Shingo に報告

---

## Part 3: 運用メモ

### PAT 更新（1年後）

1. hikky-cc アカウントで `https://github.com/settings/personal-access-tokens` を開く
2. `salesanchor-cc-bot-2026` を選択 → 「Regenerate token」
3. 新トークンを `~/.claude-access.env` の値に上書き
4. CC に再度 Part 2 を実施させる

### ロールバック（緊急時）

```bash
# shingo-ops に戻す（Shingo の PAT が ~/.claude-access.env に SHINGO_OPS_PAT として保存済みの場合）
source ~/.claude-access.env
echo "${SHINGO_OPS_PAT}" | gh auth login --hostname github.com --with-token
```

---

## 関連

- ADR-136: `docs/adr/ADR-136-cc-bot-github-identity.md`
- B-11（認証情報管理ポリシー）: `docs/B-11_secret-management.md`
- 参照: `docs/runbooks/secret-rotation.md`
