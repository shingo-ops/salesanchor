---
mode: handoff
---
<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — ai-ops-247

> この文書は何か：報知器が鳴ったら、システムが知らせて応急処置をし、AI が人の代わりに調べて直し、振り返りで改善していく仕組みの作り方です。全体を 7 段階に分け、段階ごとに実装カードと実装承認を取ります。

親: [docs/specs/ai-ops-247/README.md](../../specs/ai-ops-247/README.md)

**対象ADR**: ADR-1012（本テーマ・Proposed）、ADR-1009（予備 C）、ADR-115（デプロイ自動ロールバック）、ADR-079（読み取り専用の監視アクセス）、ADR-080/081（監視 VPS）、ADR-136（危険 PR の GO）、ADR-1004（LLM 使用量台帳）  
**recon**: [docs/handoff/ai-ops-247/recon.md](recon.md)  
**KGI**: [docs/specs/ai-ops-247/kgi.md](../../specs/ai-ops-247/kgi.md)（PO 承認 2026-10-13）  
**日付**: 2026-10-13  
**担当**: 設計パートナー（Opus）  
**状態**: 設計案（全体設計）。各段階の詳細（変更前後のコード・触らない範囲）は段階ごとの実装カードで確定する

---

## 1. あるべき姿

[ideal-state.md](../../specs/ai-ops-247/ideal-state.md)（PO 原文）。要点: 監視はシステムに任せ、報知器が鳴ったときだけ AI を呼ぶ。24 時間、人の関与なしで直る。誤った修理でシステムが壊れていかない。失敗から学び続ける。

## 2. KGI

[kgi.md](../../specs/ai-ops-247/kgi.md) の 6 件（感度・精度・応急処置・AI の修理・24 時間・PDCA）。KPI は「達成 KGI 数 ◯/6」。

## 3. 全体像（変更前 → 変更後）

**変更前**（recon §1〜§6）:

```
監視 ─┬─ Alertmanager ─→ Discord 監視チャンネル ─→ 人が見る（Mac が動いていれば C の受付も読む）
      └─ Grafana     ─→ Discord（別経路）
応急処置: デプロイ時のロールバックと抽出ジョブ回収だけ
記録: なし
```

**変更後**:

```
① 報知器   Prometheus / Loki / Uptime Kuma のルール（全ルールに「page / auto / ticket」の札と手順書リンク）
              │ 経路は Alertmanager 1 本にまとめる（配線の正本）
              ▼
② 振り分け Alertmanager ─┬─→ Discord 監視チャンネル（今までどおり。人の目）
                         └─→ 保守 API（アプリ backend・Bearer 認証）
                                │ 障害記録（アプリ DB・正本）に 1 件として記録（同じ原因はまとめる）
                                ▼
③ 応急処置 prod1 の応急処置係（ホストの定期実行）が「症状→処置」一覧の処置だけを実行
              │ 回数の上限・全停止スイッチあり。結果を障害記録へ
              ▼
④ AI       保守 API → Claude Code routines の /fire（本命 B・クラウド・Mac 不要）
              │ AI は Grafana（読み取り専用）と保守 API で調べる
              │ 止血は「一覧の処置の依頼」だけ。修理は PR（claude/ ブランチ）→ 既存の審査と GO
              │ B が 5 分以内に着手しなければ、Discord に「B 未着手」→ Mac の受付（予備 C）が拾う
              ▼
⑤ PDCA     障害ごとに振り返り（障害記録の欄）→ 改善 PR → 保守用の担当定義に教訓を追記（PR）
              月次成績表（super-admin 画面・既存の金型だけで作る）
```

### 配線と DB の正本（PO 条件「データを分散させない」）

| 情報 | 正本（1 か所） | 写し・表示 |
|---|---|---|
| 鳴らす条件 | repo の `monitoring/` 配下のルール | prod2 の稼働設定（段階1 で repo との一致を機械で確認） |
| 通知の経路 | Alertmanager（`monitoring/alertmanager/alertmanager.yml`） | Grafana の通知先は段階0 の確認後、Alertmanager へ寄せる |
| 障害・処置・AI の記録・振り返り | アプリ DB の障害記録の表（段階2 で新設） | Discord の投稿・成績表画面は表示だけ |
| 症状→処置の一覧 | repo の 1 ファイル（段階3 で新設） | 応急処置係と AI はこれを読むだけ |
| AI の振る舞い（担当定義） | repo の 1 ファイル（段階4 で新設） | B（routines）と C（ops-worker）が同じものを読む |

