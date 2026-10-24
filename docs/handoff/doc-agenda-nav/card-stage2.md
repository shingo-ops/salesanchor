# 実装カード 段2-1 — 目次 docs/INDEX.md を新しく作り、届かない文書を表紙につなぐ

> この文書は何か：doc-agenda-nav 段2 の前半（書類だけ）の作業指示書です。AI が手順書を「目次 → 章 → 末端」の順で探せるよう、目次 docs/INDEX.md を新しく作り、仕様書の索引に「いつ読むか」の列を足し、どこからも案内されていない仕様書 15本を各表紙に1行ずつ登録し、2本を同じ作業の記録置き場へ移します。目次から届くかを機械で調べる仕組み（新しい CI・reach.py の取り込み）は段2-2 で別に作ります。

- 設計: docs/handoff/doc-agenda-nav/design.md §4（構造図の「後」）・§5・§8（段2の行）、docs/handoff/doc-agenda-nav/unreachable-list.md §3・§4（扱いは PO の委任で確定済み）
- 対象ADR: ADR-1040（Proposed）。関連: ADR-076
- 状態: 設計は審査済み（PR #4649）。PO の実装承認: 2026-10-23「1」（Opus が示した選択肢1「誤作動直し、目次の新設、決まりの引っ越しまでを順に進めてよい」への返事）
- 段2を2つの PR に分ける理由（Opus の判断）: 書類の追加・移動と、新しい CI の追加は、戻し方も確かめ方も違う。1PR に混ぜると片方だけ戻せない（design §8 の「1段=1PR。変更→反映→測定→次」の考え方を、段の中でも当てはめる）
- 危険便（ADR-136 の危険パス）: いいえ（docs/ 配下だけ。CLAUDE.md・AGENTS.md・STANDARD-WORKFLOW.md・scripts・workflows・migrations は触らない）
- 作業の最初に、作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）
- 担当: 実装と確かめは Sonnet（model "sonnet"）、審査は Opus（reviewer を model "opus" で新しく起こす）、マージは Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段2-1 の実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§9・§10） |
| guards/01-read.md | 全コマンドを `cd /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage2 && ` で始める。`git diff` は merge-base 起点 | ○（§5-3・§5-4） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない（文面はすべて §4 に確定値で書いた） | ○（§4） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§9） |

## 1. 範囲

入れる: §3 の触るファイルだけ。文面は §4 に書いたものを写す（担当は文面を考えない）。

入れない: CLAUDE.md・AGENTS.md（入口から目次へのリンクは段3c）、新しい CI・reach.py（段2-2）、docs/specs/README.md の既存列の中身（「いつ読むか」列の追加と §4-2 の2行以外は変えない）、表紙の既存行の書き換え、lessons.d の中身、docs/specs/process-hardening/proof-of-behavior/README.md の素のパス表記（段2-2 で到達の数え方を決めるときに扱う）。

## 2. 前提の事実（2026-10-23 担当(Sonnet)が origin/main 5cb04e081 で集め、Opus が読んだ。生出力 /tmp/CC報告ファイル/an-stage2/recon/。5cb04e081 → ce23a7930 の間の docs の変更は card-stage2a.md の追加だけ＝Opus 実測）

| # | 事実 | 出典 |
|---|---|---|
| F1 | docs/INDEX.md は無い | recon 11 |
| F2 | docs/specs/README.md は101行。表の見出しは :9 `\| 領域 \| 設計仕様書（あるべき姿） \| 状態 \|`、区切り :10、データ行は :11〜:88 の78行。:98-101 が「追加のしかた」 | 03-specs-readme.txt |
| F3 | 15本の登録先の表紙と一覧節の書式は表紙ごとに違う（箇条書き・表・リンクの有無）。行番号は §4-3 に書いた | 04-*.txt |
| F4 | 移す2本を参照するのは docs/handoff/fix-unify-type-mismatch/design.md:42-43 だけ（unreachable-list.md §3 #16・#17）。2本の中の参照は同じフォルダの名前か、リポジトリ根からのパスで、移しても切れない | 05.txt |
| F5 | docs/ai-agents/lessons.d/ は22ファイル。読む道具は scripts/lessons-view.sh | 09-10.txt |
| F6 | docs/ops/ は runner-commands.md・self-hosted-runner-credential-trap.md の2本。docs/runbooks/ は md 21本 | 09-10.txt |

