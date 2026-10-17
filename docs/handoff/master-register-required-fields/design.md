# design: 共用商品マスタ登録の必須項目と「確認済みの空」

> この文書は何か: 商品マスタに商品を登録するとき、決まった項目の入れ忘れをシステムで止めるための設計（素人向け: 「空欄のまま登録できないようにする仕組み」の作り方）。
> 親（設計仕様書）: [docs/specs/product-master/README.md](../../specs/product-master/README.md)
> 現在地: [docs/handoff/master-register-required-fields/recon.md](./recon.md)（実測 origin/main b7e3f28d3）、追加調査 /tmp/CC報告ファイル/master-required-fields/add/（origin/main 539b0fe41）
> 状態: 設計案作成済み・Opus 自己審査済み（同一 AI の審査であり独立レビューではない）・KGI と3便は PO 承認済み（2026-10-16）・実装未着手

## 0. PO の言葉（原文）
- 2026-10-16「マスタに登録するときはマーク、日本語商品名、英語商品名、発売日、検索ワード、除外ワード、中分類、細分類、カテゴリ(箱系、シングル系)などは登録するようにしてほしい、恒久化出来る？」
- 2026-10-16「マークは公式出ないものは採用しない、公式サイトやカードショップ、情報サイトから情報を入手しても存在しなければ推測で埋めずに空欄にして良い、英語名に関しては公式に存在しないが英語圏での呼び方を確認する、1呼称でなく、幅広く海外で使われている英語名がいい」
- 2026-10-16 「画面と API でこれらの項目を入力必須にし、細分類を選ぶ欄を新しく作る設計に進めてよいか」への回答「y」
- 2026-10-16「KGI G1〜G4・3便（①受け皿 migration ②画面 ③保存を止める）・英語名が英語圏でも見つからなければ印付きで空を認める、で進めてよいか」への回答「y」
- 2026-10-16「マークについてはない商品もある、推測や存在しないマークは登録禁止」／調べ方の案への回答「y→型番はなければ登録しなくて良い」（docs/specs/product-master/registration-rules.md §3・#4372）

## 1. 目的と KGI（PO 承認済み 2026-10-16）
目的: 共用商品を新しく登録するとき、9項目の入れ忘れが起きないようにする。空にしてよい項目は「調べたが存在しない」と印を付けたときだけ空を認める。

| KGI | 判定（○×） | 測り方 |
|---|---|---|
| G1 | 便3 反映後に新しく登録された共用商品で、9項目のうち「空で、しかも確認済みの印も無い」ものが **0件** | 本番 SELECT（§7 V1） |
| G2 | 画面の新規追加で、英語名を空にし「公式・海外で無し」の印も付けずに保存 → 赤字の案内が出て保存されない | PO 目視 |
| G3 | 画面に「細分類」の選択欄があり、選んだゲームで使える細分類だけが並ぶ | PO 目視 |
| G4 | 細分類が1つも無いゲーム（名探偵コナン・デュエル・マスターズ）でも、細分類マスタの画面でゲームを紐づければ登録できる | PO 目視 |

## 2. 対象の9項目と、空を認めるか
| 項目（画面の名前） | DB | 空を認めるか | 根拠 |
|---|---|---|---|
| 日本語名 | products.name | 認めない（今も必須） | recon 4-b |
| 英語名 | products.name_en | **確認済みの印があれば認める** | PO: 公式に無ければ英語圏で広く使われる名前を調べる。見つからない場合は印付きで空を認める（PO 2026-10-16 承認） |
| 型番（マーク） | products.mark | 確認済みの印があれば認める | PO: 存在しなければ空欄でよい。仕様書 3-2「空のこともある」 |
| 発売日 | products.release_date | 確認済みの印があれば認める | 10/16 登録13品のうち5品は公式の日付が確認できなかった |
| 検索ワード | product_search_keywords（1語以上） | 認めない | 共用1411件で空0件（recon 4-e）。解析の手がかり |
| 除外ワード | product_exclude_keywords | 確認済みの印があれば認める | 共用1411件中1174件が無し。除外語が要らない商品は普通にある |
| 中分類（作品） | products.work_id → type_master | 認めない（今も NOT NULL） | recon 4-b |
| 細分類 | products.product_format_id → product_formats | 認めない | PO の指示。共用1247/1411件は入っている（add/q2） |
| 商品区分（箱系・シングル系） | products.product_category_id | 認めない | PO の指示 |

