# design: AI が足した見張りを記録できる道（草案・2026-11-09）

状態: 設計案作成済み／自己審査済み（同じ AI。§12）／§9 は PO 決定済み（2026-11-09「1」＝案1）／クラウドでの設計審査は未実施／実装未着手。
根拠: recon.md（同じフォルダ）。関係 ADR: ADR-1034・ADR-1033・ADR-1029。

## 1. 目的（PO の言葉から）
- PO の言葉（2026-11-09）:「原則私はエンジニアではないから見張りを足すのはあなたと実行者だけ」。
- 今は、AI が設計し PR で入れた見張りでも、~/.claude に入れるのは PO の `!`、記録には PO の「1」（本文にハッシュの入った同意票）が要る。記録の道が無いので、週次点検で毎回「異常」に出る（11/02・11/09）。
- 目的: 見張りを足す・強める作業は AI だけで最後まで進み、週次点検に異常として出ないこと。見張りを外す・弱める変更は、今までどおり必ず異常として見つかること。

## 2. KGI（PO が週次点検の1行で○×を判定できる形）
| 番号 | 基準 | 今 | 目標 | 測り方 |
|---|---|---|---|---|
| K1 | GitHub main にマージ済みの PR から入れた見張り（足す・組に足す）が、週次点検の `ABNORMAL_REASON=B` に出る件数 | 11/09 で3件 | 導入後の毎週 0件 | 週次点検の出力の B の行を数える |
| K2 | 見張りを外す・組から抜く・PR に無い中身に書き換える変更が B に出る割合 | 100%（今は全部出る） | 100% のまま | 試験（A3〜A5）で各1件ずつ作り、全部 B に出ること |
| K3 | 見張りを入れるために PO が `!` を打つ回数 | mac-test-guard で1回 | 0回（導入時の1回を除く） | 新しい見張りの設計書の「導入」の欄に PO の `!` が無いこと |

## 3. 対象と対象外
- 対象: ~/.claude/settings.json の hooks（user:hooks）と ~/.claude/scripts/ の見張りの本体（hook_files）。
- 対象外（今までどおり PO の「1」）: 見張りを外す・弱める変更、permissions.deny / ask / defaultMode、確認を省く設定、autoMode.soft_deny / environment、danger_ops、本番の設定。

## 4. 変更前後
| | 変更前 | 変更後 |
|---|---|---|
| 見張りの正本 | リポジトリの `scripts/agent-hooks/<名前>/`（mac-test-guard で既にこの形） | 同じ。正本の無い見張りは対象外 |
| ~/.claude へ入れる人 | PO が `!` で install.sh | Opus か実行役が `bash ~/.salesanchor-tools/scripts/agent-hooks/<名前>/install.sh`（GitHub main に揃えた写しの版だけ）。自動判定の例外 HKI-1 で通す |
| 台帳への記録 | PO の「1」で `consent:` の record（無いと B） | install.sh の最後で `perm-change.py record --po-ref PR#<n>` を自動で書く |
| 点検の確かめ | user:hooks・hook_files の PR 番号は通らない（consent-audit.py:906） | 「強める変更」に限り PR 番号で通す（§5） |
| 外す・弱める | PO の `!`＋「1」 | 変わらない |

## 5. 「強める変更」の定め方（点検が機械で判定する）
PR 番号 `PR#n` で説明できるのは、次のどれかに当たるものだけ。どれにも当たらなければ今までどおり B。
1. hook_files の増: そのファイルの中身の sha256 先頭8桁が、PR #n のマージの版の `scripts/agent-hooks/` の下の同じ名前のファイルと一致し、PR #n の差分がそのファイルを変えている。
2. user:hooks の増: その組のすべての命令が `~/.claude/scripts/<相対パス>` を指し、そのファイルが 1. を満たすか、前回の写しで既に登録済み。
3. user:hooks の「組の入れ替え」: 減の組 E_old と、同じ record の束にある増の組 E_new が、同じ event と matcher で、E_new の命令が E_old の命令をすべて含む（足しただけ）。減の行には `--replaced-by <E_new の sha8>` と E_old の中身（命令はパスだけ。値は出さない）を付け、点検は中身の sha8 が item_hash と同じことを確かめる。
4. hook_files の中身の書き換え（同じパスで中身が変わる）: 1. の条件に加え、PR #n の差分で、その見張りの試験ファイル（`scripts/agent-hooks/<名前>/test_*.py`）の行が1行も消えていない（足しただけ）。試験の行を消す・変える直しは「弱める」かもしれないので B。【PO 決定 §9 案1】

あわせて、PR #n は ADR-1029 の審査（新しく起動した opus の審査役の APPROVE）を通ってマージされていることを条件にする（既にマージの見張りで強制されている）。審査役の確認項目に「この PR は見張りの止める範囲を狭めていないか」を1行足す。

