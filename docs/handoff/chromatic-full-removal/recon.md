# recon — Chromatic 関連の完全撤去

**仕事名**: chromatic-full-removal
**日付**: 2026-06-24
**対象ADR**: ADR-073
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/package.json:47` | `"chromatic": "npx chromatic --project-token=$CHROMATIC_PROJECT_TOKEN"` スクリプト。撤去対象。 |
| `frontend/package.json:86` | `"@chromatic-com/storybook": "^5.2.1"` devDependency。撤去対象。 |
| `frontend/package.json:102` | `"chromatic": "^16.0.0"` devDependency。撤去対象。 |
| `frontend/package-lock.json` | chromatic 言及 18箇所（上記2パッケージのロックエントリ）。npm install 再生成で除去。 |
| `frontend/.storybook/main.ts:14` | `"@chromatic-com/storybook"` プラグイン登録。撤去対象。 |
| `frontend/.storybook/main.ts:21` | `// firebase/app と firebase/auth を Storybook/Chromatic 環境でモックに差し替える` コメント。文言除去対象。 |
| `frontend/src/lib/__storybook-mocks__/firebase-app.ts:1` | `// Storybook/Chromatic 用 firebase/app モック` コメント。モック実体は残す。 |
| `frontend/src/lib/__storybook-mocks__/firebase-auth.ts:1` | `// Storybook/Chromatic 用 firebase/auth モック` コメント。モック実体は残す。 |
| `docs/adr/ADR-073-design-system-kgi-rubric.md:77` | 「ビジュアルリグレッションテスト（Chromatic等）（現フェーズでは手動確認で代替）」。**撤去しない**（Chromatic不使用を肯定する根拠）。 |
| `.github/workflows/deploy.yml:52` | `# 他ワークフロー（chromatic/e2e/frontend-check）と統一。` コメントのみ。実行なし。 |

---

## ワークフロー `.github/workflows/chromatic.yml` の実在確認

```
git ls-files -- '.github/workflows/chromatic.yml'  → (空出力)
git show origin/develop:.github/workflows/chromatic.yml → fatal: path does not exist in 'origin/develop'
```

**結論**: `chromatic.yml` は develop に**存在しない**。PR #2519（MERGED）の `docs/handoff/remove-chromatic-ci/evidence.md:3` に「snapshot of the deleted file」と記載されており、PR #2519 よりも前に削除済みと判断。変更1（workflow 削除）は**実施不要**。

---

## PR #2519 の実態

- `git show 45b02e06 --stat` の差分: `docs/handoff/remove-chromatic-ci/` 配下 3 ファイル追加 + `active-work.md` + `tasks/todo.md` のみ
- `frontend/package.json`・`frontend/.storybook/main.ts` への変更は**ゼロ**
- `docs/handoff/remove-chromatic-ci/design.md` の設計は残ったが実装 PR は起票されず、実装はすべて未着手
- 「設計書があるから完了」と誤認しうる構造の実例。本作業の完了定義は `git grep 0件 ＋ ビルド成功` とする

---

## ruleset・required status checks

- `gh api repos/shingo-ops/salesanchor/rulesets/15777895 --jq '...'` で現在の 10件を確認（2026-06-24 PUT後）
- `Chromatic Snapshot` / `UI Tests (Chromatic App)` / `UI Tests (chromium)` は required に含まれていない
- **required 除去作業は不要**

---

## 残すもの（改竄しない）

- `docs/adr/ADR-073-design-system-kgi-rubric.md:77`（Chromatic不使用を肯定する根拠として保持）
- `docs/handoff/remove-chromatic-ci/` 配下（過去スプリント記録）
- `docs/ai-agents/evidence-registry.md:53`・各 handoff の履歴言及（過去記録）

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | chromatic.yml が develop に存在するか | `git ls-files` + `git show origin/develop:...` で確認 | ✅ 解消済み（存在しない） |
| 2 | ruleset に Chromatic が required として残っているか | `gh api` で 10件確認 | ✅ 解消済み（含まれていない） |

**未解決ゼロ確認**: 全て解消済み

---

**正本設計**: `docs/handoff/chromatic-full-removal/design.md`
