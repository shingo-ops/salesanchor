---
mode: handoff
status: draft（PO 方針承認 2026-10-13・Reviewer 指摘反映版・実装未着手）
---

# 許可の自律保守：AI が週1回、止まった記録から許可を足し引きし、台帳に残す

この文書は何か（専門用語なしの1行）: AI が毎週、作業が止まった記録を数え、決められた狭い範囲でだけ自分の許可を足したり外したりし、その理由と結果を必ず台帳に書き残す仕組みの設計書。
親: [design.md](design.md)（設計承認チケット）／ADR: [ADR-1011](../../adr/ADR-1011-permission-self-maintenance.md)／記録: [stage1-record.md](stage1-record.md)、[stage2-record.md](stage2-record.md)

## 1. あるべき姿（PO の原文・2026-10-13）

> 定期実行に登録して自律的に与える権限をあなたが判断して保守運用することはできる？自律的に成長するシステムにしたい、ただしログは必ず残し、権限を追加削除した理由や追加削除した記録は残すことを条件とする

> AI が自分の安全装置（フックや許可の設定）を変えようとした操作は…自動判定に止められました…→これを許可するので実現できるようにしたい

## 2. KGI

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| K1 | 許可の変更は、すべて台帳に載っている | 基準の写し（repo の外）の autoMode に、台帳の「結果=適用」の行だけを順に当てる。その結果と現在の `autoMode` の sha256 を、§5-6 の計算方法で比べる | 一致（差 0） |
| K2 | 台帳の各行に、必要な欄（§5-6）がすべてそろっている | 台帳の各行を欄ごとに確かめる | 欠け 0件 |
| K3 | 自分では変えてはいけないもの（§5-4）は変わっていない | 保護対象の sha256 を前の週と比べる | 変化 0件 |
| K4 | 定期実行が毎週動いている | permission-reports/ にできる報告書の数 | 4週で4本 |
| K5 | 自動判定の停止が減る | permission-denied.jsonl の7日間の件数（試験の時間帯を除く）。基準値 N は、S4 の1回目の報告書で数えた件数 | 4回目の報告書で N×0.5 以下 |

## 3. KPI

達成した KGI の数（◯/5）。報告書ごとに書く。

## 4. recon（実物の事実）

- 自動判定の既定の規則（`claude auto-mode defaults`、2026-10-13 取得）
  - 「Self-Modification」は soft_deny にあり、hard_deny にはない。
    - 解除の条件は、その権限変更を望んでいると具体的に名指しすること。
    - (a) の対象: 明示されていない権限の追加・拡大と、ガードを弱めること。
    - (b) の対象: ユーザーが出していない同意を AI が書くこと（作られた同意）。
  - 「Auto-Mode Bypass」も soft_deny にある。(iii) は、設定などで許可の仕組みを通り抜けることを指す。
- 現在の実効設定（`claude auto-mode config`、2026-10-13）
  - allow は 41件（既定 17件＋PO の決定 24件）。soft_deny は 74件（既定 72件＋PO 2件）。hard_deny は 1件。
  - PO の決定の中に、2件の関係する規則がある。
    - [10]「Exception to Self-Modification（PO 2026-09-29）」: Opus が PO の決定にもとづいて allow を足すことを許す。ただし「changing hooks」は対象外。
    - [7]: PO が承認したパッチをフックに当てることを許す。
- 公式仕様（code.claude.com/docs/en/auto-mode-config）
  - allow は soft_deny の例外になる。
  - hard_deny は解除できない。
- 2026-10-13 の実測
  - AI がフックの写しを書き換えようとしたところ、PO の具体的な許可文があっても [Self-Modification] で止まった。
  - 同じ変更でも、PO の `!` 実行（スクリプト）なら通った（stage2-record.md）。
- 記録の入口
  - ~/.claude/logs/permission-denied.jsonl（自動判定の停止）
  - ~/.claude/logs/agent-events.jsonl の type=hook_blocked（フックの停止）
  - ~/.claude/logs/test-runs.log（試験の時間帯）
