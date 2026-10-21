# ADR-1025: 解析の誤り報告から自律修正まで — 報告は本番の表 1 か所、起動は agent-console が Discord の 1 チャンネルを読む

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（設計のみ。実装・本番反映は未着手。区分は ADR-1015 の A。migrations を含む便は ADR-136 の GO 手順が別に要る） |
| 備考 | PO 承認済み（2026-10-17 チャット）。KGI G1〜G6「y」、新商品登録は Discord の y を介す（C3 維持）「y」、報告ボタンは super admin のみ（スタッフ全員案に「n」）、数量・価格は数字で完全一致「y」、メモはメモ語マスタから複数選ぶ「y」、再解析と Discord 記録は自動セッションに任せる「y」 |
| 起案日 | 2026-10-17 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1015（区分 A）、ADR-1003（GO の委任）、ADR-136（危険 PR の GO 手順）、ADR-027（i18n）、ADR-144（UI 金型）、ADR-113（設計持ち込みの様式） |
| 設計・根拠 | [design.md](../handoff/analysis-error-report/design.md)、[recon.md](../handoff/analysis-error-report/recon.md)、[kgi.md](../specs/analysis-error-report/kgi.md)、[ideal-state.md](../specs/analysis-error-report/ideal-state.md) |

---

## Context（なぜ必要か）

解析の誤りは、今は PO がチャットで AI に伝え、PO がセッションを開いて直させている。PO の願いは「誤り報告のボタンを押すと、Discord にアラートが届き、agent-console にセッションが開き、AI が原因と対策を書いて直し、再解析して正答を確かめ、Discord に記録を残す」こと（[ideal-state.md](../specs/analysis-error-report/ideal-state.md)）。

制約は 3 つ。Mac では開発もしているので重い常駐処理を入れない（PO）。データの正本を分散させない（PO の恒久指示）。既存の誤り訂正の表 item_corrections は配信の精度ゲートが項目を問わず「修正済み」と数えるため、報告を入れると集計が変わる（recon §4、tcg_distribution_svc.py:557-559）。

## Decision（何を決めたか）

1. 報告の正本は本番 DB の新しい表 3 つ（public）だけ。analysis_error_reports（先頭列 report_code `ER-`＋6 桁）、analysis_error_report_fields（選んだ項目ごとの正解）、analysis_error_report_events（追記だけ）。Discord とセッションは写し。item_corrections は使わない。
2. 画面は在庫表の行ドロワーの解析タブ（super admin だけ）。1 問目「何が間違っていますか？」を複数選択、2 問目「正解は？」を選んだ項目だけ順に聞く。答えは正本の候補から選ぶ（商品・単位・販売状態・状態・メモ）か数字（数量・価格）。既存の金型だけを使う。
3. 本番 backend が保存の直後に Discord の誤り報告チャンネルへ webhook で知らせる。本文は報告番号と項目名だけ。
4. 起動は Mac の agent-console が誤り報告チャンネルを 30 秒ごとに Discord の REST で読む（外へ出る通信だけ）。決めた webhook の投稿で `ER-`＋6 桁に合うものだけ拾い、決まった文の指示でセッションを開く。報告の文面は指示に入れない。同時 1・1 時間 6・同じ番号 1 回、止めるスイッチを持つ。
5. 自動セッションは専用の鍵（ERROR_REPORT_AGENT_TOKEN）で、報告を読む・原因と対策を記録する・その報告のジョブ 1 件を再解析する、だけができる。マスタの書き込みは今の委任の範囲（design §6）で、範囲外は Discord で PO の y を待つ。マージしない。
6. 正答の判定は AI ではなくコード。再解析後の値と報告の正解を項目ごとに比べ、全部一致で resolved、1 つでも違えば unresolved。結果を events と Discord に書く。

## Why（なぜこの形か）

- Discord を読む形（案 a）は、Mac に受付口が増えず、常駐の Claude Code（RSS 65〜400MB）が要らない（recon §6・§7）。眠っていた間の投稿も「最後に処理した投稿より後」を読めば取りこぼさない。30 秒に 1 回は Discord の公式の全体上限 50 回/秒の内（https://docs.discord.com/developers/topics/rate-limits）。
- 本番 API を Mac から頻繁に読む案は本番に +17,280 回/日の呼び出しを足し、PO が指定した Discord 経由の流れと違う（recon §10）。
- 正解を選択肢と数字で受けることで、照合を完全一致の機械判定にできる。メモは本番の現行行でメモが入る 821 行のうち 661 行がメモ語マスタの語だけで成り立つ（/tmp 調査 memo-format-recon）。

## Consequences（結果）

- PO の作業が要る: Discord のチャンネルと webhook の作成、bot の招待、GitHub Secret の登録。
- agent-console の上限とスイッチは別リポジトリのため本リポジトリの CI が届かない。agent-console 側の試験で守る。
- 規約 §3-7 の今の原文は未確認のまま（PO の決定で ai-ops-247 design.md の案F 不採用の記録は外す）。

## 戻し方

- agent-console の読み取りを止めるスイッチを入れる（起動が止まる）。
- 画面のボタンは解析タブの 1 か所。表は追記だけで既存の表を変えないため、使わなくなっても他の処理に影響しない。
