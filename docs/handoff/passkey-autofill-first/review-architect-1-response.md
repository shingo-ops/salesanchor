# 審査1（REVISE）への直し — Opus（2026-11-24）

審査1の本文は枝 release/passkey-autofill-review1 の review-architect-1.md（4394474cd）。指摘の根拠は手元でも確かめた（main.tsx:16 StrictMode・LoginPage.tsx:44/48/49 の loading・enrolling・promptOpen・authErrorMessage.ts:36・cloud/rules.md:15 の merge 禁止・package.json:28/45・auth.py:1134-1140）。

| 番号 | どこを直したか |
|---|---|
| R1 | design.md §4-1-3 `startPasskeyAutofill(isStale)` と2か所の確認。§4-2-2 を世代の番号（genRef）に。card §3-1・§3-2・T3・T12 |
| R2 | design.md §4-2-2 の条件に `!enrolling && !promptOpen && !loading`。§4-2-3 に busyRef と reject しない waitRef の型。§4-2-5 は `!loading` で1回始め直る形に。§4-3 書き直し。card §3-2・T11 |
| R3 | design.md §4-2-2 の始め直しを (a) タイマー (b) visibilitychange に。§6 に「隠れたタブで札切れ」「StrictMode の古い待ち受け」の2行。card §3-2・T10 |
| R4 | card 手順0 に preflight。手順2 を `git checkout <枝> -- <docs>` に。手順5 に check:i18n-missing-keys・check:error-text-next-action・check:jsx-emoji。手順7 を明示の git add に。手順8 を `commit -F` に |
| R5 | card §3-3 に T9〜T12。design.md §7 の試験行・§8 の守り手を T4〜T12 に |
| R6 | design.md §7 P1 に登録件数の前提と「判定不能」。P2・P3 に Chrome の版と `immediateGet` の記録。P7 を命令の形に（i18n の検査が CI 必須かは未確認と明記） |
| L4 | design.md §4-1-3 に `o.extensions` を渡す1行 |
| L5 | design.md §4-2-3 に state `immediateOk` の初期値 false |

直していない軽い指摘: L1（行番号のずれ・カードの「行番号は目印」で足りる）、L6（今の signInWithPasskey と同じ扱い・悪化なし）、L9（完了報告は Opus の作業）。
