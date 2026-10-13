---
mode: handoff
status: draft（PO 決定 2026-10-14・文書だけの変更）
---

# 許可保守の定期実行を、Claude Desktop から agent-console へ移す

この文書は何か（専門用語なしの1行）: 許可の週次保守を、入っていない Claude Desktop ではなく自作アプリ agent-console の定期実行で回す形に、手順書と設計書の書き方を直すための計画書。
親: [../design-approval-ticket/self-maintenance-design.md](../design-approval-ticket/self-maintenance-design.md)／ADR: [ADR-1011](../../adr/ADR-1011-permission-self-maintenance.md)（変更しない。Desktop 固定の記述が無い）／現状の調査: [recon.md](recon.md)／設計仕様書（あるべき姿）: 対象外（純粋な書類の変更。docs/STANDARD-WORKFLOW.md §1.5 の対象外に当たる）

## 1. 目的（PO の原文・2026-10-14）

- PO 原文1:「このアプリの定期実行で管理させる」
- PO 原文2:「y」＝「月〜金の9:00に毎日起動し、その週の保守が済んでいれば何もせずに終える」形にする。

KGI（PO が文書の中身で ○× を判定できる粒度）:

| # | 合格条件 | 判定の仕方 | 合格ライン |
|---|---|---|---|
| K1 | ROUTINE.md が agent-console の定期実行の登録内容（役割・フォルダ・曜日・時刻・指示文）を表で示している | `docs/handoff/design-approval-ticket/routine/ROUTINE.md` の「登録手順」の表を読む | 5項目すべてある |
| K2 | 指示文に「今週の分が済んでいるかの確認」があり、済みなら 1 行報告だけで終わる | 指示文の該当節を読む | 判定材料 2 種類・終了時の報告文がある |
| K3 | Desktop 固定・週1回前提の記述が、変更記録を除いて残っていない | `git grep -n "Desktop\|定期タスク\|週1回\|次の回" docs/handoff/design-approval-ticket/` | 残りは「変更の経緯」「Desktop には無い」と書いた比較、および「実施は週1回」「毎日の戻し確認」と書き直した文だけ |
| K4 | 指示文が 8192 字以内で制御文字を含まない | 文字数を数える | 8192 以下・禁止文字 0 |

## 2. 対象と対象外

- 対象（書き換える文書だけ）:
  - `docs/handoff/design-approval-ticket/routine/ROUTINE.md`
  - `docs/handoff/design-approval-ticket/self-maintenance-design.md`（§4・§9・§10・段と承認 S4・末尾の変更履歴）
  - `docs/handoff/design-approval-ticket/s4-card.md`
  - 新規: 本書と recon.md
