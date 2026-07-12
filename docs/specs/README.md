# 設計仕様書 索引（あるべき姿の地図）

> この一覧は「どの領域の開発で、どの設計仕様書（あるべき姿）を正本にするか」を引くための地図。
> ルールの正本は [`docs/STANDARD-WORKFLOW.md`](../STANDARD-WORKFLOW.md) §1.5。
> **索引に載る領域に触れる開発は、その設計仕様書を先に読む（無ければ作る）。**

## 一覧

| 領域 | 設計仕様書（あるべき姿） | 状態 |
|---|---|---|
| ブランチ運用（develop 廃止後の開発環境） | [branch-operations/README.md](branch-operations/README.md) | 公開 |
| 文書の親子構造 標準ルール化 | doc-parent-child/README.md (doc-parent-child/README.md) | 公開 |
| 商品マスタ | [product-master/README.md](product-master/README.md) | 公開 |
| 設計パートナー長期安定体制（循環の形） | [design-partner-loop/README.md](design-partner-loop/README.md) | 公開 |
| エージェント完結の設計体制 | [agent-complete-design/README.md](agent-complete-design/README.md) | 公開 |
| 開発の無駄な停止ゼロ | [dev-continuity/README.md](dev-continuity/README.md) | 公開 |
| GO記録の自動転記 | [go-record-transcription/](../handoff/go-record-transcription/) | 草案 |
| 画面部品の標準（component-standard） | [component-standard.md](component-standard.md) | 公開 |
| UI/UXデザインシステム（design-system。トークン・共通部品・SSOT。component-standardは本テーマの子） | [design-system/README.md](design-system/README.md) | KGI・design承認済 2026-07-04 |
| デザイントークンSSOT化（色・文字・アイコン・コンポーネント・文字サイズ・値・アニメーション・グラフ・ページ構成の索引化・重複排除） | [design-tokens-ssot/README.md](design-tokens-ssot/README.md) | あるべき姿・KGI承認済 2026-07-09 |
| └ カレンダー色CSS変数化（schedule の 7 カレンダー色） | [design-tokens-ssot/color/calendar/README.md](design-tokens-ssot/color/calendar/README.md) | 公開 |
| └ アイコン色の用途別トークン集約（10箇所の色決定ポイントをカテゴリ別に束ねる） | [design-tokens-ssot/color/icon/README.md](design-tokens-ssot/color/icon/README.md) | 公開 |
| 在庫管理 | [inventory-management/README.md](inventory-management/README.md) | 親README公開（A/B/C完成・D未着手） |
| ├ 提供元フィード翻訳（feed-translation） | [inventory-management/feed-translation/README.md](inventory-management/feed-translation/README.md) | あるべき姿・KGI完成 2026-07-05 |
| └ 在庫解析（inventory-analytics） | [inventory-management/inventory-analytics/README.md](inventory-management/inventory-analytics/README.md) | 表紙のみ・KGI未 |
| ├ 種類分けマスタ（tcg_type） | （作成予定） | 未 |
| ├ 品目マスタ（item） | （作成予定） | 未 |
| ├ HTSコードマスタ | （作成予定） | 未 |
| ├ 素材マスタ | （作成予定） | 未 |
| ├ 状態マスタ（condition） | （作成予定） | 未 |
| └ 単位マスタ（unit） | （作成予定） | 未 |
| 取引フロー（lead→deal→company→order・SSOT） | [transaction-flow/README.md](transaction-flow/README.md) | KGI承認済 2026-07-02 |
| DB設計のSSOT化（db-ssot。同じ事実は1か所・データ分散防止。会話/予測値/金額/分類の重複解消） | [db-ssot/README.md](db-ssot/README.md) | あるべき姿・KGI確定 2026-07-09 |
| 文書体系（ナレッジベース） | [doc-estate/README.md](./doc-estate/README.md) | KGI承認済 |
| Sales Anchor アプリ全体（親） | [sales-anchor-app/README.md](sales-anchor-app/README.md) | KGI承認済 2026-07-04 |
| 見積もり・請求書（quote-invoice。独立ページ・受信箱からは導線のみ） | [quote-invoice/README.md](quote-invoice/README.md) | あるべき姿・KGI確定 2026-07-08 |
| 売上管理（sales-management。売上そのものの分析・ダッシュボード/CRMとは非重複） | [sales-management/README.md](sales-management/README.md) | あるべき姿・KGI・To-Be確定 2026-07-09 |
| 顧客管理（customer-management。顧客の理解・優先順位・引き継ぎに専念。売上の本格数値のベース） | [customer-management/README.md](customer-management/README.md) | あるべき姿・KGI・To-Be確定 2026-07-10 |
| プロフィール・アカウント設定（profile-account-settings。プロフィール=テナント/アカウント設定=個人スタッフ。オーナー設定はプロフィールに統合） | [profile-account-settings/README.md](profile-account-settings/README.md) | あるべき姿・KGI・To-Be確定 2026-07-11 |
| recon（現状把握）標準（あるべき姿・KGI・調査観点ひな型の集約） | [recon-standard/README.md](recon-standard/README.md) | あるべき姿・KGI承認済 2026-07-06 |
| カレンダー（schedule。全予定の見える化・源泉SSOT参照・やることフィード共有） | [schedule/README.md](schedule/README.md) | KGI承認済 2026-07-03 |
| ダッシュボード（dashboard。羅針盤・やることフィード・目標カスケード・AI提案） | [dashboard/README.md](dashboard/README.md) | KGI承認済 2026-07-03 |
| チームボード（team-board。ボールの所在・無担当警報・presence。接点：受信箱がSSOT） | [team-board/README.md](team-board/README.md) | KGI承認済 2026-07-03 |
| 受信箱（inbox。全顧客やり取りの集約表示・子テーマの配置定義。親は見せ方のみ） | [inbox/README.md](inbox/README.md) | KGI承認済 2026-07-04 |
| 受注管理(業務画面。ステータス別ページ・境界:データ構造は取引フローが正本) | [order-management/README.md](order-management/README.md) | KGI承認済 2026-07-04 |
| 在庫（自社在庫／ドロップシッピングの2種。接点：order_item の出どころ参照） | （仕様書未作成） | **pending** |
| 予約販売（接点：order の派生フロー） | （仕様書未作成） | **pending** |
| 送料マスタ（接点：見積送料の算出） | （仕様書未作成） | **pending** |
| 請求先/配送先の住所区別（接点：company/order の住所） | （仕様書未作成） | **pending** |
| 為替レート | （仕様書未作成・関連ADR: ADR-148） | 未 |
| 翻訳送信・グロッサリ（接点: conversation_logs。会話ログの紐付けは取引フロー） | [inbox/translation-glossary/README.md](inbox/translation-glossary/README.md) | 仕様書あり（KGI承認済み・To-Be design済・recon未） |
| Discord連携 | （仕様書未作成・関連: ADR-009, 014, 100, 091） | 未 |
| Meta（FB/IG）連携 | （仕様書未作成・関連: ADR-024, 025, 041, 026） | 未 |
| 認証・権限・ロール | （仕様書未作成・関連: ADR-023, 032, 138） | 未 |
| テナント管理・RLS | （仕様書未作成・関連: ADR-072, 034, 036） | 未 |
| 出荷キャリア連携（接点: order_shipping_details。発送の事実は取引フロー） | （仕様書未作成・関連: ADR-103, 123, 128） | 未 |


## specs外に散在する仕様書（存在の記録のみ・中身の判定は棚卸し便で）
以下は docs/ 直下に置かれた仕様書らしきファイル。生きているか古いかは未確認。移動・削除はここではしない。
- docs/FEATURE_SPECIFICATION.md
- docs/FEEDBACK_FORM_DESIGN.md
- docs/data_deletion_callback_design.md
- docs/products_design.md

## 追加のしかた
新しい設計仕様書を作ったら、この表に「領域名｜相対リンク｜状態」を1行足す。
状態は「公開＝読める／未＝これから作る」の2値で書く。
凡例（暫定・正規化は棚卸し便で実施）: 未＝枠のみ／pending＝接点記載済み・仕様書未作成／草案＝作成中／KGI承認済＝あるべき姿とKGIがPO承認済み。
