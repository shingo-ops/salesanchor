<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — リードのカルテで成約しやすさを分析する（下調べ）

**仕事名**: リードのカルテ項目と商談のやり取りから、成約しやすい型を回帰分析で見つける土台づくり  
**日付**: 2026-10-31  
**対象ADR**: ADR-015（リードの土台・返信速度）、ADR-119（lead_channels）、ADR-108（店舗の形の複数選択）、ADR-109（状態の不変コード）  
**担当**: Claude Opus（設計担当。読み取りのみ。書き込みは一切していない）  
**基準**: origin/main 5c13bfbef

- 状態: 下調べ済み（読み取りのみ）。KGI 未承認・設計 未作成・実装 未着手。テナント001へのテスト用データの投入は未実施（設計と PO の明示の承認が要る）。
- PO の方針（2026-10-31）: 本物の記録がほぼ無いなら、テナント001にテスト用のデータを入れて、どんな分析ができ、画面でどう見えるかを確かめる（選択肢2）。推測禁止・配線と DB の SSOT 厳守・データの分散禁止・画面の部品はデザイントークンと金型を守る。分からないことは PO に聞く。

---

## 1. 記録されている項目（コードの事実）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/schemas/lead.py:31` | 状態 LeadStatus。`existing_customer`＝成約、`lost`＝失注（31〜39行） |
| `backend/app/schemas/lead.py:42` | 種類 Inbound / Outbound（42〜44行） |
| `backend/app/schemas/lead.py:47` | 温度 Hot/Warm/Cold、規模、顧客タイプ（47〜62行） |
| `backend/app/schemas/lead.py:64` | 返信の速さ（手入力の3段階 24h以内/3日以内/3日超。64〜67行） |
| `backend/app/schemas/lead.py:115` | 流入経路 channel_type（自由文字列30字） |
| `backend/app/schemas/lead.py:126` | 国 country（自由文字列100字） |
| `backend/app/schemas/lead.py:178` | 店舗の形 sales_form（単一）。180行に複数選択 sales_form_selections |
| `backend/app/schemas/lead.py:183` | 失注理由（主因1件必須）。184行に相見積もりの確認 competitor_check（はい/いいえ） |
| `backend/app/schemas/lead.py:189` | 扱う作品 target_titles（自由記述500字。選択式ではない） |
| `backend/app/services/tenant.py:1022` | メッセージ表 meta_messages（lead_id・platform・direction・created_at。1022〜1036行） |
| `backend/app/services/tenant.py:1045` | lead_channels（1リードに複数の経路。messenger/instagram/discord。1045〜1054行） |
| `migrations/20260604_090000_create_conversation_logs.sql:34` | 会話の記録 conversation_logs（lead_id・channel_type・direction・occurred_at。34〜55行） |
| `migrations/20260614_100000_create_sales_form_tables.sql:89` | 店舗の形の選択肢（実店舗・EC・ライブ配信・卸・その他）は tenant_004 にだけ入れている（89〜97行） |
| `migrations/046_adr015_lead_foundation.sql:56` | first_inquiry_at・first_response_at を追加（ADR-015 §3 返信速度の自動計測用。105〜107行に説明） |
| `backend/app/services/tenant.py:384` | 新しいテナントのリード表にも first_inquiry_at（384行）・first_response_at（385行）がある |

## 2. 既にある分析と画面（コードの事実）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/analytics.py:963` | 属性ごとの成約率。軸は経路・国・店舗の形・温度・返信の速さの5つ（977〜981行）。1項目ずつ見る |
| `backend/app/routers/analytics.py:984` | 件数の少ない値は全体の率へ寄せる（k=10。式は1010行） |
| `backend/app/routers/analytics.py:1813` | 成約しやすさ×見込み金額の優先リスト（priority-prospects） |
| `frontend/src/pages/dashboard/DashboardPage.tsx:1` | ダッシュボード画面。同じフォルダに PriorityProspectsSection・FunnelReasonsPage など |

既にあるのは「1項目ずつの成約率」。複数の項目を同時に見て、ほかの項目の影響を差し引く計算（回帰分析）はまだ無い。

