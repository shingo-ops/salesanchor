# recon: CI の画面検査が「1件も走らない」赤になる原因調べ

> この文書は何か（1行）: 画面検査（Playwright）が内容の失敗ではなく**起動前に落ちている**ことを、CI のログと社内の先例から確かめた記録。

**日付**: 2026-10-26
**由来**: PR #4780（Popover 金型・宿題 C2）の CI で `画面検査（内部）` が 31 秒で赤になった

## 1. 一次情報（CI のログ原文）

`gh run view --job 121414365101 --log-failed`（run 40274501029・`画面検査（内部）`）:

```
BEWARE: your OS is not officially supported by Playwright; installing dependencies for ubuntu26.04-x64 as a fallback.
Cannot install dependencies for ubuntu26.04-x64 with Playwright 1.59.1!
Failed to install browsers
Error: ERROR: Playwright does not support chromium on ubuntu26.04-x64
##[error]Process completed with exit code 1.
```

落ちたのは `Install Playwright browsers` ステップ＝**テストは1件も実行されていない**。
つまり「検査が何かを見つけて赤」ではなく「検査が始まる前に赤」。

## 2. なぜ今になって起きたか

- `.github/workflows/e2e.yml` の Playwright を使う2ジョブは `runs-on: ubuntu-latest`。
- GitHub の `ubuntu-latest` が **ubuntu-26.04** を指すようになった。
- `frontend/package.json:92` の `@playwright/test` は `^1.59.1` で、この版は ubuntu-26.04 用の依存を入れられない。

**キャッシュが当たっても直らない**: `.github/workflows/e2e.yml` のキャッシュ鍵は `playwright-${{ runner.os }}-<version>` で
OS 版を含まない（`:184`）。当たった場合に走る `Install system deps (chromium)`（`:190-192`）＝
`npx playwright install-deps chromium` も同じ理由で落ちる。**どちらの道でも赤**。

## 3. 社内に先例がある（同じ症状・同じ直し方）

`.github/workflows/karte-gate.yml:37-38`:

```
    # ubuntu-26.04 では Playwright 1.59.1 が依存（日本語フォント）を入れられず基準画像と食い違うため固定（2026-10-23 run 39929732953）
    runs-on: ubuntu-24.04
```

コミット `da513ba49`（2026-10-24）「ci: karte-gate-run の実行環境を ubuntu-24.04 に固定」。
**同じ run 40274501029 の中で、この karte-gate は緑（`karte-gate-run` pass 2m8s）**＝
固定すれば動くことが**同一実行の中で実証されている**。

## 4. 影響範囲

| ジョブ | 場所 | いまの状態 |
|---|---|---|
| `画面検査（内部）`（`visual-language-run`） | `.github/workflows/e2e.yml:148-152` | **赤（1件も走らない）**。frontend を触る PR すべてで同じ |
| `Playwright E2E (chromium)`（`playwright`） | 同 `:245-248` | `if: false` で停止中（2026-06-01 から）。再開した瞬間に同じ赤になる |
| `karte-gate-run` | `.github/workflows/karte-gate.yml:38` | **すでに ubuntu-24.04 固定済み＝緑** |
| `.github/workflows/brand-asset-monitor.yml` / `.github/workflows/qa-smoke.yml` | Playwright を使うが本便の対象外 | 定期実行・手動実行で PR を塞がないため別途 |

## 5. 分かったこと（結論）

- `.github/workflows/e2e.yml` の Playwright 2ジョブの `runs-on` を **`ubuntu-24.04` に固定するだけ**で直る。
- 版上げ（`@playwright/test` の更新）は**基準画像の食い違い**を招き得るので本便では採らない（karte-gate が固定を選んだ理由と同じ）。