## 3. 触るファイル（これ以外は触らない）

- 新設: `docs/INDEX.md`
- 変更: `docs/specs/README.md`
- 変更: `docs/specs/attachment-storage/README.md`, `docs/specs/dashboard/README.md`, `docs/specs/schedule/README.md`, `docs/specs/inbox/README.md`, `docs/specs/inventory-management/README.md`, `docs/specs/ledger-guard/README.md`, `docs/specs/process-hardening/README.md`, `docs/specs/product-master/README.md`, `docs/specs/local-hooks-ssot/README.md`
- 移動（`git mv`）: `docs/specs/master-ssot-migration/design-fix-unify-type-mismatch.md` → `docs/handoff/fix-unify-type-mismatch/design-fix-unify-type-mismatch.md`、`docs/specs/master-ssot-migration/recon-fix-unify-type-mismatch.md` → `docs/handoff/fix-unify-type-mismatch/recon-fix-unify-type-mismatch.md`
- 変更: `docs/handoff/fix-unify-type-mismatch/design.md`（:42・:43 の行末に添え書きだけ）
- 変更: `docs/handoff/doc-agenda-nav/card-stage2.md`（このカード。担当は §11 報告欄の追記だけ）

## 4. 作り方

### 4-1. docs/INDEX.md（新設。次の全文をそのまま。行数は §5-1 で数える）

```markdown
# 目次（AI 向け指示文書）

> 入口（AGENTS.md・CLAUDE.md）には安全の決まりだけを置く。作業の型と手順書は、この目次から「章 → 末端」の順にたどり、必要になったときに読む。
> この目次の設計: [doc-agenda-nav](specs/doc-agenda-nav/README.md)（ADR-1040）。行を足すときは表の書式に合わせ、「いつ読むか」を空欄にしない。

| 章 | 末端（読むもの） | いつ読むか |
|---|---|---|
| A 開発の進め方 | [標準開発フロー](STANDARD-WORKFLOW.md) | 便（1回の作業）を始める前 |
| A 開発の進め方 | [実行役のチェックリスト](ai-agents/executor-checklist.md) | 実装・調査の作業前、commit の前、PR を作る前 |
| A 開発の進め方 | [ブランチ運用](specs/branch-operations/README.md) | ブランチと作業場所を作る前、PR を作る・マージする前 |
| A 開発の進め方 | [設計パートナーの手順](ai-agents/design-partner.md) | 設計の担当（Planner・Architect）を始めるとき |
| A 開発の進め方 | [実装役への指示の定型文](ai-agents/executor-preamble.md) | 実装役に作業を渡す指示を書くとき |
| A 開発の進め方 | [教訓メモのフォルダ](ai-agents/lessons.d/)（まとめて読む: `bash scripts/lessons-view.sh`） | 設計・審査で、過去の失敗を確かめるとき |
| B 設計仕様書 | [設計仕様書の索引](specs/README.md) | 新しいテーマを始める前、索引に載る領域に触れる前 |
| C 設計判断（ADR） | [機能から ADR を引く索引](adr/FEATURE-INDEX.md) | 現状把握（recon）で既存の設計判断を探すとき |
| C 設計判断（ADR） | [ADR の一覧](adr/README.md) | ADR を足す・変えるとき（一覧は `node scripts/generate-adr-index.js` で作り直す） |
| D 領域別ルール | [frontend の決まり](../frontend/CLAUDE.md)・[frontend の AGENTS](../frontend/AGENTS.md) | frontend/ のファイルを触るとき |
| D 領域別ルール | [backend の決まり](../backend/CLAUDE.md)・[backend の AGENTS](../backend/AGENTS.md) | backend/ のファイルを触るとき |
| E 商品マスタ登録 | [商品マスタ登録の決まり](specs/product-master/registration-rules.md) | 商品マスタに商品を登録する・登録内容を直すとき |
| F 運用・本番 | [サーバーで使うコマンド](ops/runner-commands.md) | VPS・本番のコンテナで作業するとき |
| F 運用・本番 | [自前の実行機の資格情報の落とし穴](ops/self-hosted-runner-credential-trap.md) | GitHub の自前の実行機（self-hosted runner）を触るとき |
| F 運用・本番 | [手順書のフォルダ](runbooks/) | 監視・デプロイ・障害対応の手順を探すとき |
```