対象外: メーカー（PO の列挙に無い。UCP・Wizards のようにメーカー一覧に無い会社があり、足す経路も無い→別件）、小分類、既存1411件の空欄埋め（別件）、テナント商品（backend/app/routers/products.py:379 ほか）。

## 3. 代替案と選択
| 論点 | 案 | 採否と理由 |
|---|---|---|
| 「確認済みの空」をどこに持つか | A 新しい表 `product_blank_confirmations` | **採用**。1か所に記録され（SSOT）、後から「入れ忘れ」と「確認済み」を SELECT で区別できる（G1 が測れる） |
| | B products に列を足す | 不採用。products は列数上限1600に当たった事故があり、列追加は作り直しが要る（memory products_attnum_limit_incident） |
| | C 印を保存しない（画面のチェックだけ） | 不採用。編集のたびに印を付け直すことになり、G1 も測れない |
| 止め方 | 保存を止める（422） | **採用**。PO の「入力必須」。Akeneo は点数表示で止めない方式（§9）だが、PO は止めることを求めている |
| 既存商品の編集 | 編集のたびに9項目全部を必須にする | 不採用。古い868件などの空欄を、関係ない直しのたびに埋めさせることになる |
| | **入っている値（または確認済みの印）を、印なしの空に戻すことだけ止める**。古い空欄は画面に「未入力」と出す | 採用 |
| 細分類の選択肢 | 全25種を出す | 不採用。ゲームに合わない細分類を選べてしまう |
| | **ゲームとの紐づけ表 product_format_game_links（多対多、69行）にあるものだけ出す** | 採用。多対多の設計（docs/handoff/product-format-many-to-many/design.md:25）に沿う。ただし紐づけを画面で編集する手段が今は無い（コードの読み書き0件、add/q1b）→ 細分類マスタ画面に「使えるゲーム」の編集を足す |

## 4. 変更内容（便に分ける。各便とも Sonnet 実装・Opus 審査）
### 便1 データの受け皿（migration を含む＝危険PR・GO 要）
- migration: `public.product_blank_confirmations`（product_id → products(id) ON DELETE CASCADE、field_code は 'name_en'・'mark'・'release_date'・'exclude_keywords' のみ（CHECK）、confirmed_by、confirmed_at、note、PK(product_id, field_code)）。RLS は products の共用行と同じ考え（書き込みは app.is_operator）。保護表として migration-guard.yml の一覧に足す。値は入れない（ADR-155・ADR-1007）。
- API: 4つの入口（POST /tcg/products/create、POST /tcg/products、PUT /tcg/products/detail/{id}、CSV 取り込み）が `product_format_id` と `blank_confirmations`（項目名の配列）を受け取り、保存する。**この便では止めない**。
- 共通の検査関数 `check_required_fields(...)` を1つ作り（tcg_product_master_svc.py）、4つの入口はこれだけを呼ぶ。便1では結果をログに残すだけ。
- 値が入った項目の確認済みの印は、同じトランザクションで外す。

### 便2 画面
- 商品詳細ドロワー（TcgProductDetailDrawer.tsx）と解析レビューの登録ドロワー（ProductMasterDrawer.tsx）:
  - 細分類の Select（components/ の金型）。選択肢はゲームとの紐づけ表から。
  - 英語名・型番・発売日・除外ワードの横に「調べたが無い」チェック（金型のチェック欄）。
  - 必須の印と、空のときの赤字の案内。
  - 既存商品の空欄に「未入力」の表示。
- 細分類マスタ画面（ProductFormatsMasterPanel.tsx）に「使えるゲーム」の編集を足す（product_format_game_links の追加・外し）。
- 文言は ja.json と en.json に同じキーで足す（ADR-027）。
- CSV 取り込みの列 `product_format_code` と `blank_confirmed`（項目名をカンマで区切る）を足し、取り込み画面の説明を直す。