- 対象外（触らない）: ADR-1011（根拠は recon.md §0）、routine/*.py、台帳 permission-ledger.md、`~/.claude` 配下、agent-console リポジトリ、agent-console の版の更新（v0.19.0 の導入は別作業・手空き待ち）、製品コード・スクリプト・設定。

## 3. 変更前後

| 箇所（変更前） | 変更前 | 変更後 |
|---|---|---|
| routine/ROUTINE.md:1-21 | Desktop の定期タスクの登録手順（Routines → New routine → Local、権限モードを画面で選ぶ、Run now で always allow、取りこぼしは復帰時に追い付く） | agent-console の定期実行の登録内容の表（役割 opus-designer、本店、月〜金、09:00、指示文）と前提（v0.18.0 以上、K15 合格）、制約 4 点、未確認 3 点 |
| routine/ROUTINE.md:22-24（指示文の頭） | すぐ「最初に必ず行う」 | 先に「毎日の途中記録の確認」（§3-1b）、次に「今週の分が済んでいるかの確認」。済みなら何もせず 1 行報告で終了 |
| self-maintenance-design.md:54 | Desktop のローカル定期タスク（PO 採用 2026-10-11） | agent-console の定期実行（PO 決定 2026-10-14）。月〜金 9:00、済みなら終える |
| `self-maintenance-design.md:179,181,194` | Desktop の画面で登録／Desktop の定期タスク | agent-console の画面で登録／agent-console の定期実行 |
| self-maintenance-design.md §9 の守り手（:172） | 定期タスクの手順9 | 定期実行の手順9 |
| self-maintenance-design.md 末尾 | 変更履歴の節なし | 「変更履歴」節を新設し、2026-10-14 の変更と PO 原文1・2 を引用 |
| `s4-card.md:38,45` | Desktop のローカル定期タスク／Desktop → Code → Routines → New routine → Local | agent-console の定期実行／画面と役割・曜日・時刻。HTTP API は認証方式が未確認のため書かない |

### 3-1. 「今週の分が済んでいるか」の判定（recon.md §A4 に基づく）

- 今週 = JST の月曜 0:00 から。
- 確認A（済み）: origin/main の `docs/handoff/design-approval-ticket/permission-reports/` に、YYYY-MM-DD.md の形そのもので日付が今週の月曜以降のファイルがある。2026-10-13-s2-trial.md のような後ろに文字が続く名前は数えない。
- 確認B（作業中または済み）: `gh pr list --repo shingo-ops/salesanchor --state all --limit 50 --search "head:release/permission-maintenance-" ...` で、headRefName が `release/permission-maintenance-` で始まり、今週の月曜 0:00 JST（gh の createdAt は UTC なので UTC の日曜 15:00）以降に作られ、state が OPEN または MERGED の PR がある。マージされずに閉じた PR は数えない（その週は再び試みる）。`--search` を付けるのは、リポジトリ全体の PR が1日に約55件あり、`--limit 50` だけでは月曜の PR が水曜には範囲の外に出るため（審査の実測）。
- 放置の検出: 確認B で当たった PR が OPEN で、作成から 20 時間以上たっていれば「済み」としない。`NEEDS_DECISION: 保守 PR #N が OPEN のまま 20 時間以上（閉じる／続ける）` の 1 行を報告して終える（保守には進まない）。
- 確認A か 確認B に当たれば、何も変更せず「今週分は済み（根拠: …）」の 1 行だけ報告して終わる。当たらなければ従来の手順へ進む。
- 台帳の行は、候補が無い週に行が作られるか文書から特定できないため、判定材料にしない。

### 3-1b. 毎日の途中記録の確認（済み判定より前・読み取りだけ）

- 毎日の最初に、pending.json（~/.claude/logs/permission-maintenance-pending.json。パスは routine/sm_apply.py の DEFAULT_PENDING と同じ）を見る。無ければ次へ進む。
- ある場合、ts（UTC）が 20 時間未満なら同じ日の実行中とみなして次へ進む。20 時間以上なら、何も変更せず `NEEDS_DECISION: 許可保守の途中の記録が残っています（pending.json ts=…。手順0で戻すか判断してください）` の 1 行で終える。ts が無い・読めないときも同じ形（理由: ts なし／読めない）で終える。.done-* は見ない。
- 20 時間とする理由: 毎日 9:00 の起動で、前日 9:00 以降に始まった途中停止を翌日に確実に検出するため。
- 戻す作業（recover）は、この確認では行わない。戻すかは PO 判断で、手順0で行う。よって「読み取りだけ」の約束に例外は無い。台帳の「戻した」行を追記する仕組みも、本変更では足さない（手順0は変更前のまま）。

### 3-2. 指示文の長さ

- 変更後の指示文（`## 指示文（ここから下を貼る）` の下）は 5171 字（Python の len。JavaScript の length と同じ UTF-16 単位でも同数。実測 2026-10-14）。上限 8192 字（`/Users/tanizawashingo/agent-console/server/routines.ts:17`）に対して余裕がある。改行とタブは制御文字の禁止に当たらない（同 `:23`）。

## 4. 代替案と選択理由

| 案 | 内容 | 選ばなかった／選んだ理由 |
|---|---|---|
| 採用 | 月〜金の 9:00 に毎日起動。済んでいれば何もせず終える | アプリは取りこぼしを追い付かない（recon.md §B4）。月曜 1 回だけだと、その朝にスリープやアプリ停止があると週が丸ごと飛ぶ。毎日にすれば、金曜までに 1 回起動できれば足りる。PO 決定（原文2） |
| 月曜のみ | weekdays=[1] で毎週 1 回 | 月曜 9:00 を逃すとその週は保守なし。追い付きがない以上、救済の余地が無い |
| アプリに追い付き機能を足す | agent-console 側を改造して取りこぼしを追いかける | agent-console リポジトリは本作業の対象外。追い付きは対象外と設計済み（/Users/tanizawashingo/agent-console/docs/handoff/routines-new-session/design.md:14）。仕様変更の影響が他の定期実行にも及ぶ |
| Claude Desktop を入れる | 従来の Desktop 定期タスクを維持 | この Mac に Claude Desktop が無い（変更前の routine/ROUTINE.md:8 の 2026-10-13 確認）。PO 原文1 に反する |
| 毎日の自動 recover | pending.json が古ければ起動のたびに自動で戻す | 不採用。理由: 台帳 K1 との不一致、偽の「戻した」行、許可判定に止められるおそれ、/tmp 実行の危険（審査 review-4247-2.md） |

## 5. リスク

| リスク | 内容 | 対処 |
|---|---|---|
| 金曜までに起動できない週 | 保守なし（追い付きなし） | ROUTINE.md の制約に明記。K4（4 週で報告書 4 本、self-maintenance-design.md:24）で気づける |
| 毎日セッションが増える | 済みの日も短いセッションが開き、自動では閉じない（上限 16） | ROUTINE.md の制約に明記。古い会話は PO が閉じる |
| 権限モードが auto 固定 | Desktop の always allow 相当が無い。SM- 例外の文が効くか未確認 | 未確認として ROUTINE.md に残す。初回の試行で確認。効かなければ self-maintenance-design.md:149 の「AI が案 → PO が `!` で反映」に戻す |
| 「送信済み」を成功と読み違える | 履歴の「送信済み」は指示を送れたという意味だけ | 成否は報告書・PR で確かめると明記 |
| pending.json の持ち越し | 手順6以降で途中終了すると `SM-` の文が有効なまま残る | 最長: 途中停止から翌営業日 9:00 の検出まで（金曜に止まれば月曜）。戻すのは PO 判断。毎日の途中記録の確認（§3-1b）が NEEDS_DECISION で知らせる |
| 確認画面で指示が入らない | 起動直後のフォルダ信頼などの画面に指示が入ると届かない | K15 で確認（agent-console 側 `docs/handoff/routines-new-session/design.md:60,84`） |
| 版が古い | 導入済み 0.17.0 は旧仕様 | 前提に「v0.18.0 以上が導入済み」を書いた。更新は別作業 |
| Sonnet・Fable の呼び出し | opus-designer から model 指定で呼べるか未確認 | 未確認として残す。初回の試行で確認 |

## 6. 受入基準

| 基準 | 検証方法 |
|---|---|
| ROUTINE.md の登録手順が 5 項目（役割・フォルダ・曜日・時刻・指示文）の表になっている | `sed -n 1,40p docs/handoff/design-approval-ticket/routine/ROUTINE.md` で表を目視 |
| 指示文の先頭に「今週の分が済んでいるかの確認」がある | `grep -n "今週の分が済んでいるか" docs/handoff/design-approval-ticket/routine/ROUTINE.md` |
| 判定材料（報告書 YYYY-MM-DD.md・`release/permission-maintenance-` の PR）が、ROUTINE.md:60,81 と permission-reports/README.md:5 の記述と一致する | 本書 §3-1 と各ファイルの行を突き合わせる |
| 指示文が 8192 字以内、制御文字（改行・タブ以外）なし | `python3 -I` で文字数と禁止文字を数えた結果を PR 本文に記す |
| Desktop 固定・週1回前提の記述が残っていない | `git grep -n "Desktop\|定期タスク\|週1回\|次の回" docs/handoff/design-approval-ticket/` の出力が、変更の経緯・比較の文・「実施は週1回」と書き直した文だけ |
| 変更履歴に PO 原文1・2がそのまま引用されている | `grep -n "このアプリの定期実行で管理させる" docs/handoff/design-approval-ticket/self-maintenance-design.md` |
| ADR-1011 と routine/*.py と台帳が変わっていない | `git diff origin/main...HEAD --stat` に含まれない |
| 変更が docs/ だけである | `git diff origin/main...HEAD --name-only` がすべて docs/ と .claude-pipeline/active-work.d/ |

## 7. 外部・過去事例の参照と我々への応用

- 外部事例: 該当なし。理由: 社内の自作アプリの定期実行機能に合わせた文書の書き換えで、外部の導入事例から学ぶ設計判断（新技術の選択・方式の比較）が無い。仕様の根拠は agent-console 自身の設計書と実装（recon.md §B）で足りる。
- 過去事例（手元）: ①/Users/tanizawashingo/agent-console/docs/handoff/routines-new-session/design.md:39（取りこぼしは追い付かない。現行どおり）。②`docs/handoff/design-approval-ticket/self-maintenance-design.md:54`（2026-10-11 の Desktop 採用）を、PO 決定 2026-10-14 で置き換える。応用: 追い付きが無い前提で、毎日起動＋「済みなら終える」にして取りこぼしを吸収する。

## 8. 維持の仕組み

- 守り手: docs/handoff/design-approval-ticket/permission-reports/README.md（週次報告書の置き場。K4 の「4 週で報告書 4 本」で、定期実行が動いているかを見る）と、人手（PO が週 1 回報告書を読む）。この変更専用の機械的な関所は無い。
- 対象: 「実行基盤が agent-console である」という記述が、ROUTINE.md・self-maintenance-design.md・s4-card.md で食い違わないこと。agent-console の版が上がって定期実行の仕様（追い付き・権限モード・上限）が変わったとき、ROUTINE.md の制約欄を更新すること。
- 関所なしの場合: 人手で守る。理由: 文書間の整合を機械的に検査する関所が無く、新設は本変更の範囲外。agent-console の版を更新する便で、ROUTINE.md の前提と制約を見直す。