### 4-2. docs/specs/README.md

1. :9 を `| 領域 | 設計仕様書（あるべき姿） | 状態 | いつ読むか |` に、:10 を `|---|---|---|---|` にする。
2. :11〜:88 の各行の行末（最後の `|` の後ろ）に、半角空白・下の表の「いつ読むか」の文字列・半角空白・`|` を足す。行の既存部分は1字も変えない。各行の「領域」列の先頭が下の表の「領域の書き出し」と一致しなければ、書かずに BLOCKED:（行がずれている）。
3. :99 の `新しい設計仕様書を作ったら、この表に「領域名｜相対リンク｜状態」を1行足す。` を `新しい設計仕様書を作ったら、この表に「領域名｜相対リンク｜状態｜いつ読むか」を1行足す。「いつ読むか」は空欄にしない（目次 docs/INDEX.md の章B）。` にする。

| 行 | 領域の書き出し | いつ読むか |
|---|---|---|
| 11 | AI 保守運用 | 監視・障害対応・AI の自動起動を変える前 |
| 12 | まとめ売り | まとめ売り（セット）の読み取り・保存・表示を変える前 |
| 13 | 解析の誤り報告 | 解析の誤り報告から自動修正までの流れを変える前 |
| 14 | Discord 監視通知 | 監視の通知を受けて AI が動く仕組みを変える前 |
| 15 | ブランチ運用 | ブランチ・作業場所の作り方、PR・マージの手順を変える前 |
| 16 | reaper 自動掃除 | 作業場所の自動回収を変える前 |
| 17 | AI向け指示文書 | AI 向け指示文書の入口・目次を変える前 |
| 18 | 文書の親子構造 | 表紙と子文書の親子をつくる・並べ替える前 |
| 19 | 商品マスタ | 商品マスタの項目・登録・照合を変える前 |
| 20 | 設計パートナー長期安定体制 | 設計の担当の進め方を変える前 |
| 21 | エージェント完結の設計体制 | AI だけで設計を進める体制を変える前 |
| 22 | 開発の無駄な停止ゼロ | 開発が止まる原因（待ち・見張り）を直す前 |
| 23 | GO記録の自動転記 | GO の記録・マージ前の検査を変える前 |
| 24 | 画面部品の標準 | 画面部品を新しく作る・変える前 |
| 25 | UI/UXデザインシステム | 色・部品・画面の見た目を変える前 |
| 26 | ├ ページタイトル金型 | ページの題名・説明文を変える前 |
| 27 | └ ページヘッダー金型v2 | ページ上部（ヘッダー・パンくず）を変える前 |
| 28 | └ 入力部品 寸法金型 | プルダウン・入力欄の大きさを変える前 |
| 29 | └ アプリ視覚デザイン言語 | 画面の見た目の方向性を変える前 |
| 30 | デザイントークンSSOT化 | 色・文字・アイコンなどの値を足す・変える前 |
| 31 | └ カレンダー色CSS変数化 | カレンダーの色を変える前 |
| 32 | └ アイコン色の用途別トークン集約 | アイコンの色を変える前 |
| 33 | 在庫管理 | 在庫の取り込み・表示・解析を変える前 |
| 34 | ├ 提供元フィード翻訳 | 仕入元の投稿の翻訳を変える前 |
| 35 | ├ LINE完売ルール | LINE の完売の読み取りの規則を変える前 |
| 36 | │ └ 同じ投稿の〆 | 〆の投稿で在庫を完売にする規則を変える前 |
| 37 | ├ 在庫の閲覧専用ページ | お客さん向けの在庫閲覧ページを変える前 |
| 38 | └ 在庫解析 | 在庫の分析機能を変える前 |
| 39 | 管理センター | 全データの基盤管理の画面を変える前 |
| 40 | ├ 種類分けマスタ | 種類分けマスタを作る・変える前（仕様書はまだ無い） |
| 41 | ├ 品目マスタ | 品目マスタを作る・変える前（仕様書はまだ無い） |
| 42 | ├ HTSコードマスタ | HTS コードマスタを作る・変える前（仕様書はまだ無い） |
| 43 | ├ 素材マスタ | 素材マスタを作る・変える前（仕様書はまだ無い） |
| 44 | ├ 状態マスタ | 状態マスタを作る・変える前（仕様書はまだ無い） |
| 45 | └ 単位マスタ | 単位マスタを作る・変える前（仕様書はまだ無い） |
| 46 | 取引フロー | 引き合い・商談・会社・注文のつながりを変える前 |
| 47 | DB設計のSSOT化 | DB に表・列を足す・変える前 |
| 48 | 文書体系 | docs/ の文書の置き場所を決める前 |
| 49 | 教訓の1便1ファイル化 | 教訓メモを書く・清書する前 |
| 50 | Sales Anchor アプリ全体 | アプリ全体の構成（ページの並び・役割分担）を変える前 |
| 51 | 見積もり・請求書 | 見積書・請求書を変える前 |
| 52 | 売上管理 | 売上の集計・分析を変える前 |
| 53 | 顧客管理 | 顧客の情報・画面を変える前 |
| 54 | プロフィール・アカウント設定 | 会社のプロフィール・個人のアカウント設定を変える前 |
| 55 | recon（現状把握）標準 | 現状把握（recon）のやり方を変える前 |
| 56 | カレンダー | 予定・カレンダーを変える前 |
| 57 | ダッシュボード | ダッシュボードを変える前 |
| 58 | チームボード | チームボードを変える前 |
| 59 | 受信箱 | 受信箱の画面を変える前 |
| 60 | 受注管理 | 受注の業務画面を変える前 |
| 61 | 在庫（自社在庫 | 自社在庫とドロップシッピングの区別を扱う前（仕様書はまだ無い） |
| 62 | 予約販売 | 予約販売を扱う前（仕様書はまだ無い） |
| 63 | 送料マスタ | 送料の計算を扱う前（仕様書はまだ無い） |
| 64 | 請求先/配送先の住所区別 | 請求先・配送先の住所を扱う前（仕様書はまだ無い） |
| 65 | 為替レート | 為替レートを扱う前（関連 ADR を読む） |
| 66 | 翻訳送信・グロッサリ | 翻訳して送る機能・用語集を変える前 |
| 67 | 帳票・フォーム送付 | 見積・請求書・フォームを送る導線を変える前 |
| 68 | 定型文 | 定型文の設定・呼び出しを変える前 |
| 69 | Discord連携 | Discord との連携を変える前（関連 ADR を読む） |
| 70 | Meta（FB/IG）連携 | Facebook・Instagram との連携を変える前（関連 ADR を読む） |
| 71 | 認証・権限・ロール | ロール・権限を変える前 |
| 72 | ログイン方式 | ログイン・パスキー・再設定メールを変える前 |
| 73 | テナント管理・RLS | 会社ごとのデータの分け方（RLS）を変える前 |
| 74 | 接続元 IP の決め方 | 接続元 IP の扱いを変える前 |
| 75 | 例外の中身を応答に出さない | エラー時の応答の中身を変える前 |
| 76 | 一覧の全件取得 | 全件取得・ファイル出力・閲覧の記録を変える前 |
| 77 | 権限・秘密SSOT化 | 鍵・権限の台帳を変える前 |
| 78 | 出荷キャリア連携 | 配送業者との連携を扱う前（関連 ADR を読む） |
| 79 | 開発ループの自動ガード化 | 手順ミスを止める見張り・関所を足す・変える前 |
| 80 | サーバーリソース最適化 | サーバーのメモリ・ディスクの掃除を変える前 |
| 81 | Docker（Colima）使い終わり自動停止 | Mac の試験用 DB の自動停止を変える前 |
| 82 | Mac の自動お手入れの見張り | Mac の定期作業の見張りを変える前 |
| 83 | 仮想マシンが要る試験 | 仮想マシンが要る試験を行う前 |
| 84 | 個人側検問の正本化 | ~/.claude の見張り（フック）を変える前 |
| 85 | データ保全 | バックアップ・復旧の仕組みを変える前 |
| 86 | 添付ファイルの保管 | 受信した画像の保存を変える前 |
| 87 | Discordリアクション | 受信箱の絵文字リアクションを変える前 |
| 88 | LINE解析 Gemini 書き写しの調整記録 | LINE 解析の指示書を変える前、精度の推移を確かめるとき |