### 便2 の分け方（2026-10-17 Opus。変更は一度に1つ）
- 便2a（バックエンド・カード card-bin2a.md）: 詳細 GET に印（blank_confirmations）を足し revision にも入れる／3つの選択肢の口（詳細・/tcg/products/lookups・registration-form）に細分類と紐づくゲーム id を足す／細分類と作品（work_id）の照合（紐づけに無い組み合わせは 422。詳細保存は細分類か作品が変わったときだけ）／細分類マスタ API に game_ids と PUT `/super-admin/product-formats/{id}/games`（使用中の組み合わせを外すと 409）。
  - 根拠（本番読み取り 2026-10-17）: 細分類と作品の両方が入った共用商品 1247 件のうち、紐づけに無い組み合わせは 0 件（/tmp/CC報告ファイル/master-required-fields/bin2a/prod-pairs.txt）。紐づけ表に RLS は無く、アプリのロールに INSERT・DELETE 権限がある（prod-links-rls.txt）。
- 便2b（画面）: 上の「便2 画面」のドロワー2つ・登録フォーム・細分類マスタ画面。金型と i18n。
- 便2c（CSV）: 列 `product_format_code`・`blank_confirmed` を足す。便2の間は旧10列も受け付け、新列を必須にするのは便3。往復 CSV・取り込み画面の説明・テンプレートも直す。
- 紐づけの無いゲーム: 8981（既存の共用商品 2 件・細分類あり 0 件）・8982（3 件・0 件）（prod-dm-conan.txt）。便3の前に PO に確かめる。

### 便3 止める
- `check_required_fields` が足りない項目を返したら 422（新規登録の全入口）。詳細保存は「値や印のある項目を、印なしの空にする」ときだけ 422。
- 私（Opus）と担当が使う登録台本も create_product を通るので、同じ検査で止まる。

## 5. 影響範囲
- 呼び出し元: recon 4-b の表の全入口と、その画面3つ（TcgProductDetailDrawer.tsx:138・reviewActions.ts:120・TcgProductImportPanel.tsx:52）。
- 解析: name_en と product_format_id を読む解析コードは無い（recon 4-g）→ 解析の結果は変わらない。
- 既存データは書き換えない。

## 6. リスクと対処
| リスク | 対処 |
|---|---|
| 便3のあと、細分類の紐づけが無いゲームの商品が登録できない | 便2で紐づけの編集を足してから便3。便3の前に、紐づけの無いゲーム（8981・8982）を PO に見せて紐づける |
| CSV 取り込みが新しい列なしで全部止まる | 便2で列と説明を足し、便3の前に告知。便3の 422 には足りない項目名を全部出す |
| 確認済みの印が乱用される（調べずに印を付ける） | 印に confirmed_by と時刻を残す。月に1回、印の件数を数えて PO に見せる（§10） |
| 英語名の「無し」が乱用される | PO 2026-10-16 承認で空を認める。乱用は上の印の数え上げで見る |

## 7. 受け入れ基準と検証方法
| 基準 | 検証方法 |
|---|---|
| V1 便3反映後の新規共用商品で「空かつ印なし」が0件 | 本番 SELECT（products と product_blank_confirmations を突き合わせ、9項目ごとに件数） |
| V2 4つの入口すべてで、足りない項目があると 422 と項目名が返る | backend の単体試験（入口ごと×項目ごと） |
| V3 詳細保存で、入っている値を印なしで空にすると 422、印ありなら保存できる | backend の単体試験 |
| V4 値を入れると確認済みの印が消える | backend の単体試験＋本番 SELECT |
| V5 ドロワーで細分類はゲームに紐づくものだけが出る | frontend 試験＋Playwright 画面確認 |
| V6 ja.json と en.json のキーが一致 | 既存の CI |
| V7 migration に値の INSERT が無い | migration-guard（既存のチェック7） |
| V8 G2〜G4 | PO 目視 |

## 8. 計画
便1（GO 要）→ 便2a → 便2b → 便2c → 紐づけの無いゲームを PO 確認のうえ紐づけ → 便3。各便は設計→実装カード→実装→審査→反映→測定の順で、一度に1つずつ。

## 9. 外部・過去事例
- Akeneo PIM（商品情報管理ソフト）の公式ヘルプ（取得 2026-10-16）。
  - 必須の項目は商品の種類（family）ごとに、出し先（channel）ごとに決める。
  - 埋まり具合を「完成度」の割合で示すが、保存そのものは止めない。
  - 出典: https://help.akeneo.com/pim/serenity/articles/what-is-the-completeness.html 、https://help.akeneo.com/pim/v3/articles/manage-your-families.html
  - 我々への応用:
    - (1) 必須の項目を「全商品一律」ではなく「項目ごとに空を認めるかどうか」で分ける考えを取り入れた（§2）。
    - (2) 埋まり具合を数で見る考えは、§10 の月次の数え上げとして取り入れた。
  - 適用の限界: Akeneo は止めない方式で、PO の求める「止める」とは違う。効果の数値は出典に無いので、成功の証明には使わない。
