# ADR-1011: AI による許可の自律保守（週1回・SM- の文だけ・台帳必須）

| 項目 | 内容 |
|------|------|
| ステータス | Accepted |
| 備考 | 2026-10-13 に PO が方針を了承。同日、受入試験 S2 に合格（permission-reports/2026-10-13-s2-trial.md）。2026-10-15 PO 決定で、審査担当を Fable から Opus へ変更（標準の審査は Opus）。2026-10-19 ADR-1034 で「範囲外」のうち `SM-` で始まらない allow の文を、道具 `perm-change.py` を通す場合に限って改めた |
| 起案日 | 2026-10-13 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1003（GO 委譲。本 ADR は GO の範囲を変えない） |

---

## What（何を決めたか）

AI（Claude Opus 設計担当）は週1回の定期実行のなかで、Claude Code の自動判定の許可（`~/.claude/settings.json` の `autoMode.allow`）に、先頭が `SM-` の文を足したり外したりしてよい。条件は次のとおり。

- 変更の前に、報告書と台帳の行を文書 PR でマージする。
- その PR は Reviewer が APPROVE している。
- 変更の前にバックアップを取り、変更のあとに試験する。

範囲と順序の詳細は docs/handoff/design-approval-ticket/self-maintenance-design.md による。

## Why（なぜ）

PO の原文（2026-10-13）:「自律的に成長するシステムにしたい、ただしログは必ず残し、権限を追加削除した理由や追加削除した記録は残すことを条件とする」「これを許可するので実現できるようにしたい」。

AI が自分の許可を変えることは、自動判定の「Self-Modification」で止められる。この規則は soft_deny なので、PO が名指しした例外の文で外せる。

## 範囲外（AI が自分では変えない）

- `SM-` で始まらない allow の文
- 例外の文そのもの
- hard_deny / soft_deny / environment / permissions / hooks
- ~/.claude/scripts/ の下のファイル
- 試験スクリプト
- 台帳の既存の行
- 本番・秘密情報・DROP・TRUNCATE・ALTER・DELETE・force push・ブランチ保護・外部 GUI に関わる許可

フックの変更は、今までどおり「AI がパッチを作り、PO が `!` で反映する」形で行う。

## 解除

PO が「許可保守停止」と言った時点で終える（ADR-1003 の「委譲停止」とは別の言葉）。PO が docs/handoff/design-approval-ticket/po-unregister-self-maintenance.sh を `!` で実行して、例外の文を外す。

## 弊害・トレードオフ

- AI が自分の許可を広げられるようになる。次の4つで歯止めをかける。
  - 範囲を `SM-` の文の追加と削除だけにする
  - 文の形を縛る（ワイルドカード・本番・秘密・~/.claude に触れる文は書けない）
  - 変更の前に台帳への記録と Reviewer の APPROVE を必須にする
  - 毎週、台帳を最初から再生した結果が現在の設定と一致するかを確かめる
- 例外の文が実際に効くかは、自動判定（文章で判定する）しだいで、保証がない。受入試験で実測し、効かない場合は「AI が案を出し、PO が `!` で反映する」形に戻す。

## 外部・過去事例

該当なし＋理由: AI が自分の許可を記録にもとづいて保守する、数値つきの公開事例を確認していない。社内の段1（PR #4175、停止の記録）と段2（PR #4182、試験一式）の実績を土台にする。

## 維持の仕組み

- 守り手: 定期実行の手順9（台帳の再生による一致確認と、保護対象の sha256 比較）と Reviewer（Opus）の審査。
- 記録: docs/handoff/design-approval-ticket/permission-ledger.md（変更はすべてここに残す。分散させない）。
