# 結果: py312-guard（2026-10-16）

状態: 実装済み・導入済み（`~/.claude/settings.json` に 1 本追加。控え `~/.claude/settings.json.bak-py312-guard-20261016171002`）。AGENTS.md 追記 4f0ec4266。

| # | 結果 | 根拠 |
|---|---|---|
| K1〜K5 | ○ 単体 9/9 合格（K1 12 形・K2 10 形は subTest） | /tmp/CC報告ファイル/py312-guard/impl/2_unittest.txt |
| K5 記録 | ○ agent-events.jsonl に `hook: python-version-guard` の 1 行（08:12:03Z） | Opus 実機 |
| K6 | ○ Opus 本体で `python3 -m venv /tmp/py312-guard-probe` が拒否され、作られなかった。`/usr/local/bin/python3.12 -m venv /tmp/py312-guard-probe312` は rc=0・version 3.12.8 | Opus 実機 |
| K7 | ○ rustc 最大 0 本（5 秒ごと 23 回）。自前の組み立て 0 件。install rc=0・119 秒 | /tmp/CC報告ファイル/py312-guard/k7/ |

## 記しておくこと
- K7 中の負荷（1 分平均）は 39.33 → 最大 122.04。測定前から 39 あり、他セッションの負荷が含まれる。install 単独の寄与は切り分けていない（rustc は 0）
- 件数の数え方: recon P8 の「26 件」は再現できなかった。担当の実測は PreToolUse の塊 18→19、hook コマンド 24→25（追加は 1 本だけ、差分で確認）
- 測定用の `/tmp/py312-guard-probe312` は、削除が不可逆操作の見張りに止められて残っている（/tmp のため再起動で消える。迂回はしていない）