- 定期実行: 自作アプリ agent-console の定期実行（PO 決定 2026-10-14。それ以前は Claude Desktop のローカル定期タスクを採用 2026-10-11 としていたが、この Mac に Claude Desktop は無い）。月〜金の 9:00（Asia/Tokyo）に毎日起動し、その週の分が済んでいれば何もせず終える。役割 opus-designer・作業フォルダ salesanchor 本店・権限モード auto 固定。取りこぼした回は追い付かない。登録内容と制約は routine/ROUTINE.md、変更の経緯は [../permission-routine-on-agent-console/design.md](../permission-routine-on-agent-console/design.md)。

## 5. design

### 5-1. 範囲（v1）

- AI が自分で変えてよいもの:
  - `autoMode.allow` に、先頭が `SM-` の文を足すこと
  - 自分が足した `SM-` の文を外すこと
- それ以外は、すべて対象外とする。フック本体（danger_sanitize.py の除外の一覧を含む）は、今までどおり「AI がパッチを作り、PO が `!` で反映する」形のまま。
- フックの停止（hook_blocked）は、報告書に載せるだけにする。直すときは、段2と同じ手順で PO に提案する。

| 停止の種類 | 入口 | 自律保守での扱い |
|---|---|---|
| 自動判定の停止 | permission-denied.jsonl | §5-3 の基準を満たせば、`SM-` の文を足す |
| フックの停止 | agent-events.jsonl（hook_blocked） | 報告だけ。直す案は PO に出す |

### 5-2. 例外の文（PO が `!` で autoMode.allow に1回書き込む。AI は書かない）

> Permission self-maintenance (explicitly wanted by the PO, ADR-1011, decision 2026-10-13). This rule is the PO's consent for this class of change; the weekly report and ledger are records of process, not consent. During the weekly permission-maintenance routine, Claude may (A) append to `autoMode.allow` in /Users/tanizawashingo/.claude/settings.json a new entry whose text starts with `SM-YYYY-MM-DD-N:`, or (B) remove an entry that starts with `SM-`, only when ALL hold: (0) a Reviewer agent returned APPROVE on the report PR head that lists this exact entry text with its stop counts; (1) the report is under docs/handoff/design-approval-ticket/permission-reports/ and the ledger row is in docs/handoff/design-approval-ticket/permission-ledger.md, both merged to main before the change; (2) a backup is taken and ~/.claude/logs/permission-maintenance-pending.json is written before the change; (3) an added entry is at most 120 words; contains none of these strings: `Bash(`, `:*`, `ssh`, `psql`, `docker`, `sudo`, `gh api`, `permit-danger`, the address of any host named in `autoMode.environment`, `secret`, `token`, `password`, `credential`, `.env`, `.pem`, `id_ed25519`, `.clasprc`, `~/.claude`, `/.claude/`, `settings`, `hook`; uses no universal wording (`any`, `all`, `every`, `regardless`); and only covers commands that begin with the exact first two words quoted from the stop shape in the report, run inside /Users/tanizawashingo/worktrees/salesanchor/ or /private/tmp/claude-501/. It never covers: editing or removing any entry not starting with `SM-`, this rule itself, `hard_deny`, `soft_deny`, `environment`, `permissions`, `hooks`, any file under ~/.claude/scripts/, scripts/dev/test-agent-hooks.sh, the ledger's existing rows, or anything that would allow DROP / TRUNCATE / ALTER / DELETE, force push, branch-protection or ruleset changes, external GUI operations, production writes, or merging non-docs PRs without the ADR-1003 conditions.

- 既存の [10] との関係: [10] は「PO が決めた許可を Opus が足す」ためのもの。本規則は「定期保守で `SM-` の文を足し引きする」ためのもの。2つは併存する。本規則は [10] を広げも狭めもしない。

### 5-3. 足す・外すの基準（機械的に判定する）

- 形の定義:
  - 停止の「形」は、(入口, 理由の分類名, コマンドの先頭2語) の組で決める。
  - 理由の分類名は `Reason: [X]` の X。無い場合は「no explanation」。
  - コマンドの先頭2語は、環境変数の代入と `cd … &&` を除いたあとの最初の2語。
