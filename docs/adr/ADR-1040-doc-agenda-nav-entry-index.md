# ADR-1040: AI 向け指示文書を「入口→目次→章→末端」に組み替え、本文の正本を AGENTS.md に置く

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（2026-10-24。採用の根拠: PO 承認「1」2026-10-23＝段3c に進み決まりも正式にする。入口の入れ替えはこの PR） |
| 備考 | 設計は審査10回目 APPROVE・PR #4649 で保存済み。KGI と構造は PO 承認済み（2026-10-22 原文「1」）。入口の上限は PO 回答「1」＝90行。各段の実装は段ごとに PO の実装承認を受ける（本 ADR の起案は実装開始の承認を兼ねない）。段3c（入口の入れ替え）の前に PO の承認で Accepted に上げる |
| 起案日 | 2026-10-22 |
| 方針の決定者 | Shingo（PO）。設計: Claude Opus |
| 一部改訂 | ADR-076（docs/adr/ADR-076-claude-md-hierarchy.md）の §1 サイズ上限のルート行と §2「ファイル名は必ず CLAUDE.md」。本 ADR が Accepted になったときに効く |
| 関連 | ADR-076（CLAUDE.md 階層）、ADR-113（設計持ち込みの様式）、ADR-012（What/How 分離） |
| 設計 | docs/handoff/doc-agenda-nav/design.md・recon.md、親仕様書 docs/specs/doc-agenda-nav/README.md・kgi.md |

---

## Context（なぜ必要か）

- PO の言葉（2026-10-22）: 「マニュアルのようにアジェンダがあり、章ごとに分類されていて指定の手順書や作業方法などは再分類された末端ページに辿り着くまで読めない仕様にすれば無駄な情報がなくなり、精度も向上する」。
- 今、会話の始まりに自動で入る指示は 313行・12,992字（design §2 KGI-1）。ルートの CLAUDE.md は 120行、AGENTS.md は 281行で、同じ決まりが2ファイル以上に本文として書かれている（recon §2-4 の9語すべて）。
- 目次から辿れない仕様書が docs/specs に 17本、docs/ai-agents に 19本ある（docs/handoff/doc-agenda-nav/unreachable-list.md §1）。
- Claude Code は CLAUDE.md を読み、`@パス` で別ファイルを取り込む。Codex は AGENTS.md を読む。PO は Codex を今も使っている（design §10-3、PO 原文「2,どのAIを使っても指示が届くように指示をＳＳＯＴしている」）。

## ADR-076 との衝突点

1. ADR-076:55（本 ADR で「一部改訂」の1行を足す前の行番号。足した後は :56）は「上限が小さすぎると具体例が削除され AI の判断精度が低下する」を理由にルートの上限を 120行のまま据え置いた。本 ADR は入口の上限を 90行（AGENTS.md 80・CLAUDE.md 10）に下げる。具体例は削らず、目次の先の末端ページへ移す（写しは作らない）。
2. ADR-076 §2 と frontend/scripts/check-claude-size.js:58 は「ファイル名は必ず CLAUDE.md」とする。本 ADR は本文の正本を AGENTS.md に置き、CLAUDE.md は `@AGENTS.md` の1行と Claude 固有の数行だけにする。CLAUDE.md が自動で読まれる点は変わらない。
3. .github/workflows/check-claude-size.yml:23 の変更判定パス `'**/CLAUDE.md'` はルートの CLAUDE.md に一致せず、ルートの CLAUDE.md は今も行数検査されていない（既存の穴。design §8 段2a で直す）。

## Decision（何を決めたか）

1. 入口は AGENTS.md（全 AI 共通の正本）と CLAUDE.md（`@AGENTS.md`＋Claude 固有）の2本。合計の上限は 90行で、check-claude-size.js の LIMITS に AGENTS.md 80・CLAUDE.md 10 として登録する（ファイルごとの判定の和で合計も守る）。
2. 入口に残すのは前提と安全の決まり（不可逆操作の PO 確認・VPS 鍵の制限・main/develop への直接コミットと直 push の禁止）と、目次へのリンク1本。安全の決まりは入口から移さない（design KGI-7）。
3. 目次 docs/INDEX.md を新設し、章ごとに「いつ読むか」を1行付ける。作業の手順は目次→章→末端ページと辿って読む（入口→目次→章→末端の3段以内。末端は各テーマの表紙）。
4. 文書を移すとき、元の場所には目次へのリンクだけを残し、写しは作らない。
5. 目次から届かない文書を数える CI を新設し、警告から始めて、連続5回の PR で0件になったら失敗に上げる。必須チェックへの登録は別に PO 確認をとる。
6. 商品マスタ登録ルールを差し込むフックの条件は「マスタ」と「登録」が同じ文に近く出たときだけにする（design §8 段1）。
7. 実装は 1段＝1PR で、変える→反映を確かめる→測る→次へ、の順に進める（段の一覧は design §8・§20）。

## Why（なぜこの形か）

- 本文の正本を AGENTS.md にすると、Claude（取り込み）と Codex（直接読む）の両方に同じ1か所の文が届く。CLAUDE.md を正本にして AGENTS.md を `@CLAUDE.md` にする案は、Codex が `@` を展開しない前提では Codex に本文が届かないので採らない（design §7）。
- 取り込みは文脈を減らさない（取り込んだ分も読まれる）ため、行数を減らす手段は「末端へ移して目次から辿る」しかない（design §5）。
- 90行は、ユーザー側を含めた会話開始時の合計を 200行以下にする予算配分として決めた。90行を直接示す外部の一次資料は無い（design §14-4）。入口の案文は実際に書いて 54行（45・9）で収まる（design §5-2）。

## Consequences（結果）

- ADR-076 の §1 ルート行（120行）と §2 の命名の決まりは、本 ADR が Accepted になった時点で本 ADR の Decision 1・2 に置き換わる。frontend・backend の CLAUDE.md の上限と階層の決まりは ADR-076 のまま。
- check-claude-size.js のエラー文（「ファイル名は必ず CLAUDE.md」）と LIMITS は段3c で本 ADR に合わせて直す。
- 手順を読むのに1〜3回ファイルを開く手間が増える。開いた割合は design KGI-10 で記録する。
- 戻し方: 各段の PR を revert する（design §8 の戻し方の列）。

## 強制の仕組み

| 仕組み | 担当 | 効果 |
|---|---|---|
| 行数検査 CI | .github/workflows/check-claude-size.yml・frontend/scripts/check-claude-size.js | 入口が上限を超えたら失敗（段2a・段3c で対象と上限を直す） |
| 到達検査 CI | 段2で新設 | 目次から届かない文書を数える |
| 設計持ち込みの検査 | .github/workflows/process-artifacts-gate.yml | PR に recon・design・対象 ADR の記載を求める |
