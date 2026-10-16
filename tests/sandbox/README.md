# tests/sandbox

この文書は何か(専門用語なしの1行): GitHub 上の試験場（sandbox-test）で動かす試験スクリプトの置き方。

規則の正本: [docs/ops/runner-commands.md](../../docs/ops/runner-commands.md)「仮想マシンが要る試験（GitHub で行う）」

## 置き方
- 1 ファイル＝1 試験。`tests/sandbox/<名前>.sh`。名前は英小文字・数字・ハイフンのみ（64 文字まで）。
- 実行: `gh workflow run sandbox-test.yml --ref <ブランチ> -f test=<名前>` → `gh run watch`
- `--ref` に指定したブランチの tests/sandbox が使われる。

## 守ること
- secrets・本番データ・本番への接続を使わない。パスワード等は試験専用の固定値にする。ログは公開される。
- 失敗時は片付ける前に `docker logs` を出す（trap の中で出す。先に消すと原因が追えない）。
- 後始末は trap で行い、コンテナを残さない。
- runner のディスクは約 14GB。前後で `df -h /` がログに出る。
