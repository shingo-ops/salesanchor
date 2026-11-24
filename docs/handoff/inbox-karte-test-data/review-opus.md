# Opus 審査: 住所から開いたときのカルテの最初のタブ

- 審査日: 2026-11-24（Opus・同じ AI による設計と審査。独立した第二者レビューではない）
- 対象: commit 4f91faeb2（クラウド Sonnet の実装）と、設計 `docs/handoff/inbox-karte-test-data/design.md`・カード `docs/handoff/inbox-karte-test-data/card.md`
- 判定: **APPROVE**

## 1. 設計の審査

- 期待値の正本: `docs/adr/ADR-1089-inbox-karte-stage-layout.md`（成約後は顧客タブから開く）。段階の並びは `frontend/src/pages/inbox/karteLayout.ts` の 1 か所のまま（新しい段階の一覧を書かない）
- 原因は本番の観測（953 が商談で開く）とコードの行（recon.md §2）で一致。未確認なし
- 受入条件 U1〜U5 は試験とファイル一覧で ○× が付けられる

## 2. 実装の照合（カード §1 との一致）

- `frontend/src/pages/inbox/useInboxState.ts`: 足したのはカードの 3 か所だけ（印の useRef・selectLead での印下ろし・カルテ到着時の 1 回だけの効果）。文字どおり一致
- 新しい試験 `frontend/src/pages/inbox/useInboxState.karteTabFromUrl.test.tsx`: カード §2 の 4 本（existing_customer→company、follow_up_short→company、lead/negotiating→deal、選んだタブが戻されない）。題は英語（lint の決まり）
- 触ったのは 2 ファイルと `docs/handoff/inbox-karte-test-data/`・台帳 1 行だけ（`git diff origin/main --name-only`）

## 3. クラウドの確かめの結果（クラウドの報告。手元では流していない）

- vitest（unit）: 11 ファイル・74 本が緑
- eslint: 0 件
- tsc: 4 件。すべて触っていないファイル（`api/generated/schema` が無い 2 件、`SoldOutResultsPanel.tsx` の暗黙 any 2 件）。受信箱の件は 0 件。最終判定は CI「Lint & Dark Mode Check」で行う

## 4. 残り

- CI 緑と、マージ前の審査役（reviewer・opus）の APPROVE
- 本番反映のあと、テナント001の 951・952・953 で最初のタブを確かめ直す（U1・U2）
