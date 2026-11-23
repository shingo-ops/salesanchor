# recon — ブラウザ操作の Opus への委任

**この文書は何か（専門用語なしの1行）**: 「画面操作を AI に任せる」前に、今の決まりと仕組みがどうなっているかを、ファイルの行で確かめた記録。

親: [../../specs/browser-operation-delegation/README.md](../../specs/browser-operation-delegation/README.md) ／ 設計: [design.md](design.md) ／ 決定: [../../adr/ADR-1085-browser-operation-delegation.md](../../adr/ADR-1085-browser-operation-delegation.md)

- 調べた日: 2026-11-22（JST）
- 基準: `origin/main` 2560f963f から作った作業場所 `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation`
- 生の出力: `/tmp/CC報告ファイル/browser-deleg-adrgrep.txt`（決まりの検索 19 行）、`/tmp/CC報告ファイル/browser-deleg-preflight.txt`

---

## R1. 既存 ADR の検索

- 実行: `git grep -n -i -E "外部 ?GUI|ブラウザ操作|画面操作|claude.in.chrome|人の動作確認|人が実際に動作確認" -- docs/adr AGENTS.md docs/STANDARD-WORKFLOW.md docs/ai-agents docs/specs/README.md`（19 行）
- 該当 ADR: ADR-042（Evaluator の Layer 2 = Claude in Chrome）、ADR-055（Playwright の設定。Layer 2 は別途）、ADR-1003（GO 委任の例外に外部 GUI）、ADR-1011（自律保守の対象外に外部 GUI）、ADR-1033（同意票）。ADR-046〜051 は Evaluator 欄の「Layer 2 不要」の記載のみ。
- `docs/specs/README.md` に、ブラウザ操作の委任を扱うテーマは無い（「委任|権限|GO|agent」で検索した該当は ai-ops-247・go-record-transcription・auth-roles・secrets-permission-ssot・process-hardening で、どれも画面操作の線引きを扱わない）。→ STANDARD-WORKFLOW.md §1.8 の「新規テーマ」。

## R2. 今の決まり（止めている箇所）

| # | 場所 | 中身（要約） |
|---|---|---|
| R2-1 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/AGENTS.md:17` | 「不可逆操作は必ず PO 確認」の列に「Cloudflare・Firebase等の外部GUI操作」 |
| R2-2 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/STANDARD-WORKFLOW.md:145` | PO 本人の GO が必須の例外に「外部 GUI 操作」 |
| R2-3 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/adr/ADR-1003-go-delegation-to-opus.md:40` | GO 委任の例外「外部 GUI（Cloudflare・Firebase 等）の操作」 |
| R2-4 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/adr/ADR-1003-go-delegation-to-opus.md:45` と `:79` | 外部 GUI 操作は機械で見ていない。手順（人手）で守る |
| R2-5 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/STANDARD-WORKFLOW.md:95` | 完了の定義 4「人が実際に動作確認を行い」 |
| R2-6 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/STANDARD-WORKFLOW.md:98` | 確かめの場所は本番の tenant_001。tenant_004 には触れない。tenant_006 は Meta 審査の撮影専用 |
| R2-7 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/STANDARD-WORKFLOW.md:170` | このファイルの変更は PR＋PO 承認のみ |
| R2-8 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/adr/ADR-1011-permission-self-maintenance.md:37` | 許可の自律保守の対象外に「外部 GUI に関わる許可」 |
| R2-9 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/adr/ADR-1033-conversation-consent-ticket.md:20` | 同意票で通さない操作に「見張り役そのものの設定」→ 新しい見張りの取り付けは PO の `!` 実行が要る |

## R3. 今ある仕組み（使える部品）

| # | 場所 | 事実 |
|---|---|---|
| R3-1 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/adr/ADR-042-guardrails-and-release-flow.md:134` | Evaluator の Layer 2 として Claude in Chrome が決まりに入っている |
| R3-2 | `/Users/tanizawashingo/.claude/agents/evaluator.md:41`〜`:55` | Layer 2 を使う場面（本番のログイン済みの確かめ・Meta 審査の撮影・GCP/Cloudflare/Firebase の確かめ）と注意（再現しない・同時に1つ・本番の Chrome を直接動かす・alert を出さない・壊す操作は確認） |
| R3-3 | `/Users/tanizawashingo/.claude/scripts/local-agent-guard/guard.py:100`〜`:105` | 手元で起動してよい担当は reviewer(opus) と evaluator(opus/fable)。evaluator は Chrome を使える |
| R3-4 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/handoff/conversation-consent/hooks/consent_check.py:416` | `check(hook_input, command, now, home=None)` は任意の文字列 `command` を同意票の `操作N:` と完全一致で照らす。`:461`〜`:467` の `main()` は Bash の `tool_input.command` を渡している |
| R3-5 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/scripts/dev/consent-audit.py:11` | 週次点検 `--audit [--permissions]`。ADR-1033 の維持の仕組みで毎週月曜 09:30 に動く |
| R3-6 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/handoff/conversation-consent/po-apply-consent.sh` | 見張りを PO の `!` 実行で取り付け、試験が不合格なら自動で戻す型（`docs/handoff/conversation-consent/po-rollback-consent.sh` と対） |

## R4. 今ない仕組み（穴）

- R4-1【事実】`/Users/tanizawashingo/.claude/settings.json` の hooks に、`mcp__claude-in-chrome__` に当たる matcher は無い。全体に当たる PreToolUse は 「agent-start-hook.sh」（セッション開始の記録だけ。`/Users/tanizawashingo/.claude/scripts/agent-start-hook.sh:1`〜`:30`）。Bash 向けの `local-agent-guard`（`.claude/settings.json:570`）は Agent と Bash だけ。
- R4-2【事実】作業場所の `.claude/settings.json` の PreToolUse の matcher は `SubagentHandback`・`Bash`・`Write|Edit`・`mcp__github__.*` の4つで、Chrome は無い。
- R4-3【事実】`permissions.allow/ask/deny` に chrome の語を含む行は、「~/.claude/settings.json」・作業場所の `.claude/settings.json` のどちらにも 0 行。
- → 今は、Chrome の操作を機械で止める・数える仕組みが 0 個。止めているのは R2 の文の決まりと、毎回 PO に聞く手順だけ。

## R5. 社内の実績（AI が Chrome で確かめた記録）

| # | 場所 | 事実 |
|---|---|---|
| R5-1 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/handoff/secretary-voice/results.md:4` `:15` `:16` `:74` | 2026-11-19 01 時台、PO の「1」で Opus が PO の Chrome を操作して測った。K4 短い 10/10（最長 0.839 秒）・長い 10/10（最長 0.697 秒）、K5 字数一致 30/30・494 字=494 字。スマホ側は PO が操作 |
| R5-2 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/handoff/status-ssot-contact-company/recon.md:85` と `docs/handoff/status-ssot-contact-company/design.md:203` | 2026-11-11 AI が Chrome で本番の画面の選択肢を目視。設計の受け入れ基準 K4 の検証方法が「Chrome で開いて数える（保存はしない）」 |
| R5-3 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/ai-agents/evidence-registry.md` | 「Opus…Chrome」「Claude in Chrome」の語の記録は 0 件（3,541 行を検索）。確かめの記録のひな形（`:7`〜`:20`）に「誰が確かめたか」の欄は無い。「確認者」の行は全体で 1 件だけ（`:1251` `- 確認者: Shingo`） |
| R5-4 | PO 発言（ideal-state.md） | Meta の申請前の必須項目、Google Workspace のドメイン設定と Gmail の送受信の確かめを Opus が Chrome でやり切った。【未確認】リポジトリ・メモリにこの2件の作業記録は見つからない（Workspace は 0 件、Meta は「Chrome 専用プロファイル作成」の未完了の1行のみ）。PO の言葉を正本とする |

