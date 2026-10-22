# design — 解析の誤り報告から自律修正まで（草案）

> この文書は何か: 誤り報告ボタンから、AI の自動セッション、修正、再解析、正解との機械照合、Discord への記録までの作り方の設計案。
> 親: [docs/specs/analysis-error-report/README.md](../../specs/analysis-error-report/README.md)／あるべき姿: [ideal-state.md](../../specs/analysis-error-report/ideal-state.md)／KGI: [kgi.md](../../specs/analysis-error-report/kgi.md)／現状: [recon.md](./recon.md)

状態: 設計案作成済み・自己審査 APPROVE（§12）・KGI は PO 承認済み（2026-10-17「y」）・実装未着手。区分: ADR-1015 の A（新機能・migrations・新 API・agent-console の新しい口）。

## 1. 目的
super admin が見つけた解析の誤りを、ボタンで「何が間違っているか」と「正解」の形で報告する。報告から AI が自動で原因を調べ、委任範囲で直し、再解析の結果を正解と機械で照合し、Discord に残す（あるべき姿 §1）。

## 2. 全体の流れ
```
[1] 在庫表の行ドロワー（解析タブ・super admin）
     「誤り報告」→ 何が間違っていますか？（複数選択）→ 選んだ項目ごとに 正解は？ → 送信
[2] 本番 backend: 報告を表に保存（正本）→ Discord の誤り報告チャンネルへ webhook で通知（本文は報告番号と項目名だけ）
[3] Mac の agent-console: 誤り報告チャンネルを 30 秒ごとに読む（外へ出る通信だけ）
     → 決めた webhook からの投稿だけを拾い、報告番号だけを取り出す → セッションを開いて決まった指示を送る
[4] 自動セッション（Claude Code・Opus）: 報告を本番から読み、原因と対策を Discord のスレッドに書き、操作一覧（§6）の範囲で直す
[5] 本番 backend: 再解析 → 報告の正解と再解析後の値を項目ごとに照合（AI ではなくコードで判定）→ 結果を表に保存し Discord に書く
```

## 3. 選んだ経路と理由
| 案 | 中身 | 判断 |
|---|---|---|
| a. agent-console が Discord の 1 チャンネルを読む | Mac から外へ出る通信だけ。Claude Code を常駐させない | **採用**。Mac に受付口が増えない（recon §7）。常駐の Claude Code（RSS 65〜400MB・recon §6）が要らない（PO「重い処理は入れたくない」）。眠っていた間の投稿は「最後に処理した投稿より後」を読み直せば取りこぼさない |
| b. ADR-1009 の受付（常駐 Claude Code）が受けて agent-console に頼む | 既にある部品 | 不採用。常駐セッションが要る・今は止まっている（recon §6）・研究プレビューに依存 |
| c. Mac が本番の API を数秒ごとに読む（Discord を通さない） | 本番の呼び出しが +17,280 回/日（recon §10） | 不採用。PO が Discord 経由の流れを指定（あるべき姿 §1） |
| d. 本番から Mac へ直接送る（Tailscale） | Mac に受付口が増える | 不採用 |

- 規約: docs/handoff/ai-ops-247/design.md:174 の案F 不採用の記録は PO の決定で外す（あるべき姿 §2）。規約 §3-7 の今の原文は【未確認】（§10 U5）。

## 4. 作るもの

### 4-1 表（public・正本はここだけ。Discord とセッションは写し）
| 表 | 列 | 備考 |
|---|---|---|
| analysis_error_reports | report_code（先頭・`ER-` ＋ 6 桁連番）, id, extraction_item_id, extraction_job_id, reported_by, reported_at, status（open / working / resolved / unresolved / cancelled）, discord_message_id | 1 報告 1 行 |
| analysis_error_report_fields | report_id, field_name（product_id / quantity / price / unit / condition / status / note）, system_value, expected_value, expected_missing_product（bool） | 選んだ項目ごとに 1 行 |
| analysis_error_report_events | report_id, at, actor, kind（created / notified / session_opened / cause / action / reanalyzed / verified）, payload JSONB | 追記だけ（UPDATE・DELETE を権限で禁止） |
- item_corrections には入れない。理由: 配信の精度ゲートが field_name を問わず「修正済み」と数えるため（recon §4、tcg_distribution_svc.py:557-559）。
- RLS・権限の付け方は pipeline の public 表の今の型に合わせる（実装カードで file:line を固定）。