障害記録を repo や GitHub Issue に置かない理由: リポジトリは PUBLIC（recon §5）。

## 4. recon

[recon.md](recon.md)。主な事実: 計器の無いルール 4 本（`monitoring/prometheus/alert_rules.yml:51`・:61・:71・:81）、BackendHighLatency が 14 日で 320 回、unhealthy の自動再起動なし（`docker-compose.yml:198` ほか）、一次記録のある過去障害 4 件中 報知器先行 0 件（10/2 の 1 件は未確認）、障害記録なし、未解決の不明点 5 件（recon 不明点 #3〜#7）。

## 5. 段階ごとの設計

各段階は「1 便 1 目的」の実装カードに分ける。カード発行前に design-partner.md §5.5 のチェックを行う。段階の順番は依存関係の順（記録の器が無いと処置も AI も記録できない）。

### 段階0 基準値と本番の事実（実装なし）

- PO に読み取り専用の script を `!` で 1 回実行してもらう（PO 指示: PO の ! 実行はスクリプト化して短い 1 行で渡す）。取るもの: prod2 で動いているルールと repo の差・Alertmanager の版・Grafana のアラートルールの有無・Kuma の通知先・prod1/prod2 の空きメモリ・10/2 の HighDiskUsage が Discord に届いたか。
- 鍵や URL は表示せず、件数・一致/不一致だけを出す script にする。
- 結果で recon 不明点 #3・#6 を閉じ、kgi.md の基準値を確定する。

### 段階1 報知器（KGI 1・2）

1. 計器の無いルール 4 本を直す。軽い exporter を入れるか、既にある指標でルールを書き直すかを、段階0 の空きメモリで決める（カードで選択理由を書く）。
2. 足す見張り: celery の失敗・beat の停止（pushgateway に「最後に動いた時刻」）・バックアップの鮮度・証明書の期限・Gemini の失敗率（llm_usage_events）・待ち行列の長さ・Kuma の `monitor_status`。
3. 全ルールに札を付ける: `page`（人か AI が要る）／`auto`（応急処置で済む。Google SRE「ロボット的対応で済むものはページにしない」）／`ticket`（急がない）。各ルールに手順書リンク。
4. BackendHighLatency は 14 日分の実測から条件を決め直す（KGI 2 の精度）。同名ルール BackendErrorSpike の重複を解消。
5. prod2 の稼働ルールと repo の一致を定期に確かめる仕組み（ずれたら通知）。
6. Grafana の通知先は、段階0 で Grafana 自身のルールが無いと確認できたら Alertmanager へ一本化する。

### 段階2 障害記録と保守 API（KGI 1〜6 の物差し）

- アプリ DB に障害記録の表を新設（migration・危険 PR として ADR-136 の GO）。1 件の障害に、通知・処置・AI の調べ・修理 PR・振り返り・再発の結び付きを持たせる。KGI の判定に要る時刻（最初の通知・人が気づいた時刻・処置完了・AI 着手）を列にする。
- 保守 API（backend・super admin 相当の専用キー。bot キーの流用か新設かは recon 不明点 #4 をこのカードで比較して決める）:
  - Alertmanager の webhook を受けて記録（同じ fingerprint はまとめる＝KGI 2 の「繰り返しは 1 件」）
  - AI と応急処置係が記録を読み書きする
- 全停止スイッチ: DB の 1 か所の設定。中継・応急処置・AI 起動のすべてがこれを見る（AWS 2025-10 の教訓）。
- Alertmanager の受け先に保守 API を追加（Discord は残す）。認証は Bearer（`authorization`）だけ。カードで `amtool check-config` を必須にする（recon 不明点 #2）。

### 段階3 応急処置（KGI 3）

- celery-worker・celery-beat・discord-gateway・gemini-egress に healthcheck を足す。
- 応急処置係: prod1 のホストで定期実行する script（既存の f2-cleanup と同じ置き方。docker の操作権を持つ新しいコンテナは作らない）。repo の「症状→処置」一覧に載った処置だけを実行する。
- 起動の契機と経路（正本は障害記録 1 か所）: 応急処置係は 1 分ごとに保守 API から「札 auto で未処置の障害記録」と「AI の処置依頼（障害記録に付いた依頼）」を読み、一覧の処置を実行し、結果を同じ障害記録へ書く。ホストで症状を直接見て処置を始めることはしない（記録より先に処置が起きないようにする）。保守 API に届かないときは処置しない（Discord への通知は Alertmanager から別に届く）。
- ブレーキ: 1 コンテナにつき 1 時間に再起動 3 回まで。超えたら処置を止めて page に上げる。全停止スイッチを毎回確認。処置前後の状態を障害記録に残す（悪化 0 件の判定に使う）。
- デプロイで migration が失敗したのにヘルスが正常のまま残る問題（recon §4 2026-10-03）は、デプロイの失敗通知を障害記録に入れて page にする（ロールバック条件の変更は危険 PR として別カード）。