「領域の書き出し」の照合は、行頭の `| ` を除いた「領域」列が、上の文字列で始まるかで見る（`├`・`└`・`│` の記号と空白も含めて一致させる）。

### 4-3. 15本を各表紙に1行ずつ登録する

文書名の後ろの説明は、各文書の1行目の見出しから `# ` を除いた文字列（Opus が 2026-10-23 に作業場所 ce23a7930 で `head -1` して写した）。差し込む位置は「:N の直後」＝その行の次の行に新しい行を入れる（既存行は変えない）。表の中の `\|` は、ファイルには `|` として書く。

| # | 表紙 | 差し込む位置 | 足す1行 |
|---|---|---|---|
| 1 | docs/specs/attachment-storage/README.md | :29 の直後 | `- [to-be.md](./to-be.md) — 添付ファイルの保管 理想の設計図（To-Be）` |
| 2 | docs/specs/dashboard/README.md | :11 の直後 | `\| [to-be.md](./to-be.md) \| ダッシュボード（dashboard）— 理想形設計図（To-Be） \| — \|` |
| 3 | docs/specs/dashboard/README.md | #2 の行の直後 | `\| [track-record.md](./track-record.md) \| ダッシュボード（dashboard）— track-record（実績台帳） \| — \|` |
| 4 | docs/specs/schedule/README.md | :11 の直後 | `\| [to-be.md](./to-be.md) \| カレンダー（schedule）— 理想形設計図（To-Be） \| — \|` |
| 5 | docs/specs/schedule/README.md | #4 の行の直後 | `\| [track-record.md](./track-record.md) \| カレンダー（schedule）— track-record（実績台帳） \| — \|` |
| 6 | docs/specs/inbox/README.md | :23 の直後 | `- [track-record.md](./track-record.md) — 受信箱（inbox） track-record` |
| 7 | docs/specs/inventory-management/README.md | :26 の直後 | `- [spec-v1.0.md](./spec-v1.0.md)（509行）は spec.md の v1.0 起案版。spec.md §Version で v1.1〜v1.3 に置き換え済み。` |
| 8 | docs/specs/ledger-guard/README.md | :12 の直後 | `- design G2 — 本店main以外警告（差分設計）: [design-g2.md](./design-g2.md)` |
| 9 | docs/specs/process-hardening/README.md | :8 の直後 | `- 柱1 design — 検査結果の取り違え・マージ経路: [design-pillar1.md](./design-pillar1.md)` |
| 13 | docs/specs/process-hardening/README.md | #9 の行の直後 | `- 子テーマ 動作実測ゲート（proof-of-behavior）: [proof-of-behavior/README.md](./proof-of-behavior/README.md)` |
| 10 | docs/specs/product-master/README.md | :134 の直後 | `- [商品分類の決定記録](./product-classification-decisions.md)` |
| 11 | docs/specs/product-master/README.md | #10 の行の直後 | `- [開発計画書: 商品マスタ 英語名・発売日の欠損補完（tcg_products）](./dev-plans/2026-09-tcg-product-master-fill-title-date.md)` |
| 12 | docs/specs/local-hooks-ssot/README.md | :8 の直後 | `- [guard-disabled-record.md](guard-disabled-record.md) — gh-scope-guard 無効化の記録（2026-08-31）` |

