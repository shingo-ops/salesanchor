# DB正本シートの再開調査（2026-09-10）

この文書は、整理途中のスプレッドシートで何を確認でき、何をまだ決められないかを残す記録です。

親: [DB設計のSSOT化](../../specs/db-ssot/README.md)

## 調査の位置づけ

- 既存テーマの延長。POの依頼は、スプレッドシートで進めていたDBのSSOT整理の再開。
- 調査担当: Codex（設計パートナー）。製品実装・DB接続・本番操作・シート編集は実施していない。
- 状態: 初回棚卸し済み。対象タブの正式な位置づけ、GAS等の更新経路、最新本番DBは未確認。設計合格・実装可能の判定は出していない。
- PO確認待ち: 「Copy of」「backup」「旧」が付かないタブを現在の設計案として扱ってよいか。これらの名前だけでは正本・廃止・削除可能を断定しない。

## 再開後に確認したPOの意図

以下はPOの発話原文。設計全体・製品実装・マージのGOではない。

- シートの用途: 「Sales AnchorのDBを作り直すための設計見本」
- リードの単位: 「見込み客1人につき1件、1人に1つしかつかない親元のID」
- 同じ会社の別人のまとめ方: 「会社IDを親元に子どもとしてまとめる」
- 会社不明時の登録と会社IDの発生: 「よい、リードIDから発起、商談が成約したらこちらからフォームを送り、顧客がフォームの入力を完了するとDBに会社IDが登録される」

設計への反映: リードは人を識別する親元であり、相談・注文ごとに新しいリードを作る設計にはしない。全テーブルに直接リードIDを置くか、途中の親を経由するかは、この発話だけで決めない。

既存設計との照合: `docs/specs/db-ssot/deal-removal/design.md:65-67` はleadを全ての親とし、注文はcompanyを経由させる。`docs/specs/db-ssot/implementation-plan/design.md:24` にはcontacts概念を廃止して会社に連絡手段を持たせる旧方針がある。「人に1つ」の今回の定義と会社単位のまとめ方を、推測で同一視しない。

会社と人の関係: POの追加回答により、会社IDを親とし、人ごとのリードIDを子としてまとめる。先の「親元のID」は人の識別を示すが、会社より上位の構造とはしない。会社1件に複数の人をまとめられることを設計条件にする。人が複数会社に所属する場合の扱いは未確認。

現行との差: `backend/app/services/tenant.py:190-195` はcompaniesがlead_idを必須保持し、`backend/app/schemas/company.py:116` も会社作成に出自リードを必須としている。今回の会社→人の所属関係と、既存の会社→出自リードの参照は意味を分けて設計する必要がある。単純に参照を反転する実装はまだ指示しない。

登録順序: 会社ID未設定でリードを登録できる。POが示した順序はリードIDから開始→商談成約→こちらからフォーム送付→顧客の入力完了でDBに会社ID登録。会社を先に必須作成する設計にはしない。会社と人の所属関係と、IDが発生する時間順序を分けて扱う。同じ会社が既に存在する場合の照合・再利用方法、フォーム再送信時の扱いは未確認。

成約の意味は追加回答で訂正された。商談成約=取引内容などへの合意、取引成約=商品到着を含むキャンセル・トラブルのない取引完了。フォーム送付は前者の後。全業務フローのPO原文と、注文ごとの状態を分ける[設計草案・自己審査](design-status.md)を保存した。次の確認は返金・返品を伴って解決した取引を成約件数に含めるか。

既存文書には `docs/specs/db-ssot/classification-master/design.md:48` の入金時成約と、`docs/specs/transaction-flow/README.md:82` の取引完了時成約が併存。今回の意図に合わせた正式改訂は未実施。草案の自己審査はREVISEであり、実装可能とはしていない。

追加のPO決定原文: 「商談合意したらフォームを送る形なので無しで」。商談合意の独立ステータスを設けず、合意後にフォーム送付する流れとする。設計担当が先に提案した商談合意状態の追加は取り下げ、design-status.mdを修正した。

返金・返品後の集計は、全額返金・全商品返品は除外、一部返金・一部返品および返金返品なしで解決した注文は成約へ含める。履歴は保持。通常の分割発送は全商品到着後に成約、会社ID=顧客ID、金額集計は紐づいたorderの額から返金を差し引く（1万円−2千円=8千円）こともPO確認済み。確認対象・回答原文・期待値はdesign-status.mdに保存。次は会社の重複判別方法を確認する。