### 段階4 AI（本命 B）と共用の担当定義（KGI 4・5）

- 共用の担当定義（repo の 1 ファイル）: 調べる順番・使ってよい道具・止血は一覧の処置の依頼だけ・不可逆操作は止まって PO に承認依頼・修理は PR・報告の型。B と C の両方がこれを読む。教訓は PR で追記する。
- routine の設定（PO が claude.ai の Web で作る。トークンは Web でしか発行できない）:
  - 起動: API（/fire）。保守 API が障害記録 1 件につき 1 回だけ呼ぶ。1 時間 20 回で自前の上限（公式上限 30 回より下）
  - 渡す文: 障害記録の ID だけ。中身は AI が保守 API から読む（`<routine-fire-payload>` は信用しないデータとして扱う）
  - 通信: Custom で `app.salesanchor.jp` と `api.salesanchor.jp` だけ。Grafana の Viewer トークンと保守 API のキーは network secrets（AI から鍵が見えない）
  - SSH・DB 直結・コネクタは使わない
- AI ができること: 監視の読み取り・記録の読み書き・一覧の処置の依頼（実行は応急処置係）・claude/ ブランチへの PR。マージと本番反映は今のルールのまま（`docs/adr/ADR-136-cc-bot-github-identity.md`・GO 委任の範囲）。
- 着手の見張り: 保守 API が /fire 後 5 分以内に AI の着手記録が無ければ、Discord に「B 未着手」を投稿する（段階5 の C が拾う）。
- 不可逆操作・一覧外の操作が要るとき（B は許可確認なしで動く＝recon §6 のため、止まる仕組みを記録の状態で作る）: AI は障害記録を「PO 承認待ち」にして、必要な操作の原文と理由を書いて終了する → 保守 API が Discord の監視チャンネルへ webhook で投稿する（Mac に頼らない）→ PO が承認するときは super-admin 画面の障害記録で「承認」を押す（承認は記録に残す）→ 保守 API がもう一度 /fire する。承認された操作の実行先は、回数の上限を超えて止まった一覧の処置を再開させる場合は応急処置係、一覧外・不可逆の操作は PO 本人または既存の GO 手順。画面の部品は段階6 と同じく既存の金型だけで作る。
- 段階4 のカード発行の前提: recon 不明点 #7（監視からの常時起動がサブスクの「ordinary, individual usage」に入るか）について PO の判断を得る。
- 試作で先に確かめること（カード発行前）: ① /fire から着手までの時間 ② Viewer トークンで Grafana の問い合わせができるか（recon 不明点 #5） ③ routine が repo の担当定義を読むか。結果を evidence-registry に記録。

### 段階5 予備 C の完成（KGI 5 の予備・PO 条件）

- ADR-1009 の残り E7・E8・E10・KGI-1〜4 を本番配置で実測する（使用量の枠が戻った後。戻る日時は recon §6 のとおり未確認のため、PO の使用量画面で確認してから起動。起動は PO の `!`）。
- C は「B 未着手」の投稿と、保守 API に届かなかった通知だけを扱う（B と同じ障害に二重に動かない）。
- ops-worker が段階4 の共用担当定義を読むようにする。

### 段階6 PDCA と月次成績表（KGI 6）

- 障害ごとの振り返り（原因・効いた処置・効かなかった処置・次の改善）を障害記録に書く。改善は PR、教訓は共用担当定義へ PR。
- 成績表: 障害記録から KGI 1〜6 を計算する API（計算は backend 1 か所。画面で計算しない）と super-admin 画面。画面は既存の金型（`frontend/src/components/DataTable.tsx`・Card・Badge・Callout・EmptyState）とデザイントークンだけで作る。グラフは金型が無いので使わない（使うなら PO の許可を得て金型を先に登録・`docs/CC_UI_GOVERNANCE.md:9`）。文字はすべて i18n。
- 月 1 回、routine（スケジュール起動）が成績表を読み、前月比で悪化した KGI を PO に報告する。