あわせて、各文書の1行目が上の説明と一致することを `head -1` で確かめる（違えば書かずに BLOCKED:）。

#14・#15（proof-of-behavior の ideal-state.md・kgi.md）は #13 の表紙に名前があるため、ここでは何も足さない（unreachable-list.md §3）。

差し込む前に、差し込む位置の行が次の文字列で始まることを確かめ、違えば書かずに BLOCKED:（行がずれている）: #1 `- [kgi.md]`／#2・#4 `| \`kgi.md\``／#6 `- [design.md]`／#7 `- \`spec.md\``／#8 `- 定点観測台帳`／#9 `- 親: 索引`／#10 `- [同テーマの実物確認]`／#12 `- [kgi.md]`。

### 4-4. 2本を移す

1. `git mv docs/specs/master-ssot-migration/design-fix-unify-type-mismatch.md docs/handoff/fix-unify-type-mismatch/design-fix-unify-type-mismatch.md`
2. `git mv docs/specs/master-ssot-migration/recon-fix-unify-type-mismatch.md docs/handoff/fix-unify-type-mismatch/recon-fix-unify-type-mismatch.md`
3. docs/handoff/fix-unify-type-mismatch/design.md の :42 と :43 の行末に、それぞれ `（2026-10 に同フォルダへ移動）` を足す（パスは書き換えない＝記録の原本はそのまま）。
4. 移す前に `git grep -n 'design-fix-unify-type-mismatch\|recon-fix-unify-type-mismatch' HEAD` を実行し、出力を報告に貼る。F4 以外（design.md:42-43 と移す2本の中身以外）に参照があれば、移さずに NEEDS_DECISION:。

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/an-stage2/impl/ に保存）

