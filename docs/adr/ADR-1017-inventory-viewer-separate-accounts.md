# ADR-1017: 在庫の閲覧専用ページは、アプリと交わらない閲覧専用アカウントで開く

| 項目 | 内容 |
|------|------|
| ステータス | Proposed |
| 備考 | 草案。PO の決定済み：閲覧者はアプリのユーザーにしない（2026-10-15 Y）。列は今の GAS と同じ13列（2026-10-15 y）。ログインはメールのリンクで行い、登録フォームの情報で管理する（2026-10-15）。残りの決定待ちは設計書の §PO 決定待ちに書いてある |
| 起案日 | 2026-10-15 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1014（在庫の行の定義は1か所）、ADR-1008（取引先・顧客の正本。申込の email は取引先に写さず、本契約の便で参照列でつなぐ）、ADR-1013（自社ログイン。本 ADR は、その表と鍵を閲覧者に流用しない）、ADR-144・ADR-067（金型とデザイントークン）、ADR-027（i18n） |

---

## What（何を決めたか）

1. GAS の在庫一覧に代わる閲覧ページを、app.salesanchor.jp/viewer/ に置く。
2. 閲覧者はアプリのユーザー（public.users）にしない。閲覧者は新しい表 public.viewer_accounts に置き、テナントは持たせない。
3. 閲覧者のトークンは、アプリのトークンと次の点で分ける。
   - iss："salesanchor-viewer"
   - 署名鍵：AUTH_VIEWER_JWT_SECRET
   - sub："viewer:<id>"
   - Redis：`jwt:` の名前空間を使わない
4. この結果、既存の get_current_user は閲覧者のトークンを受け付けない。逆に、閲覧者用の get_current_viewer はアプリのトークンを受け付けない。
5. 閲覧者が呼べる入口は、VIEWER_ROUTE_ALLOWLIST の6本だけにする（signup・verify-email・login・session・logout・inventory）。
6. 6本以外のすべての入口が閲覧者のトークンを拒否することを、全ルートを列挙するテストで固定する。
7. 在庫のデータは、1分に1回だけ、run_distribution（GAS への配信）と共通の build_distribution_rows（安全装置 #8・#8b、設定の読み込み、fetch_output_rows＝ADR-1014 の1か所の定義、の順）を通して作り、Redis に置いて全員に配る。GAS に配信される行と同じものを作る。DB の表やシートには写しを作らない。

## Why（なぜ）

- GAS は、Google の枠を読むだけで 3〜7 秒かかる。目標の「1秒以内の表示」は GAS の外でしか届かない。
- 閲覧者をアプリのユーザーにすると、在庫を見るだけの権限にしても 614 本中 74 本の入口に届き、仕入元の情報や会話本文まで見えてしまう。閲覧者を別のアカウントにすれば、届く入口は6本になる。API を後から足しても、閲覧者に漏れる経路が仕組みとして生まれない。
- 全員に同じ作り置きを配れば、閲覧者が増えても DB の負荷は増えない。

## 根拠

- docs/handoff/gas-viewer-fresh-fast/recon.md
- docs/handoff/gas-viewer-fresh-fast/security-recon.md
- docs/handoff/gas-viewer-fresh-fast/design.md（審査は r1〜r5 が Fable、r6 から Opus。r5 APPROVE の後に PO 決定を反映した版を r6 で REVISE。r7 で再審査する。最新の判定は design.md 冒頭の「審査」欄を正とする）
