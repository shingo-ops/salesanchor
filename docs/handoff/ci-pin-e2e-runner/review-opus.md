# review-opus: 画面検査の実行環境固定 — 独立審査

> この文書は何か（1行）: ワークフロー1ファイルの変更と設計書類を、設計担当（Opus）が自分で動かした検査と CI の原文だけを根拠に点検した記録。

**日付**: 2026-10-26
**審査対象**: PR #4781（`release/ci-pin-e2e-runner`・HEAD `3a1898b3b`）
**設計**: `docs/handoff/ci-pin-e2e-runner/design.md`／**recon**: 同 `recon.md`

## 1. 自分で確かめた一次情報

| 何を | どこで | 結果 |
|---|---|---|
| 壊れていた証拠 | run 40274501029（PR #4780）の `画面検査（内部）` ログ原文 | `ERROR: Playwright does not support chromium on ubuntu26.04-x64`。落ちたのは `Install Playwright browsers` ステップ＝**テスト0件** |
| 直った証拠 | run 40278386495（本 PR）の `画面検査（内部）` ログ原文 | `Running 363 tests using 4 workers` → **286 passed / 77 skipped / 失敗0**（5.0m）。**0件→286件** |
| 他の検査を壊していないこと | `gh pr checks 4781` | **40 pass / 0 fail / 9 skipping**。`process-artifacts gate` も pass |
| 固定先が妥当であること | 同一 run 40274501029 内の `karte-gate-run`（`ubuntu-24.04`） | **緑**＝同じ時刻・同じ Playwright 版で 24.04 なら動く（対照） |
| 先例と同じ形であること | `.github/workflows/karte-gate.yml:37-38`（コミット `da513ba49`・2026-10-24） | 理由コメント＋`runs-on: ubuntu-24.04`。**本便も同じ形**（流儀を増やしていない） |
| YAML の構文 | 手元 `python3` の `yaml.safe_load` | OK |
| 変更の大きさ | `git diff --stat` | `.github/workflows/e2e.yml` のみ・9行追加 2行削除（うち6行がコメント） |

**77 skipped の中身**: `inbox-single-column.spec.ts`（既存。本便の前から同じ）。
「skip の中身を必ず見る」の教訓どおり確認済みで、本便が新たに飛ばしたものは**0件**。

## 2. 重大な指摘（1件・この審査で直した）

### R1. 直したことを自分の PR で確かめられなかった

1回目の CI（run 40277891567）で `画面検査（内部）` が **skipping**。
`detect-changes` のフィルタが `frontend/**` だけを見ており、**画面検査の定義そのものを変えた PR は
「フロント未変更」と判定される**ため。これでは設計 ② K1・⑤ C3（この PR で緑を確かめる）が
原理的に満たせない＝**書いた基準が測れない設計**だった。

**直した所**: フィルタに `.github/workflows/e2e.yml` 自身を追加（`:50-55`）。
2回目の CI で画面検査が実際に走り **286 passed** を返した＝基準が測れる形になった。

## 3. 残す指摘（直さない・起票する）

| # | 指摘 | 判断 |
|---|---|---|
| R2 | `ubuntu-24.04` もいつか提供終了する | 期限は GitHub のアナウンス次第。⑫ D3（Playwright 版上げで固定を外す）として起票済み |
| R3 | キャッシュ鍵 `playwright-${{ runner.os }}-<version>` が OS 版を区別しない | 今回は「当たっても `install-deps` が落ちる」ので実害に差はない。⑫ D2 として起票済み |
| R4 | 「テスト0件」を機械が異常と見なす仕組みが無い（今回は人が気づいた） | 本便の範囲外。⑫ D4 として起票済み |
| R5 | 同じ穴（自分の定義を変えた PR で自分が走らない）が他のワークフローにもある可能性 | ⑫ D5 として起票済み |
| R6 | `.github/workflows/brand-asset-monitor.yml`・`.github/workflows/qa-smoke.yml` も Playwright を使う | 定期・手動実行で PR を塞がない。⑫ D1 として起票済み |

## 4. 設計との一致

| 設計 | 実装 | 一致 |
|---|---|---|
| ④ `visual-language-run` を `ubuntu-24.04` に固定＋理由コメント | `.github/workflows/e2e.yml:148-155` | ○ |
| ④ `playwright`（停止中）も同じ形に揃える | 同 `:248-255` | ○ |
| ④ 変更検出フィルタに本ワークフロー自身 | 同 `:50-55` | ○ |
| ④ テストの中身・spec・Playwright の版・キャッシュ鍵は触らない | `git diff` は `runs-on` 2行＋フィルタ1行＋コメントのみ | ○ |

## 5. 判定

**APPROVE**。壊れていた状態（テスト0件で赤）と直った状態（286件合格）の**両方を CI の原文で確認**済み。
R1 は本審査で直して測れる形にした。R2〜R6 は ⑫ に起票して次便へ送る。