## 6. 弊害・トレードオフ

- **使用量**: routines はサブスクの枠を使う（公式）。B と C は同じ枠なので、枠が尽きると両方止まる → 障害 1 件に 1 回だけ起動・自前の上限 20 回/時。枠切れで /fire が失敗したら Discord で PO に知らせる（人に戻す）。
- **研究プレビュー**: routines の仕様が変わる可能性（公式の注意書き）→ C を予備に保つ。代替候補は GitHub Actions の claude-code-action（サブスクの OAuth トークンで動く・公式）。
- **AI の誤修理**（PO の最大の懸念）→ AI は本番に直接書かない。止血は一覧の処置だけ、修理は PR で既存の審査・CI・GO を通す。ITBench（2025）で SRE 課題の自動解決は 11.4%。AI の判断を信じ切らない前提で設計する。
- **自動処置の暴走**（AWS 2025-10）→ 回数の上限・全停止スイッチ・処置前後の記録。
- **プロンプトは防壁にならない**（Replit 2025-07）→ 権限で塞ぐ（DB 直結なし・SSH なし・鍵は VM の外）。
- **規約**: routines の公式ページが監視ツールからの起動を使い道に載せていることを根拠にする。規約本文に routines を名指しした一文は無い（recon §6）。
- **報知器を増やすと誤報も増える** → 札（page/auto/ticket）と KGI 2 の測定で毎月見直す。
- **戻し方**: 全停止スイッチを入れる → routine を Web で OFF → Alertmanager の保守 API 宛てを外す。Discord への通知は今までどおり残るので、人の目には戻る。

## 7. 外部・過去事例の参照と我々への応用

- 事例1: AWS us-east-1 DynamoDB 障害（AWS 公式ポストモーテム https://aws.amazon.com/message/101925/ 、2025-10-19〜20、約 14 時間 32 分）。自動化が空の DNS レコードを書き込み、自動では戻れなくなった。AWS は自動化を全世界で停止し、1 回に変えられる量の上限を足した → 応用: 全停止スイッチ・回数の上限（段階2・3）
- 事例2: Replit の AI が本番 DB を削除（eWeek 2025-07-22 https://www.eweek.com/news/replit-ai-coding-assistant-failure/ ）。凍結の指示に反して削除 → 応用: 指示ではなく権限で塞ぐ（段階4 の通信と鍵の制限）
- 事例3: Google SRE book 第 6 章（https://sre.google/sre-book/monitoring-distributed-systems/ ）「Every page should be actionable」「ロボット的対応で済むものはページにしない」→ 応用: 札 page/auto/ticket と KGI 2（段階1）
- 事例4: IBM ITBench（ICML 2025 https://proceedings.mlr.press/v267/jha25a.html ）SRE 課題の自動解決 11.4%（102 シナリオ）→ 応用: AI の修理は PR と審査を通す（段階4）
- 事例5: Microsoft RCACopilot（EuroSys'24 https://www.microsoft.com/en-us/research/publication/automatic-root-cause-analysis-via-large-language-models-for-cloud-incidents ）原因分類の精度最大 0.766、Meta（2024-06-24 https://engineering.fb.com/2024/06/24/data-infrastructure/leveraging-ai-for-efficient-incident-response/ ）上位 5 候補に原因 42% → 応用: AI の原因推定は「候補と根拠」として記録し、確定は振り返りで行う（段階6）
- 限界: 上記の成功値は大企業・ベンダー自身の数字で、1 人運用の小さなサービスでの実測は見つけていない。本設計の成否は KGI の実測だけで判定する。

## 8. 代替案と選んだ理由

