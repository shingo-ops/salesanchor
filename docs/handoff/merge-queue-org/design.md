# 設計 — 会社名義へ移して、本線への合流を GitHub 純正の順番待ちの列に通す

- 状態: 設計案（PO 未承認）。名義の移し・ruleset の変更は PO の最終確認（同意票）まで行わない。
- 下調べ: docs/handoff/merge-queue-org/recon.md（以下 R§）。ADR 案: docs/handoff/merge-queue-org/adr-draft.md
- PO の選択: 2026-11-10「1」＝「会社の名義に移して、GitHub純正の順番待ちの列を使う方向で設計する」
- 関連 ADR: ADR-135（本線＝本番投入可・:66 で merge queue を不採用）・ADR-136（危険 PR の GO）・ADR-1029（マージ前の審査をフックで強制）・ADR-1011（hooks は AI がパッチ・PO が `!` で反映）・ADR-1003（docs-only の合流）

## 1. 目的と、利用者に見える変化

- 何のため: 本線に入れる順番を機械が決めるようにして、PR が追い越されるたびに確かめをやり直す無駄（#5335 で 9 回）と、「若い番号に譲る」を AI が守れなかった問題（R§0）を、仕組みでなくす。
- 変化（前）: 合流ボタンを押した人が早い者勝ち。本線が進むと他の全 PR が「古い」になり、取り込み→16 の確かめ（20 分超）をやり直す。
- 変化（後）: PR は「列に入れる」だけ。GitHub が前の PR を含めた形で確かめ、通った順に 1 件ずつ本線に入れる。取り込みのやり直しは要らない。列を通らない合流は GitHub が拒む。

## 2. 成功条件（KGI・KPI。○×か数で判定）

| ID | 条件 | 測り方 | 基準値（変更前） |
|---|---|---|---|
| K1 | 本線への合流は全件が列を通る | `gh api repos/<新>/rulesets/<id>` に merge_queue の規則があり bypass_actors が空。導入後 14 日の合流 PR 全件で GraphQL `timelineItems(itemTypes:[ADDED_TO_MERGE_QUEUE_EVENT])` が 1 件以上 | 0%（列が無い） |
| K2 | 追い越しによる取り込みのやり直し | 導入後 14 日の合流 PR ごとに、最初の審査 APPROVE 以降に入った「本線を取り込む commit」の数。中央値 0・最大 1 以下 | 便0 で直近 14 日を数えて記録する（#5335 は 9） |
| K3 | 列に入れてから本線に入るまで | 同 14 日の `added_to_merge_queue` → `merged` の時間の中央値が 60 分以下 | 便0 で「全部緑になってから合流まで」を直近 14 日で数えて記録する |
| K4 | 列が止まったら気付く | 一番古い列の項目が 60 分進まないとき、15 分以内に Discord の PO 宛てに 1 通届く。便2 の後に試しの PR で 1 回起こして確かめる | 見張り 0 |
| K5 | 移しで本番が壊れない | 移した直後の最初の配備で deploy 成功・smoke 成功・app と /api/health が 200 | — |
| K6 | 移しで設定が欠けない | secret 86=86・ruleset 2=2（中身一致）・自前の実行機の数が移す前と同じ・Pages が新 URL で開ける | R§6-3 の値 |

K3 の 60 分は「確かめ 1 回（20〜25 分）＋前に並ぶ分」の目安。PO の承認で確定する。

## 3. 選んだ案と、選ばなかった案

- 選んだ案 D: 既存の会社名義 GEN-RYU-System（free・PO が admin・shingo-cc が member・R§6-2）へ名前を変えずに移し、本線の ruleset に「merge queue 必須」を足す。
  - 理由1: 公式に「organization が持つ public リポジトリなら使える」（R§2）。会社名義は既にあり、新しく作る物が無い。
  - 理由2: 列を通らない合流を GitHub 自身が拒む。画面からの合流・自動合流・AI の合流のどの道でも効く。Shopify は v1 で「列を使わない道」を残して詰まり、v2 で普通の合流ボタンを止めて 90% 超を列に乗せた（R§7）。
  - 理由3: 列の中で確かめる。Shopify v1 の失敗（列の中で確かめず 50 件超が詰まった）を最初から避ける。Atlassian は合流起因の失敗を 7〜10% → ほぼ 0 にした（R§7）。