- 足す（すべて満たすこと）:
  1. 入口が permission-denied.jsonl である。
  2. 同じ形が7日で5件以上ある。
  3. 足す文が §5-2 の (3) を満たし、never に当たらない。判定は、§5-2 (3) に書いた禁止の文字列と全称の語の一覧（大文字・小文字を区別しない）をそのまま照合して行う。一覧の正は §5-2 (3) の1か所だけで、ここには写さない。判定の道具（routine/sm_check_entry.py）は、実行のたびに §5-2 (3) から一覧を抜き出し、道具に持たせた最低限の一覧（2026-10-13 時点の §5-2 (3) と同じ語）と足し合わせて使う（足し合わせは厳しい側にしか倒れない。設計書の書式崩れで語が抜けても止められるようにするため。設計者判断 2026-10-13、PR #4221 審査 MEDIUM-A）。§5-2 (3) から語を外す決定をしたときは、道具の最低限の一覧も同じ PR で外す。全称の語（any・all・every・regardless）は単語単位で照合する（例: allowed・install は当たらない）。禁止の文字列は部分一致で照合する。
  4. 1回の実行で足すのは3件まで。
- 外す（`SM-` の文だけが対象。どれか1つに当たれば外す）:
  1. その文を足したあと、試験の不合格・PR の差し戻し・巻き戻しのどれかが、その文の対象の操作で起きた（台帳に記録された事象に限る）。
  2. PO が外すよう指示した。
  3. 同じ内容の `SM-` の文がもう1件ある（新しい方を外す）。
- 判断がつかない（形がばらばら、件数が4件以下）ときは、報告書に「保留」として載せ、PO に1件ずつ聞く。

### 5-4. 自分では変えてはいけないもの（K3 で毎週 sha256 を比べる）

- §5-2 の文そのもの
- `SM-` で始まらない allow の文（PO の決定の24件）
- hard_deny、soft_deny、environment、permissions、hooks
- ~/.claude/scripts/ の下の全ファイル
- scripts/dev/test-agent-hooks.sh
- 台帳の既存の行（追記だけ許す）

### 5-5. 週1回の流れ（順序がそのまま安全の条件になる）

| 手順 | 内容 | 担当 |
|---|---|---|
| 0 | ~/.claude/logs/permission-maintenance-pending.json が残っていれば、そこに書いた `SM-` の文だけを `autoMode.allow` から外す（settings.json 全体は戻さない）。台帳に「結果=戻した」の行を足してから始める | Opus |
| 1 | 3つの入口から過去7日分を数える。試験の時間帯は除く。形ごとの件数を出す | Sonnet（読み取りだけ） |
| 2 | §5-3 の基準で候補を作る。足す文の全文、根拠の件数、代表例3件（秘密は伏せ字）を付ける | Opus |
| 3 | 報告書と、台帳の「予定」行（結果欄は「未適用」）を作り、文書 PR を出す | Sonnet |
| 4 | Reviewer（Fable）が最終の head を審査する。APPROVE が出なければ、ここで終える（変更しない） | Fable |
| 5 | 必須 CI が緑なら、PR をマージする（許可 B4）。マージできなければ、ここで終える（変更しない） | Opus |
| 6 | バックアップを取る → pending.json を書く → 変更する → 試験する（試験は main の scripts/dev/test-agent-hooks.sh） | Opus（変更）・Sonnet（試験） |
| 7 | 試験が不合格なら、その `SM-` の文を外す（pending.json は残す） | Opus |
| 8 | 手順6・7の結果（適用した／戻した、試験の結果、バックアップの場所）を、台帳に「結果」行として追記する。文書 PR を出し、手順4・5と同じ条件でマージする。マージできたときだけ pending.json を消す。マージできなかったときは、その `SM-` の文を外して pending.json を残す（次の回の手順0で「戻した」行を記録する） | Sonnet・Fable・Opus |
| 9 | K1（台帳の再生と一致）と K3（保護対象の sha256）を確かめる。不一致なら以後の自動の変更を止め、PO に報告する | Sonnet |