- 社内の前例: 10/16 の13品の登録では、英語名が13品とも空、型番は4品だけ、発売日は8品だけだった（/tmp/CC報告ファイル/inventory-6checks/box-priority/unreg/fields/target_rows.txt）。これが今回の発端。

## 10. 決まりの文書化
- 新しい ADR（ADR-1020 の予定。番号は起票時に確かめる）: 「共用商品の登録必須項目と確認済みの空」。ADR-155（正規の更新は CSV と画面）の上に足す。ADR 追加後は `node scripts/generate-adr-index.js` を実行する。
- 仕様書 docs/specs/product-master/README.md の 3-2 に、PO の言葉を引用して「必須・空を認める条件」を足す（あるべき姿は PO の言葉のみ）。

## 11. 自己審査（Architect 役・同一 AI）
- 判定: **APPROVE（2026-10-16 更新）**
  - 前回 REVISE の理由（英語名の空）は PO 承認で解消。
  - そのほかは recon・add の事実と突き合わせ済み。
- 確かめたこと:
  - 4つの入口は recon 4-b の全走査と一致する。
  - 細分類の紐づけはコードで読み書きされていない（add/q1b）。
  - 紐づけの無いゲームは2つ（add/q3）。
  - 解析は name_en と product_format_id を読まない（recon 4-g）。
- 実装カードの前に確かめたこと（2026-10-16 Sonnet 調査・origin/main 74eb678cf）:
  - RLS の前例: migrations/20260628_170000_add_app_fx_rates.sql:46-63（ENABLE/FORCE・SELECT は USING(true)・書き込みは app.is_operator='true'）、products は migrations/20260626_130000_force_rls_public_products.sql:5-38。新しい表はこの形に揃える。
  - 保護表の一覧の正本は scripts/migration-guard/protected-tables.txt（:11-37）。migration の実行一覧 scripts/run_all_migrations.sh の末尾にも足す。
  - 往復 CSV（tcg_product_roundtrip_svc.py:318-408）は CSV_COLUMNS を継承するため、便1では列を足さない（列の追加は便2）。止める対象には便3で入れる。
  - 本番の 1247件に細分類を入れた経路は分かっていない（未確認。今回の設計には影響しない）。

## 維持の仕組み
- 守り手: .github/workflows/migration-guard.yml（新しい表を保護一覧に足し、値の投入を止める）
- 守り手: backend の単体試験（V2〜V4。CI の backend テストで毎回走る）
- 対象: 4つの入口が同じ検査関数を通ること。新しい入口を足したときに検査を通さないと、入れ忘れが再発する → ADR に「共用商品を書く入口は必ず check_required_fields を通す」と書く
- 毎週月曜 09:00（日本時間）、本番の Celery の作業 report-master-required-fields-weekly（backend/app/tasks/master_required_fields_monitor.py）が、便3反映後に作られた共用商品の「空かつ印なし」の件数（9項目ごと）と「調べたが無い」の印の件数を管理者用 Discord に送る。0 件でも毎週送る。届かない週は作業が止まっている。⚠️ が出たら Opus が該当の商品を調べて PO に候補表を出す（ADR-1020 便4c）
- 人手で守るもの: 確認済みの印の乱用。月に1回、印の件数を数えて PO に見せる（理由: 印が正しいかは機械では判定できない）

## 便4a 在庫の商品画面の口（2026-10-17 追記）
- 定着点検（Opus・2026-10-17）で、`backend/app/routers/products.py:379` の `POST /products` を「テナント商品」として対象外にしていたのは読み違いと分かった。PostgreSQL では `public.products` に tenant_id NULL で作る（:94-96・:375）。
- 本番では work_id の NOT NULL で INSERT が失敗しており、行は作られていない（直近720時間の呼び出し0件）。ただし理由が画面に出ず、口を直せば入れ忘れの行を作れる状態だった。
- 対処: POST は PostgreSQL では常に9項目を検査して 422（中分類・細分類・商品区分を受け取れないため）。PATCH は共用の行で4項目を空に戻す更新を 422。画面は requiredFieldsMessage で言葉を出す。