- 選ばなかった案 A: 個人名義のまま、合流台本に鍵を付けて 1 件ずつにする自作の列。画面と自動の合流に効かない。自作の列は見張りが無いと黙って止まる（R§7 mergify）。PO が選んだのは純正。
- 選ばなかった案 B: 外部サービス（Mergify 等）を個人名義に入れる。外部に書き込みの権限を渡すことになり、費用と規約は未調査。PO が選んだのは純正。
- 選ばなかった案 C: strict（最新の本線に揃っていること）を外すだけ。追い越しのやり直しは消えるが、「2 つの PR は単独では緑、合わせると壊れる」を本線に入れてしまう。Atlassian の 7〜10% はこの種類。

## 4. 列の設定（便2 で ruleset 15777895 に足す）

| 設定 | 値 | 理由 |
|---|---|---|
| 合流方式 | MERGE | 本リポジトリは merge commit のみ（ruleset の PR 規則・CLAUDE.md）。2026-04-23 の純正列の不具合は squash の場合で、merge は対象外（R§7） |
| 同時に確かめる数 | 5 | 1 日 46 件・25 分未満の間隔が 56%（R§1）。1 件ずつ順だと 1 日 72 件が上限（確かめ 20 分）で、昼の集中で待ちが延びる。5 本を先回りで確かめる。Atlassian は 300 件/日で 14 |
| 一度に本線へ入れる数 | 最小 1・最大 1 | 本線への 1 回の push＝1 回の配備＝1 つの PR に保つ。ADR-135/136 の「1 リリース 1 テーマ」「GO は PR 番号ごと」と食い違わない |
| 最小件数の待ち時間 | 0 分 | 最小 1 なので待たない |
| 確かめの制限時間 | 60 分 | 今の確かめは 20 分超。CI の 99% 止まり（memory: ci_pytest_99_hang）の 15 分取り消しを含めても余裕を持たせる |
| 失敗していない PR だけ合流 | 有効 | 赤を含む組み合わせを本線に入れない |
| strict（最新に揃っていること） | 無効にする | 列が「前の PR を含めた最新」で確かめるので不要。有効のままだと列に入る前の取り込み待ちが残り、K2 が下がらない。**便2 の同意票に明記して PO が判断する** |
| bypass_actors | 空のまま | 列を飛ばせる人を作らない。`gh pr merge --admin` も通らない（R§2 の gh の説明・ruleset は bypass に載った人だけ通す） |

develop の ruleset 16619490 は触らない（新しい作業に使わない・CLAUDE.md）。

## 5. 必須 16 件の、列の中での動かし方（便0）

方針: 全部の workflow の `on:` に `merge_group:` を足す（足さないと列で Pending のまま止まる・R§2）。そのうえで job ごとに次のどちらかにする。

- 甲「合わせた形で確かめ直す」: 2 つの PR を合わせたときに壊れうるもの。列では `github.event.merge_group.base_sha`..`head_sha` を比べる範囲に使う。
- 乙「列では飛ばす」: PR の本文・PR の差分だけで決まり、合わせても結果が変わらないもの。job に `if: github.event_name != 'merge_group'` を付ける（job を条件で飛ばすと Success と数えられる・R§2）。列に入った PR の中身は止まっている（列に入った後に push すると列から外れる）ので、PR で通った結果がそのまま使える。

| 必須の確かめ | 扱い | 理由 |
|---|---|---|
| pytest | 甲 | 合わせて壊れる代表 |
| テナントスキーマ整合性チェック | 甲 | 2 つの移行と model の組み合わせ |
| マイグレーションSQL 実行テスト（実DB） | 甲 | 移行の順番と組み合わせ |
| models.py に新 Column → … | 乙 | 1 つの PR の中で model と移行が揃っているかの確かめ |
| ADR-072 tenant schema lint | 甲 | 全体の走査 |
| Lint & Dark Mode Check | 甲 | 全体の走査。concurrency が `github.ref` なので列の枝ごとに分かれる（取り消し合わない） |
| gitleaks | 甲 | 軽い。合わせた差分も見る |
| CLAUDE.md line count | 甲 | 2 つの PR の追記で 90 行を超えうる |
| ADR index is up to date | 甲 | 2 つの PR が ADR を足すと索引が古くなる（合わせて壊れる典型） |
| UI governance gate | 乙 | PR の差分の部品を見る。カードで行を読み、全体走査なら甲に変える |
| dangling-route gate | 甲 | 片方が道を消し、片方がその道を使うと壊れる |
| warn-direct-lesson-edit | 乙 | PR の差分の警告（R§8 U7 をカードで確かめる） |
| guard-authoring/evaluation | 乙 | PR の差分に対する試験。concurrency が pull_request.number（R§4） |
| process-artifacts gate | 乙 | PR 本文と PR のファイル一覧を見る |
| API contract is up to date | 甲 | 2 つの PR の API 変更で生成物が古くなる |
| doc index reachability | 甲 | 全体の走査 |