用途の確認を受け、旧帳票やGASの全面的な維持を今回の設計目標とはしない。現行シートの値を正しいDB設計と見なさず、項目の意味と関係の見本として評価する。既存シート自体の編集・削除は引き続き未実施。

## 証拠の固定

フォーム発行の追加要件: POがリードID必須・リードなし発行不可・重複防止を明示。ADR-097および登録フォームコードを照合し、同じ人の再送と同じ会社の別人の登録は別の重複問題であること、既存の登録処理は会社作成済みを前提とすることを確認。原文・行番号・弊害・未決事項はdesign-status.md §6に記録。

- 原資料: https://docs.google.com/spreadsheets/d/1WocLyYqPEli2N1IEqlYBYAg-ewy7V5J22-gfU6NFjT4/edit
- 取得: XLSX export、HTTP 200、3,523,152 bytes。
- SHA-256: `0257660aac3a87fb83f655386c345a599b86901f45678d6d8eeeb5678f696582`
- リポジトリ基準: `origin/main` / `6e1335725bb8dfdf390125c4caf5a93f705f4821`。公式 `scripts/new-worktree.sh` で `release/db-ssot-sheet-recon` を作成。
- 全134タブをXMLから抽出。空でないタブ132、数式セル43,838。全タブ名・非空行数・列見出し・数式を検査した。業務上の全項目の意味を確認し終えたという意味ではない。
- [全タブの棚卸し](inventory.md)、[30組の参照照合](relations.md)。個人情報・認証情報・会話本文は成果物に転載しない。
- 原XLSXと抽出JSONは一時領域に保持。リポジトリには入れない。Google Sheets固有の数式はexport時にDUMMYFUNCTION等に変換されているため、今回の値は取得時の保存値。再計算・GAS実行をしていない。

## 1. 全体像

「部品」は、データの保管タブ、参照用マスタ、集計・帳票、更新・検査経路を指す。

主な行数（見出しを除く非空行）: リード管理10、顧客マスタ6、オーダー管理12、オーダー明細25、発送8、発送明細2、仕入れ12、見積もり管理1、見積もり明細3、会話ログ249。根拠は各タブの2行目以降とinventory.md。

名前にbackupを含むタブ35、Copy ofで始まるタブ10。これは名称の集計であり、利用状況の判定ではない。

## 2. 共用部品・参照関係

列見出しで指定した30組の親子関係を、空欄・一致・不一致に分けて照合した。空欄が仕様違反かどうかは未判定。

| 観測事実 | 根拠 | 解釈の限界 |
|---|---|---|
| 顧客6行の源流リードIDは全てリード管理に存在 | 顧客マスタ!B2:B7 → リード管理!A2:A11 | 必須制約や更新時の保証は未確認 |
| 注文12行の顧客・リード・配送先・支払先IDは全て各参照先に存在 | オーダー管理!C2:F13 | 値が現在一致することだけを確認 |
| 注文明細25行・発送8行・仕入れ12行の注文IDは全て存在 | 各タブB列 → オーダー管理!A2:A13 | 仕入れは注文明細単位への接続を未確認 |
| 顧客税務番号2行は顧客と番号種別に接続 | 顧客税務番号!B2:C3 | 番号の税務上の要件・有効性は調査対象外 |
| 見積1行のリードIDが参照先にない | 見積もり管理!B2=`LDI-00001`、リード管理!A2:A11 | `LDI-0001`へ勝手に補正しない。対象人物の同一性は未確認 |
| 会話249行のリードIDは現リード一覧に0件一致、Copy側に249件一致 | 会話ログ（商談用）!B2:B250、リード管理!A2:A11、Copy of リード管理!A列 | 25種類のリードID。異なるデータ集合が併存。現行10件への移し替えは根拠なし |
| 発送明細2行のオーダー明細IDは空欄 | 発送明細!C2:C3 | 注文外の発送を許すか等の仕様が未確認 |
| 注文明細の商品IDは25行中24行空欄 | オーダー明細!K2:K26 | 商品名から自動同定できるとは限らない |

独立検算: 最初のJSON集計とは別に原XLSXの対象XMLを直接読み、会話249/249不一致・Copy側249/249一致・見積1/1不一致をassertで確認した。別のAIによるレビューではない。

## 3. 非共用部品・二重保持の候補

