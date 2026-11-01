<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — storybook-auth-mock-exports

**仕事名**: storybook-auth-mock-exports  
**日付**: 2026-11-01  
**対象ADR**: ADR-067（見本集 Storybook を部品の見本の置き場とする）  
**担当**: architect（Opus）

---

## 何が起きているか（観測事実）

- 本線 e14ace4b6（#4989）を含む枝で、CI の Storybook build check が MISSING_EXPORT 3件で失敗する。失敗を確かめたのは、#4989 自身の枝、PR #4974 の先頭 4fdad8215・49c459985、別の枝 9b6a3b701。本線そのものでの点検の記録は確かめていない（未確認）。
- 失敗の文面（PR #4974 の run 41301008736）は、`frontend/src/lib/firebase-auth.ts` が読み込む `EmailAuthProvider`・`reauthenticateWithCredential`・`updatePassword` が、見本用の写し `frontend/src/lib/__storybook-mocks__/firebase-auth.ts` に無いというもの。
- 本線 4172d0c9f を土台にした PR #4974 の 31a865517 では、同じ点検が success だった。

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/.storybook/main.ts:35` | 見本集では firebase/auth を見本用の写しに差し替える |
| `frontend/src/lib/__storybook-mocks__/firebase-auth.ts:4` | 写しには getAuth・onAuthStateChanged・signInWithEmailAndPassword・signOut・sendPasswordResetEmail の5つしか無い（4〜22行） |
| `frontend/src/lib/firebase-auth.ts:3` | 本物は EmailAuthProvider（3行）・reauthenticateWithCredential（5行）・updatePassword（9行）も firebase/auth から読み込む |
| `frontend/src/lib/firebase-auth.ts:161` | EmailAuthProvider は credential(email, password) を持つ形で使う |
| `frontend/src/lib/firebase-auth.ts:169` | reauthenticateWithCredential は user と credential を受け取る |
| `frontend/src/lib/firebase-auth.ts:182` | updatePassword は user と新しいパスワードを受け取る |
| `frontend/src/hooks/usePermissions.ts:11` | 本線 e14ace4b6（#4989）で useApiQuery を読み込むようになった |
| `frontend/src/lib/query/apiQuery.ts:16` | apiQuery は AuthContext を読み込む |
| `frontend/src/contexts/AuthContext.tsx:14` | AuthContext は lib/firebase-auth を読み込む |
| `frontend/src/components/PriorityScoreOverride.tsx:11` | 見本のある部品が usePermissions を使うので、見本集の組み立てに firebase-auth.ts が入る |
| `.github/workflows/frontend-check.yml:86` | 点検は npm run build-storybook を流す |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 失敗はこの写しの不足だけが原因か | 失敗の文面の3件がすべて写しの不足の export。ほかのエラーは無い（run 41301008736 の記録） | ✅ 解消済み |
| 2 | 本物の3つは見本集で呼ばれるか | 見本集は組み立てるだけで、パスワード変更の画面の見本は無い。写しは形だけあればよい。呼ばれた時は既存の写しと同じく「見本集では使えない」と分かる失敗にする | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
