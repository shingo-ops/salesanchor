# 反映記録 1: 段階A（PR #5120）

- 記録: 2026-11-04 Claude Opus（設計担当）

## 1. 起きたこと

- 2026-11-04 19:5x JST ごろ、`gh pr merge 5120 --merge` が `502 Bad Gateway` を返した。直後の `gh pr view 5120` では state=MERGED、mergeCommit=63a69bfb653b955e5a3a87dd3ce908b003a995bc。
- 約 35 分後、`gh run list --commit 63a69bfb653b955e5a3a87dd3ce908b003a995bc` は 0 件。`gh run list --workflow deploy.yml` の最新は 7d56ab771（2026-11-04T09:04:56Z）のまま。
- つまり main への push の合図が GitHub 側で出ず、deploy.yml（`on: push: branches: main` のみ。手動起動なし）が動かなかった。

## 2. 対処

- この記録だけを足す docs の PR を main へ合流し、push の合図をもう一度出す。deploy.yml は main の HEAD を反映するので、#5120 の変更もこの反映に含まれる。
- コードの変更・手動の反映は行わない。

## 3. 確かめること

| 基準 | 検証方法 |
|---|---|
| この PR の合流コミットで deploy.yml が success | `gh run list --workflow deploy.yml` |
| 本番の画面に段階A が届く | design.md §2-4 の A3（001 の所有者で Chrome で開く） |