### 4-2 本番 API
| 口 | 認証 | 役目 |
|---|---|---|
| POST /tcg/items/{extraction_item_id}/error-reports | super admin（require_super_admin） | 報告を保存して Discord に通知。応答に report_code |
| GET /ops/error-reports/{report_code} | 新しい専用の鍵（ERROR_REPORT_AGENT_TOKEN） | 自動セッションが報告と行の今の値を読む |
| POST /ops/error-reports/{report_code}/events | 同上 | 原因・対策・変更を記録（kind は cause / action だけ） |
| POST /ops/error-reports/{report_code}/reanalyze | 同上 | その報告のジョブ 1 件だけ再解析する新しい Celery タスクを積む。タスクの中で reanalyze_v102_job を呼び、続けて照合を直接呼ぶ（既存の型: tcg_extraction.py:734-760 は続きを関数内で直接呼ぶ。chain/link の前例は無い） |
- 照合: 再解析後の analysis_results の値と analysis_error_report_fields.expected_value を項目ごとに比べる。全部一致で resolved、1 つでも違えば unresolved。結果は events（verified）に保存し、Discord に項目ごとの○×を書く。
- 鍵は読む・記録する・その報告の 1 ジョブを再解析する、だけに使える。マスタ書き込みには使えない。

### 4-3 画面（frontend・金型とトークンだけ）
- 置き場所: InventoryRowDrawer.tsx の AnalysisPane（super admin だけが見る解析タブ・recon §1）に「誤り報告」ボタン。
- 1 問目「何が間違っていますか？」: Checkbox の複数選択。選べる項目は 商品・数量・価格・単位・状態・販売状態・メモ（ItemComparison.tsx:26・:41-50 の項目）。
- 2 問目「正解は？」（選んだ項目だけ順に出す）:
  | 項目 | 答え方 | 候補の正本 |
  |---|---|---|
  | 商品 | AsyncCombobox で検索して選ぶ。「マスタに無い」チェックも置く | GET /tcg/products/search |
  | 単位・販売状態 | Select | GET /tcg/review/value-options |
  | 状態 | Select | GET /tcg/conditions/review-options |
  | 数量・価格 | TextField type="number"（前例 ReviewValueFixForm.tsx:102・PO 2026-10-17「y」） | 正本の候補なし。照合は完全一致 |
  | メモ | MultiSelect でメモ語マスタから複数選ぶ（PO 2026-10-17「y」。文字入力の決定を置き換え） | public.tcg_note_master.label_ja（15 種類・tcg_analyzer_svc.py:1193-1197）。照合は選んだ語の集合が一致するか。候補は super admin 用の GET（backend/app/routers/super_admin_note_master.py:123-）から enabled=true の共有行（tenant_id IS NULL）だけを使う。候補専用 API は無い（調査 /tmp/CC報告ファイル/autofix-u346.md） |
- 枠: Modal。段階式の金型は無いので、ReviewFixWizard.tsx と同じ組み方（feature 内）にする。文言は全部 t("key")、ja/en 同じキー（ADR-027）。

### 4-4 agent-console（別リポジトリ・版上げとタグ）
- 誤り報告チャンネルを 30 秒ごとに Discord の REST（GET /channels/{id}/messages?after=<最後の ID>&limit=100）で読む。bot に要る権限は VIEW_CHANNEL と READ_MESSAGE_HISTORY だけ。鍵は bot トークン（Mac の鍵ファイルだけに置く）。429 と X-RateLimit-* ヘッダに従って待つ（公式 https://docs.discord.com/developers/topics/rate-limits：全体の上限 50 回/秒。30 秒に 1 回はその内）。
- 拾う判定はメッセージの webhook_id が決めた webhook と一致すること（公式 https://docs.discord.com/developers/resources/message）。
- 作る場所: 今の稼働の版（v0.43.0 以降）を土台にする。受け口の部品は ADR-1039 の設計（agent-console `docs/handoff/discord-pdca/design.md` §4-1）と共通（2026-10-22 直し。決定 ADR-1025 Decision 4 は変えない）。
- 拾うのは、決めた webhook の投稿で、本文が `ER-` ＋ 6 桁に合うものだけ。他の文は読まない。
- 最後に処理した投稿の ID を保存する。起動時と眠りから戻った後はそれより後を読む（G2b）。
- 同じ report_code のセッションがあれば開かない。同時に開くのは 1 つ、1 時間に 6 つまで。全停止は `halt_all`（不具合報告と誤り報告の両方の種類が見る。PO 2026-10-21「1」）が入っている間は開かない。設定ファイルの `enabled` は受け口の有効・無効。
- セッションに送る指示は決まった文だけ: 「誤り報告 ER-xxxxxx を docs/specs/analysis-error-report/playbook.md に従って処理する」。報告の文面は指示に入れない（AI が文面を指示と取り違えないため）。

