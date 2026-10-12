# design: 試作版 v102 の予約の判定に「発売日・先の日付・見出し」を加える（便PO）

参照: docs/handoff/v102-preorder-context/recon.md、[card-PO.md](./card-PO.md)、docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:26。

## 1. 目的（PO の言葉、2026-10-12）
- 「商品マスタの発売日から商品の発売日が未来→予約商品と判断することは出来ると考えるがどうか」
- 「10月中旬発送予定や[10/14入荷などは再販商品の予約案内なのだがこういった商品も予約とシステムが判断することは出来る」
- 3つ（発売日・先の日付・見出し）を組み合わせる案に「y」。
- 利用者に見える変化：在庫一覧・配信で、予約の案内の件の状態が「In Stock」から「Pre-order」になる。

## 2. 変更（v102 経路だけ。v101・v10・旧経路・shadow は挙動不変）
| 場所 | 変更前 | 変更後 |
|---|---|---|
| backend/app/services/v102_status_context.py（新規） | 無し | resolve_status_v2 が DEFAULT で決めた件だけ、RELEASE_AHEAD → DATE_AHEAD → HEADING の順で決め直す。語・日付の書き方・ステータス名はすべて tcg_status_master の行から読む |
| backend/app/services/tcg_status_values.py（新規） | effect・match_type の値が各所に文字列で散在 | 値の定数を1か所に（OUTPUT・EXCLUDE・HEADING・DATE_AHEAD・RELEASE_AHEAD、REGEX・LITERAL・DEFAULT・RELEASE） |
| backend/app/schemas/central_masters.py:553-554 | effect {OUTPUT, EXCLUDE}・match_type {REGEX, LITERAL, DEFAULT} | 上の定数の集合（新しい値の行が入っても管理画面の一覧 API が落ちない） |
| gemini_raw_copy_v102_product_first.py:122-124 | 発売日・投稿日なし | ProductFirstMasters に product_release（既定は空）・posted_date（既定 None）。load_product_first_masters が products.release_date を読む |
| line_analysis_v102_svc.py:1072-1136 | 投稿日を読まない | load_posted_date（job の source_messages.line_posted_at を JST の日付に）を masters に載せる |
| gemini_raw_copy_v101.py:897-931, :1330-1370 | 件の行だけで判定 | v102 のときだけ、全件の lines の和集合（落とした件を含む）と発売日・投稿日を渡す |
| 件の dict | — | status_basis（例 RELEASE_AHEAD:2026-10-31 / DATE_AHEAD:10/16発送 / HEADING:4）を載せる。DB には書かない |
| 管理画面（RuleManagementPanel・RuleDrawer・ruleEffects.ts・ja/en.json） | 新しい effect の行を表示・編集できない | 「予約の手がかり」タブ。新しい effect・match_type と除外語を編集できる。既存の不具合（保存で match_type が LITERAL に上書きされる）を直す |
| データ（tcg_status_master） | — | 本 PR では入れない。候補6行と SQL は data/（precheck・dryrun・commit・verify・rollback）。投入は PO の y の後 |

### 決め直しの規則
- 発売日（RELEASE_AHEAD）：件の商品の release_date が投稿日（JST）より後。
- 先の日付（DATE_AHEAD）：件の行に規則の正規表現（名前付きグループ m 必須、d・part 任意）が当たり、除外語が当たらない。期限は d があればその日、上旬→10日・中旬→20日・下旬/末/頃→月末、月だけなら月末。年は、投稿と同じ月なら投稿年、投稿月の1つ前の月（CURRENT_YEAR_BACK_MONTHS）は過ぎた月（1月の投稿の12月は前の年）、それより前の月は翌年。期限が投稿日の翌日（NEXT_DAY_GRACE_DAYS）より後なら当たり。成り立たない日付（2/30 等）は当たらない。（便PO2、PO 決定 2026-10-12）
- 見出し（HEADING）：件の最初の行から上へ、どの件の lines にも入っていない空でない行を順に見て、規則（priority 順）に最初に当たった行の canonical。canonical が今の状態と同じ（在庫の見出し）なら変えない。
- Sold out（EXCLUDE）・既存の OUTPUT の Pre-order は変えない。

## 3. 受入条件
| 基準 | 検証方法 |
|---|---|
| T1 規則の行が無いとき、全件の結果が変更前と同じ | 置き換え試験：本番の v102 現行行 111 job・2,693 件で、規則なしの変更後と変更前の差 0 件（/tmp/CC報告ファイル/preorder-design/test/、手元・社外秘） |
| T2 候補6行を足したとき、status 以外の列の変化 0 件・Sold out の変化 0 件 | 同上：status 以外 0・Sold out 16件中 0 |
| T3 予約の見出しの下の In Stock 280 件がすべて Pre-order | 同上：HEADING 205＋DATE_AHEAD 53＋RELEASE_AHEAD 22＝280（gap75/all280.csv） |
| T4 「明日発送予定」は不変・規則の各分岐（未来/当日/過去、旬、翌年、2/30、見出しの除外語、在庫見出しで打ち切り） | テスト backend/tests/test_v102_status_context.py（33件） |
| T5 新しい effect・match_type の行で既存の読み手が落ちない・挙動不変 | テスト backend/tests/test_status_master_context_values.py（24件） |
| T6 管理画面で新しい effect の行を作成・編集でき、match_type が上書きされない | テスト RuleDrawer.test.tsx・ruleEffects.test.ts、npm run check:all |
| T7 本番反映後、規則の行を入れるまで状態の分布が変わらない | デプロイ後の解析で Pre-order の件数が反映前の水準（現行 2件程度）のまま（本番読み取り） |

## 4. 代替案
- 別の表を作る：規則が2か所に分かれ SSOT に反する → 既存の tcg_status_master を広げる（CHECK 制約が無く、検証は central_masters.py だけ）。
- Gemini に予約かを判断させる：PO 方針「Gemini は行番号・数量・価格、判断はシステム」に反する → システムが行番号から読む。
- 見出しの語をコードに書く：金型（マスタ）に無いハードコード → すべて表の行から読む。

## 5. リスクと対処
- 翌日の発送（投稿 10/10 の「10/11発送」）も予約になる → PO 判断待ち（§7）。判断次第で規則の行で調整する（コードは変えない想定。変える場合は別便）。
- 見出しの語が広すぎる → 除外語（ご予約可能・集荷予約・在庫なし 等）を表で持ち、管理画面で直せる。

## 6. 戻し方
- データ：data/rollback.sql（enabled=false、行は消さない）。これで変更前の判定に戻る（T1）。
- コード：PR を revert。

## 7. PO 判断待ち（データ投入の前提）
- PO 決定（2026-10-12）：投稿の翌日までの発送は在庫のまま（「y：投稿の翌日までの発送は在庫のままにします。→y,発送日の情報は発送日情報に記載する条件で」）。過ぎた月は来年（「今年が過ぎてしまっているのであれば来年」）、ただし投稿月の1つ前の月は今年（「これは今年だと考える」、境目に「y」）。便PO2 で反映。発送日の文字の保存先は PO 判断待ち。
- 件に入っていない商品行が見出しとして読まれうる（レビュー MEDIUM-2）。置き換え試験の HEADING 205 件で当たった見出しの文字は7種（【予約商品】・◆予約商品◆・予約品 等）で、商品行は 0。除外語は管理画面で直せる。
- 候補6行と、変わる件の全件の一覧を見せて y を取ってから commit.sql を流し、48時間分の job を解析し直す。

## 外部・過去事例の参照と我々への応用
- 外部事例：使わない（仕入元ごとの書き方に合わせた社内の判定規則で、比べられる公開の実測が無いため）。
- 過去事例：便ER #4129（判断できない状態を Error＋要確認にした）。規則で決まらないものは推測で決めない、という同じ方針で、手がかりが無い件は従来の DEFAULT のまま。

## 維持の仕組み
- テスト（規則の分岐・既存の読み手の互換・管理画面）が CI で毎回走る。
- 規則の語は管理画面「予約の手がかり」タブで直せる（コード変更不要）。
- 守り手: CI（backend/tests/test_v102_status_context.py、backend/tests/test_status_master_context_values.py、frontend の RuleDrawer.test.tsx・ruleEffects.test.ts）