## 3. 書き込みの入口（テスト用データを入れる道の候補・コードの事実）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/leads.py:405` | リードを作る POST /leads |
| `backend/app/routers/leads.py:494` | リードを直す PATCH /leads/{id}（状態・カルテ項目） |
| `backend/app/routers/leads.py:800` | 成約への変換 |
| `backend/app/routers/leads.py:1770` | メッセージ送信。実際に Meta へ送るため、テスト用データには使えない |
| `backend/app/routers/conv_logs.py:225` | 会話の記録を手で入れる POST /leads/{lead_id}/conv-logs（向き・本文・日時を指定できる） |
| `backend/app/routers/conv_logs.py:247` | 自動の経路（connection_type が auto）には手で入れられない（入口の排他） |

## 4. 本番の件数（読み取り専用の道 ADR-1024 で数えた。2026-10-31 12:35〜13:10 JST）

| 数えたもの | tenant_004（本物） | tenant_001（テスト用） |
|---|---|---|
| リードの数 | 56（全部「新規リード」） | 2 |
| 成約の数 | 0 | 0 |
| 種類（Inbound/Outbound）が入っている数 | 5 | 未計測 |
| 経路が入っている数 | 56 | 未計測 |
| 国・店舗の形・温度・返信の速さ・扱う作品 | 各 0 | 未計測 |
| メッセージ（meta_messages） | 25（リードに結び付き 24） | 4 |
| 会話の記録（conversation_logs） | 6 | 0 |
| 店舗の形の選択肢 | 5 | 0 |
| 失注理由の選択肢 | 未計測 | 15 |
| first_inquiry_at・first_response_at | 0・0 | 0・0 |

経路の種類（channel_masters）は 001・004 とも同じ6つ: 自動 discord・instagram・messenger ／ 手入力 whatsapp・phone・in_person。

tenant_006 はリード 74・成約 8 があるが、Meta の審査専用なので使わない。

結論: 本物の記録では成約が 0 件で、カルテ項目もほぼ空。回帰分析はできない。PO の方針どおり、テナント001のテスト用データで見え方を確かめる道に進む。

## 5. 足りない項目・配線（事実）

- シュリンク付き/ノーシュリンクの箱の扱い: リードに項目が無い（`git grep -i shrink` はリード関係で 0 件。当たったのは解析の指示書だけ）。
- 扱う商材: 選択式の項目が無く、自由記述 target_titles だけ。
- 成約した日・状態が変わった日の履歴: 履歴の表が無い（`git grep` で status_history・converted_at・won_at など 0 件）。updated_at は状態以外の変更でも変わるので代わりにならない。
- 返信の速さの自動計測（ADR-015 §3）: 列は作られたが、書き込む処理がどこにも無い（`git grep first_response_at` は表の定義・migration・文書だけ）。docs/specs/db-ssot/handover.md 131行と docs/specs/management-center/lead/data-dictionary.md 49〜50行で「未実装・削除候補」と記録済み。
  - SSOT の観点: 返信の速さはメッセージ表の送受信の時刻から計算できる。別の列に写して持つとデータが2か所に分かれるので、設計では「メッセージ表から計算する」を第一候補にする（設計で決める。ここでは事実だけ）。
- Instagram・Facebook の会話は Meta の受け口（webhook）からしか入らない。手で入れる入口（`backend/app/routers/conv_logs.py:247`）は自動の経路を拒む。そのため、Instagram・Facebook のリードに「過去の日時のテスト用のやり取り」を正規の入口で入れる道は無い。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | Instagram・Facebook のリードのテスト用のやり取りをどう入れるか（正規の入口が無い） | PO に聞く（手入力の経路だけでやり取りを入れる／やり取りは入れない 等） | 未解決（PO 判断待ち） |
| 2 | シュリンクの扱い・扱う商材・成約日をどう持つか（項目が無い） | 設計で案を出し PO に聞く | 未解決（設計で扱う） |
| 3 | テナント001の各カルテ項目の空欄率 | 読み取りの道で数える | 未解決（設計前に数える） |

**未解決ゼロ確認**: 未解決 3件。#1 は PO の判断が要るため、解消まで設計を確定しない。

---

## 補足

- 過去の構想メモ: リードの分析は「成約しやすさ」を示すもので原因ではない。こちらの返信の速さは「見込みの高い相手ほど急いで返す」逆向きの影響が混ざる。相手の返信の速さ・やり取りの濃さは原因ではなく見込みの目印として扱う。
- 先行の回帰分析（解析の誤り）の設計: docs/handoff/accuracy-measurement/design-regression.md（同じ計算の考え方を使える）。
