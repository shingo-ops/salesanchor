# design: 規則文書の「GO は PO 単独・人がマージ」を今のルールにそろえる

参照: recon.md（同じフォルダ）、ADR-1003（docs/adr/ADR-1003-go-delegation-to-opus.md）、ADR-136（docs/adr/ADR-136-cc-bot-github-identity.md）

## 目的
新しいセッションの AI が古い規則文書を読んで「GO やマージは人に頼む」と勘違いしないようにする（PO 2026-10-15 の依頼）。2026-10-15 の Approve の恒久委任を ADR-1003 に書く作業は、AI による書き込みが自動の安全判定に止められたため、この PR には入れない（PO 判断待ち）。

## 変更前後
- 変更前: recon.md の各所が「GO は PO 単独」「人がマージ」「GO: Shingo」と書いている。
- 変更後:
  - ADR-136 の3か所に「ADR-1003 により上書き」の注記を足す（決定本文は残す）。
  - STANDARD-WORKFLOW.md・BRANCH_PROTECTION_SETUP.md・PULL_REQUEST_TEMPLATE.md・executor-preamble.md・.claude/agents/governance.md を「GO は PO、ADR-1003 により例外を除き Opus へ委任。マージは GO 後に Opus」に書き換える。
  - design-partner.md §6-1 の GO記録の転記の項は、Lessons Guard の規則どおり lessons.d/20261015-go-record-delegated-issuer.md のポストで補う。
  - STANDARD-WORKFLOW.md の GO コメントの書式を、PO 本人の GO と委任の GO で分ける。
  - docs/adr/README.md は generate-adr-index.js による再生成。

## 対象外
- ADR-1003・opus-delegation.md への Approve の委任の追記（自動の安全判定に止められた。PO 判断待ち）。
- scripts/check-process-artifacts.js の部分一致の判定の修正（別便。カード→実装→コード審査）。
- opus-delegation.md（PR #4293 と同じファイルのため）。
- 過去の設計書・ADR（recon.md の「触らないもの」）。

## 代替案
- 古い記述を削除する案: ADR-136 は決定の記録なので本文を消すと経緯が追えなくなる。注記で上書きを示す方を選ぶ。運用の手順書（STANDARD-WORKFLOW 等）は今のルールに書き換える。

## 受入条件
|基準|検証方法|
|---|---|
| 運用の手順書に「GO は PO 単独」「human merge」が残っていない | `git grep -nE "human merge|PO（Shingo）単独|Shingo の GO 記録が必須|PO の GO を確認済み" -- docs/STANDARD-WORKFLOW.md docs/ai-agents .claude/agents .github/PULL_REQUEST_TEMPLATE.md` が 0 件 |
| ADR-136 の「PO 単独」の3か所に ADR-1003 の注記がある | `grep -c "ADR-1003 により上書き" docs/adr/ADR-136-cc-bot-github-identity.md` が 3 |
| ADR の索引が最新 | CI「ADR index is up to date」が pass |

## 外部・過去事例の参照と我々への応用
該当なし。社内の権限ルールの文書を今の決定にそろえるだけで、技術的な選択を含まないため。

## リスクと対処
- 書き換えで意味が変わる: Fable の設計審査で diff を確認する。
- 例外まで委任と読める: 例外一覧を STANDARD-WORKFLOW.md に明記する。

## 戻し方
この PR を revert する。

## 維持の仕組み
守り手: 人手（Opus）。ルールを変える PR を作るときは、同じ語（GO・マージ・Approve）を git grep で探し、運用の手順書も同じ PR で直す。部分一致の判定は別便で機械の検査にする。