| 案 | 長所 | 短所 | 判断 |
|---|---|---|---|
| B. Claude Code routines（API 起動・クラウド） | Mac 不要・公式機能・監視からの起動が公式の使い道に載る | 研究プレビュー・サブスク枠を使う・1 時間の上限 | **本命**（PO 承認 2026-10-13） |
| C. Mac 上の Discord 受付（ADR-1009） | 実装済み・承認ボタンあり | Mac が眠ると止まる | **予備**。構築と動作確認まで完了させる（PO 条件） |
| D. GitHub Actions の claude-code-action（OAuth トークン） | 公式・サブスクで可 | `repository_dispatch` での起動は公式ページに明記なし | B が使えなくなったときの候補 |
| E. API キー（従量課金） | 規約上の扱いが明確 | 費用が別にかかる | 不採用（PO の方向性はサブスク枠内。必要になれば PO 判断） |
| F. 自作アプリ（agent-console）から自動で指示 | 自由度が高い | 規約 §3-7 の「自動・非人間のアクセス」に当たる恐れ | 不採用 |
| G. AI の毎日の見回り | 単純 | PO が不要と判断（監視はシステムに任せる） | 不採用（PO 判断） |

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 段階0: 本番の事実 6 項目（ルール差・版・Grafana ルール有無・Kuma 通知先・空きメモリ・10/2 の通知到達）が取れ、recon 不明点 #3・#6 が閉じる | PO の `!` 実行の生出力を /tmp/CC報告ファイル/ に保存し、recon を更新 |
| 段階1: 全ルールが本番で計器を持つ（`absent()` で 0 本） | Prometheus の問い合わせ結果を PR 本文に貼る |
| 段階1: 全ルールに札と手順書リンクがある（欠け 0 本） | ルールファイルを読む検査 script を CI に追加し、その結果 |
| 段階1: 足した見張りが擬似の故障で鳴る（celery 停止・beat 停止・バックアップ古い・証明書期限・Kuma down） | 手元の docker compose（`docker-compose.yml` と `docker-compose.monitoring.yml` を同時に起動）で 1 件ずつ起こし通知時刻を記録。本番は Alertmanager の擬似アラート（amtool）1 件で経路だけ確認。結果を evidence-registry に記録 |
| 段階2: Alertmanager の通知 1 件が障害記録 1 件になり、繰り返しは同じ記録にまとまる | pytest（保守 API）＋本番での擬似アラート 1 件 |
| 段階2: 全停止スイッチを入れると、記録以外の動作（処置・AI 起動）が 0 件 | pytest と本番での 1 回の切り替え試験 |
| 段階3: 一覧の症状を起こすと 5 分以内に処置が終わり回復する／上限を超えると止まって page | 手元の docker compose で症状ごとに試験（成功率と時間を記録）。本番は影響の小さい 1 コンテナ（celery-beat）で 1 回だけ、PO に日時を伝えてから |
| 段階4: 擬似アラートから 5 分以内に AI が着手し、障害記録に調べた結果が書かれる。Mac を閉じた状態で 3 回 | 障害記録の時刻（通知・着手）と Mac の状態の記録 |
| 段階4: AI が一覧外の操作と不可逆操作を実行しない | 擬似アラートで「DB の行を消せば直る」状況を作り、AI が PO 承認依頼で止まることを確認 |
| 段階5: ADR-1009 の E7・E8・E10・KGI-1〜4 が ○ | ADR-1009 design §8 の手順で実測し evidence-registry に記録 |
| 段階5: B が着手しないとき C が拾い、B が着手したときは C が動かない（二重 0 件） | /fire を意図的に失敗させる試験と通常の試験を各 1 回 |
| 段階6: 成績表画面が KGI 1〜6 を表示し、金型以外の部品・色の直値が 0 | Evaluator（Playwright）＋ ESLint・デザイントークン検査（CI） |
| 段階6: 振り返りが無い障害が月末に 0 件 | 成績表の「振り返り未記入」件数 |
| 段階6: 既知の障害記録から計算した KGI 1〜6 の値が期待値と一致する | pytest（成績表 API に固定の障害記録を与え、手計算の期待値と比べる） |
| 段階4: PO 承認待ちの記録が Mac を閉じた状態でも Discord に投稿され、承認後に再び AI が着手する | 擬似アラートで 1 回試験し、記録の状態の移り変わりと時刻を残す |

## 技術 How・KPI

- KPI: 達成 KGI 数 ◯/6（月次成績表で測る）
- 技術選択: 監視は今の Prometheus/Loki/Alertmanager/Kuma を使い続ける（新しい監視製品は入れない）。障害記録はアプリ DB（正本 1 か所・PUBLIC repo を避ける）。AI はクラウドの routines（Mac 不要）。応急処置はホストの定期実行（docker 操作権を持つコンテナを増やさない）。

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 設計 | 本設計一式と ADR-1012（Proposed）を docs PR で main へ | 設計パートナー |
| 段階0 | 読み取り専用 script を作り、PO が `!` で 1 回実行。recon と基準値を更新 | 設計パートナー（script は Sonnet）・実行は PO |
| 段階1〜6 | 段階ごとに実装カード → PO の実装承認 → Sonnet が実装 → Fable 審査 → CI → マージ（危険 PR は ADR-136） | 設計パートナー・Sonnet |
| 段階4 の PO 操作 | routine の作成とトークン発行（Web のみ）・network secrets 登録・トークンを本番の secrets へ（secrets 変更は PO） | PO |
| 段階5 | 使用量の枠が戻ったことを PO が画面で確認した後に、PO が ! bash ~/discord-test/start-ops-intake.sh で受付を起動し、実測 | PO（起動）・設計パートナー（実測） |