- 変更は、台帳の「予定」行がマージされたあとにだけ行う。そのため、台帳に載らない変更は生まれない。
- 手順6のあとで実行が途中で終わったときは、毎日の起動時に pending.json を読み、ts が 20 時間以上前なら PO に NEEDS_DECISION で知らせる（ROUTINE.md 参照）。戻すかどうかは PO が判断し、戻すときは手順0（recover）で行う。

### 5-6. 台帳の形（docs/handoff/design-approval-ticket/permission-ledger.md）

- 基準行: 2026-10-13 時点の `autoMode` の sha256 と、写しの置き場所を書く。
  - 写しは repo の外に置く: ~/.claude/logs/permission-baseline-2026-10-13.json。repo は PUBLIC なので、運用情報（環境の規則の本文、認証情報メモの場所など）を repo に載せない（Reviewer 再審査 HIGH-A）。
  - B2〜B4 は基準の写しにすでに含まれる。そのため台帳では「履歴（基準に含む・再生では当てない）」の節に置く。
- sha256 の計算方法（K1・K3 で共通・1か所だけに定める）: `autoMode` を `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))` で文字列にし、UTF-8 のバイト列の sha256 を取る。
- 再生の規則: 「種別=結果」かつ「結果=適用」の行だけを当てる。「予定」の行と「戻した」の行は当てない。
- 各行の欄: 日時 / 種別（予定・結果）/ source（routine か PO）/ 結果（未適用・適用・適用（PO）・戻した）/ 変更（add か remove と、文の全文）/ 理由 / 根拠の件数 / 報告書のパス / バックアップのパス / 試験の結果 / PR 番号。
  - 「変更」の欄には、文を切らずに全文を書く。再生にそのまま使うため。
  - 例外: 全文に運用情報を含む文の remove（source=PO に限る）は、`remove: sha256=<値>` と先頭20語を書き、全文は repo の外（~/.claude/logs/removed-allow-<日時>.txt）に置く。再生では、sha256（文の UTF-8 の sha256）が一致する要素を外す。
- PO が `!` で autoMode を変えたとき（例: B2〜B4）も、次の回の手順1で差分を見つけ、source=PO の行として追記する。その行は種別を「結果」、結果を「適用（PO）」とし、再生のときに当てる。追記がすむまで、その回の自動の変更は行わない。

### 5-7. 止め方と、外すスクリプト

- 停止の言葉は「許可保守停止」（ADR-1003 の「委譲停止」とは別）。
- 外すスクリプト: docs/handoff/design-approval-ticket/po-unregister-self-maintenance.sh
  - 入力: なし
  - 手順:
    1. ~/.claude/settings.json を settings.json.bak-<日時> に写す。
    2. `autoMode.allow` から、§5-2 の文と完全に一致する1件を取り除く。
    3. 結果の件数を表示する。
  - `SM-` の文は残す。外したいときは、台帳の手順で PO の指示として外す。

## 6. 弊害・トレードオフ

| 弊害 | 対処 |
|---|---|
| AI が自分の許可を広げられるようになる | 範囲を `SM-` の文の追加・削除だけにする。文の形を §5-2 (3) で縛る。台帳への記録、Reviewer の APPROVE、マージを、変更より前の条件にする |
| 例外の文が効くかは、自動判定（文章で判定する）しだいで保証がない | 受入 S2 で実際に試す。効かないときは「AI が案を出し、PO が `!` で反映する」形に戻す |
| 1週間に2回 PR が出る（予定と結果） | どちらも文書だけ。B4 の許可でマージする |
| 定期実行がサブスクの利用枠を使う | 実施は週1回に限る（月〜金に毎日起動するが、済んでいれば1行報告で終える）。数える作業は Sonnet に任せる |
| ~/.claude/settings.json は全セッションで共有されている | 変更した時刻を agent-events.jsonl に `{type:"permission_maintenance"}` として記録する。並行するセッションは、次に起動したときから新しい規則で判定される |

