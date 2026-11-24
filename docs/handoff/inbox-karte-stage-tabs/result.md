# 結果: 受信箱のカルテを段階で出し分け（ADR-1089）

- 設計: `docs/handoff/inbox-karte-stage-tabs/design.md`
- 決定: `docs/adr/ADR-1089-inbox-karte-stage-layout.md`

## 状態

| 項目 | 状態 | 根拠 |
|---|---|---|
| 実装 | 済 | クラウドの Sonnet（commit c1dadf231）・基準画像の作り直し（commit d6f8e343b） |
| 審査 | APPROVE | reviewer（opus）`VERDICT: APPROVE on dbb8031b8372c904ff05c7ca8c7265d39fa778db PR #5721` |
| CI | 全部緑 | マージ直前（2026-11-24 13:37 JST ごろ）の `gh pr checks 5721`: pass 60・skipping 10・fail 0・pending 0。マージ後に取り直すと流し直しの分が足され pass 63・skipping 11・fail 0（同じ名前の重なりを除くと pass 61・skipping 11）。どちらも fail 0 |
| GO | 委任の GO | PR #5721 本文の「### GO記録」（ADR-1003） |
| main へ合流 | 済 | 2026-11-24 13:38 JST・merge commit d48aeb8a2 |
| 本番反映 | 済 | Deploy to VPS run 45327835795・success・2026-11-24 13:44 JST |

## 本番で見たこと（Opus が Chrome で観測・2026-11-24 13:45 ごろ）

- 成約後の顧客（既存顧客の会話）を開くと、カルテのタブは「顧客・連絡先・商談」の順で、顧客タブで開いた。前の版の並び（商談・顧客・連絡先）から変わっていることで、新しい版が届いていると判断した。
- 顧客タブの項目は、呼び名・国・顧客タイプ・取り扱いタイトル・販売形態・次回アクション・実績・CS メモで、`frontend/src/pages/inbox/karteLayout.ts` の CUSTOMER_LAYOUT と一致した。

## 本番でまだ見ていないこと

- リードと商談中の会話の本番の画面。画面を押す操作は Chrome の見張りで PO の同意が要るため、押していない。
  - 代わりの根拠: CI の Karte Visual Gate（karte-gate-run）が、リード・商談中・成約後の資料で「出る／出ない」と基準画像を確かめて pass。
- 成約後の段階のうち、本番で開いたのは既存顧客の会話1件だけ。追い込み（短期・長期）の会話は本番で見ていない（CI の Karte Visual Gate は追い込み（短期）の資料で確かめて pass）。
- 失注の会話の e2e 試験は無い（表に無い段階は今の見せ方のまま。部品の試験 `frontend/src/pages/inbox/karteLayout.test.ts` だけで確かめている）。

## PO に聞くこと

- 失注・対象外の段階の見せ方は、今のまま（ADR-1089 What 3）。変えたいかは PO の判断。
