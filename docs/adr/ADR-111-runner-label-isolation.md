# ADR-111: runner-label-isolation — Shingo-Mac-Temp 専用ラベルによる開発環境分離

| 項目 | 内容 |
|------|------|
| ステータス | Accepted |
| 作成日 | 2026-06-05 |
| 起案 | しんご（PO）、ひとし（森本） |
| 関連 ADR | ADR-029（self-hosted runner fleet）Amendment |

## What

`claude-pipeline.yml` の全ジョブを Shingo-Mac-Temp のみで実行されるよう固定する。

## Why

ADR-029 では macOS ラベルを持つ2台のMac（Shingo-Mac-Temp / Hikky-dev-Mac）が存在し、`runs-on: [self-hosted, macOS]` ではGitHubがどちらかに無作為に振り分ける設計だった。

しかし 2026-06 時点でこの設計に問題が顕在化した:

- claude-pipeline.yml の各ジョブが Hikky-dev-Mac（Suttanさんのマシン）で実行される場合がある
- Suttanさんの作業中に Claude Code が突然起動するという事象が発生
- 開発者のマシンに意図しない副作用を与えることは運用上受け入れられない

## Decision

Shingo-Mac-Temp に専用の GitHub Runner カスタムラベル `shingo-mac` を付与し、`claude-pipeline.yml` の全ジョブの `runs-on` を `[self-hosted, macOS, shingo-mac]` に変更する。

GitHub の `runs-on` は複数ラベルを AND 条件で評価するため、`shingo-mac` ラベルを持たない Hikky-dev-Mac には一切ジョブが割り当てられなくなる。

### 変更内容

**GitHub Settings（手動・しんごさんが実施）:**

> Settings → Actions → Runners → Shingo-Mac-Temp → Edit → カスタムラベル `shingo-mac` を追加
> （Hikky-dev-Mac には追加しない）

**コード変更（claude-pipeline.yml）:**

```yaml
# 変更前
runs-on: [self-hosted, macOS]

# 変更後
runs-on: [self-hosted, macOS, shingo-mac]
```

対象ジョブ（8箇所）: context / researcher / claude-worker / reviewer / evaluator / governance / automerge / regenerate

**定着化（runner-label-lint.yml）:**

`[self-hosted, macOS]` に `shingo-mac` がない設定を CI で自動検出・エラーにする新ステップを追加。

## Consequences

- Hikky-dev-Mac は claude-pipeline の実行対象から完全に除外される
- Shingo-Mac-Temp がオフラインの場合、パイプラインは runner が来るまでキューで待機する（従来通り）
- `runner-label-lint` CI により、誰かが誤って `shingo-mac` ラベルを外した設定に戻した場合でも即時検出される
