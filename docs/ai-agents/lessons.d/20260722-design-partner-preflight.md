# 設計パートナーの推測混入と、手元関所による是正（2026-07-22）

## 事象

reaper 配線修正（K1）の1セッション中に、設計パートナーが「実測せず断定した」ことに起因する手戻りが 7 件発生した。

1. PR の base を develop と断定（正本 STANDARD-WORKFLOW.md の記述を確認せず踏襲）→ 608ファイル・約3万行の巨大混入PR #3041 を作成、クローズ
2. 「既存赤を抱えたままマージするのが常態」と断定 → 実測では #3040/#3039/#3038 はいずれも pass でマージされており、事実に反していた
3. Frontend の赤を「main 全体を見るゲート」と推測 → 実際は GITHUB_BASE_REF=develop の旧 run の残骸
4. 「reaper 運用は branch-operations に寄っている」と実装役の要約を鵜呑み → 実物では当該配下の reaper 言及 0 件
5. recon/design を docs/specs 配下に作成 → 関所 check-process-artifacts.js:196 は `docs/handoff/` をハードコード要求しており形式違反
6. 手元関所の環境変数を PR_BODY と誤記（正しくは MOCK_PR_BODY）→ 空本文を検査し、無効な判定を根拠にしかけた
7. 完了報告時に、本題（K1未完）を到達点の一覧から落とした

## 根本原因

着手前に、その工程が要求する仕様（正本の記述・関所の実コード・文書の中身）を実物で読まずに設計した。
セッションを跨いだ学習は成立しないため、「次から気をつける」は対策にならない。

## 有効だった対策（実測済み）

関所 scripts/check-process-artifacts.js は手元で単体実行できる。

    MOCK_PR_BODY="<PR本文>" BASE_SHA="$(git rev-parse origin/main)" HEAD_SHA="$(git rev-parse HEAD)" \
      PR_NUMBER=0 REPO=shingo-ops/salesanchor node scripts/check-process-artifacts.js

- 実行時間 0.389 秒（2026-07-22 実測）
- 手元の判定文言と CI の判定文言が一字一句一致することを実測（PR #3043・同一の ❌ 2行）
- 本カード方式で push 前に走らせた結果、PR #3043 は手元 exit=0 → CI pass となり、CI 往復が発生しなかった

## 採るべき運用

危険操作を含むカードには、push・PR作成の前に上記の手元関所実行を必須手順として組み込み、exit=1 なら停止して生出力を報告する（自力修正禁止）。
設計パートナーが関所の要求仕様を記憶している必要はなくなる（機械が手前で判定するため）。

## 未確立（正直な明記）

pre-push 等による機械強制は未実装。理由は 2 点の実測事実による。
- core.hooksPath が frontend/.husky を指しており、.git/hooks への設置は無効
- 過去に「フックが警告を出したが実行は完了した＝阻止力なし」が実測されている（EV-20260703-003）
機械強制を設計する場合は、違反PRで実際にブロックされることの実測を合格条件に含めること。
