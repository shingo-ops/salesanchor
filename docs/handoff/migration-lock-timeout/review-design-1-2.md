# 設計審査 — migration-lock-timeout 便1.2（design.md §14）

- 審査者: Claude Opus（Architect の役。設計を書いたのと同じ AI による自己審査で、独立した第二者レビューではない）
- 日時: 2026-10-22
- 判定: **APPROVE**（4回目。設計合格。PO 承認・マージ・本番反映の承認を兼ねない）
- PO 承認: K7 の数え方の変更（表示2秒以内 → 移行の鍵による待ち2秒以内）は PO 2026-10-22「1」。

## 経緯
| 回 | 判定 | 主な指摘 |
|---|---|---|
| 1 | REVISE | 開始が trap より前・wait の扱い・既存試験の切り出しとの干渉・`${PSQL}` の ON_ERROR_STOP・1つの -c で1トランザクションになる・conditions ビューの逆順の鍵・表の範囲（tcg_distribution_settings・認証）・T7 の形・K7 の意味の変化 |
| 2 | REVISE | `$EPOCHREALTIME` の8進数・つながらない回が成功に数えられる・`read_probe_stop` 内の失敗で ai_ro が飛ぶ・置き場所・T2/T7 のタイミング・PID の受け渡し・slow 行の時刻・K12 の抽出方法・流し方 |
| 3 | REVISE | T9 の ai_ro 側の確かめ方が設計と食い違う・試験 DB の利用者名/DB 名・`--ref` |
| 4 | APPROVE | 申し送り: T9 の比較は行頭の空白を除く（`^[[:space:]]*if declare -F read_probe_stop`）。§14-6 に反映済み |

## 確かめたこと（4回目までの要点）
| 観点 | 結果 | 根拠 |
|---|---|---|
| 計測が必ず止まるか | 止まる。開始は trap（`scripts/run_all_migrations.sh:148`）の後、子は毎回 `kill -0` で親を確かめる | design §14-4 |
| 計測が入れ替えの成否を変えないか | 変えない。`read_probe_stop \|\| true` で呼び、中の各行も `\|\| true` | design §14-4、T3・T8・T9 |
| 計測が deadlock の相手にならないか | 1表1文（-c を繰り返す）、ビューでなく `line_conditions` を読む | design §14-4・§14-5、PostgreSQL 16 文書（app-psql.html） |
| 表の範囲が在庫表のクエリと一致するか | 6関数から拾う13表＋users＝14表。ast で実物と一致を確かめた | design §14-5 |
| 公開ログに SQL・表名が出ないか | 子の出力は全部捨てる、`wait 2>/dev/null` | design §14-4、T5 |
| 移行ステップが走るか | 走る（`scripts/**` が migrations の判定に入る） | `.github/workflows/deploy.yml:38-43` |

## 未確認（実装・試験で閉じる）
- prod1 の bash の版（`$EPOCHREALTIME`）。初回の入れ替えで invalid=0 を確かめる（K10）。
- bash 5 で `wait 2>/dev/null` が終了の表示を消すか。T5 で確かめる。

- 生の審査記録: `/tmp/CC報告ファイル/k7-probe-review/`、`/tmp/CC報告ファイル/k7-probe-recon2/`（リポジトリ外）。
