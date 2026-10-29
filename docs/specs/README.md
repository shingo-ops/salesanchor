# 設計仕様書 索引（あるべき姿の地図）

> この一覧は「どの領域の開発で、どの設計仕様書（あるべき姿）を正本にするか」を引くための地図。
> ルールの正本は [`docs/STANDARD-WORKFLOW.md`](../STANDARD-WORKFLOW.md) §1.5。
> **索引に載る領域に触れる開発は、その設計仕様書を先に読む（無ければ作る）。**

## 一覧

| 領域 | 設計仕様書（あるべき姿） | 状態 | いつ読むか |
|---|---|---|---|
| AI 保守運用 24 時間化（ai-ops-247。報知器の感度・精度、応急処置、Mac に頼らない AI 起動〔routines〕、障害記録と月次成績表。discord-ops-intake は Mac 依存のため本テーマの予備 C） | [ai-ops-247/README.md](ai-ops-247/README.md) | あるべき姿・KGI 6件 PO承認 2026-10-13・recon・design・ADR-1012 草案・実装未着手 | 監視・障害対応・AI の自動起動を変える前 |
| まとめ売り（N単位セット）の読み取り（bundle-sale。「40パックセット/¥24,000 残り15」を全商品で 商品名＋40パックセット／中身の単位／まとめ1つの値段／まとめの数 で保存・表示。ADR-1021 便2 の置き換え） | [bundle-sale/README.md](bundle-sale/README.md) | あるべき姿 2026-10-17・KGI K1〜K6 PO 合意 2026-10-17・recon・design（審査 APPROVE）・ADR-1027 Proposed・便1 カード作成・実装未着手 | まとめ売り（セット）の読み取り・保存・表示を変える前 |
| 解析の誤り報告から自律修正まで（analysis-error-report。在庫表の行ドロワーで誤りと正解を報告→Discord→agent-console の自動セッション→再解析と機械照合→Discord に記録） | [analysis-error-report/README.md](analysis-error-report/README.md) | あるべき姿・KGI PO承認 2026-10-17・recon・design草案・実装未着手 | 解析の誤り報告から自動修正までの流れを変える前 |
| Discord 監視通知 → AI 保守運用（discord-ops-intake。監視 webhook を Claude Code が受けて調査・委任範囲で対応） | [discord-ops-intake/README.md](discord-ops-intake/README.md) | あるべき姿・KGI提示（KGI-3 PO修正反映）・recon・design草案 2026-10-13・実装未着手 | 監視の通知を受けて AI が動く仕組みを変える前 |
| ブランチ運用（develop 廃止後の開発環境） | [branch-operations/README.md](branch-operations/README.md) | 公開 | ブランチ・作業場所の作り方、PR・マージの手順を変える前 |
| reaper 自動掃除（worktree の自動回収） | [reaper-auto-cleanup/README.md](reaper-auto-cleanup/README.md) | あるべき姿・KGI・recon・design済 2026-07-22 | 作業場所の自動回収を変える前 |
| AI向け指示文書の「入口→目次→章→末端ページ」化（doc-agenda-nav。会話のたびに読む文書を短い入口だけにし、手順書は目次からたどって必要なときだけ読む） | [doc-agenda-nav/README.md](doc-agenda-nav/README.md) | 完了・KGI 全項目合格（2026-10-26・#4772）・ADR-1040・段1b #4775 | AI 向け指示文書の入口・目次を変える前 |
| 決まりを機械の検査に変える（rule-enforcement。誰が作業しても決まり違反の変更が main に入らず本番に出ないように、決まりを台帳で仕分け、必須チェック・違反の見本・提出前の検査で守る） | [rule-enforcement/README.md](rule-enforcement/README.md) | KGI G1〜G5 PO 承認 2026-10-27・recon・design（審査5回目 APPROVE・#4815）・R0 調査完了（recon §12）・R1a 台帳と検査を警告で開始（ADR-1047 Proposed）・R0.5 以降未着手 | 決まりの文書・必須チェック・提出前の検査を変える前 |
| 文書の親子構造 標準ルール化 | doc-parent-child/README.md (doc-parent-child/README.md) | 公開 | 表紙と子文書の親子をつくる・並べ替える前 |
| 商品マスタ | [product-master/README.md](product-master/README.md) | 公開 | 商品マスタの項目・登録・照合を変える前 |
| 設計パートナー長期安定体制（循環の形） | [design-partner-loop/README.md](design-partner-loop/README.md) | 公開 | 設計の担当の進め方を変える前 |
| エージェント完結の設計体制 | [agent-complete-design/README.md](agent-complete-design/README.md) | 公開 | AI だけで設計を進める体制を変える前 |
| 開発の無駄な停止ゼロ | [dev-continuity/README.md](dev-continuity/README.md) | 公開 | 開発が止まる原因（待ち・見張り）を直す前 |
| 台帳と本店の守り（ledger-guard。本店に書類を置きっぱなしにせず各自の作業場所に書く守りと、台帳の書き先の分割） | [ledger-guard/README.md](ledger-guard/README.md) | 第1弾適用済み・KGI-G1達成 2026-07-04 | 本店（main の写し）を守る見張りや、台帳の書き先を変える前 |
| GO記録の自動転記・マージ前検査 | [go-record-transcription/](../handoff/go-record-transcription/)・[LINE期限付き委任](../handoff/go-record-transcription/line-delegation.md) | 設計範囲・GO取消期限PO合意 2026-09-10・方式全体は草案/自己審査REVISE | GO の記録・マージ前の検査を変える前 |
| 画面部品の標準（component-standard） | [component-standard.md](component-standard.md) | 公開 | 画面部品を新しく作る・変える前 |
| UI/UXデザインシステム（design-system。トークン・共通部品・SSOT。component-standardは本テーマの子） | [design-system/README.md](design-system/README.md) | KGI・design承認済 2026-07-04 | 色・部品・画面の見た目を変える前 |
| ├ ページタイトル金型（page-title。題名・説明文を共通部品PageLayoutに集約・1ヵ所直せば全ページ変わる） | [design-system/component-ssot/page-title/README.md](design-system/component-ssot/page-title/README.md) | 公開（全ページ移行完了 2026-07-19） | ページの題名・説明文を変える前 |
| └ ページヘッダー金型v2（page-header-v2。ヘッダー枠の中身と並びの統一＋階層パンくず＋位置ズレ番人） | [design-system/component-ssot/page-header-v2/README.md](design-system/component-ssot/page-header-v2/README.md) | あるべき姿改訂5済・便1〜3a本番反映済・操作台実装前 2026-07-20 | ページ上部（ヘッダー・パンくず）を変える前 |
| └ 入力部品 寸法金型（field-size。プルダウン・入力欄の高さ3段×幅3段を独立選択で統一） | [design-system/component-ssot/field-size/README.md](design-system/component-ssot/field-size/README.md) | あるべき姿確定・KGI/design骨子済・実装前 2026-07-21 | プルダウン・入力欄の大きさを変える前 |
| └ アプリ視覚デザイン言語（visual-language。金型の美しさ・PC/スマホの使いやすさ・ベンチマーク観察。値の正本はトークン/金型のまま） | [design-system/visual-language/README.md](design-system/visual-language/README.md) | KGI承認済 2026-10-02・設計草案・実装前 | 画面の見た目の方向性を変える前 |
| デザイントークンSSOT化（色・文字・アイコン・コンポーネント・文字サイズ・値・アニメーション・グラフ・ページ構成の索引化・重複排除） | [design-tokens-ssot/README.md](design-tokens-ssot/README.md) | あるべき姿・KGI承認済 2026-07-09 | 色・文字・アイコンなどの値を足す・変える前 |
| └ カレンダー色CSS変数化（schedule の 7 カレンダー色） | [design-tokens-ssot/color/calendar/README.md](design-tokens-ssot/color/calendar/README.md) | 公開 | カレンダーの色を変える前 |
| └ アイコン色の用途別トークン集約（10箇所の色決定ポイントをカテゴリ別に束ねる） | [design-tokens-ssot/color/icon/README.md](design-tokens-ssot/color/icon/README.md) | 公開 | アイコンの色を変える前 |
| 在庫管理 | [inventory-management/README.md](inventory-management/README.md) | 親のあるべき姿・KGI確定 2026-07-12・A/B/C/feed-translation/inventory-analytics すべて あるべき姿・KGI・To-Be完成 | 在庫の取り込み・表示・解析を変える前 |
| ├ 提供元フィード翻訳（feed-translation） | [inventory-management/feed-translation/README.md](inventory-management/feed-translation/README.md) | あるべき姿・KGI完成 2026-07-05 | 仕入元の投稿の翻訳を変える前 |
| ├ LINE完売ルールの認識合わせ・引き継ぎ | [合意と未決事項](../handoff/tcg-import-latest-only/sold-out-rules-handoff.md) | C01〜C43合意・[詳細設計案](../handoff/tcg-import-latest-only/sold-out-rules-design.md)作成・本番DB/接続実測済・自己審査REVISE・Q24未決。実装未着手 | LINE の完売の読み取りの規則を変える前 |
| │ ├ 同じ投稿の〆を在庫の件に効かせる（規則13。価格のない〆が同じ商品・状態の在庫の件を完売にする） | [設計](../handoff/v102-shime-same-post-stock/design.md) | KGI PO承認 2026-10-19・設計案・審査反映済・本番反映済（#4525、2026-10-19） | 〆の投稿で在庫を完売にする規則を変える前 |
| │ └ v102 の決まりの直し（v102-rule-fixes。状態の言葉の表「傷あり」系・状態の語で単位を上書きする条件・状態の見出し・件の外の〆を、一度に1つずつ直す） | [設計](../handoff/v102-rule-fixes/design.md) | KGI・便の分け方 PO承認 2026-10-25・自己審査（便1・2 APPROVE／便3・4 REVISE）・実装未着手 | v102 の状態・単位・見出し・〆の決まりを変える前 |
| ├ 在庫の閲覧専用ページ（inventory-viewer。お客さんが自社サーバーで在庫表だけを見る・GAS 在庫一覧の置き換え） | [inventory-management/inventory-viewer/README.md](inventory-management/inventory-viewer/README.md) | あるべき姿・KGI 作成 2026-10-15・設計 PO 承認済 2026-10-16・実装着手 | お客さん向けの在庫閲覧ページを変える前 |
| └ 在庫解析（inventory-analytics） | [inventory-management/inventory-analytics/README.md](inventory-management/inventory-analytics/README.md) | あるべき姿・KGI・To-Be完成 2026-07-15 | 在庫の分析機能を変える前 |
| 管理センター（management-center。全データの基盤管理＝データセンターの役割。CRM等の分析機能とは意図的に別役割） | [management-center/README.md](management-center/README.md) | あるべき姿・KGI・To-Be確定 2026-07-15 | 全データの基盤管理の画面を変える前 |
| ├ 種類分けマスタ（tcg_type） | （作成予定） | 未 | 種類分けマスタを作る・変える前（仕様書はまだ無い） |
| ├ 品目マスタ（item） | （作成予定） | 未 | 品目マスタを作る・変える前（仕様書はまだ無い） |
| ├ HTSコードマスタ | （作成予定） | 未 | HTS コードマスタを作る・変える前（仕様書はまだ無い） |
| ├ 素材マスタ | （作成予定） | 未 | 素材マスタを作る・変える前（仕様書はまだ無い） |
| ├ 状態マスタ（condition） | （作成予定） | 未 | 状態マスタを作る・変える前（仕様書はまだ無い） |
| └ 単位マスタ（unit） | （作成予定） | 未 | 単位マスタを作る・変える前（仕様書はまだ無い） |
| 取引フロー（lead→deal→company→order・SSOT） | [transaction-flow/README.md](transaction-flow/README.md) | KGI承認済 2026-07-02 | 引き合い・商談・会社・注文のつながりを変える前 |
| リードをまとめる（lead-merge。取引フローの子。13表の付け替え・空欄だけ埋める・受信箱カルテの「⋯」から） | [transaction-flow/lead-merge/README.md](transaction-flow/lead-merge/README.md)（関連: ADR-1049, 119） | あるべき姿=PO発言転記・設計審査済み 2026-10-28 | 同じお客さまの2件のリードをまとめる機能を変える前 |
| DB設計のSSOT化（db-ssot。同じ事実は1か所・データ分散防止。会話/予測値/金額/分類の重複解消） | [db-ssot/README.md](db-ssot/README.md) | あるべき姿・KGI確定 2026-07-09 | DB に表・列を足す・変える前 |
| 文書体系（ナレッジベース） | [doc-estate/README.md](./doc-estate/README.md) | KGI承認済 | docs/ の文書の置き場所を決める前 |
| 教訓の1便1ファイル化（lessons-guard。design-partner.md §6追記衝突の根絶） | [lessons-guard/README.md](./lessons-guard/README.md) | 設計中 | 教訓メモを書く・清書する前 |
| Sales Anchor アプリ全体（親） | [sales-anchor-app/README.md](sales-anchor-app/README.md) | KGI承認済 2026-07-04 | アプリ全体の構成（ページの並び・役割分担）を変える前 |
| 見積もり・請求書（quote-invoice。独立ページ・受信箱からは導線のみ） | [quote-invoice/README.md](quote-invoice/README.md) | あるべき姿・KGI確定 2026-07-08 | 見積書・請求書を変える前 |
| 売上管理（sales-management。売上そのものの分析・ダッシュボード/CRMとは非重複） | [sales-management/README.md](sales-management/README.md) | あるべき姿・KGI・To-Be確定 2026-07-09 | 売上の集計・分析を変える前 |
| 顧客管理（customer-management。顧客の理解・優先順位・引き継ぎに専念。売上の本格数値のベース） | [customer-management/README.md](customer-management/README.md) | あるべき姿・KGI・To-Be確定 2026-07-10 | 顧客の情報・画面を変える前 |
| プロフィール・アカウント設定（profile-account-settings。プロフィール=テナント/アカウント設定=個人スタッフ。オーナー設定はプロフィールに統合） | [profile-account-settings/README.md](profile-account-settings/README.md) | あるべき姿・KGI・To-Be確定 2026-07-11 | 会社のプロフィール・個人のアカウント設定を変える前 |
| recon（現状把握）標準（あるべき姿・KGI・調査観点ひな型の集約） | [recon-standard/README.md](recon-standard/README.md) | あるべき姿・KGI承認済 2026-07-06 | 現状把握（recon）のやり方を変える前 |
| カレンダー（schedule。全予定の見える化・源泉SSOT参照・やることフィード共有） | [schedule/README.md](schedule/README.md) | KGI承認済 2026-07-03 | 予定・カレンダーを変える前 |
| ダッシュボード（dashboard。羅針盤・やることフィード・目標カスケード・AI提案） | [dashboard/README.md](dashboard/README.md) | KGI承認済 2026-07-03 | ダッシュボードを変える前 |
| チームボード（team-board。ボールの所在・無担当警報・presence。接点：受信箱がSSOT） | [team-board/README.md](team-board/README.md) | KGI承認済 2026-07-03 | チームボードを変える前 |
| 受信箱（inbox。全顧客やり取りの集約表示・子テーマの配置定義。親は見せ方のみ） | [inbox/README.md](inbox/README.md) | KGI承認済 2026-07-04 | 受信箱の画面を変える前 |
| 受注管理(業務画面。ステータス別ページ・境界:データ構造は取引フローが正本) | [order-management/README.md](order-management/README.md) | KGI承認済 2026-07-04 | 受注の業務画面を変える前 |
| 在庫（自社在庫／ドロップシッピングの2種。接点：order_item の出どころ参照） | （仕様書未作成） | **pending** | 自社在庫とドロップシッピングの区別を扱う前（仕様書はまだ無い） |
| 予約販売（接点：order の派生フロー） | （仕様書未作成） | **pending** | 予約販売を扱う前（仕様書はまだ無い） |
| 送料マスタ（接点：見積送料の算出） | （仕様書未作成） | **pending** | 送料の計算を扱う前（仕様書はまだ無い） |
| 請求先/配送先の住所区別（接点：company/order の住所） | （仕様書未作成） | **pending** | 請求先・配送先の住所を扱う前（仕様書はまだ無い） |
| 為替レート | （仕様書未作成・関連ADR: ADR-148） | 未 | 為替レートを扱う前（関連 ADR を読む） |
| 翻訳送信・グロッサリ（接点: conversation_logs。会話ログの紐付けは取引フロー） | [inbox/translation-glossary/README.md](inbox/translation-glossary/README.md) | 仕様書あり（KGI承認済み・To-Be design済・recon未） | 翻訳して送る機能・用語集を変える前 |
| 帳票・フォーム送付（見積・請求書・フォームの送付導線。中身の作りは quote-invoice、入金確認は受注管理を参照） | [inbox/invoice-form-send/README.md](inbox/invoice-form-send/README.md) | 仕様書あり（KGI承認済み・To-Be design済・recon未） | 見積・請求書・フォームを送る導線を変える前 |
| 定型文(message-templates。人が書く文章ひな型の設定画面と受信箱からの呼び出し。AI翻訳は translation-glossary が正本・独立) | [inbox/message-templates/README.md](inbox/message-templates/README.md) | 仕様書あり(KGI承認済み・To-Be design済・recon未) | 定型文の設定・呼び出しを変える前 |
| Discord連携 | （仕様書未作成・関連: ADR-009, 014, 100, 091） | 未 | Discord との連携を変える前（関連 ADR を読む） |
| Meta（FB/IG）連携 | （仕様書未作成・関連: ADR-024, 025, 041, 026） | 未 | Facebook・Instagram との連携を変える前（関連 ADR を読む） |
| 認証・権限・ロール（auth-roles。各社のロールと運営者 super admin の境界） | [auth-roles/README.md](auth-roles/README.md)（関連: ADR-023, 032, 138, 147, 1007） | 仕様書あり（あるべき姿=PO発言転記・KGI PO承認済み 2026-10-10） | ロール・権限を変える前 |
| ログイン方式（auth-login。自社サーバーでのパスワード・パスキー・再設定メール） | [auth-login/README.md](auth-login/README.md)（関連: ADR-1013, 138, 1008） | 仕様書あり（あるべき姿=PO発言転記・KGI PO承認済み 2026-10-13） | ログイン・パスキー・再設定メールを変える前 |
| テナント管理・RLS（tenant-rls。会社ごとのデータを DB の RLS で他社から見えなくする） | [tenant-rls/README.md](tenant-rls/README.md)（関連: ADR-1018, 145, 072, 131, 034, 036） | 仕様書あり（あるべき姿=PO発言転記・KGI PO承認済み 2026-10-15・段階①〜③ 本番反映済み 2026-10-16・KGI-1/3 ○、KGI-2 はログイン成功と画面目視が未観測） | 会社ごとのデータの分け方（RLS）を変える前 |
| 接続元 IP の決め方（client-ip。回数制限・監査記録・セッション保護に使う IP を、利用者が書き換えられない値から 1 つの関数で決める） | [client-ip/README.md](client-ip/README.md)（関連: ADR-127, 1013, 1019） | 仕様書あり（あるべき姿=PO発言転記・KGI PO承認済み 2026-10-16・本番反映済み 2026-10-16 #4390・K1〜K4 ○・追補 S5b 端末登録 #4437 本番反映 2026-10-17・D1〜D3 ○） | 接続元 IP の扱いを変える前 |
| 例外の中身を応答に出さない（db-error-detail。DB の失敗時に SQL 文・入力値を画面に出さず、ログにだけ残す） | [db-error-detail/README.md](db-error-detail/README.md) | 仕様書あり（あるべき姿=PO発言転記・KGI PO承認済み 2026-10-16・本番反映済み #4399・K1〜K3 ○） | エラー時の応答の中身を変える前 |
| 一覧の全件取得・ファイル出力の記録と閲覧の大量検知（get-access-audit。誰が全件や CSV を取ったかを記録し、10 分 500 回超の閲覧を警告） | [get-access-audit/README.md](get-access-audit/README.md) | 仕様書あり（あるべき姿=PO発言転記・KGI は 2026-10-17 一任に基づき Opus 確定・本番反映済み #4411・K1〜K4 ○・追補1 #4421 F1〜F3 ○） | 全件取得・ファイル出力・閲覧の記録を変える前 |
| 権限・秘密SSOT化（secrets-permission-ssot。鍵・権限を1冊の台帳で管理し置き間違いを警報） | [secrets-permission-ssot/README.md](secrets-permission-ssot/README.md) | あるべき姿確定・KGI確定 2026-07-20 | 鍵・権限の台帳を変える前 |
| 出荷キャリア連携（接点: order_shipping_details。発送の事実は取引フロー） | （仕様書未作成・関連: ADR-103, 123, 128） | 未 | 配送業者との連携を扱う前（関連 ADR を読む） |
| 開発ループの自動ガード化（process-hardening。AIエージェントの手順ミスを機械で自動で止める/正す） | [process-hardening/README.md](process-hardening/README.md) | あるべき姿確定 2026-07-19 | 手順ミスを止める見張り・関所を足す・変える前 |
| サーバーリソース最適化 | docs/specs/server-resource-optimization/README.md(メモリ・ディスクのゴミ排除と自動掃除) | 公開 | サーバーのメモリ・ディスクの掃除を変える前 |
| Docker（Colima）使い終わり自動停止（colima-idle-stop。PO の Mac で使っていない試験用 DB の入れ物を自動で止めてメモリを空ける） | [colima-idle-stop/README.md](colima-idle-stop/README.md) | あるべき姿=PO発言転記・実装済み（#4294）・KGI 7/7 合格 2026-10-15 | Mac の試験用 DB の自動停止を変える前 |
| Mac の自動お手入れの見張り（mac-jobs-watch。Docker 自動停止と毎日の自動片付けが止まったり失敗したりしたら Discord で知らせる） | [mac-jobs-watch/README.md](mac-jobs-watch/README.md) | あるべき姿=PO発言転記・設置済み K1〜K5 合格（2026-10-15 #4315）・K6 観測待ち | Mac の定期作業の見張りを変える前 |
| 仮想マシンが要る試験を GitHub で行う（vm-test-on-gha。PO の Mac で試験用の仮想マシンを作らず、GitHub のコンピュータで試す） | [vm-test-on-gha/README.md](vm-test-on-gha/README.md) | あるべき姿=PO発言転記・KGI PO承認済み 2026-10-16・設計審査済み・実装中 | 仮想マシンが要る試験を行う前 |
| 個人側検問の正本化(local-hooks-ssot) | [local-hooks-ssot/README.md](local-hooks-ssot/README.md) | あるべき姿・KGI承認済 2026-07-20 | ~/.claude の見張り（フック）を変える前 |
| └ 社外秘の原文の書き写しを送る前に止める見張り（confidential-quote-guard。仕入元の投稿の文面を書類に書き写したまま git push・PR 本文で送ろうとすると止める） | [設計](../handoff/confidential-quote-guard/design.md) | 方針 PO「2」2026-10-25・自己審査 APPROVE・実装未着手 | 社外秘の書類の扱い・送る前の見張りを変える前 |
| データ保全（data-durability。バックアップ・多重化・復旧演習。壊れないことと戻せることの両方） | [data-durability/README.md](data-durability/README.md) | あるべき姿・KGI承認済 2026-09-01 | バックアップ・復旧の仕組みを変える前 |
| 添付ファイルの保管（attachment-storage。Discord等で受けた画像を自社保存し、期限切れ・投稿削除でも受信箱に残す） | [attachment-storage/README.md](attachment-storage/README.md) | あるべき姿・KGI確定 2026-09-01 | 受信した画像の保存を変える前 |
| Discordリアクション（discord-reaction。受信箱でDiscordと同じように絵文字を付ける・見る） | discord-reaction/README.md | あるべき姿・KGI確定 2026-09-04 | 受信箱の絵文字リアクションを変える前 |
| LINE解析 Gemini 書き写しの調整記録（line-analysis-tuning。版をまたいだ精度の推移・PO の判断・事故の履歴台帳） | [line-analysis-tuning/README.md](line-analysis-tuning/README.md)・[試験の記録](line-analysis-tuning/track-record.md) | 公開（記録開始 2026-10-07） | LINE 解析の指示書を変える前、精度の推移を確かめるとき |


## specs外に散在する仕様書（存在の記録のみ・中身の判定は棚卸し便で）
以下は docs/ 直下に置かれた仕様書らしきファイル。生きているか古いかは未確認。移動・削除はここではしない。
- docs/FEATURE_SPECIFICATION.md
- docs/FEEDBACK_FORM_DESIGN.md
- docs/data_deletion_callback_design.md
- docs/products_design.md

## 追加のしかた
新しい設計仕様書を作ったら、この表に「領域名｜相対リンク｜状態｜いつ読むか」を1行足す。「いつ読むか」は空欄にしない（目次 docs/INDEX.md の章B）。
状態は「公開＝読める／未＝これから作る」の2値で書く。
凡例（暫定・正規化は棚卸し便で実施）: 未＝枠のみ／pending＝接点記載済み・仕様書未作成／草案＝作成中／KGI承認済＝あるべき姿とKGIがPO承認済み。