### 4-5 自動セッションの手順書（playbook.md）
1. GET /ops/error-reports/{code} で報告を読む。本番 DB の読み取りは今の恒久許可の道を使う。
2. 原因を決める。外部サイト（公式）を見てよい（あるべき姿 §4）。値の決め方は registration-rules.md。
3. 原因・対策を Discord のスレッドと events に書く。
4. §6 の操作一覧の範囲で直す。範囲外は Discord で PO に y/n を聞いて待つ。
5. 再解析を積む → 照合の結果を待つ → resolved ならスレッドに「正答」と書いて閉じる。unresolved なら「未解決」と書き、PO 宛てで止まる。

## 5. 変更の前と後
| 場面 | 今 | 後 |
|---|---|---|
| 誤りを見つけた | チャットで AI に伝える | ドロワーのボタンで正解つきで報告 |
| AI が動き出す | PO がセッションを開く | 30 秒＋起動待ち（最大 120 秒・launch.ts）で自動で開く |
| 正答の判定 | AI 数体＋Opus の判断 | コードが正解と照合（○×） |

## 6. 操作一覧（PO の一括承認を受ける対象）
| # | 操作 | 自動セッションだけで行う | 出所 |
|---|---|---|---|
| O1 | 既存商品への検索ワードの追加 | 可（事後に Discord へ記録） | PO 10/15 恒久委任 |
| O2 | 商品区分の変更 | 候補を Discord に出し PO の y の後 | PO 10/16 恒久委任（候補は先に PO へ） |
| O3 | 新商品の登録 | 出典 URL 付きの候補表を Discord に出し PO の y の後 | PO 10/17「y」・registration-rules.md C3 |
| O4 | 除外ワードの追加・状態の語の追加 | PO の y の後 | 委任の範囲外（recon・autofix-recon §5） |
| O5 | コードの修正 | worktree で直して PR を出すまで。マージ・反映は今の GO 手順 | ADR-1015・ADR-1003 |
| O6 | その報告のジョブ 1 件の再解析 | 可（専用の鍵の口だけ） | PO 2026-10-17「y」 |
| O7 | Discord のスレッドへの書き込み・events への記録 | 可 | PO 2026-10-17「y」 |

## 7. 危険と対処
| 危険 | 対処 |
|---|---|
| 報告の文面に指示のような文が入る | 文面はセッションへの指示に入れない。データとして API から読む |
| 偽の Discord 投稿でセッションが開く | 決めた webhook の投稿だけ拾う。拾うのは報告番号だけで、中身は本番から読む（存在しない番号は捨てる） |
| ボタンの連打で大量に開く | 同時 1・1 時間 6・同じ番号は 1 回 |
| 自動セッションの暴走 | §6 の範囲。止めるスイッチ。マージは今の GO 手順 |
| 鍵の漏れ | 専用の鍵は読む・記録・1 ジョブ再解析だけ。bot トークンは読むだけの権限のチャンネル 1 つ |
| 再解析が他の行の is_current を付け替える（recon・autofix-recon §3） | 照合は報告した行だけを見る。付け替えの前後は events に残す |

