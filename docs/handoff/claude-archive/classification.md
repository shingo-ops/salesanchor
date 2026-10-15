# 残す（HDDへ）／消す の仕分け案（2026-10-15 Opus 作成）

状態: PO 承認済み（2026-10-15、PO の返答「Y」）。承認の範囲: ①今日中に「残す」分を鍵付きで HDD に1回写す（追加のみ・何も消さない） ②毎日写す仕組みと「消す」分の片付けは、設計と審査を通してから入れる。

根拠: /tmp/CC報告ファイル/archive-sort/inventory.md（Sonnet 実測）、/tmp/CC報告ファイル/storage-audit/summary.md
基準: 「Claude の開発精度・エージェントとしての成長につながるか」＝ 判断の経緯・PO の指示と訂正・審査の指摘・失敗と直し方 が読み取れる物は残す。作り直せる物・一時的な作業物は消す。

## A. 残す（HDDへ写す。Mac 側は今までどおり）
| 物 | 場所 | 量 | 理由 | 自動削除 |
|---|---|---|---|---|
| 会話の記録（主セッション） | ~/.claude/projects/*/<id>.jsonl | 約766MB/30日 | PO の指示・訂正・設計判断の全経緯 | 30日で消える（公式 claude-directory） |
| 担当（サブエージェント）の記録 | 同 <id>/subagents/ | 約2.1GB/30日 | 実装・調査・審査の過程と失敗 | 親と一緒に30日で消える |
| 大きな道具の出力 | 同 <id>/tool-results/ | 約336MB/30日 | 会話の記録から参照される本体の一部 | 30日で消える |
| 記憶（memory） | ~/.claude/projects/*/memory/ | 約1MB | 学んだ教訓そのもの | 消えない（念のため写す） |
| PO の入力履歴 | ~/.claude/history.jsonl | 約14MB | PO の言葉の全履歴 | 消えない（念のため写す） |
| 計画 | ~/.claude/plans/ | 344KB | 設計の下書き | 30日で消える |
| 設計・調査・審査・証拠の文書 | /tmp/CC報告ファイル/**/*.md | 約14MB | 判断の根拠と審査の指摘 | 自動削除なし（/tmp） |
| 保管庫 | ~/CC報告ファイル-keep/ | 約810MB | 既に「残す」と決めた物・引き継ぎ書 | 自動削除なし |
| 作戦ボード・定期実行の監査・レビューコメント | agent-console dataDir の boards/・routine-audit.jsonl・diff-comments.json | 未計測（小さい見込みは未確認） | KGI/KPI と判断の記録 | 削除処理は未確認 |
| PO が送った画像 | dataDir uploads/、/private/tmp/claude-501/*/images/ | uploads 未計測、images 約20MB | PO の指摘の材料 | uploads は新しい100件だけ残る |

## B. 消す（残さない）
| 物 | 場所 | 量 | 理由 |
|---|---|---|---|
| 調査の生出力・作業用コピー | /tmp/CC報告ファイル の *.txt/*.json/*.log/*.sql/*.py/*.html 等、写真 *.png | 約600MB＋ | 要点は .md に残る。その時の状態の生データで学びは薄い |
| 各セッションの作業メモ | /private/tmp/claude-501/*/scratchpad、tasks/b*.output | 約2.75GB | 一時的な作業物 |
| 編集前の控え | ~/.claude/file-history | 約36MB | 変更は git に残る |
| 作り直せる物 | plugins・skills・npm キャッシュ・node_modules・アプリ旧版・作業場所(worktree) | 数GB | 再取得・再生成できる（旧版・worktree・npm は既存の毎朝の片付けが消している） |
| その他の一時物 | paste-cache・shell-snapshots・session-env・debug・logs・backups | 数十MB | Claude Code の一時ファイル |
| 秘密 | ~/.claude/agent-tokens.json* ほか合言葉・トークン類 | - | HDD に写さない（漏れの元） |

## 決めずに残している点（設計で扱う）
- HDD は暗号化されていない（diskutil: Encrypted No）。会話の記録には社外秘（仕入元の分析等）が入る。→ 暗号化した入れ物（APFS 暗号化ディスクイメージ、鍵はキーチェーン）に入れる案。
- 会話の記録は毎日1日分ずつ消えている（最古 9/14）。初回の写しが遅れるほど失う。
- 写したあと Mac 側から消す物（B）を毎朝の片付け（disk-janitor）に加える。消す前に「HDD に写せた」ことを確かめてから消す。
- dataDir の実測（フックが担当に禁じているため未計測）。
- 圧縮した場合の量は未計測（無圧縮で年約40GB、HDD 5.5TB）。