## 6. 入れる道（install.sh の型）
- 置き場所は `scripts/agent-hooks/<名前>/install.sh`。mac-test-guard の install.sh（写す→原本と比べる→試験→settings の控え→1件足す→JSON を読み直す）の型に、最後の「台帳に record を書く」を足す。足すだけで、外す処理を持たない（外すのは rollback.sh で、PO の `!` のまま）。
- 自動判定の例外 HKI-1（PO が導入時に `!` で1回だけ足す。ADR-1034 の PDL-1 と同じ形）:
  > HKI-1: Running exactly `bash ~/.salesanchor-tools/scripts/agent-hooks/<name>/install.sh` is allowed, only when ~/.salesanchor-tools is clean and at GitHub main (checked by `perm-change.py sync`). These install scripts only add a guard hook that was reviewed and merged by PR; they never remove or loosen hooks. Running rollback.sh, editing settings files directly, or running any other script under ~/.claude is still Self-Modification.
- 実装は mac-test-guard の install.sh を1つ目の対象にして、今週の3件を PR #5039・#5049 で記録し直せるかを試す。

## 7. 代替案
| 案 | 中身 | 採らない理由 |
|---|---|---|
| A 今のまま | PO の `!` と「1」 | PO の原則に反する。毎週異常が出て、本当の異常が埋もれる |
| B 見張りは全部 PR 番号で通す | 外す変更も通す | Opus は自分でマージできるので、見張りを外すことも AI だけで済む。ADR-1034 が閉じた穴が開く |
| C 点検から見張りを外す | 数えない | 弱める変更も見つからなくなる |
| D（採る） 強める変更だけ PR 番号で通す | §5 | 足す作業は AI だけ、外す・弱めるは PO の目に必ず届く |

## 8. リスクと対処
1. 中身の書き換えで、試験を消さずに止める範囲を狭める。対処: §5-4 の試験の条件と審査役の確認項目（PO 決定 §9 案1）。それでも残る分は受け入れたリスクとして ADR に書く。
2. HKI-1 の例外の文が広く読まれ、ほかの台本まで通る。対処: 道と名前の形を `~/.salesanchor-tools/scripts/agent-hooks/*/install.sh` に固定し、sync で版を確かめる。導入後、AI が rollback.sh や別の台本を走らせたら止まることを試す（A6）。
3. 1つの PR を何度も使う。対処: 今の「同じ po_ref と item_hash の組は1回」をそのまま使う（design.md:195）。
- 戻し方: HKI-1 を外す台本（PO の `!`）と、consent-audit.py の §5 の分岐を元に戻す PR。
- 外部事例: 使わない。社内の決まり（誰が確認するか）の変更で、外の数値が設計の正しさを示さないため。

## 9. PO の決定（2026-11-09。PO の返事「1」＝下の案1）
見張りの「中身の書き換え」を AI の確認だけで記録してよいか。
- 案1（採用）: 試験の行が1行も消えていない直しは AI で記録。試験を消す・変える直しと、外す変更は PO の「1」。
- 案2: 足す変更だけ AI で記録。中身の直しは全部 PO の「1」。
- 案3: 外す変更も含めて全部 AI で記録。

## 10. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| A1 §5-1〜3 を満たす増・入れ替えが B に出ない | 試験（一時の HOME と一時の git リポジトリ。既存の permission-delegation-tests.py に足す） |
| A2 今週の3件を PR #5039・#5049 の record で説明でき、B が0件 | 実物の写しで点検を流し直す（`--commit-snapshot` なし） |
| A3 組から命令を抜く入れ替えが B | 試験 |
| A4 PR に無い中身・`scripts/agent-hooks/` の外のファイルが B | 試験 |
| A5 試験の行を消した PR での中身の書き換えが B（案1のとき） | 試験 |
| A6 AI が rollback.sh・別の台本を走らせると自動判定で止まる | 導入後に1回ずつ試し、止まった記録を残す |
| A7 install.sh が足すだけで、2回流しても1件 | 試験（mac-test-guard の test と同じ型） |

## 11. 維持の仕組み
- 週次点検（agent-console の定期作業）が毎週 K1・K2 を出す。B が出たら今までどおり Opus が中身を調べて PO に報告する。
- 新しい見張りの設計書は「正本は `scripts/agent-hooks/<名前>/`、導入は AI が install.sh」を書く。

## 12. 設計審査（Architect・同じ AI の自己審査。独立した第二者の審査ではない）
- 判定: REVISE（§9 は PO 決定で解消。残る②③をクラウドの設計審査と実装カードで固める）。
- 確かめたこと: 今の判定の場所（consent-audit.py:801・:845・:906）、今週の3件の中身と GitHub main の正本の一致（recon 1）、install.sh の型（mac-test-guard/install.sh）。
- 残る点: ①（解消）§9 は PO 決定。②HKI-1 が実際に通るかは未確認（recon 未確認）。③§5-3 の「同じ record の束」の決め方（同じ PR 番号で同じ日の行）を実装カードで固める。
- 正式な審査（クラウドでの設計審査）は PO の §9 の回答の後に行う。