- `github.event.pull_request.*`・head_ref・base_ref を使う甲の workflow（R§4 の列）は、列では merge_group の base_sha/head_sha を使う形に直す。行の変更前後はカード（便0）で全件書く。
- 列の一時枝（`gh-readonly-queue/main/...`）で push 起動の workflow が余計に走らないか、`push:` の branches 指定を全 83 本でカードに一覧する。
- 個人名義のうちは merge_group が起きないので、便0 を入れても今の動きは変わらない（入れて安全）。

## 6. 合流の道の直し（便0 に含める。列の前後どちらでも動く形）

| 道 | 直し |
|---|---|
| scripts/gh-pr-merge-safe.sh | `gh pr merge` の後、PR が MERGED か「列に入った」かを読み分ける。列に入ったら、MERGED になるまで待つか、「列に入れた」と報告して終わる（どちらにするかはカードで決め、K3 を測れる記録を残す）。worktree の片付けと台帳の DONE は MERGED を見てから |
| scripts/dev/check-pr-merge-ready.py | 名前の直書き（:14,:16,:166-169）を `gh repo view --json nameWithOwner` か環境変数から取る。CLEAN の判定は残す |
| .github/workflows/ledger-auto-done-main.yml | `gh pr merge --auto --merge` は列が必須の枝では「緑になったら列に入る」になる（R§2）。動きはそのまま。便2 の後に 1 件で確かめる |
| .github/workflows/ledger-done-update-branch.yml | 列が入ると不要。便3 で止める（便2 の前に止めると今の運用が詰まる） |
| scripts/agent-hooks/review-gate/gate.py:53 | STRICT_CHECK_REPOS に新しい名前を足す（旧と新の両方。大文字小文字は区別しない）。`--admin` を止める行を足す。手元の写し（~/.claude/scripts/review-gate）は ADR-1011 どおり PO が `!` で反映 |
| R§6-4 の直書き全部 | `${{ github.repository }}`・`gh repo view`・`GITHUB_REPOSITORY` から取る形に直す。試験の固定値と CODEOWNERS は新名へ |

## 7. 進め方（便ごとに 1 つ変え、測ってから次へ）

| 便 | 中身 | 本番への影響 | 承認 |
|---|---|---|---|
| 便0 | §5・§6 のコード。K2・K3 の基準値を数える | なし（個人名義では merge_group が起きない） | 実装カード＋PO の実装承認。合流は通常の審査 |
| 便1 | 名義の移し（PO が画面で行う）。§8 の手順 | 移す数分、合流を止める | **PO の同意票（不可逆）** |
| 便2 | ruleset に merge queue を足し strict を外す。列の見張り（§9）を入れる | 合流の仕方が変わる | **PO の同意票（ruleset の変更・permit-danger）** |
| 便3 | update-branch の自動作業を止める・Pages の URL の差し替え・覚え書き「若い番号に譲る」の廃止の提案・ADR を Accepted に | なし | 通常 |

戻し方:
- 便0: PR を戻す（merge_group の起動は個人名義では動かないので戻さなくても害はない）。
- 便1: **元の名前には戻せない前提**（R§8 U4）。git と Web の転送は残る。移した先で動かし続けることを前提に、便1 の前に §8 の点検を全部済ませる。
- 便2: ruleset から merge queue の規則を外し strict を戻す（API 1 回・PO の同意票）。保存しておいた変更前の JSON に戻す。

## 8. 便1 の手順（名義の移し）

移す前（Opus）:
1. ruleset 2 件・リポジトリの設定・secret の名前の一覧（値は読めない・名前だけ）・Pages の設定を JSON で保存する。
2. 開いている PR の数と、列の代わりに合流を止める時間帯を PO と決める（移す数分間は合流しない）。
3. 便0 が本線に入り、直書きが残っていないことを `git grep -n 'shingo-ops/salesanchor' -- scripts .github backend frontend` で 0 件（文書を除く）にしてある。

移す前（PO・画面で読むだけ）: R§8 の U2（実行機）・U3（webhook・deploy key・GitHub App）を読む。個人名義に入れた App（claude.ai の GitHub 連携を含む）が会社名義で要るかを決める。

移す（PO・画面）: Settings → Danger Zone → Transfer → GEN-RYU-System・名前は salesanchor のまま。

