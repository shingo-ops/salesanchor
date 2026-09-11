# 同値カラーalias材料便：既存ゲートの通過条件

観測固定SHA: `4734fe7f`。git showで現物確認。製品・CI・設定・正式文書は未変更。今回GO認証の再調査・架空承認記録はしていない。

## 結論

CI変更は不要。新しい用途名をsrc/index.cssのlight/darkに同値aliasとして追加し、追加理由・既存token流用の確認・パリティ実行結果をPR本文に記載する。指定4チェックを実施後に全てチェック済みで置く。これは本文形式の検査であり、PO本人による承認認証ではない。

## 実際の判定

frontend/scripts/check-new-tokens.js:
- GITHUB_BASE_REF未設定ならexit0で何も検査しない。通常ローカルのnpm run check:new-tokensだけでは成功証拠にならない。
- base=main/head=developだけskip。今回のrelease/*は対象。
- frontendをcwdとしてgit diff origin/<base>...HEAD -- src/tokens.css とsrc/index.cssを見る。未コミット差分は対象でない。
- 追加行の `--name:` を拾うだけなので、既存tokenの値変更行も「新規」と数える。light/dark同名も各宣言を数える。ログ件数を新しい固有名の個数と混同しない。
- 本文が「デザイントークン変更時」または「check:dark-parity」を含む必要がある。
- 4つの対象文字列それぞれを含む最初の行を探し、その行が行頭 `- [x]` または `- [X]` であることを要求する。インデント付きチェックは不合格。同じ対象文字列を前段の未チェック項目/説明行へ重複記載するとそちらで失敗する。
- 実装は対象項目が欠落するとskipしてしまうが、この穴を使わず正式テンプレ4件を全て記載する。hasCheckedItems変数は計算されるだけで判定に使われない。
- git diff失敗もcontinueしてしまう。比較参照が実在しdiff読取成功したことを別途確認し、skipを合格根拠にしない。

## 推奨するPR本文部分

以下は実施後に使用する本文形式。今チェックを実行済みとして登録するものではない。GO行を含まない。

```markdown
概要：既存色を参照する用途別の名前を追加し、重複した固定色の編集元を一本化する。色・テーマ別表示・操作は変更しない。
変更表：追加する用途名、参照先、light/darkの解決値、置換する箇所を記載する。

### デザイントークン変更時（tokens.css / index.css を変更した場合）
- [x] 新しいトークンを追加した場合、その**理由**を概要欄に記載した
- [x] 色トークンは `:root`（ライト）と `:root.force-dark`（ダーク）の両方に追加した
- [x] `npm run check:dark-parity` でパリティ確認済み
- [x] 既存トークンで代替できないか確認した（トークン重複防止）
```

根拠: .github/PULL_REQUEST_TEMPLATE.md:48–52 と実スクリプトのREQUIRED_ITEMS/lines.find/行頭regex。

## その他の色ゲート

| 検査 | 同値aliasで必要な確認 |
|---|---|
| check:dark-parity | index.cssの最初の:rootと:root.force-darkから抽出。用途名を両側へ定義。同じ名前があるだけで解決値の同一性は証明しない |
| check:css-colors | index.css/tokens.css以外のhex/rgb/rgbaを検出。利用CSSはvar参照に置換。名前変更だけで値が同じかは別途解決値を確認 |
| check:css-values / CSS var fallbacks / ESLint | 既存の数値・fallback・inline色制約を維持。alias便で入力/寸法/挙動へ変更を広げない |
| check:color-token-sync | 最初のrootでbg/text/accent/border/success/warning/danger/info接頭辞のtokenはDesignSystemPage.tsxのCOLOR_TOKENSへ掲載必須。icon等の別接頭辞はこの検査の対象外だがカタログ要否は設計に従う |
| scripts/check-design-token-ratchet.sh | tokens.css以外の変更CSS/TS/TSX/JSXについてhex件数がファイル単位で増えると失敗。**index.cssは対象**。新しい用途は既存tokenのaliasなのでhex増加なしにする。コメントのhexも数えるため、追加説明は製品CSSへ不要なhexを複製せず文書の対応表へ置く |
| audit:unused-tokens | workflowではcontinue-on-error:true。非ブロック。未使用の候補表示を使用済み証明と扱わない |

新用途名を足しただけでは同値を保証しない。light/darkごとに参照連鎖を解決し、置換前の実値との一致、未定義参照0、循環0を確認する。既存値と一致しない候補はこの同値便へ混載しない。

## 実行順序（実装後、既存の必須経路を使用）

1. 専用ブランチで対象差分を作成。別機能を保持。比較するmain SHAを固定して記録。
2. frontendでnpm ci後、npm run check:all、npx tsc --noEmit、npm run test:coverage、npm run build、npm run build-storybookを実行し結果を保存。既に同じ変更に対して成功済みなら重複実行不要。check:allにはcss-colors/dark-parity/css-values/color-token-syncを含む。
3. 実装コミット後、git rev-parse --verify origin/mainとgit diff origin/main...HEAD -- frontend/src/index.css frontend/src/tokens.cssで比較参照・対象差分を確認。
4. 成功した検証と用途別同値表に基づき本文の4項目をチェックする。PR本文は一時ファイルから--body-fileで設定する。本文にGOを創作しない。
5. check-new-tokensをローカルでCI相当として確認する場合は、frontend cwd、GITHUB_BASE_REF=main、GITHUB_HEAD_REF=実ブランチ、PR_BODY=本文ファイルの**実改行を保持した全文**を環境として渡す。Python等のsubprocess.run(...,env=...)で読み込めばshell展開を避けられる。出力に対象宣言列挙とチェックリスト確認を求める。単にexit0だけを合格証拠にしない。
6. ラチェットはBASE_SHA=記録した比較元、HEAD_SHA=実装commitで実行。commit前の作業treeを検査したとは言わない。
7. PRの実Frontend Checkを確認。frontend-check.ymlはfrontend/**のPRでNode22、npm ci、check:all、tsc、新token本文検査、coverage、Storybookを実行する。新token本文はgithub.event.pull_request.bodyから取得される。本文修正だけで自動再実行されるイベント指定はないので、本文を完成させてPR提出し、対象runに渡った本文と結果を確認する。既存の他required checkも通す。現行Ruleset必須集合は今回API再取得していない。

## 本ターンの検証と限界

固定4734fe7fのcheck-new-tokens本体をメモリ内VMに読み、git diffだけを1宣言追加の固定文字列に置換して本文判定を直接実行した（製品ファイルを書換えず、git参照の正常性試験でもない）。

```text
all4 exit 0
unchecked exit 1
indented exit 1
no-section exit 1
```

all4は4項目行頭-x形式、uncheckedは色の1項目だけ未チェック、indentedは2空白インデント、no-sectionは空本文。これは本文形式の実測。今回のalias実装・Node22・ビルド・実GitHub CIの結果ではない。