## R6. 道具の仕様（公式の資料で確かめた）

- R6-1 Claude Code の hooks（Context7 `/websites/code_claude`、出典 https://code.claude.com/docs/en/hooks）: MCP の道具は `mcp__<server>__<tool>` の名で PreToolUse に来る。サーバー全体は `mcp__<server>__.*`（`.*` 必須）。exit 2 で呼び出しを止め、stderr が AI への説明になる。
- R6-2 Chrome の道具の入力（このセッションで道具の定義を読んで確認）: `navigate` は `url`、`computer` は `action`・`coordinate`・`text`・`action_summary`（押す・打つ操作に「何をするか」の短い文）、`form_input` は `value`・`action_summary`、`javascript_tool` は `text`（任意の JavaScript）、`file_upload` は `paths`、`browser_batch` は `actions[]`（中に上の道具の入力が並ぶ）。
- R6-3【事実】`computer` のクリックは座標だけで、押した先の URL・ボタン名は入力に無い。分かるのは AI が書く `action_summary` だけ。→ 見張りはクリック先を確実には知れない（設計 §6 の受け入れるリスク）。
- R6-4 Claude in Chrome 自身の歯止め（Anthropic のヘルプ https://support.claude.com/en/articles/12902446 と https://support.claude.com/en/articles/12902428 の検索の抜粋）: 購入・金融取引は許可に関係なく禁止。「常に許可」でも、ファイルのダウンロード・機密に当たる入力・認可の付与は毎回確認。サイトごとの許可がある。【未確認】金融サイトが「全面ブロック」か「許可制」かは、ページの版で書き方が違い、今の版を確かめられていない。設計はこの点に頼らない。

## R7. 追記（2026-11-23・PO の決定の後の確かめ）