| 観測事実 | 根拠 | 未確認事項 |
|---|---|---|
| リードと顧客で名前・国・メール・営業担当IDが各6/6行一致し、両タブの当該列は数式0 | リード管理!C/F/P/Z列、顧客マスタ!C/D/E/J列、源流リードIDで照合 | 同一の生きた事実か、確定時点の控えか。GAS書込元・編集可否 |
| リードにdeal_resultとlead_statusが併存 | リード管理!D1/AY1。Dは7行非空、AYは10行非空 | 結果と進行状態を別事実として設計したか、移行残骸か |
| 配送方法・発送日・追跡番号が注文と発送に存在 | オーダー管理!V1:X1、発送!D1:F1 | 注文側が希望値・集約値・旧列のどれか |
| 同一注文に複数発送がある | 発送!B2:B3=`ORD-0001`、B6/B9=`ORD-0004` | 注文1行の追跡番号欄で代表値を持つ設計か |
| 請求書PDFの7数式セルが顧客マスタ_旧を参照 | 請求書_PDF出力!B11:B17 | 帳票が現在使われているか。旧タブ削除は不可 |
| 売上データ644数式セルが顧客マスタ_旧を参照 | 📊売上データ、例AB6/AB7/AB8/AB9/AB11 | 数式参照の存在のみ。現在の実行・利用状況は未確認 |

数式がないことは手入力の証明ではない。GASや外部プログラムが値を書いている可能性を未確認として残す。名称重複だけで列削除・統合を決めない。

## 4. ルールの所在と実物との差

- 原則: [既存KGI](../../specs/db-ssot/kgi.md) K1〜K5、[ADR-095](../../adr/ADR-095-sa-ssot-two-backbone-architecture.md):48-52。確定時点の控えと二重手入力を区別する。
- 旧割当表: [ssot-allocation.md](../../specs/transaction-flow/ssot-allocation.md):28-41 はdeal経由を記載。一方、[deal-removal/design.md](../../specs/db-ssot/deal-removal/design.md):72-75 はordersをcompany参照、quotesをlead参照へ変更している。旧表だけから現行設計を決められない。
- コード: `backend/app/services/tenant.py:346-367` はleadsに整数id、文字列lead_code、status、assigned_toを定義。シートはlead_id、lead_status、sales_assignee_id等であり、そのままDB列名として採用できない。
- 実際の読み書き列: `backend/app/routers/leads.py:64-84`。表示用コードとDBの主キーを区別した対応表が必要。
- 注文: `backend/app/services/tenant.py:452-466` はcompany_id参照とpaid_atを定義。シートのcustomer_id/source_lead_id/payment_confirmed_atとの対応は未確定。
- 注文明細: `backend/app/services/tenant.py:899-918` はproduct_idをpublic.products参照、product_name/condition等を保持。シートだけからアプリ側の重複廃止を指示しない。
- これらは取得したコミットのソースの観測。本番にこの定義だけが存在するとは主張しない。全migrationの適用状態・実DBは未確認。

## 5. 維持の仕組み

- シート内の過去記録: DEV参照整合性監査ログ!A203:K223（最新タイムスタンプの21行）。見積の不一致を既に記録。構造監査はDEV構造監査ログ!A103:Q206（最新タイムスタンプの104行）。
- タイムスタンプの数値をExcel日付として変換すると、参照監査2026-08-26 18:40:57、構造監査2026-08-13 22:30:27。タイムゾーン未確認。最新シート構造を監査済みという証拠にはならない。
- 過去ログのリード営業担当の空欄判定と、現在のsales_assignee_id 10/10非空は一致しない。ログを再開時の合格証として流用しない。
- `.github/workflows/condition-vocab-check.yml:9-21` はアプリの分類値検査。今回のGoogle SheetsをこのCIが保証するという根拠は得ていない。
- 監査GAS・書込GAS・トリガー・外部連携設定はXLSXに含まれないため未確認。どの操作で検査され、誰が直すかも未確認。

## 6. あるべき姿との対照

| 既存KGI | 今回確認した範囲 | 判定 |
|---|---|---|
| K1 同じ事実の二重保持0 | 顧客とリードに同値列あり。意味と書込経路未確認 | 未判定 |
| K2 各事実の正本が全数明記 | 原本候補・Copy・旧参照が併存。全列の正本対応表は今回未確立 | 未判定 |
| K3 他は参照 | 30組を測定。会話・見積で指定親に不一致あり | 現タブ組合せでは不足 |
| K4 分類値をマスタ参照 | 選択肢マスタV2が存在。リードの流入元ID10/10空欄 | 適用・必須性未確認 |
| K5 必ずリードにたどれる | 会話249行と見積1行が現在のリード10行にたどれない | 現タブ組合せでは不足 |

