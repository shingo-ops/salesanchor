# ADR-1033: 危険な操作を、会話での同意（同意票と「1」）でも通せるようにする

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（便1のマージ時点。反映と K0 の実測の後に昇格） |
| 備考 | PO 2026-10-19「会話の中で合意した事項であれば許可して再度許可を発行しなくても進めてほしい」「権限不足で毎回止まるのをやめ、本当に判断が必要な時だけ止まりたい」 |
| 起案日 | 2026-10-19 |
| 方針の決定者 | Shingo（PO）。設計は同日 PO 承認（選択肢「1. この設計で進める」に「1」と回答） |
| 関連 | ADR-1003（GO 発行の委譲。許可券の運用は 45 行目）、ADR-136（危険 PR の GO 手順。本 ADR は代わりにならない）、ADR-1011（週次の保守） |

---

## What（何を決めたか）

1. 許可券（`permit-danger.sh`）の代わりに、**同意票**でも危険な操作を通せるようにする。
   - AI が、返事の最後の text ブロックに `[同意票]` と `操作N: <コマンド全文1行>` を書き、`1. 上の同意票の操作を実行する` で始まる選択肢の行を置く。
   - PO が typed（打ち込み）で「1」だけを答えると、その完全一致のコマンドが1回だけ通る。「1」から30分で失効する。
   - 判定は新しい部品 `consent_check.py` が、会話記録の末尾 4MB を読んで行う（10 段の判定）。貼り付け・サブエージェントの報告・task-notification・`!` の出力・channel・queued の「1」は同意にならない。
   - 同じ同意票の同じ操作は1回だけ。使用済みの台帳（`consent-used.jsonl`）に flock で排他して記録する。
2. 同意で通さない操作（除外）を置く。main/develop への push、force push、`git reset --hard`、`DROP DATABASE`、`clasp push`、見張り役そのものの設定、Branch Protection・Ruleset、`workflow-lint.yml`、本店の破壊系 git など（設計 §4-4）。
3. 同意の偽造を防ぐ見張りを足す。会話記録・台帳の Bash／Write／Edit／MultiEdit／NotebookEdit での操作、tmux・osascript・`/chat/queue` による端末への入力注入を止め、`consent_guard_blocked` を記録する（設計 §4-5）。
4. 不要な停止を減らす。`rm -rf` の対象が `/tmp/CC報告ファイル/`・`/private/tmp/claude-501/`・作業場所の下なら止めない（設計 §4-6(a)）。`--body-file` が読めない停止の文に手順を示す（同 (b)）。
5. 同意票は ADR-136 の「GO #PR番号」の代わりにならない。危険 PR の GO は今までどおり PO 単独で、番号つきで受ける。

詳しい設計は `docs/handoff/conversation-consent/design.md`（第5版・Architect 4回目 APPROVE）。

## Why

- 危険な操作のたびに PO が `! bash scripts/permit-danger.sh "<op>"` を打つのは、PO の負担が大きく、合意済みの作業まで止まる。
- 許可券は op の部分一致と期限だけで消費され、何を許したかがコマンド全文に束縛されない。同意票は PO が読んだ文字と実際のコマンドを完全一致で結ぶ。

## 受け入れたリスク

**R1（PO 受容 2026-10-19）**: AI が、文字を分けて組み立てるなどで偽造を防ぐ見張りを逃れると、端末に「1」を送り込む・記録に偽の行を足すなどで、自分で同意を作れる。見張りは文字列照合で、悪意への完全な対策ではない。今の許可券も AI が `permit-danger.sh` を実行すれば作れる水準で、それより弱くはならない。

PO の受容の言葉（原文、選択肢「1.【おすすめ】受け入れて進める」への回答、2026-10-19）:

> 1,定期実行に追加された権限などをチェックするセッションを開く仕組みを入れて定期的にチェックする

PO の追加条件は、下の「維持の仕組み」の週次点検（K13）で満たす。

見つける手段: `consent_guard_blocked` のうち偽造の疑い（kind が inject・write）が1件でも記録されたら、この仕組みを止めて（`po-rollback-consent.sh`）PO に報告する。なお記録と点検スクリプトは AI が書き換えられるので、見つける手段自体も消せる。これも受け入れる範囲とする。

その他の受け入れるリスク: R2（「1」の直後に取り消しを打っても記録への書込みが遅れると通る。取り消すときは Esc で止める）、R6（操作が `bash <file>` のとき、「1」の後にファイルの中身を書き換えられる。今の許可券と同じ水準）。

## 戻し方

`! bash docs/handoff/conversation-consent/po-rollback-consent.sh`。反映時に作ったバックアップから、フック4つ・settings.json・permit_bridge.py を戻し、`consent_check.py` を取り除く。反映（`po-apply-consent.sh`）も、本物の試験が不合格なら同じ手順で自動で戻す。

## 測り方

設計 K0〜K13。反映前に、全受け入れ試験 T1〜T9（`scripts/dev/test-agent-hooks.sh`）を試作と本物の両方に対して通す。K0（フックが動く時点で、PO の直前の入力が記録に書かれている）は、反映後の本物の利用で20回測り、遅れが1件でもあれば設計の案 F（UserPromptSubmit で別台帳に記録）へ切り替える。

## 維持の仕組み

- 担当は Opus。週次の保守に `python3 scripts/dev/consent-audit.py --audit` を足す（台帳と記録の突き合わせ、`consent_guard_blocked` のうち偽造の疑い（kind が inject・write）と読み取りの空振りの件数）。
- **権限の定期点検（PO の追加条件）**: agent-console の定期実行に「同意と権限の週次点検」を登録し、毎週月曜 09:30 に点検用のセッションを開く。`python3 scripts/dev/consent-audit.py --audit --permissions` で、(1) 同意で通った操作と、記録に同意票と typed の「1」が見つからないもの（0件が正常）、(2) `consent_guard_blocked` のうち偽造の疑い（kind が inject・write。0件が正常。読み取りの空振りは参考の件数で異常にしない）、(3) 許可券の発行・消費の件数、(4) settings の `permissions.allow`・`hooks` と許可券の増減（前回の写しとの比較。値は出さず項目名と件数だけ）を前週と比べる。異常があれば PO に報告し、(1)(2) なら仕組みを止める案も選択肢に出す。登録は反映後に Opus が行う。
- 試験は `scripts/dev/test-agent-hooks.sh` に入り、`po-apply` のたびに走る。
