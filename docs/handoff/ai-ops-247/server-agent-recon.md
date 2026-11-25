# 保守運用の担当をサーバーに常駐させる件 — 現在地（recon）

- 状態: 調べ終わり（2026-11-25 18:15 JST 時点の実測）
- 親: ADR-1012（AI 保守運用 24 時間化）・`docs/handoff/ai-ops-247/stage4-design.md`
- PO の依頼（2026-11-25・原文）: 「保守運用だがprod2の監視サーバーにubuntuを構築してclaude codeを入れておくことは出来る？保守運用専用のエージェントをサーバー上に入れておいて、Agent consoleじゃなくてdisocord上で私とキャッチボールが出来るように出来るとPCの負荷を下げられるし、スマホでも確認して指示を投げることが出来ると間がている」→ 設計担当の4つの確かめの提案に PO「1」（正式に設計する。まず4つを測る）。
- 調べた人: Opus（設計担当）。本番は読むだけ（下の F1 は `free -m` などの表示だけ）。

## 1. 既存 ADR の検索

- `git grep -n -i -E "prod2|監視 ?VPS|channels|Discord|常駐" -- docs/adr/` で関係するものを拾い、次を読んだ。
  - `docs/adr/ADR-1012-ai-ops-247.md:20` routines はサブスクの枠から引かれる。
  - `docs/adr/ADR-1012-ai-ops-247.md:42` 監視からの常時起動が「ordinary, individual usage」に入るかは公式に明言なし。段階4 の前に PO 判断を仰ぐ（未決のまま）。
  - `docs/adr/ADR-1012-ai-ops-247.md:43` 代わりの候補は GitHub Actions の claude-code-action（案 D）。
  - `docs/adr/ADR-1009-discord-ops-intake.md`（予備 C: Mac 上の Discord 受付）・`docs/adr/ADR-1039-discord-pdca-agent-console.md`（Discord の不具合報告を agent-console で受ける件）。
  - `docs/adr/ADR-080-monitoring-vps-separation.md`・`docs/adr/ADR-081-monitoring-vps-final-operational-design.md`（監視 VPS）。
- この依頼と食い違う決定は見つからなかった。サーバーに Claude Code を常駐させる決定・却下の記録も無い。

## 2. 観測した事実

| # | 事実 | 根拠 |
|---|---|---|
| F1 | prod2 のメモリは全部で 3,915MB。使えるのは 2,546MB。スワップは 0。CPU は 4 個。ディスクは 158GB 空き。動いているのは監視の 11 個のコンテナ（最大は grafana 153.5MiB） | 2026-11-25 09:15:15Z に prod2 で `free -m`・`nproc`・`df -h /`・`docker stats --no-stream`（Mac の手元の記録 /tmp/CC報告ファイル/workresv/prod2-mem.txt） |
| F2 | 9 月 29 日の prod2 は Ubuntu 24.04.4・使えるメモリ 2,581MB | `docs/handoff/gemini-egress-via-prod2/recon.md:54` |
| F3 | prod2 には prod1 へ常時つなぐ autossh の仕組み（monitoring-tunnel.service）がある。つなぐための認証の置き場は確かめていない（sudo にパスワードが要り読めない・同じ表の :53） | `docs/handoff/gemini-egress-via-prod2/recon.md:47` |
| F4 | Claude Code の公式の動く条件: Ubuntu 20.04 以上・メモリ 4GB 以上 | https://code.claude.com/docs/en/setup「System requirements」（Context7 で 2026-11-25 に取得） |
| F5 | Discord の公式の道具（discord@claude-plugins-official）がある。`claude --channels plugin:discord@claude-plugins-official` で起動する。channels は研究プレビュー | https://code.claude.com/docs/en/channels・https://code.claude.com/docs/en/cli-reference（Context7 で 2026-11-25 に取得） |
| F6 | 公式の Discord の道具は、ボットの投稿を読まずに捨てる（`if (msg.author.bot) return`） | 0.0.4 では server.ts:806（`docs/adr/ADR-1009-discord-ops-intake.md:16`）。今の 0.0.6 では 912 行目（Mac の手元の写し ~/.claude/plugins/marketplaces/claude-plugins-official/external_plugins/discord/server.ts・2026-11-25 に grep・リポジトリの外） |
| F7 | 自前で手直しした道具は `--dangerously-load-development-channels` が要る。対話の画面で確認が出る。`-p` では無視される | https://code.claude.com/docs/en/channels-reference（Context7 で 2026-11-25 に取得） |
| F8 | サブスクのログインは「ordinary use」向け。Pro・Max の上限は「ordinary, individual usage」を前提にしている。製品やサービスを作る人は API の鍵を使う | https://code.claude.com/docs/en/legal-and-compliance（Context7 で 2026-11-25 に取得） |
| F9 | Remote Control: 自分の機械で動く Claude Code を、スマホの Claude アプリから操作できる。機械と claude の処理は動いたままにしておく必要がある | https://code.claude.com/docs/en/remote-control（Context7 で 2026-11-25 に取得） |
| F10 | Mac の手元の Claude Code（2.1.332）は、長く使った会話 1 つで 482MB を使っていた | 2026-11-25 に `ps -axo rss,command`（/tmp/CC報告ファイル/workresv/claude-rss.txt） |
| F11 | 段階4 では、異常の知らせを受けて AI を起こすのはサーバー側（クラウドの routines）。Discord を通さない | `docs/handoff/ai-ops-247/stage4-design.md:80-95`（U1 の選んだ案）・`docs/handoff/ai-ops-247/stage4-requirements.md:112`（R4） |
| F12 | channels はログインのしかたとして claude.ai のログインと Console の API の鍵の両方に対応する（Bedrock などは対象外） | https://code.claude.com/docs/en/channels 冒頭（Context7 で 2026-11-25 に取得） |

## 3. 未確認（設計では前提にしない。試しで確かめる）

- U-a: 公式の Discord の道具で起動した Claude Code が、サーバーの再起動のあと人の操作なしで立ち上がり直せるか（初回の信頼の画面などが出るか）。
- U-b: Linux で 24 時間動かしたときのメモリの増え方（F10 は Mac の 1 回の値）。
- U-c: 24 時間の常駐がサブスクの「ordinary, individual usage」に入るか（公式に明言なし。F8・ADR-1012:42）。
- U-d: さくらの VPS の今の月額。調べた資料は時期がばらばら（石狩 4G は 3,227〜3,520 円/月、大阪 4G は 3,740 円/月と書く資料がある）。公式の料金ページで確かめていない。