5-1. `wc -l docs/INDEX.md`（期待: 60 以下）と、§4-1 のコードブロックの中身との `diff`（期待: 差分なし）。
5-2. `awk -F'|' 'NR>=11 && NR<=88 { if (NF!=6 || $5 ~ /^[[:space:]]*$/) print NR": "$0 }' docs/specs/README.md`（期待: 何も出ない＝78行すべて4列で「いつ読むか」が空でない）。あわせて `sed -n 9,10p docs/specs/README.md` と :99 の行。
5-3. `git diff "$(git merge-base origin/main HEAD)" -- docs/specs/README.md | grep '^-' | grep -v '^---' | wc -l` が 81（変えた行 = 見出し2行＋データ78行＋:99 の1行）、`grep '^+' | grep -v '^+++' | wc -l` も 81。
5-4. `git diff "$(git merge-base origin/main HEAD)" -- docs/specs/attachment-storage/README.md docs/specs/dashboard/README.md docs/specs/schedule/README.md docs/specs/inbox/README.md docs/specs/inventory-management/README.md docs/specs/ledger-guard/README.md docs/specs/process-hardening/README.md docs/specs/product-master/README.md docs/specs/local-hooks-ssot/README.md` の全文（期待: `+` の行が13行で、`---` 以外の `-` の行が無い）。
5-5. 親の表紙から名前で引けることを、次の grep で示す（各行 1 件以上ヒット。#14・#15 は proof-of-behavior/README.md に名前があること）:
`grep -c '](./to-be.md)' docs/specs/attachment-storage/README.md docs/specs/dashboard/README.md docs/specs/schedule/README.md`／`grep -c '](./track-record.md)' docs/specs/dashboard/README.md docs/specs/schedule/README.md docs/specs/inbox/README.md`／`grep -c 'spec-v1.0.md' docs/specs/inventory-management/README.md`／`grep -c 'design-g2.md' docs/specs/ledger-guard/README.md`／`grep -c 'design-pillar1.md\|proof-of-behavior/README.md' docs/specs/process-hardening/README.md`／`grep -c 'product-classification-decisions.md\|2026-09-tcg-product-master-fill-title-date.md' docs/specs/product-master/README.md`／`grep -c 'guard-disabled-record.md' docs/specs/local-hooks-ssot/README.md`／`grep -c 'ideal-state.md\|kgi.md' docs/specs/process-hardening/proof-of-behavior/README.md`／`grep -c 'lessons.d/' docs/INDEX.md`。
5-6. `git status --short` と `git diff "$(git merge-base origin/main HEAD)" --stat -M`（期待: §3 のファイルだけ。移動2本は rename として 100% で出る）。
5-7. 参考の測定（合否には使わない。段2-2 の数え方を決める材料）: ~/CC報告ファイル-keep/agenda-nav-20261022/unreach/reach.py を /tmp/CC報告ファイル/an-stage2/impl/reach-index.py に写し、写しの :12 の `entries = [...]` だけを `entries = ["docs/INDEX.md"]` に変え、`python3 -I /tmp/CC報告ファイル/an-stage2/impl/reach-index.py "$PWD" plain HEAD` と `... any HEAD` の2つを実行して全文を保存する。リポジトリにはこの台本を入れない。

