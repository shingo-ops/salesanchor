# recon — card-lint（カードの機械検査）

**仕事名**: card-lint  
**日付**: 2026-09-08  
**対象ADR**: 対象外（開発運用の道具であり、製品コードの設計判断を伴わない）  
**担当**: architect（設計パートナー）  
**親**: docs/handoff/design-partner-card-ops/guards.md  
**関連**: docs/handoff/design-partner-card-ops/card-ops.md、docs/handoff/design-partner-card-ops/backlog.md

> この文書は何か（専門用語なしの1行）:
> 設計パートナーが出すカードを、実行前に機械で検査する道具を作るために、いまの実行環境で何が使えるかを測った記録。

実測: CARD-LINT-RECON-01（2026-09-08）。origin/main は PR #3358 マージ後（226bb39f）。  
書き込みは一切行っていない。

---

## file:line 引用表

| 引用先 | 確認内容 |
|-------|---------|
| `scripts/ledger-lookup.sh:1` | 既存スクリプトの書式: `#!/bin/bash` → 用途コメント → 使い方 → exit コードの意味 → 設計文書のパス → `set -u` |
| `scripts/ledger-lookup.sh:8` | `set -u` のみ。`set -e` は使っていない |
| `docs/handoff/design-partner-card-ops/guards/11-lint.md` | 検査式 L01〜L23 の一覧（本設計で確定させる対象） |

## 実行環境（実測）

| 項目 | 実測値 | 設計への影響 |
|---|---|---|
| grep | BSD grep 2.6.0-FreeBSD | **`-P`（Perl 正規表現）が使えない**（`invalid option -- P`・exit 2） |
| 否定先読み `(?!...)` | 使えない | L01・L13・L19 を書き直す必要がある |
| awk | version 20200816（BSD awk） | GNU 拡張は使えない前提で書く |
| `scripts/*.sh` の本数 | 55 | 新規1本を足す |
| shellcheck を使う CI | `.github/workflows/hook-test.yml` の1本のみ | 書式の縛りは緩い |
| `scripts/` 配下のテスト | `test_pre_commit_hook.py`・`test_rollback_simulation.sh`・`tests/` ディレクトリ | テストの置き場は既存にある |

## 検査対象（カードの構造）

カードは1つのコードブロックで、次の見出しを持つ（card-ops.md §5 の固定順）。

カードID／上書き宣言／目的／出力の置き場／禁止（名指し）／停止条件／受領確認／手順／報告様式／END OF CARD

検査はこのテキストを標準入力またはファイルで受け取り、行単位で判定する。

## 本セッションで観測した停止（検査の対象）

| 停止 | 検査式で止まるか |
|---|---|
| 危険語を grep のパターンに書いた | 止まる（L23） |
| 1コマンドに7行分を詰めて SyntaxError | **新規**（L24: 1コマンドの文字数） |
| `git add` にパス14個を並べて SyntaxError | 同上 |
| プレースホルダを残した | 止まる（L02） |
| 検索語にバッククォートを含めた | **新規**（L25） |
| `cd` 接頭辞なし | 止まる（L01） |
| 報告ファイルのパスの誤記 | 止まらない（カードは正しかった） |
| `gh run view` を書いた | 止まる（L21） |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 1コマンドが何文字を超えると SyntaxError になるか | 段階的に長さを変えて実測する | 未解消（L24 の閾値は暫定 200 字とし、実測後に改める） |
| 2 | BSD awk で書いた式が意図どおり動くか | 実装時に1本ずつ実行して確かめる | 未解消（design の受け入れ基準に含む） |
| 3 | UserPromptSubmit フックが本環境で使えるか | `~/.claude/settings.json` の書式を実測する | 未解消（接続は本設計の範囲外・backlog #2） |

**未解決ゼロ確認**: 3件が未解消。#1・#2 は実装の中で解消する（検査式の確定条件）。#3 は接続の便で扱う。

## 実測の出所

- CARD-LINT-RECON-01（2026-09-08・読み取り専用・10手順）
- 本セッションの停止記録（2026-09-07〜08）
