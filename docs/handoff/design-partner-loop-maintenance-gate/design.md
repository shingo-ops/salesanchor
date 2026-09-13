# design — 維持の仕組み欄の必須化（関所で機械強制）

> この文書は何か（専門用語なしの1行）: どの設計書にも「この設計を誰が見張るか（点検担当）」の欄を必ず書かせ、書き忘れや架空の名指しを受付（CI）が止められるようにする工事の設計図。

親（あるべき姿＋KGI）へのリンク: [../../specs/design-partner-loop/README.md](../../specs/design-partner-loop/README.md) §5「維持の仕組み必須化便」
recon: docs/handoff/design-partner-loop-maintenance-gate/recon.md
対象ADR: ADR-121

## 1. あるべき姿（親§1・PO自筆から）
「全ての開発に、あるべき姿・KGI・recon・design・維持する仕組みがあり、全て紐づいていて、長期的に誰が見ても引き継いでも理解してキャッチアップできる状態」。本便はこのうち「維持する仕組み」欄の必須化を実装する。

## 2. KGI（○×・数値）
| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| 1 | 正本に「全designに維持の仕組み欄必須・空欄不可」が明文 | docs/STANDARD-WORKFLOW.md を目視 | 在る=1 |
| 2 | 欄の書式3点（守り手パス／対象／関所なし時は人手で守る＋理由）が正本に定義済み | 記載点数 | 3/3 |
| 3 | 本便の design.md に記入済みの維持の仕組み欄の実例が在る | 記入欄数 | 3/3 |
| 4 | 維持欄が空のdesignをテストで検知する | node scripts/tests/test-process-artifacts.js の該当ケース | 検知 1/1 |
| 5 | 架空パスを名指ししたdesignをテストで検知する | 同上 | 検知 1/1 |
| 6 | 正常designの誤検知・猶予未満PRの巻き込みが無い | 同上 | 誤検知 0・巻き込み 0 |

## 3. KPI
欠陥検知率 2/2＝100%／誤検知 0件／猶予巻き込み 0件／正本必須3項目 3/3／見本記入 3/3。達成KGI数 ◯/6 で親§5へ報告。

## 4. 技術How
(a) 正本 `docs/STANDARD-WORKFLOW.md` §1.6 の直後に §1.7 を新設し、次を明文化する:
- 全 design.md は末尾に「## 維持の仕組み」欄を必須とする。空欄不可。
- 書式: 「- 守り手: <関所ファイルの相対パス>」「- 対象: この設計の何が壊れると困るか」「- 関所なしの場合: 人手で守る＋理由」。
- 本ルールは関所（process-artifacts gate）が機械検査する（初期は警告・安定後に停止へ引き上げ）。

(b) `scripts/check-process-artifacts.js` の validateDesignDoc に検査を2つ追加する（手本＝364-377行の外部事例欄チェック）:
- 検査A（空欄）: /^##[^\n]*維持の仕組み/m 見出しの存在と、「守り手:」行の値が非空であること。
- 検査B（実在）: 守り手の値が「人手で守る」以外のとき、extractFileCitations→validateFileCitations と同方式（existsSync）でパス実在を確認。架空パスはエラー。
- 発動条件: process.env.PR_NUMBER が GRACE_THRESHOLD_PR(2600) 以上のときのみ（未満はスキップ＝過去PRを巻き込まない）。
- 段階投入: 環境変数 MAINTENANCE_ENFORCE が 'fail' のとき printFailure 行き、未設定または 'warn' のとき ⚠️ 警告出力のみで通す。初期はワークフロー未設定＝warn。fail への引き上げは後日PO判断（ワークフローに env 1行追加のPR）。

(c) `scripts/tests/test-process-artifacts.js` にケース4本を追加: ①維持欄なし（warn/failの両モードで検知）②守り手が架空パス③正常（誤検知ゼロ確認）④PR_NUMBER=2599（スキップ確認）。

## 5. 触るファイル（これ以外に触らない）
docs/STANDARD-WORKFLOW.md／scripts/check-process-artifacts.js／scripts/tests/test-process-artifacts.js／docs/handoff/design-partner-loop-maintenance-gate/recon.md／docs/handoff/design-partner-loop-maintenance-gate/design.md

## 6. 弊害・トレードオフ（空欄不可）
- 全開発で design.md の記入が3行分増える（準備9割の方針どおりの負担増）。
- warn 期間中は書き忘れが表示のみで止まらない（fail引き上げまでの過渡リスク）。
- 欄の中身の適切性（その守り手で本当に守れるか）は機械で判定しない。人のレビューに残る（案Aの意図的な限界）。
- 修正mdが積み重なる複数枚構成は未対応。関所は「設計:」の1枚のみ検査（次便で拡張）。

## 7. 外部・過去事例の参照と我々への応用
過去事例: 本リポの子→親リンク実在チェック（ADR-121、2026-06-13変更でファイル実在確認方式を確立）。応用: 同じ existsSync 方式を「守り手パス」に横展開する。新規発明はゼロで、実証済みパターンの再利用に徹する。

## 8. 受入基準（検証方法つき）
| 基準 | 検証方法 |
|---|---|
| KGI1-2 正本§1.7の明文と書式3点 | マージ後の docs/STANDARD-WORKFLOW.md を目視で確認 |
| KGI3 本designの維持欄実例 | 本ファイル§9を目視で確認 |
| KGI4-6 検知2/2・誤検知0・巻き込み0 | node scripts/tests/test-process-artifacts.js を実行し全ケース緑 |
| 関所全体の退行なし | 同テストの既存ケースが全て緑のまま |

## 9. 維持の仕組み
- 守り手: .github/workflows/process-artifacts-gate.yml
- 対象: 正本§1.7の維持欄ルールと、validateDesignDoc の検査A/B（この設計が入れた検査自体）が壊れる・外されること。
- 補足: 正本と関所本体は DANGEROUS_PATTERNS の自己保護対象（変更にPO自筆GO必須）。検査の退行は scripts/tests/test-process-artifacts.js の追加ケースが検知する。