不明を一致／不足／余剰へ強制分類しない。現状把握全体は未完了。数値の不一致だけでは設計欠陥かデータ入れ替え途中かを判定できない。

## 7. ノイズ・境界・次の一手

- 旧・Copy・backupは削除対象としない。数式から使われる旧タブも実在する。
- 同じIDの繰り返しでも、親子関係の子側では正常な場合がある。主キーの重複と混同しない。
- 空欄参照はすべて報告するが、必須であるとの承認済み定義がない欄をエラーと断定しない。
- 外部成功事例は今回不要。再開位置の確認は手元のシート・既存設計・コードの一致が根拠であり、他社事例では代替できない。ライブラリ/API仕様の調査は行っていない。
- シートの公開状態で担当者マスタU列password_hash 8件、V列password_salt 8件、ログインセッションA列session_id 69件の非空を確認。値は転載・使用せず、公開設定を制限付きへ戻すようPOへ連絡済み。認証情報の有効性・公開解除の実施は未確認。

次の順序（提案・未承認設計）:

1. POが現在の設計案として扱うタブ範囲を指定する。旧データ・Copy側の削除はしない。
2. 指定されたタブについて、まず「リード・顧客・会話」の列ごとの意味、正本、参照先、確定時点の控え、計算値を既存様式で整理する。重複列の意味はGASの書込経路とPOの業務意図で確定する。
3. サンプルデータの世代差を整理し、参照照合を再実行する。IDのゼロを削るだけの自動補正は禁止。
4. 確立した項目からDB列・API・テストへの対応表を作る。最新DBの確認が必要になった時点で承認済みread-only手順と対象を確認する。
5. 設計作成後、同一AIによるArchitect自己審査を実施する。今は未決事項があるためAPPROVE・実装カード発行を行わない。

現在の成果: 調査記録をローカル保存。設計審査未実施、POの設計承認なし、PR未提出、実装未着手。

## 2026-09-16 UI金型10候補の固定版照合

EV-20260916-DB-SHEET-105。読み取りのみ。参照はローカルorigin/mainの固定SHA `8c695b8010f465fa342d98243e9d37d917f26843`。本番配備版との一致や本番画面の動作は未確認。作業ブランチの古い実装だけで判断しないためgit showで固定版を読んだ。新しいAPI/ライブラリ仕様の判断はしていない。

| 候補金型 | 今回の適用候補 | 部品本体 | Storybook登録の根拠（title/component） |
|---|---|---|---|
| PageLayout | 全業務ページのタイトルと操作入口 | frontend/src/components/PageLayout.tsx | frontend/src/components/PageLayout.stories.tsx:10 / :11 |
| Button | 確定/保存/取消などの操作 | frontend/src/components/Button.tsx | frontend/src/components/Button.stories.tsx:12 / :13 |
| TextField | 入金日/数量/設定値の入力候補 | frontend/src/components/TextField.tsx | frontend/src/components/TextField.stories.tsx:10 / :11 |
| Select | 合意済み選択肢の表示 | frontend/src/components/Select.tsx | frontend/src/components/Select.stories.tsx:18 / :19 |
| Textarea | 理由の記録 | frontend/src/components/Textarea.tsx | frontend/src/components/Textarea.stories.tsx:10 / :11 |
| DataTable | 一覧と履歴 | frontend/src/components/DataTable.tsx | frontend/src/components/DataTable.stories.tsx:47 / :48 |
| Badge | 確認待ち等の状態表示 | frontend/src/components/Badge.tsx | frontend/src/components/Badge.stories.tsx:5 / :6 |
| Modal | 確認操作を同画面で行う候補 | frontend/src/components/Modal.tsx | frontend/src/components/Modal.stories.tsx:8 / :9 |
| Drawer | 一覧から詳細を開く候補 | frontend/src/components/Drawer.tsx | frontend/src/components/Drawer.stories.tsx:11 / :12 |
| EmptyState | 未登録/検索結果なしの表示 | frontend/src/components/EmptyState.tsx | frontend/src/components/EmptyState.stories.tsx:8 / :9 |

実測: 本体10/10存在、対応stories10/10存在、titleとcomponentの登録10/10一致。frontend/.storybook/main.ts:8-12はsrc/**/*.stories.@(js|jsx|mjs|ts|tsx)を検出対象とする。Storybookのビルド/起動/視覚検査は実行していないため10部品の利用可能性・全状態合格とはしない。

