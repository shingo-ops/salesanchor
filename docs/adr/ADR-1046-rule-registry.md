# ADR-1046: 決まりは台帳を正本にし、台帳の検査を1つの関所にまとめる

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（R1a は警告で始める。必須化は連続 5 回の PR で誤検知 0 を確かめてから別の GO で判断する） |
| 備考 | PO 2026-10-27「1」（D1）：rule-enforcement の R0 から先へ進む |
| 起案日 | 2026-10-27 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1029（review-gate。R3 で本 ADR の台帳に置き換える。ADR-1029:31,36）、ADR-1040（警告で始め、連続 5 回の PR で 0 件なら失敗に上げる）、ADR-135（必須チェックの登録）、ADR-136（承認数を使わず記録を検査する） |
| 設計・根拠 | [design.md §5 R1・§6](../handoff/rule-enforcement/design.md)、[recon.md §4](../handoff/rule-enforcement/recon.md)、[kgi.md](../specs/rule-enforcement/kgi.md) |

---

## What（何を決めたか）

1. 決まりの正本は台帳 `docs/specs/rule-enforcement/rules.yml` にする。決まりの語（`words:`）を含む文書の行は、台帳のどれかの項目（`rules`）か、決まりではない行の印（`not_rules`）に必ず載せる。どちらにも載っていない行は「未仕分け」として数える。
2. 台帳の項目は `kind` が gate（機械が止める）・review（人が見る）・exempt（対象外）の3つ。gate には、止めている必須チェックの名前（`required-checks.txt` にあるもの）と、違反の見本（fixture）を持たせる。見本は R2 で置くので、R1a では「R2 で見本を置く」と書いた gate は警告にとどめる。
3. 検査は `scripts/ci/check_rule_registry.py` と `.github/workflows/rule-registry.yml`（ジョブ名 `rule registry`）の1か所にまとめる。見るのは、未仕分けの数と行、台帳の anchor が文書に実在するか、kind ごとの必須項目、gate の check が必須チェックにあるか、1行が2項目に重ならないか。出力は人が読む形と `--json`。
4. R1a は警告で始める（ステップに `continue-on-error: true`）。台帳に入れるのは、recon §4 で「止める」とされ、止めている必須チェックが `required-checks.txt` にある決まりだけ。それ以外の行の仕分け（review・exempt・not_rules）は設計担当が行い、R1a では行わない。
5. 台帳・`rule-docs.txt`・`required-checks.txt`・`prod-secrets.txt` は、変更に GO 記録を要る対象にする（`scripts/check-process-artifacts.js` の DANGEROUS_PATTERNS に4行足す）。
6. R3 で、ADR-1029:31,36 にある review-gate の「何を審査するか」の定めを、この台帳の review 項目に置き換える。それまで ADR-1029 は有効のまま。

## Why（なぜ）

- 決まりは複数の文書に散っており、どの決まりが機械で止まり、どれが文書だけなのかを一覧で言えない。KGI G1（未仕分けの数が見える）と G5（決まりの行を足したのに台帳を更新しない変更が失敗になる）を満たすには、行と台帳の対応を機械で照らす正本が要る。
- 検査を複数に分けると、決まりごとに「どの検査が守るか」が食い違う。1つの関所にまとめ、必須チェックの名前の一覧と突き合わせれば、「止めると書いてあるのに止まっていない」決まりを見つけられる。
- いきなり必須にすると、誤検知で全 PR が止まる。ADR-1040 と同じく警告で始め、誤検知 0 を確かめてから上げる。

## 受け入れるリスク

- 決まりの語の一覧に無い言い方（「不可」「いけない」「のみ」「避ける」「don't」）の行は、数えられない。R1a では語の一覧を変えず、取りこぼしの行数だけを測って報告する。
- 同じ行に複数の決まりがある場合、1つを gate にすると、その行の他の決まりも「載った」ことになり、未仕分けの数から隠れる（例: AGENTS.md の A09 と A10、frontend/AGENTS.md の F02・F03・F16）。
- anchor は文書の文言の一部なので、文書を書き換えると台帳が失敗になる。これは意図した動き（書き換えたら台帳も更新する）。
- 警告の間は、未仕分けが残っていても PR は止まらない。

## 戻し方

`.github/workflows/rule-registry.yml` を消す（必須チェックではないので ruleset の変更は要らない）。台帳・検査スクリプト・一覧3ファイルは残してよい。DANGEROUS_PATTERNS の4行は、戻すときは GO 記録つきで消す。

## 検証

`scripts/tests/test_check_rule_registry.py`（未仕分けの行・消えた anchor・欠けた項目・存在しない check・重なりがそれぞれ失敗になること、通る例が通ること）と `scripts/tests/test-process-artifacts.js`（台帳の4ファイルが dangerous 区分になること）。実測の件数は R1a の PR 本文に記す。
