# design: PR 作成時の関所で、CI と同じ process-artifacts 検査を先に実行する

- 状態: 設計案作成済み／自己審査 APPROVE（§8）／PO 実装承認済み（2026-09-30「確立したならy」）
- 調査: `docs/handoff/local-gate-ci-parity/recon.md`
- 対象ADR: `docs/adr/ADR-121-sop-process-artifacts-gate.md`（process-artifacts gate の定義元。関連: `docs/adr/ADR-1003-go-delegation-to-opus.md` の GO 記録、`docs/adr/ADR-135-release-stowaway-prevention.md` の危険変更パターン。本便はどちらの判定も CI では変えない）

## 1. 目的（PO から見える変化）
- 設計書の不備（ADR 参照がない、recon の参照がない、受入条件表がない等）が、CI を数分待ってからではなく、**PR を作る時点で**止まる。PR #3861 と同じ不備は、PR 作成の時点で止まる

## 2. 方針: 写さずに呼ぶ
- 手元の関所 `scripts/dev/validate-pr-body.sh` から、CI と同じ `scripts/check-process-artifacts.js` を呼ぶ（検査のロジックを手元用に書き写さない＝基準が1か所）
- ただし recon §2 のとおり、そのまま呼ぶと GO 記録（PR 作成時には書けない）で必ず止まり、設計書の検査まで進まない。そこで JS に「PR 作成前の事前検査」の切り替え `LOCAL_PRECHECK=1` を加える
  - GO 記録の検査だけを飛ばす（「GO 記録は PR 番号確定後に CI で検査」と表示）
  - PR 番号に依存する検査（維持の仕組み、触る／削除するファイルの照合）は「新しい PR（2600 以上）」として実行する
  - **CI では使えない**: `GITHUB_ACTIONS=true` のときに `LOCAL_PRECHECK=1` があれば exit 1（CI で GO 記録の検査を抜ける経路を作らない）
- 既存の Python の検査は、この便では**消さない**（変更は一度に1つ。JS 呼び出しが実運用で働くことを確かめてから、重複を別便で整理する）
- 手元の関所から JS を呼ぶときは `env -u GITHUB_ACTIONS` を付ける。理由（2026-09-30 実装時の事実）: `scripts/tests/test-pr-lifecycle.py:437-453` は、PR 作成が外から注入された環境変数（GH_HOST、GH_REPO、GITHUB_ACTIONS=true）に左右されないことを確かめており、既存の `scripts/gh-pr-create-safe.sh:138` も同じ理由で `env -u GITHUB_ACTIONS` を使っている。CI の gate（`.github/workflows/process-artifacts-gate.yml:44`）は `scripts/dev/validate-pr-body.sh` を通らず JS を直接呼ぶので、CI での拒否はそのまま効く
- 事実（CI と同じ挙動のまま）: 危険変更だけの PR（例: `scripts/` のみ）は、CI でも GO 記録の検査のあと設計書の検査に進まずに終わる（`scripts/check-process-artifacts.js` の hasDangerous 分岐）。手元の関所も同じになる。これを変えるかは別便

## 3. 変更するファイル
- `scripts/check-process-artifacts.js`: `LOCAL_PRECHECK` の追加（GO 記録の検査の直前で分岐、PR 番号の猶予判定2か所、CI での使用拒否）
- `scripts/dev/validate-pr-body.sh`: 既存の検査のあとに JS を呼ぶ。入力は、変更ファイル＝`git diff --name-only origin/main...HEAD`、本文＝標準入力、作成者＝`gh api user`、ブランチ＝現在のブランチ。node がない・作成者が取れない場合は**止める**（黙って通さない）
- `scripts/tests/test-process-artifacts.js`: `LOCAL_PRECHECK` のテスト3件（GO を飛ばす／CI では拒否／PR 番号なしでも宣言照合が走る）

## 4. 対象外
- `.github/workflows/` の変更（テスト2本を CI で実行する件を含む。別便・PO 判断）
- ~/.claude/scripts/pr-body-guard.sh、~/.claude/settings.json（変更不要。今の呼び出しのまま JS まで届く。バッククォートなし表記＝リポジトリ外パスのため、process-artifacts gate のfile:line引用チェック対象外・ADR-129既知事象）
- Python 側の重複の削除（次の便）

## 5. 受入条件
| 基準 | 検証方法 |
|---|---|
| PR #3861 の修正前の設計書で、手元の関所が ADR 参照の不足で止まる | recon §2 の再現：修正前の設計書＋GO 記録なしの本文で `scripts/dev/validate-pr-body.sh` が exit 1、エラーに「ADR 参照」 |
| 修正後の設計書では手元の関所を通る | 修正後の設計書＋GO 記録なしの本文で exit 0 |
| CI では GO 記録の検査を抜けられない | `GITHUB_ACTIONS=true LOCAL_PRECHECK=1` で exit 1（テスト） |
| CI の判定は変わらない | `LOCAL_PRECHECK` なしで、recon §2 の4通りの結果が変更前と同じ |
| 既存テストが通る | `node scripts/tests/test-process-artifacts.js` と `python3 scripts/tests/test-pr-lifecycle.py` を変更前後で実行し、変更前に通っていたものが全部通る |

## 6. リスク
| リスク | 対処 |
|---|---|
| 切り替えが CI で GO 記録を抜ける穴になる | `GITHUB_ACTIONS=true` で拒否＋テスト |
| 手元の関所が厳しくなり、PR が作れなくなる | 止まる理由は CI で落ちるのと同じもの。止まったらエラー文で直し方が分かる |
| JS の入力（変更ファイル・追加ファイル等）が CI と違い、誤って止める／通す | 実装前に JS が各入力をどう使うかをコードで確認し、CI と同じ値を git から作る。分からなければ止める |

## 7. 外部・過去事例
外部事例は該当なし（社内の検査スクリプトの呼び出し方の変更で、外部の数値事例が判断を変えない）。社内事例: 手元の関所は CI のロジックを Python に書き写しており（recon §3）、CI 側に設計書の検査が追加されたときに写しが追いつかず、PR #3861 が CI で落ちた → 写さずに呼ぶ

## 8. 設計審査（同じ AI による自己審査）
- 判定: APPROVE。未確認2点（recon §5）は本便の判断に影響しない

## 9. 維持の仕組み
- 守り手: `scripts/tests/test-process-artifacts.js`（LOCAL_PRECHECK の3件）、`scripts/dev/validate-pr-body.sh`（CI と同じ JS を呼ぶので、CI の検査が増えれば手元も自動で同じになる）
- 人手: テスト2本が CI で実行されていない件は別便で PO 判断