日付入力: TextField.tsx:4にdateの説明、:26-27にnative入力属性の受け渡し、:65にrestをinputへ渡す構造を確認。TextField.stories.tsxはDefault/Required/WithError/Disabled/Sizes/FullWidth/Passwordの7例で、日付専用のstoryは確認できない。日付入力の既存金型候補として参照できるが、日付精度/地域表示/入力操作が今回の要件を満たすかは未検証。

トークン接続の読解: Button.css/FormField.css/DataTable.css/Badge.css/Modal.css/Drawer.css/EmptyState.cssにvar参照あり。固定版tokens.css:434 --comp-btn-radius、:452 --comp-input-radius、:467 --comp-badge-radius、:483 --comp-table-row-h-defaultを確認。index.css:23/:233に明暗の--text-primary。これらは代表参照の存在であり全トークンの定義/重複/全CSS値の検査結果ではない。

別の登録入口: frontend/src/pages/design-preview/sections/registry.ts:32-44はプレビューの11区分を登録し、button/form/badge/table/modal/emptystate等がある。この区分一覧とStorybookの部品一覧を同一の台帳だと扱わない。PageLayout/Drawerの名前がこの11区分にないことだけで未登録金型とは断定しない。正式な登録経路は関連デザインシステム規則との対応を引き続き確認する。

既存チェックの範囲: frontend/scripts/check-stories-count.js:24-33はsrc/components直下の.tsx（stories/test/明示除外を除く）に同名storiesがあるかを検査。下位ディレクトリ全体・story内容・操作・画面適用・アクセシビリティをこの検査だけで保証しない。frontend/package.jsonのcheck:storiesとcheck:allへの接続を読解確認。今回npm/CIは実行していない。

未確認: 金額/通貨/レートの共通表示部品、日付専用の表示/操作試験、ページごとの配置/操作契約、各部品の必要状態、登録手順の全条件、新規部品が必要か。本体やstoryの名前の一致だけで再利用を確定しない。本番のDB/APIは今回照会していない。

## 2026-09-16 金額表示・入金日・操作権限の固定版照合

EV-20260916-DB-SHEET-106。SHA `8c695b8010f465fa342d98243e9d37d917f26843`、git show/grepで読解。本番配備版/実DB/API動作は未確認。ライブラリ一般仕様を推測で採用せず、既存ソースの記述だけを確認した。

| 根拠 | 観測事実 | 理想側への適用限界 |
|---|---|---|
| frontend/src/pages/invoices/InvoicesPage.tsx:36-40 | ローカルfmtが通貨引数とja-JPを使い通貨表示する | 共通金型への登録/他画面共通利用はこの関数では確認できない |
| frontend/src/components/OrderFinancialPanel.tsx:72-83 | fmtJPYはJPY/小数0桁、fmtRateは100倍して小数1桁の百分率 | JPY固定を異通貨表示へ流用しない。百分率を為替レートの金型と扱わない |
| frontend/src/components/CommissionPanel.tsx:172-176 | 別のローカルfmtでja-JP/JPYを指定 | 上記と表示責務が複数箇所に存在する。全リポジトリの全重複数は未計測 |
| frontend/src/pages/invoices/InvoicesPage.tsx:97,102,107 | 発行/入金日時はtoLocaleDateString()、期日は文字列表示 | C60の日本時間/締切明記への適合をこれだけで保証しない |
| frontend/src/components/TextField.stories.tsx:19-88 | 通常/必須/エラー/無効/サイズ/幅/パスワードの7例 | 日付専用storyの表示/操作確認はない。native date属性転送は前回読解したが実表示未検証 |
| frontend/src/hooks/usePermissions.ts:25-26,39-46 | /me/permissionsで取得した集合をhasPermission/hasAnyで参照 | UI非表示だけではサーバー側の更新禁止を保証しない。全ページでの適用は未確認 |
| backend/app/auth/dependencies.py:531-556 | DBからtenant/userの権限を取得、要求権限のいずれかとの共通部分がなければ403 | C16の複数ロール許可の和集合と親和的。新規操作の権限キー/割当は未確定 |
| backend/app/routers/invoices.py:508-535 | 入金APIにinvoices.update検査あり。金額/実入金日入力なし、paid_at=NOW()で更新 | C05の複数入金、C56/C57の実入金日の正本をそのまま実現するものではない |