## 8. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| G1 2 問の順に聞かれ、送信で report_code が出る | Evaluator が Playwright で画面操作・録画 |
| G2a 60 秒以内に Discord に届く | 送信時刻と Discord の投稿時刻の差 |
| G2b 5 分以内に 1 つだけ開く・眠った後も開く | agent-console の監査記録と窓一覧。同じ番号を 2 回投稿して 1 つだけ |
| G3 原因・対策・変更がスレッドに出る | Discord の該当スレッド |
| G4 照合の○×が Discord と events に出る | 正解どおりの報告と、わざと違う正解の報告の 2 件で resolved と unresolved が出る |
| G5 範囲外の操作をしない・スイッチで止まる | スイッチ ON で投稿してセッションが開かないこと。鍵でマスタを書こうとして 403 |
| G6 Mac の負荷 | 導入前後 24 時間の agent-console の CPU・メモリ |

## 9. 進め方（便）
| 便 | 中身 | 区分 |
|---|---|---|
| 1 | 表 3 つ・POST /tcg/items/{id}/error-reports・Discord 通知 | A（migrations・新 API） |
| 2 | /ops/error-reports の 3 つの口・照合 | A（新 API・backend/app/tasks） |
| 3 | 画面（ボタン・2 問） | A（新しい画面） |
| 4 | agent-console の読み取り・セッション起動（版上げ・タグ） | agent-console リポジトリ |
| 5 | playbook.md・試験 2 件（G4）・負荷の測定（G6） | — |
- PO の作業（AI ではできない）: Discord に誤り報告チャンネルと webhook を作る／bot をそのチャンネルに入れる／GitHub Secret に webhook と ERROR_REPORT_AGENT_TOKEN を登録する（secrets の変更は PO 本人・ADR-1003 例外）。

## 10. 未決（すべて解決または PO 決定で受容）
- U1 解決（PO 2026-10-17「y」）: 数量・価格は数字で入力し完全一致で照合。メモはメモ語マスタから複数選び、語の集合で照合（PO 2026-10-17「y」。根拠: 本番の現行行でメモが入る 821 行のうち 661 行がマスタの語だけ・残り 160 行のうち 121 行は発送日の文＝今は ship_ja 欄。v102 の新しい行はメモ原則なし line_analysis_v102_svc.py:701。調査 /tmp/CC報告ファイル/memo-format-recon.md）。
- U2 解決（PO 2026-10-17「y」）: O6・O7 は PO の y なしで自動セッションに任せる。
- U3 解決: 数字は TextField type="number"、メモは MultiSelect、商品は AsyncCombobox（/tmp/CC報告ファイル/autofix-u346.md）。
- U4 解決: 公式の全体上限 50 回/秒の内。ルート個別の数値は公式に記載なし → 429 とヘッダに従う作りで対処（Context7 は月間上限で使えず、公式を直接確認）。
- U5 PO 決定で受容: 案F 不採用の記録は外す（PO 2026-10-17）。規約 §3-7 の今の原文は未確認のまま（設計の可否の前提にしない＝PO の判断事項として記録）。
- U6 解決: 稼働中は v0.42.3（pid 8851、/tmp/CC報告ファイル/autofix-u346.md）。

## 11. 外部・過去事例の参照と我々への応用
該当なし。理由: 社内に既にある部品（Discord webhook・agent-console の launchAndSend・再解析の Celery タスク）の組み合わせで、新しい技術を入れない。この案の調査では外部閲覧をしない（PO 2026-10-17）。

## 12. 自己審査（同一 AI による審査・独立した第二者レビューではない）
- 判定: APPROVE（2026-10-17）。
- 根拠: KGI G1〜G6 は PO 承認済み。§10 の U1〜U4・U6 は事実で解決、U2 は PO 決定、U5 は PO 決定で受容。各受け入れ基準に検証方法がある（§8）。正本は表 1 か所（§4-1）で、Discord とセッションは写し。画面は既存の金型だけ（§4-3）。
- 実装カードで固定すること: 新しい表の RLS・権限の型（pipeline の public 表の今の形の file:line）、Discord 通知の送り先 secret 名、専用の鍵の検査の書き方（ops.py の require_ops_reader と同じ型）。

## 維持の仕組み
- 守り手: .github/workflows/process-artifacts-gate.yml（migrations・新 API の PR は A 区分として GO 記録を検査）
- 対象: 報告の正本が表 1 か所であること、自動セッションがマージしないこと。
- 関所の無い部分: agent-console の上限とスイッチは人手で守る（理由: 別リポジトリで、本リポジトリの CI が届かない）。便 4 で agent-console 側の試験に上限の試験を入れる。
