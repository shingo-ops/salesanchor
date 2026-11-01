<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — storybook-auth-mock-exports

**対象ADR**: ADR-067  
**recon**: docs/handoff/storybook-auth-mock-exports/recon.md  
**日付**: 2026-11-01  
**担当**: Planner（Opus）

---

## 目的

本線で落ちている見本集の組み立ての点検（Storybook build check）を、元どおり通るようにする。見本用の写しに、本物が読み込む3つの名前を足すだけにする。アプリ本体の動きは変えない。

## 外部・過去事例の参照と我々への応用

- 該当なし：見本用の写しに足りない名前を足すだけの直し。既存の写しの書き方（`frontend/src/lib/__storybook-mocks__/firebase-auth.ts:14` の「見本集では使えない」と分かる失敗）にそろえる。

---

## 作業指示書（実装役はこれだけを行う）

触るファイル: `frontend/src/lib/__storybook-mocks__/firebase-auth.ts` の1つだけ。

変更前（22行目まで。末尾は sendPasswordResetEmail）:

```ts
export const sendPasswordResetEmail = async () => {
  throw new Error('sendPasswordResetEmail is not available in Storybook');
};
```

変更後（上の3行は変えず、そのすぐ後ろに次を足す）:

```ts

export const EmailAuthProvider = {
  credential: (email: string, password: string) => ({ email, password }),
};

export const reauthenticateWithCredential = async () => {
  throw new Error('reauthenticateWithCredential is not available in Storybook');
};

export const updatePassword = async () => {
  throw new Error('updatePassword is not available in Storybook');
};
```

触らない範囲: `frontend/src/lib/firebase-auth.ts`・`frontend/.storybook/main.ts`・`frontend/src/hooks/usePermissions.ts`・ほかの全ファイル。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 見本集の組み立てが通る | frontend で `npm run build-storybook` の終了コード 0、MISSING_EXPORT 0件。CI の Storybook build check が pass |
| 型の点検が通る | frontend で `npx tsc --noEmit` の終了コード 0 |
| 変えたファイルが1つだけ | `git diff --name-only origin/main...HEAD` が写しのファイルとこのフォルダの文書だけ |
| アプリ本体が変わらない | 写しは `frontend/.storybook/main.ts:35` の見本集の差し替えでしか使われない（`git grep __storybook-mocks__` で確かめる） |

---

## 技術 How・KPI

- KPI: 本線の Storybook build check の失敗 1 → 0。
- 技術選択: 写しに名前を足す（理由: 見本集の差し替えのしくみは既にあり、足りないのは名前だけ。本物の読み込みを変えると本番のログインに触れるので避ける）。

---

## 弊害・トレードオフ

- 本物に新しい読み込みが増えると、また同じ失敗が出る → 対策: CI の Storybook build check がそのたびに止める（守り手: `.github/workflows/frontend-check.yml`）。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 上の変更後のとおり写しに3つ足す・受け入れ基準を流す | Sonnet（クラウド） |
| 2 | 審査・マージ | Opus |

---

## 継続

- 完了後の監視: 本線と各 PR の Storybook build check。
- 次フェーズへの引き継ぎ: PR #4974 に本線を取り込み、見本集の点検が通ることを確かめてからマージする。
