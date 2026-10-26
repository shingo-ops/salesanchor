# 実装カード 段階3 便8c — 読み込み中の三項の検査が取りこぼす4つの書き方を拾えるようにする

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 方針 2026-10-23「1」、設計 2026-10-24「1」、便7のあとの残件着手 2026-10-26「1」
- 起点: 最新 origin/main。ブランチ release/loading-button-bin8c
- 根拠: 事前調査（scripts/check-ui-governance.js の maskSource・countLoadingTernary・isInsideTCall、再現 13 例の結果）。今の main で4形の実例は 0 件
- 対象ADR: ADR-144
- 実行場所: クラウド。push までを行う。PR は手元で作る（scripts/agent-hooks/cloud/rules.md）
- Opus の設計判断: prop の値の中の三項（confirmLabel={x ? ... : ...} 等）は、今後も数えない。理由: label={loading ? t("common.loading") : undefined} のように正しい使い方もあり、見分けられない。確認の小窓は便8a で confirmLoading を持ったので、直す道がある

## 1. 直す4つ（scripts/check-ui-governance.js）
(1) JSX の地の文の `'`（例 `<p>Don't {saving ? t("common.saving") : t("common.save")} it's</p>`）
- 今: maskSource の正規表現が '...' を文字列とみなし、間の t(...) まで隠す
- 直し方: maskSource で ' または " で始まる文字列に当たったとき、元の文の直前の空白でない文字（改行も空白として読み飛ばす）を見る。それが次のどれでもなければ、地の文とみなす。その1文字だけを写して、正規表現の続きをその次の位置から探す（re.lastIndex = m.index + 1）
  - 文字列が来うる記号: ( , = : ? [ { } + - * / % ! & | ^ ~ ; < >
  - 文字列が来うる語（直前が語のとき、その語全体が次のどれか）: return typeof case in of void yield await delete else throw
  - ファイルの先頭
- JSX の属性値 name="x"（直前が =）は今までどおり文字列として扱う
- 今までどおりになる（拾えないまま）のを受け入れる形: 地の文の ' の直前が > や } のとき（例 `<p>'quoted'`、`{x}'s`）。比較・矢印の > と式の } を区別できないため。この形が今の main にあるかは未確認なので、frontend/src の対象 .tsx で >' と }' を含む JSX の地の文の行を探し、件数と、その行に読込キーの三項があるかを報告する（直さない）
(2) テンプレートの入れ子（例 t(saving ? `${a ? `x` : `y`}.saving` : "common.save")）
- 今: バッククォートの正規表現が、内側のバッククォートで外側を閉じる
- 直し方: バッククォートは正規表現でなく、手で終わりを探す関数にする。${ で深さを1増やし、対応する } で減らす。式の中の文字列・テンプレート（入れ子）・コメントを読み飛ばす。深さ0のバッククォートで閉じる。隠し方と strings に積む value は今と同じ（区切りの間をまるごと _ にし、value は区切りの間の元の文）
(3) t の第2引数（例 {saving ? t("common.saving", { n }) : t("common.save")}）
- 今: t("key") の直後が ) のときだけ (A) にする
- 直し方: 直後が , のときは、masked で深さを数えて t( に対応する ) を探し、そこまでを1つの単位（unitEnd）にして (A) にする。見つからなければ今と同じ扱い
(4) i18n.t（例 {saving ? i18n.t("common.saving") : i18n.t("common.save")}）
- 今: countLoadingTernary の包みの判定と isInsideTCall が、直前の . を除外する
- 直し方: 両方の正規表現で i18n.t( と i18next.t( も t( と同じに扱う。ほかの .t(（例 obj.t(）は今までどおり拾わない
- tr( について: frontend/src で tr という名前の翻訳関数が定義・使用されているかを git grep -nE "[^A-Za-z0-9_$.]tr[[:space:]]*[(]" -- frontend/src と定義元で確かめ、件数と定義を報告する。足さない

## 2. 試験（scripts/tests/test-ui-governance.js、T72 から）
既存の型（assert(説明, 実際, 期待)、lt = countLoadingTernary）で足す。
- 1件になる: (1) の例、(1) で ' が2つ以上ある段落の中の三項、(2) の例、(3) の例、(3) の逆順 {saving ? t("common.save") : t("common.saving", { n })}、(4) の例、(4) の (B) 形 {i18n.t(saving ? "common.saving" : "common.save")}
- 0件のまま: 三項のない `<p>Don't stop. It's fine.</p>`、属性値 `<input placeholder="Don't" />`、t の第2引数があっても読込キーでない {x ? t("common.save", { n }) : t("common.cancel")}、prop の値の (4) confirmLabel={x ? i18n.t("a.disconnecting") : i18n.t("a.disconnect")}、obj.t("common.saving") を使った三項、ui-allow 付きの (3)
- 既存の T1〜T71 は書き換えずに全部 pass

## 3. 実測（生出力は /tmp/CC報告ファイル/loading-button-bin8c/impl/。無ければ作る。主要な結果は報告に書く）
- 今の main で増えないこと: origin/main の frontend/src/pages・features・components の .tsx（stories・design-system・design-preview・.test.tsx を除く）を、直す前の関数と直した後の関数の両方で数え、ファイルごとの件数を並べる。違うファイルがあれば、ファイル・行・中身を書く（差分方式なので赤にはならないが、件数を残す）。直す前の当たりは InboxMessageThread.tsx の1件だけのはず。違えば報告する
- 本体の動作: BASE_SHA=<起点> HEAD_SHA=HEAD node scripts/check-ui-governance.js exit 0
- 取りこぼしなし（段階3の着手前）: 69721d365^1 の時点で、便7a と同じ取りこぼしの確かめ（その時点のファイルを git show で読み、直した後の関数で数えた件数が、直す前の関数の件数以上）を行う

## 4. 触らない範囲
- 既存6種別の数え方、LOADING_VERBS、isLoadingKey、isInsidePropValue、ファイルの選び方、表示文
- frontend/、.github/workflows/、辞書

## 5. 文書
- docs/specs の loading-indicator の design.md（git grep -l で場所を特定）3-7 の残件③（検査が取りこぼす形4つ）の行に「便8c（card-19）で4つとも拾えるようにした。prop の値の中の三項は数えない（理由は card-19 冒頭）」を足す
- 本カード（この全文）を docs/handoff/loading-indicator/card-19.md として同じ commit に入れる

## 6. 検証
| 基準 | 検証方法 |
|---|---|
| 試験 | node scripts/tests/test-ui-governance.js が全件 pass（T1〜T71 は変えずに pass、T72 以降が §2 のとおり） |
| 4つを拾う | §2 の「1件になる」がすべて 1 |
| 拾いすぎない | §2 の「0件のまま」がすべて 0、§3 で今の main の件数が直す前と同じ（違えば中身を報告） |
| 本体の動作 | §3 で exit 0 |
| 範囲 | git diff origin/main...HEAD --name-only が scripts/check-ui-governance.js・scripts/tests/test-ui-governance.js・design.md・card-19.md だけ |

## 7. 想定分岐
- (1) の直し方で、既存の試験（T1〜T71）が落ちる → 直し方を狭める（判定する直前の文字を減らす）。それでも落ちるなら BLOCKED:（落ちた試験と理由）
- (2) の手書きの終わり探しで、閉じないテンプレートに当たる → 今の正規表現と同じく、そこから先を文字列とみなさない（落ちない）
- §3 で今の main の件数が増えたファイルがある → 中身がボタンの言葉の入れ替えなら、そのまま報告（直さない）。ボタンでないものが3件以上なら NEEDS_DECISION:
