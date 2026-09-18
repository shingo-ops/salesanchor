# Design: PR本文 diff照合チェック追加（検査6）

## 設計目標

**KGI**: PR author がローカルで PR本文 の「触るファイル:」「削除するファイル:」宣言漏れを即座に検出し、CI FAIL を事前に防ぐ

**KPI**:
- ローカル validation スクリプト実行時、宣言漏れがあれば exit 1 で返す
- CI check-process-artifacts.js と同一の除外ルールを適用し、偽陽性を最小化
- エラーメッセージで具体的なファイル名を表示（修正指示を含む）

## 実装方針

### 検査6 の位置づけ

```
validate-pr-body.sh
├─ 検査1: 「標準ワークフロー確認」セクション存在確認（必須）
├─ 検査2: recon.md パス存在確認（必須）
├─ 検査3: 設計doc パス存在確認（必須）
├─ 検査4: 「触るファイル:」セクション存在確認（必須）
├─ 検査5: 「削除するファイル:」セクション存在確認（必須）
└─ 検査6: git diff vs 宣言 照合（必須） ← 追加
```

### 照合ロジック

```
1. git diff --numstat origin/main...HEAD を実行
   ↓
2. ファイルを1行ずつ処理
   - binary (added/deleted == "-") はスキップ
   - 除外パターン適用（3パターン）
   ↓
3. PR本文から「触るファイル:」セクション抽出
   - リスト形式（- または *）対応
   - 同一行カンマ区切り対応
   - 「なし」キーワード対応
   ↓
4. 宣言漏れ検出
   - touch_files に含まれないファイル → エラー
   ↓
5. 削除ファイル照合（削除行あり かつ delete_match 存在時のみ）
   - delete_files vs declared_delete を照合
   - 未宣言の削除 → エラー
```

### 除外パターン（CI check-process-artifacts.js:757-761 から転写）

| パターン | 理由 | 例 |
|---------|------|-----|
| `package-lock.json$` | npm install で自動生成・宣言不要 | `package-lock.json` |
| `-snapshots/.*\.png$` | Playwright E2E snapshot・自動生成 | `__playwright-snapshots__/page.png` |
| `^\.claude-pipeline/active-work\.md$` | 自動更新ファイル・宣言不要 | `.claude-pipeline/active-work.md` |

### エラー出力形式

```
❌ 宣言外のファイルを変更しています:
   - src/components/Button.tsx
   - src/hooks/useButton.ts
   → 「触るファイル:」に追記してください

❌ 宣言外のファイルから行を削除しています:
   - backend/old_module.py
   → 「削除するファイル:」に追記してください
```

## 検証基準

| シナリオ | 入力 | 期待値 | 検証方法 |
|---------|------|--------|---------|
| 全ファイル宣言済み | git diff: [a.ts, b.ts] / PR本文: [a.ts, b.ts] | exit 0 | PR #3554 本体実装時に確認済み |
| 2ファイル宣言漏れ | git diff: [a.ts, b.ts, c.ts] / PR本文: [a.ts, b.ts] | exit 1 + ファイル名表示 | PR #3554 本体実装時に確認済み |
| SKIP フラグ有効 | PR_BODY_VALIDATE_SKIP=1 | exit 0 | 既存検査1-5のメカニズムを再利用 |
| git fetch タイムアウト | 30秒以上 | pass（検査6スキップ） | タイムアウト catch で処理 |
| リスト形式混在 | `- a.ts, b.ts\n- c.ts` | 全宣言を認識 | regex マッチで実装 |

## 影響範囲

### 変更ファイル
- `scripts/dev/validate-pr-body.sh`: 99行追加（検査6ロジック）

### 呼び出し元
- `.husky/commit-msg`: husky hook で実行（全PR author）
- `validate-pr-body.sh` を手動実行した develop/author（既存）
- CI 不明（pre-commit hook で自動実行される仕様であれば全PR）

### 非互換性
- なし。新しい検査の追加であり、既存検査に影響なし

## 戻し方

検査6 を削除する場合:
```bash
git revert <commit-hash>
```
→ 検査1-5 は機能継続

または該当行（107-204行）を削除してコミット。

## 測り方

1. **即座の効果**: 本PR マージ後、次のrelease PRで新しい検査6 がログに出力されるか確認
   ```
   ✅ 「検査6: diff照合」実行中...
   ```

2. **長期効果**: 以降のPRで「宣言外のファイルを変更しています」エラーが pr-body-validation で検出され、CI check-process-artifacts.js での FAIL が減少するか観測（未実装）

3. **リグレッション**: 既存検査1-5 が引き続き機能するか。検査6 の例外処理（timeout, FileNotFoundError）で既存検査をブロックしないか

## 外部事例・参考

- **Kubernetes prow PR plugins**: PR body validation with structured comment parsing
- **Angular commit-lint**: 構造化メッセージ検査で宣言と実装の齟齬を検出
- **Next.js changesets**: 変更ファイルとchangelog entry の整合性チェック
