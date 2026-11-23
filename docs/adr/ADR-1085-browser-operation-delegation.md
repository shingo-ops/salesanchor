# ADR-1085: しんごさんの Chrome の画面操作を区分つきで Opus に任せる

| 項目 | 内容 |
|------|------|
| ステータス | Draft |
| 備考 | PO 承認待ち。移り方は design.md §8。PO 2026-11-22「claude in chromeを積極的に使用してあなたが画面操作を行って私の代わりに作業をすることを許可して権限委譲させたい」「決済などに関わる重要なものは私が行う必要があり」（全文は ideal-state.md） |
| 起案日 | 2026-11-22 |
| 方針の決定者 | Shingo（PO） |
| 関連 | [ADR-042](ADR-042-guardrails-and-release-flow.md)（Evaluator Layer 2）、[ADR-1003](ADR-1003-go-delegation-to-opus.md)（GO 委任・外部 GUI の例外を一部置き換える）、[ADR-1033](ADR-1033-conversation-consent-ticket.md)（同意票を区分2で使う）。設計: `docs/handoff/browser-operation-delegation/design.md`・仕様: `docs/specs/browser-operation-delegation/` |

---

## What（何を決めたか）

1. Opus は Claude in Chrome で、2つの部屋 × 3つの区分の通りに画面を操作する（詳細は design.md §4。区分の正本は `docs/handoff/browser-operation-delegation/hooks/tiers.json` の1か所）。
   - 部屋 A（Opus 専用の Chrome のプロフィール＋各サービスの Opus 専用の利用者。支払い・請求・契約の権限を付けない）: メンバーを追加できるサービス（Google Workspace・Cloudflare・自社アプリの tenant_001 だけの利用者）。支払い・プラン・請求はサービス自身が断る（それ以外の区分3は見張りで止める）。部屋 A は後の便で設計し、最初の見張りは部屋 P だけ。
   - 部屋 P（PO の普段のログイン）: メンバーを追加できないサービス等。読む以外の操作は1操作ずつ同意票＋PO の「1」の後だけ。押した先が支払いでないかは Opus の判断に頼る部分が残る（PO 2026-11-22 選択肢2）。例外として、自社アプリの試しの画面（手元の開発用の住所だけ）では押す操作も PO の「1」なしで行う（PO 2026-11-23「1」）。
   - 区分3（PO 本人だけ・両方の部屋）: 支払い・契約・プラン・請求、パスワードと2段階認証、鍵の発行と表示、アカウントとデータの削除、本人確認の書類、お金や契約が伴う規約への同意。それ以外の規約への同意は区分2（同意の中身を Opus が読み上げてから PO の「1」。PO 2026-11-23「2」）。
   - evaluator は区分1だけ（同意票を使えないため）。見張りが部屋を見分けられるまでは全部を部屋 P として扱う。
2. 区分は PreToolUse の見張り `chrome-op-guard`（matcher `mcp__claude-in-chrome__.*`）が機械で守り、全呼び出しを記録する。見張りが壊れたときは止める。
3. 次の文を、この ADR が Proposed になり、見張りの取り付けの試験（design §7 T16）が合格した後の便2で書き換える: `AGENTS.md:17` と `docs/STANDARD-WORKFLOW.md:145` の「外部 GUI 操作」を「区分3と、ADR-1085 の見張りの外の外部 GUI 操作」へ。`docs/STANDARD-WORKFLOW.md:95` の「人が実際に動作確認」を「人、または Opus が Claude in Chrome で行い記録を残す（スマホの実機は人）」へ。`ADR-1003:40` に本 ADR への参照を足す。
4. 週次点検（ADR-1033 の月曜 09:30）に「画面操作」の節を足し、区分3が通った件数・区分2と同意の不一致・記録漏れを数える。

## Why（なぜ）

- PO の発言では、Meta の申請前の項目・Google Workspace の設定と Gmail の確かめを Opus に Chrome で任せてやり切れた（作業の記録はリポジトリに無い。recon R5-4）。社内の記録でも 2026-11-19 に Opus が PO の Chrome で 20/20・30/30 を数えて合格した（`docs/handoff/secretary-voice/results.md:15`〜`:16`）。
- 今は外部 GUI 操作を機械で見ていない（ADR-1003:45・:79、recon R4）。任せるなら、止める・数える仕組みを先に入れる。
- 画面の文で AI が操られる攻撃は、Anthropic の公表で、標準の攻撃の組で約1%（S2）、別のプロの攻撃の組で 16.7%（S2b）残る（組が違い一続きの幅ではない）。クリックの行き先を見張りは知れない（recon R6-3）。だから支払い等は、できる所ではサービスの権限で断らせ（部屋 A）、できない所では読む以外を1操作ずつ PO の「1」にする（部屋 P）。
- 他社の失敗（Replit の本番 DB 消去、Comet の乗っ取り、Operator の無断購入【一次の記事は未読】、Antigravity の確認飛ばし【一次の投稿は未読】）は、どれも「本番と試しの分け無し」「画面の文を指示扱い」「確認の飛ばし」が原因（design.md §10）。区分と見張りはそれぞれに当てている。

## 受け入れるリスク

- 部屋 P で、Opus が同意票の文と違うボタンを押す場合は機械で止まらない（design.md §6 リスク1。PO が 2026-11-22 選択肢2で承知し、2026-11-23「1」で受け入れを確かめた）。

## 戻し方

`po-rollback-chrome-guard.sh` で見張りを外し、文の決まりを本 ADR 以前に戻す PR を出す。