| # | 場所 | 事実 |
|---|---|---|
| R7-1 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/backend/app/models.py:26` `:28` | 利用者は会社（tenant）1つにだけ属する（`nullable=False`）。メールは全体で1つだけ（unique） |
| R7-2 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/docs/handoff/conversation-consent/hooks/consent_check.py:348`〜`:350` `:386`〜`:396` `:407`〜`:410` | 同意で通るのは、最後の人の入力が手で打った「1」・30 分以内・`操作N:` と完全一致・台帳で1回限り |
| R7-3 | `/Users/tanizawashingo/worktrees/salesanchor/release-browser-operation-delegation/scripts/dev/consent-audit.py:319` `:902` `:921` `:1793`〜`:1798` | 同意の突き合わせは `projects/*/*.jsonl` だけ。subagents の下を読む型は `pl_load_windows` にある。Discord の語は 0 件 |
| R7-4 | 公式 https://support.google.com/a/answer/1668003 | プランの確認・変更・更新・購入に「支払いの管理」の権限が要る（検索の抜粋） |
| R7-5 | 公式 https://support.google.com/a/answer/33327 | 別名のアドレスは1人30個まで無料。ただしログインできない |
| R7-6 | https://www.softbank.jp/biz/services/collaboration/google-workspace/price/ | Business Starter 年契約 800 円・月契約 950 円（1人・月・税抜。2025-03-17 以降）。代理店の表で、PO の契約の版は未確認 |
| R7-7 | 公式 https://code.claude.com/docs/en/chrome ／ 報告 https://github.com/anthropics/claude-code/issues/19740 | 2つつながると `/chrome` で選ぶ。選ぶ画面の名は「Browser 1」等で部屋を見分けにくい（利用者の報告） |
| R7-8 | 公式 https://www.ebay.com/sellercenter/ebay-for-business/team-access ／ https://jp-news.mercari.com/mercari-shops/info/31020 | eBay はチームアクセスで権限を選んで追加（相手は自分の eBay アカウントと2段階のログインが要る）。メルカリShops はスタッフ（管理者・担当者）。普通のメルカリにメンバーの機能は見つからない |

## R8. 手元の開発環境が外へ送るか（V7・2026-11-23・Opus が手元で読んだ）

- R8-1【事実】本店の写しの直下の環境ファイルは `.env.local`（9 行・鍵の名は FedEx の2つだけ）と `*.example` だけ。`.env` は無い（`find . -maxdepth 3 -name ".env*"`）。値は表示していない。
- R8-2【事実】`.env.local` を読むコードは無い（`git grep -n "env.local"` は `.gitignore:25` だけ）。
- R8-3【事実】シェルの環境変数と `~/.zshrc`・`~/.zprofile` に、LINE・メール・Meta・WhatsApp・Google・Discord・Gemini・FedEx・DATABASE の名を含む変数は 0 件。
- R8-4【事実】Docker は止まっている（`docker info` 失敗）。5173 番で待ち受ける処理は無い（`lsof`）。
- R8-5【事実】画面は API を同じ住所の `/api/v1` へ送る（`frontend/src/lib/api.ts:32`）。`frontend/vite.config.ts:27`〜`:30` の server 設定に中継（proxy）は無い。手元の 5173 番だけでは、データの出る画面は動かない。
- R8-6【事実】手元で全部を組み立てると、入口は nginx の 80・443 番（`docker-compose.yml:11`〜`:13`）。5173 番ではない。
- R8-7【推測】今の手元の状態では、外へ送る鍵が無いので外へは送れない。同じ理由で、データの出る画面の確かめも手元ではできない。

## R9. 道具の返事に今の住所が出るか（V5・2026-11-23・Opus が新しいタブで読むだけの操作で測った）

- R9-1【事実】`navigate` で `http://github.com/` を開いた返事は「Navigated to http://github.com/」と、渡した住所のまま（タブの欄も `http://github.com/`）。実際は `https://github.com/` に移っていた。→ `navigate` の返事の住所は信じられない。
- R9-2【事実】直後の `computer` の screenshot の返事の末尾に「Tab Context: - Executed on tabId: 1165664195 … "GitHub" ("https://github.com/")」と、移った後の住所が出た。`tabs_context_mcp` の返事も `"url":"https://github.com/"`。
- R9-3【事実】直後の `read_page` は「Can't interact with browser-internal or unparseable URLs」で失敗した（読み込み途中）。
- R9-4【事実】公式の説明（Context7 `/websites/code_claude`・hooks「PostToolUse input」）: `tool_response` は道具が返した結果そのもの。MCP の道具では文字列か内容の塊の並び。
- R9-5【未確認】見張りが受け取る `tool_response` に「Tab Context」の文が実際に入るか。会話記録を Bash で読むのは見張りで止められた（言い換えはしていない）。便1の取り付け直後の自己試験で、実物の `tool_response` を記録して確かめる。
- R9-6【事実】「Tab Context」の文は決まった形の項目ではなく、説明の文。形が変わると読めなくなる。
- R9-7【事実】同じ測りで、`tabs_context_mcp` の返事は2つの塊だった。1つ目は JSON（`{"availableTabs":[{"tabId":…,"title":"GitHub","url":"https://github.com/"}],…}`）、2つ目は「Tab Context:」で始まる文。道具の定義の入力は `createIfEmpty` だけで、`tabId` は渡せない。