移した直後（Opus）:
1. K6: secret 86・ruleset 2 件の中身を保存した JSON と突き合わせ。欠けていたら保存した JSON で作り直す案を PO に同意票で出す。
2. 手元の全 worktree と本店の `git remote set-url origin`（新 URL）。
3. ~/.claude/settings.json の自動判定の文（R§6-5）と agent-console の routines.json（11 か所）を新名に直す（settings は ADR-1034 の権限の足し引きの手順）。
4. 自前の実行機の確認（U2）。消えていたら scripts/setup-vps-runner.sh で登録し直す（本番の VPS の作業は PO の同意）。
5. 次の本線への合流で、K5（配備・smoke・200）を確かめる。
6. クラウドの依頼を 1 本（読むだけ）流して clone できるか（U5）。

## 9. 続ける仕組み（標準化・機械で守らせる）

| 仕組み | 中身 | 守らせ方 |
|---|---|---|
| 列そのもの | ruleset の merge queue 必須・bypass 空 | GitHub が列を通らない合流を拒む（人も AI も） |
| 列の見張り | 新しい workflow（schedule 15 分ごと・public なので無料）。GraphQL `repository.mergeQueue(branch:"main").entries` の一番古い `enqueuedAt` が 60 分を超えたら scripts/notify/discord-owner-ping.sh で PO に知らせる | K4。Mergify の指摘「黙って止まる」への手当て |
| 設定のずれの見張り | 週 1 で ruleset を読み、merge queue の規則が無い・bypass が空でない・strict が有効、のどれかで Discord | 誰かが外したら気付く |
| 審査の見張り | review-gate に `--admin` を止める行 | 列を飛ばす命令を AI が出せない |
| 数える | 週 1 で K2・K3 を数えて記録（14 日で判定） | 効果を数で確かめる |
| 決まりの置き場 | ADR（adr-draft.md）で ADR-135:66 の「採らない」を置き換える。覚え書き「若い番号に譲る」は便2 の後に廃止を PO に提案（覚え書きの削除は PO 判断） | 決まりを 1 か所に |

## 10. 危険と手当て

| 危険 | 手当て |
|---|---|
| 移した後、旧名に戻せない | §8 の点検を移す前に全部済ませる。戻さない前提の計画 |
| App・クラウドの連携が会社名義のリポジトリを読めない | U3・U5 を移す前と直後に確かめる。読めなければ会社名義に App を入れる（PO の画面操作） |
| ruleset が移しで消える | 保存した JSON から作り直す（U1） |
| 列の中の確かめが長くなり待ちが延びる | 同時 5 本・制限 60 分。K3 で測り、数を見て変える |
| 列が止まって誰も気付かない | §9 の見張り（K4） |
| 純正の列の不具合（2026-04-23 例） | merge 方式は当時の対象外。列の見張りと K1 の照合で気付く |
| 乙に分けた確かめが、合わせた形の問題を見逃す | 乙は PR 本文・PR 差分だけで決まる物に限る。カードで行を読んで決め、迷ったら甲 |
| 危険 PR（移行・deploy.yml・本番 scripts）の GO | 「列に入れる」＝「合流の操作」とみなし、GO（ADR-136）は列に入れる前に受け取る。最大 1 件ずつなので 1 PR＝1 配備は変わらない |

## 11. 受け入れ基準と検証方法

| 基準 | 検証方法 |
|---|---|
| 便0: 16 件全部に merge_group | `git grep -L 'merge_group' -- <16 本>` が空 |
| 便0: 乙の job は列で飛ぶ | 便2 の後の試しの PR で、乙の確かめが merge_group の run で skipped・Success |
| 便0: 直書き 0 | §8 移す前 3 の grep が 0 件 |
| 便1: K5・K6 | §8 移した直後 1・5 |
| 便2: K1 の設定 | ruleset の JSON に merge_queue（MERGE・同時 5・最大 1・制限 60）・strict=false・bypass 空 |
| 便2: K4 | 試しに列を 60 分止めて Discord に 1 通 |
| 14 日後: K1〜K3 | §2 の測り方 |

## 12. 外部事例

R§7（出典・日付・数値・適用の限界は scratchpad の mq-web/evidence.md、要点は recon.md に転記）。どの事例も「このリポジトリで確実に成功する」証明ではない。数値は他社の規模（500〜800 人・1 日 300〜400 件）のもので、ここ（1 日 46 件）にそのまま当てはめない。当てはめるのは仕組み（列の中で確かめる・列を通らない道を塞ぐ・同時数を量に合わせる・見張る）だけ。

## 13. 未解決（設計合格の前に決める・確かめる）

- R§8 の U1〜U8。とくに U2・U3・U5 は PO の画面の確認が要る。
- strict を外すこと（§4）を PO が認めるか。
- K3 の 60 分を PO が認めるか。