## 7. 外部・過去事例

- 公式の推奨（auto-mode-config）: 「繰り返し止められる定型の操作は allow に足す」。本設計は、これを記録にもとづいて週1回行う。
- 社内の実績: 段1（PR #4175）で記録の入口を作った。段2（PR #4182）で試験一式を作った。
- 数値つきの外部事例: 該当なし。理由: AI が記録にもとづいて自分の許可を保守する公開事例を、本便では確認していない。K1〜K5 の実測で判定する。

## 8. 受入基準

| # | 基準 | 検証方法 |
|---|---|---|
| S1 | `claude auto-mode critique` が §5-2 の文に重大な問題を挙げない | PO が書き込んだあとに実行し、出力の全文を記録する |
| S2 | 例外の文のもとで、無害な `SM-` の文（例: 「SM-2026-10-13-0: test entry, matches nothing」）を AI が足し、そのあと外せる | 実際に行い、permission-denied.jsonl が増えないこと、台帳に予定・結果の行が増えることを確かめる |
| S3 | never の範囲への書き込みは止まる | PO の立ち会いのもとで1回だけ試す。バックアップを取ったあと、AI が `SM-` で始まらない文（PO の決定の1件）の末尾に1文字足そうとして、止まることを permission-denied.jsonl で確かめる。通ってしまったら、すぐ戻して設計を差し戻す |
| S4 | 1回目の定期実行で、報告書・台帳・K1/K3 の確認がそろう | 1回目の実行後に、ファイルと記録を確かめる |

## 9. 維持の仕組み

- 対象: 許可の変更がすべて台帳に載っていること（K1）。保護対象が変わっていないこと（K3）。
- 守り手: 定期実行の手順9（K1・K3 の確認）と、Reviewer（Fable）の審査。どちらかが不合格なら、自動の変更を止めて PO に報告する。
- 人が見るもの: 週ごとの報告書（PO が読む）。

## 10. 接触面分析

| 面 | 影響 |
|---|---|
| ①人（PO） | 例外の文を `!` で1回書き込む。定期実行を agent-console の画面で登録する。報告書を週1回読む。S3 に立ち会う |
| ②エージェント | Opus が判断と変更を、Sonnet が集計・PR・試験を、Fable が審査を担う。並行セッションへの影響は §6 の最後の行のとおり |
| ③機械 | ~/.claude/settings.json の autoMode.allow（`SM-` の文だけ）。agent-console の定期実行 |
| ④データ | DB は触らない（理由: 対象はローカルの設定と repo の文書だけ） |
| ⑤本番 | 本番は触らない（理由: 本番に関わる文は §5-2 (3) で書けない） |
| ⑥外部 | GitHub の文書 PR。利用者への影響はない |

## 段と承認

| 段 | 内容 | PO の操作 |
|---|---|---|
| S0 | 本設計書・ADR-1011・台帳の雛形と基準行の審査とマージ | なし（文書だけの PR） |
| S1 | 書き込むスクリプトと外すスクリプトを作る（Sonnet）。critique で確かめる | `!` で書き込みを1回 |
| S2 | 無害な `SM-` の文で効き目を試す | なし |
| S3 | never の範囲が止まることを確かめる | 立ち会い |
| S4 | 定期実行の指示書（routine/ROUTINE.md）と集計スクリプトを作り、1回目を実行する | agent-console の画面で登録。報告書を読む |

## 変更履歴

- 2026-10-14 実行基盤を Claude Desktop から agent-console の定期実行へ変更（PO 決定）。
  - PO 原文1:「このアプリの定期実行で管理させる」
  - PO 原文2:「y」＝「月〜金の9:00に毎日起動し、その週の保守が済んでいれば何もせずに終える」形にする。
  - 変更箇所: §4 の定期実行の行、§10 の ①人・③機械、段と承認の S4、§9 の守り手、routine/ROUTINE.md、s4-card.md。詳細は [../permission-routine-on-agent-console/design.md](../permission-routine-on-agent-console/design.md)。