## 継続

- 完了後の監視: 月次成績表（段階6）。悪化した KGI は翌月の改善テーマにする。
- 委任範囲を広げる（例: AI の修理 PR のマージ）は、成績表の実績を見て PO が判断する。本設計では広げない。

## 維持の仕組み

- 守り手: 人手で守る（守る仕組み〔ルールの札の検査・prod2 との一致確認・全停止スイッチ・成績表〕そのものを段階1〜6 で作るため。各段階のカードで、その段階の関所のファイルをこの欄に書き足す）
- 既にある守り手: `.github/workflows/deploy.yml`（デプロイ後のヘルスチェックと自動ロールバック。ADR-115）
- 対象: ① 鳴らす条件と経路の正本が 1 か所 ② 障害記録が 1 か所 ③ AI は一覧外・不可逆の操作をしない ④ 全停止スイッチが効く ⑤ KGI が毎月測られる

## 接触面分析（6 面）

| 面 | 接触 | 対処 |
|---|---|---|
| 人 | PO は段階0 の `!` 実行、段階4 の routine 作成・secrets 登録、段階5 の起動、不可逆操作の承認だけ | 各操作は 1 行で渡す。不可逆操作の承認依頼は、B は障害記録の「PO 承認待ち」→ Discord 投稿 → super-admin 画面で承認（段階4）、C は Discord の承認チャンネル（ADR-1009） |
| エージェント | B（クラウド）と C（Mac）が同じ担当定義を読む。並行セッションには台帳（active-work.d）で周知 | 担当定義は repo の 1 ファイル。教訓は PR で追記（直接編集しない） |
| 機械 | Alertmanager の受け先追加・ルール検査の CI 追加・応急処置係の定期実行・月次 routine | ルール検査は CI に入れる。定期実行は既存 f2-cleanup と同じ置き方 |
| データ | アプリ DB に障害記録の表を新設（public スキーマ・テナントの業務データには触れない）。tenant_004 の表は読まない | migration は危険 PR（ADR-136）。記録の書き込みは保守 API の 1 か所から |
| 本番 | prod1（healthcheck 追加・応急処置係・保守 API）、prod2（ルール・Alertmanager の受け先） | 段階ごとに 1 つずつ反映 → 測定 → 次（変更は一度に 1 つ） |
| 外部 | Anthropic routines（研究プレビュー）・Discord・GitHub | routines が止まれば C と Discord 通知で人に戻る。利用者への影響は無い（監視側の変更のみ） |

## 成立性の実測（段階ごとに記入）

| # | 確かめること | 段階 | 結果 |
|---|---|---|---|
| M1 | 本番の事実 6 項目（recon 不明点 #3・#6） | 段階0 | 未実施 |
| M2 | /fire から AI 着手までの時間 | 段階4 試作 | 未実施 |
| M3 | Viewer トークンで Grafana の問い合わせができるか（recon 不明点 #5） | 段階4 試作 | 未実施 |
| M4 | routine が repo の担当定義を読むか | 段階4 試作 | 未実施 |

## 独立レビューの記録

| 日付 | 審査 | 判定 | 主な指摘と対応 |
|---|---|---|---|
| 2026-10-13 | 設計審査（Fable・同じ会社の別モデル。独立した第三者ではない） | REVISE | HIGH 3 件（ADR 索引の状態が Accepted と表示・関所で落ちるパス表記・メモリを根拠にした事実）、MEDIUM 6 件（使用量の戻る日時の出典・公式仕様の出典・応急処置の契機・B の承認経路・試験の環境・成績表の計算の検証）、LOW 5 件。すべて本文に反映（再審査は下の行に記録） |
| 2026-10-13 | 再審査（Fable） | APPROVE（条件付き） | 文書間の数字の食い違い MEDIUM 2 件（根拠登録・計画票の日時）、LOW 4 件。すべて反映 |
