# ページタイトル金型 design（recon実測＋差分設計）

> この文書は何か（専門用語なしの1行）:
> 既に63ページで使われている共通部品 PageLayout を「正式な金型」と認定し、残りの散らばりを片付けて完成させる設計図。

親: [README.md](README.md)
recon実測SHA: origin/main 29c8decb58b2c9db255ab93b9e228ebe058970be（2026-07-18）

## 1. recon（file:line 実測・要点）
recon証跡: docs/handoff/page-title/recon.md（対象ADR: ADR-067。色変更なし・ダークモード規約の維持確認）
- 金型は既に在る: frontend/src/components/PageLayout.tsx:24-35 が h2.text-page-title（title=navKey）/ subtitleKey / headerAction を提供。利用ページ63。
- タイトル文字列のSSOTも在る: frontend/src/hooks/usePageTitle.ts が src/config/routeTitles.ts を正として参照（サイドバーと同一キー）。
- 生h1/h2は pages 配下に20件。内訳（役割仕分け）:
  a) 一覧系の独自タイトル（金型に寄せる本命）: super-admin/ParseReviewPage.tsx:382,398（CSSコメントに「PageLayoutを使わず生の.page-headerを使用」明記）、coming-soon/ComingSoonPage.tsx:28 等。
  b) 詳細ページ（データ名がタイトル）: company-detail/CompanyDetailPage.tsx:150、invoice-detail:188、quote-detail:127、invoice-create:220、quote-create:140、roles/RolesPage.tsx:379。usePageTitle.ts の注記が「詳細はデータ名を生h2で」と例外指定している（本設計D1で正式な口に置き換える）。
  c) ナビ枠外画面: register系6件（RegisterPage.tsx:262,284 / RegisterChangeBillingPage.tsx:217,232 / RegisterAddressPage.tsx:279,299）、login/LoginPage.tsx:77（sr-only）、oauth-callback:135。
  d) ページ内の節見出し: company-detail/CompanyAddressesTab.tsx:70,84、schedule/SchedulePageImpl.tsx:1106（schedule-shell__title）。
- 見た目定義の散在: pages-layout.css:22-71（.page-header/.page-header h2）、company-forms.css:17-35（.page-container .page-header h1/h2）、ParseReviewPage.css:39-41、tokens.css:184-195（--page-header-mb 等のトークン）。同じ.page-headerを複数CSSが定義＝「1箇所直せば全部変わる」を弱めている。

## 2. 差分設計（D1〜D4・最小差分で KGI を満たす）
- D1 金型の口の追加: PageLayout に titleText?: string（詳細ページのデータ名用・navKey と排他）を追加。見た目props（色/サイズ等）は追加しない＝ページごとに違う見え方の再発を構造で防止。
- D2 移行: 生h1/h2のうち a) と b) を PageLayout 経由に移行（b) は titleText を使用）。invoice/quote の「タイトル — 番号」形式は titleText に文字列合成して渡す。
- D3 CSS集約: ページ題名の見た目定義を pages-layout.css の金型節1箇所に集約。company-forms.css:25-35 と ParseReviewPage.css:40-41 の重複定義は移行完了後に削除。
- D4 対象外の線引き（KGI③の分母確定）: c) ナビ枠外画面（登録/ログイン/OAuth。ページ枠=サイドバー付きレイアウトの外にあり金型の前提が合わない）、LoginPage の sr-only（視覚表示なしの読み上げ用）、d) ページ内の節見出し（ページ題名ではない。節見出しの金型化は別部品=SectionTitle の領分として全体計画書に残す）。

## 3. 弊害・トレードオフ（空欄不可）
- D3 の集約で、重複定義同士に微差がある場合はどちらかに寄せる＝一部ページの見た目に微差が出る可能性。Visual Gate と目視で確認し、差分はPOに提示して判断を仰ぐ。
- D2 の移行はページごとにDOM構造が変わるため、1ページずつの確認が必要（一括置換はしない）。
- titleText の追加は金型の口が1つ増える＝管理点の増。ただし詳細ページの例外を野良実装のまま放置するより、正式な口に一本化する方がSSOTに適う。

## 4. 外部・過去事例
色SSOT（docs/handoff/color-tokens-ssot/）の「役割で線引きし、正当な例外は明記して残す」方式を踏襲（データ色を除外した判断と同型で、ナビ枠外・節見出しを除外）。小規模のため追加の外部調査は行わない。

## 5. 受入基準（各基準に検証方法）
| 基準 | 検証方法 |
|---|---|
| titleText が金型に在り navKey と排他 | PageLayout.tsx を目視＋型チェック（CI tsc） |
| a) b) の生h1/h2 が 0件 | grep -rnE "<h1[ >]|<h2[ >]" frontend/src/pages で対象外（c,d）以外 0件 |
| ページ題名の見た目定義が1箇所 | grep で .page-header h1/h2 系定義が pages-layout.css のみ |
| 見た目の回帰なし | Visual Gate（Playwright）＋人の動作確認 |

## 6. 維持の仕組み（空欄不可）
- 守り手: 当面「人手で守る」＋理由: 生h1/h2検出の関所（grep gate）は、対象外（c,d）の除外リストを持つ必要があり、除外の妥当性が安定してから機械化する。関所化は後続便（KGI⑤は本designの人手ルール明記で 1 とし、機械化で強化）。
- 人手ルール: 新規ページのタイトルは PageLayout（navKey または titleText）経由のみ。usePageTitle.ts の注記「詳細はデータ名を生h2で」は D1 実装時に「詳細は titleText を使う」へ更新する。

## 7. 接触面分析（6面走査）
| 面 | 事実 |
|---|---|
| 人 | 全ページの題名表示。見た目の微差が出る場合はPO確認（§3） |
| エージェント | 実装役は PageLayout.tsx / 各対象ページ / pages-layout.css / company-forms.css / ParseReviewPage.css / usePageTitle.ts 注記を触る。本designが指示の正 |
| 機械 | tsc・Visual Gate・guard-hex-increase（色は触らないため影響なし）。frontend/src を触る＝process-artifacts gate の GO 必須 |
| データ | DB変更なし |
| 本番 | migration不要。フロントのみ |
| 外部 | 外部API・外部GUIの変更なし |

## 8. 実装の進め方（後続便の割り方・目安）
便1: D1（titleText追加）＋usePageTitle注記更新。便2: D2移行（a→bの順・ページ単位）。便3: D3 CSS集約＋重複削除。各便 frontend/src を触るため PO自筆 GO 必須。