## 6. 分岐ごとの対処

- §4-2・§4-3 の行の照合が合わない → その時点で書くのをやめ、合わない行番号と実物の行を貼って BLOCKED:。
- §4-4 の 4 で想定外の参照がある → 移さずに NEEDS_DECISION:。
- 見張りや自動判定に止められた → 言い換えず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 5-7 の台本がエラーで止まる → 合否に関係しないので、エラーの全文を保存して報告に書き、他の手順は続ける。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 目次 docs/INDEX.md が 60行以下で、章A〜F の各行に「いつ読むか」がある | §5-1（§4-1 と差分なし） |
| 仕様書の索引の78行すべてに「いつ読むか」がある | §5-2 |
| 索引の既存の中身は変えていない（列を足しただけ） | §5-3・レビューでの目視 |
| 届かなかった specs 17本が、15本は表紙から、2本は移動先の記録置き場からたどれる | §5-4・§5-5・§5-6 |
| lessons.d が目次からフォルダとして登録されている | §5-1（§4-1 の章A の行） |
| 触ったのは §3 のファイルだけ | §5-6 |

## 8. 戻し方

この PR の revert を main にマージする（移動2本も元の場所に戻る）。

## 9. PR

- 作業場所 /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage2 は Opus が `bash scripts/new-worktree.sh release/doc-agenda-nav-stage2`（origin/main ce23a7930 起点・2026-10-23）で作成済みで、このカードのコミットも載っている。担当は作り直さない。以後はすべてそこに `cd` してから行う。
- push は `git push -u origin release/doc-agenda-nav-stage2`。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/doc-agenda-nav-stage2 -1 --oneline` で確かめる。
- PR は `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-stage2/pr-body.md` を作り、`--body-file` で渡す。作成前に `gh auth status` で `shingo-cc` 名義を確かめる。ready で作る（`--draft` を付けない）。base は main。担当はマージしない。
- 本文は PR テンプレートに沿う。`### 標準ワークフロー確認` に recon・設計・unreachable-list.md・このカード、`対象ADR: ADR-1040（関連: ADR-076）`、`設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`、`PO承認: 「1」（2026-10-23。誤作動直し・目次の新設・決まりの引っ越しまでを順に進める選択肢への返事）`、`Opus 審査記録: コード審査はこれから`、区分は `書類のみ。ADR-1015 の A/B 区分の判定は Opus に委ねる` と書く。`触るファイル:` と `削除するファイル:` は1行・カンマ区切り・バッククォートなし。`削除するファイル:` には行を書き換えた既存ファイル（docs/specs/README.md と docs/handoff/fix-unify-type-mismatch/design.md）と、移動元の2本を書く。
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（Bash の timeout は 240000 以下）。

## 10. 報告

- 完了報告に: 冒頭の受領文／§5-1〜5-7 の出力（長いものはファイルのパス）／PR の URL／判断を要した点（事実のみ）
- 停止したとき: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 委任の定型: sleep しない／ファイルの作成と編集は Write/Edit ツールで行う／PR 作成前に validate-pr-body.sh で exit 0／フックや自動判定に止められたら言い換えて再試行しない

## 11. 報告欄（担当が追記）

本報告はカード doc-agenda-nav 段2-1 の実行結果である（2026-10-23 Sonnet）。生出力: /tmp/CC報告ファイル/an-stage2/impl/

- 5-1: INDEX.md 22行・§4-1 と差分なし。5-2: 欠落0。5-3: 変えた行 81／81。5-4: `+` 13行・`-` 0行。5-5: 全項目1件以上。5-6: §3 のファイルのみ・移動2本は rename。
- 5-7: reach-index.py を実行（plain: docs/specs/ 未到達37・any: 未到達0）。参考値で合否に使わない。
- 判断を要した点: PR 本文検証で「設計docは単一パス」「移動は波括弧形式で宣言」が必要だった（本文のみ調整）。

END OF CARD