検索範囲: frontend/srcのformatCurrency/formatMoney（lib/utils/components）とIntl.NumberFormat/toLocaleString/Intl.DateTimeFormat、ファイル名Money/Currency/Date/format、該当hooksとbackendの請求権限。共通部品が存在しないとは断定せず、今回の候補検索では今回要件を満たす登録済み共通金額/日付表示を特定できていないとする。既存の許可キーがあることを「誰に付与済みか」の証拠にしない。製品テスト/CIは今回未実行。


## 2026-09-16 旧仕様と現在合意の差分

EV-20260916-DB-SHEET-107。固定SHA `8c695b8010f465fa342d98243e9d37d917f26843` をgit showで読解。本番配備版/DBの挙動ではなく文書の記述差分。

| 根拠 | 確認した記述 | 今回の設計への扱い |
|---|---|---|
| docs/specs/transaction-flow/README.md:80-88 K7/K8/K9/K10 | 受注ID1つ、状態は記録から判定、返品等は非成約、二重入力禁止 | K9の一律非成約はC12/C21/C27の一部取消/返品後の成約条件と整合が必要。K8の全体状態は入金/条件確認を混同して設計しない |
| docs/adr/ADR-101-sa-quotation-invoice-generation.md:83-90,173 | 請求合計に決済手数料を加える記述 | C48の自社負担とは差異あり。今回の設計では顧客への自動上乗せを採用せず、正式ADR改訂対象として保持 |
| 同ADR:96,169,172 | 使用レート/配送先のスナップショット保存 | 過去の発行事実を保全する方針の根拠。C62の期日保持が実装済みという根拠ではない |

Plannerが用いた合意根拠: sheet-design.md:100,111-119のC43/C54〜C62と各design-status.mdリンク。16項目群と6操作は設計案、8確認票は未実行の期待結果。新しい業務判断や外部API仕様の推定は行っていない。


## 2026-09-16 数量サービスと残額設計の照合

EV-20260916-DB-SHEET-108。比較版は `8c695b8010f465fa342d98243e9d37d917f26843`。git show/git grepによる読解で本番動作ではない。

| 根拠 | 観測事実 | 適用限界 |
|---|---|---|
| backend/app/services/inventory_reservation.py:19-62 | 入力は在庫ID/数量/テナント。physical_qty/reserved_qtyをFOR UPDATEで読み、差分を検査しreserved_qtyへ加算 | 未到着の調達枠/顧客注文/残額使用をこの関数の入力は保持しない。並行安全性全体は未検証 |
| 同ファイル:66-95 | 解除は数量を引き、負なら0とする更新 | どの注文の割当解除かはこの引数にない。過大解除を拒否する今回要件をそのまま満たすとしない |
| 同ファイル:98-128 | 発送時はphysical_qtyを減らしreserved_qtyも減らす | 集荷/発送イベントの接続、再試行の一意性、DB制約まで確認していない |
| backend/app/routers/own_inventory.py:224-277 | reserve/releaseはproducts.update権限、qtyと在庫IDでサービス呼出、監査記録とcommit | UIに権限があっても注文別対象/残額の一体検査はこの経路では確認できない |
| backend/app/routers/order_financials.py:345,381 / analytics.py:632,1633,1773 | refund_amountを費用側や売上からの控除式で参照 | 元注文売上調整の新設時に同一返金の二重控除を避ける照合が必要。今回変更していない |

質問照合の検索範囲: 現worktreeのsheet-design.md/design-status.md、docs/specs/order-management・transaction-flow・quote-invoice、固定版docs/specs・docs/adrへ「端数/丸め/按分/配賦/移籍/転職/返金と報酬」検索。該当範囲では今回の配分/端数/移籍の確定ルールを特定できなかった。全ファイル/本番に不存在とは断定しない。

算術検算（2026-09-16、python3、製品を呼ばない限定例）:
- N01〜N06: 10−8=2、10−8−1=1、10−8−2=0、10−2−8=0、10受取−8集荷=2、8返品受取+2追加=10。
- M01/M02: 残2,000−確保2,000=0、確保を0/使用済みを2,000に移しても利用可能0。
- M03/M04: 次請求3,000−2,000=1,000、元売上10,000−2,000+次売上3,000=11,000。
- M05/M06: 月次10,000−2,000=8,000、次仕入10,000−回収1,000=9,000、元送料1,000−回収1,000=0。
- 結果: assert12/12通過。仮の数字による算術のみ。同時実行/通知重複/失敗回復/実DB/UIの検証結果ではない。
