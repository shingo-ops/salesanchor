# design: 読み込み中の表示を動く印に（2026-10-22 Opus）

参照: docs/handoff/loading-indicator/recon.md ／ 実装カード docs/handoff/loading-indicator/card-1.md ／ ADR-027・ADR-067・ADR-144

## 1 KGI（PO 2026-10-22「1」）
要確認画面（LINE解析 → 要確認タブ）で一覧の取得中、「読み込み中...」の文字ではなく金型の回る丸が出る（PO が目視で○×）。良ければ段階2で他の画面へ広げる。

## 2 現在地
recon.md §1〜§5。金型の Spinner はあるが画面では未使用、文字だけの表示が約56か所、決まりは無い。

## 3 直し方（段階1）
NeedsReviewTabsPanel.tsx:284 の p 要素を `<Spinner size="md" label={t("common.loading")} />` に替える（変更前後はカード §変更）。
- 代替案: Skeleton(table) — aria-label が英語直書き（recon §1）のため段階1では不採用。DataTable に loading 引数を足す案 — 金型変更になり範囲が広がるため段階2で検討。

## 4 受入条件
| 基準 | 検証方法 |
|---|---|
| 読み込み中に回る丸が出る | vitest: role=status・name=common.loading の訳語・class sa-spinner |
| 文字の p 要素が無い | 同じ試験 |
| 既存の試験が通る | NeedsReviewTabsPanel の vitest 全緑 |
| 規約 | eslint 0・UIガバナンス緑・i18n 差 0 |
| 本番 | PO が再読み込み後に目視 |

## 5 弊害とリスク
- 読み上げ文字は aria-label になる（画面上の文字は消える）。動きを減らす設定の利用者には止まった丸が出る（loading-animations.css:543-551）。
- 計時（便0）は loading の表示と無関係（recon・試験で確認）。

## 6 維持の仕組み
- 金型 Spinner と動きのトークンは components/loading と tokens.css が正本。UIガバナンス検査（ADR-144）が直値を止める。
- 段階2で docs/CC_UI_GOVERNANCE.md に「読み込み中は金型の Spinner／Skeleton を使う」を書き、新規の文字だけ表示を防ぐ。

## 7 外部・過去事例の参照と我々への応用
- 外部事例は使わない。理由: 金型（components/loading/README.md・Component Spec）に用途の決まり（Spinner は部分的な読み込み・表の再取得向け）が既にあり、それに従えば足りる。
- 過去事例: Button.tsx:68 が同じ Spinner を使って本番で動いている。

## 8 戻し方
この PR の revert。

---

# 段階2: 金型1つで全部の読み込み中表示が切り替わる形（2026-10-22 Opus）

参照: recon.md「段階2 の現在地」S1〜S6 ／ 実装カード card-2.md（便1）／ ADR-027・ADR-067・ADR-144

## 2-1 KGI（PO 2026-10-22）
PO 原文の要旨: 「全ての読み込みを差し替えて」「金型を変更したら全部切り替わるようにしたほうが良い」「確立したなら進める」。これを ADR-144 §4 の金型新設の PO 許可として扱う。
- K1: 読み込み中の文字だけの表示（recon S1 の T1/T2 142 件）が 0 件になり、すべて金型 `LoadingBlock` の呼び出しになる。測り方は便ごとの grep 件数。
- K2: `LoadingBlock` の中身（見た目・動き）を1か所変えると、全部の画面の読み込み中表示が変わる。Storybook と、置き換えた画面の試験で確かめる。
- K3: 新しく文字だけの読み込み中表示を pages/ に書くと、UI ガバナンス検査が赤になる（scripts/tests の試験で確かめる）。

## 2-2 直し方
### 金型 `LoadingBlock`（新設。置き場所は frontend/src/components/loading/）
- 名前: `LoadingState` は SchedulePageImpl.tsx:816 の関数と重なるので `LoadingBlock` にする（recon S2）。
- props: `label?: string`（既定は金型の中で `t("common.loading")`。ConfirmModal.tsx:31 の前例に倣う）、`size?: SpinnerSize`（既定 'md'）、`inline?: boolean`（既定 false）、`className?: string`。
- 描画: `<div className="sa-loading-block">` の中に `<Spinner size label />` を1つ。role=status は Spinner が持つ（二重にしない）。
- CSS（LoadingBlock.css、var() だけ）: 既定は `.loading`（components.css:423）と同じ寸法。display flex・中央寄せ・padding var(--space-8)・color var(--text-muted)。`inline` のときは inline-flex・padding 0・縦中央。
- 見せる文字は出さない（PO の願いは「文字ではなく動き」）。読み上げは aria-label で残る。
### 置き換えの便（1便ずつ、合流・反映・確認のあとで次へ）
- 便1: 金型の新設（tsx・css・stories・test）、index.ts への export、要確認画面（NeedsReviewTabsPanel.tsx:285）を `LoadingBlock` に置換、docs/CC_UI_GOVERNANCE.md の禁止事項の表に1行、検査に `loadingText` 計数を追加。
- 便2: pages/super-admin（31 件）。ProductMasterPanel.test.tsx:126 の扱いを含む。
- 便3以降: pages/ の残り 87 件を 40 件以下ずつ → features/ 13・components/ 11。検査の対象を features/・components/ に広げるかは便3の後に判断する。
- 別便: ボタン内の三項 T3 42 件を Button の `loading`／`loadingText` へ（HeaderButton に loading が要る）。Spinner.tsx:26・Skeleton・SplashScreen の英語既定を t() に。
- DataTable に loading を持たせる案は、置き換え後に「DataTable の外で読み込み中を出す」画面の数を数えてから判断する（今は ArchivesPage.tsx:35 等で確認済みの数が3件だけ）。
### 検査（scripts/check-ui-governance.js）
- `countLoadingText(content)` を足し、countAll に `loadingText` を加える。数えるのは、`t("…loading…")` のキー名に `loading`/`Loading` を含み、prop の値（直前の `{` の前が `=`）でないもの。`ui-allow:` が前にあれば数えない（既存の hasUiAllowBefore を使う）。
- 増分方式（BASE と HEAD の比較）のままなので、既存 142 件では赤にならず、増やしたときだけ赤になる。

## 2-3 代替案
- 各画面で Spinner を直接呼ぶ（段階1の形）: 中央寄せ・余白が画面ごとに散らばる。金型を変えても全部は変わらない。不採用。
- 既存の `.loading` class の CSS に疑似要素で丸を描く: 66 件の class なし・専用 class 33 件に届かず、読み上げも付かない。不採用。
- eslint の no-restricted-syntax: 既存の ui-allow と増分方式を使えない。不採用。

## 2-4 受入条件（便1）
| 基準 | 検証方法 |
|---|---|
| LoadingBlock が Spinner を1つ出し、既定の読み上げが common.loading の訳語 | LoadingBlock.test.tsx（i18n を import し en で "Loading..."） |
| label・size・inline が効く | 同じ試験（class と aria-label） |
| 要確認画面が LoadingBlock を使う | NeedsReviewTabsPanel.view.test.tsx の既存の試験（role=status・name "Loading..."・sa-spinner）が通る |
| 検査が新しい文字だけ表示を数える／prop と ui-allow は数えない | scripts/tests/test-ui-governance.js に追加の試験 |
| 既存の画面で検査が赤にならない | CI の UI governance gate 緑 |
| 規約 | eslint 0・tsc 新規エラー 0・i18n ja/en 差 0・CSS 直値 0 |
| 本番 | 反映後、PO が要確認画面を再読み込みして、段階1と同じ丸が出る |

## 2-5 弊害とリスク
- 共用 class（`.fu-loading`＋`.fu-empty` 等、recon S3）は便2以降で読み込みだけを外す。CSS 定義は空・エラー側のために残す。
- role=status が増えて試験が落ちる所（recon S6）は、その便で name 指定に直す。e2e は便2で実行して確かめる。
- 検査の判定は文字の形を見るだけなので、prop 以外の三項（`title={x ? t("…loading") : …}`）、テンプレート文字列の `${t(…)}`、JSX の外の `t(…)`、`loadingError` のような読み込み中でないキーを数えることがある（審査 probe-edge-cases.txt）。増分方式なので既存は赤にならず、新しく当たった場合は ui-allow で除外する。

## 2-6 維持の仕組み
- 正本は LoadingBlock（components/loading/）1つ。見た目は LoadingBlock.css と loading-animations.css、寸法はトークン。
- UI ガバナンス検査（必須チェック）が新しい文字だけ表示を止める。docs/CC_UI_GOVERNANCE.md の禁止事項の表に書く。
- 残り件数は便ごとに recon の方法（grep）で数え、memory/project_loading_indicator.md に記録する。
- 守り手: UI governance gate（.github/workflows/ui-governance-gate.yml、必須チェック）と Opus（便ごとの件数の記録）。

## 2-7 外部・過去事例の参照と我々への応用
- 外部事例は使わない。理由: 社内に同じ形の前例（Radio・RadioControl の新設 2db5c98ab と禁止事項の表への1行、ConfirmModal の既定文字 t()）があり、それに従えば足りる。
- 過去事例: 段階1（#4624）の Spinner が本番で動いている。便1は同じ Spinner を金型の中へ移すだけで、見た目は変わらない。

## 2-8 戻し方
便ごとの PR を revert。便1を戻すと要確認画面は段階1の Spinner 直接呼び出しに戻る。

## 2-9 便2（pages/super-admin 31 件）
- 直し方: 実装カード card-3.md の §1 規則 A〜C と §2 の表。要素ごと `<LoadingBlock />` に替え、label は渡さない（recon B3）。インライン style の 5 ファイルは style ごと消えて金型の見た目にそろう。
- 試験: ProductMasterPanel.test.tsx:126 を `queryByText(/^Products: \d+/)` が null の確認に替える（recon B5。試験の意図を保つ）。
- 触らない: ボタン内の三項・CSS・辞書（参照 0 になるキー 2 つは辞書整理の別便で消す）。
- 受入条件
| 基準 | 検証方法 |
|---|---|
| super-admin の文字だけ表示が 48→17 件 | countLoadingText で前後を数える（/tmp/CC報告ファイル/loading-stage2-bin2/count-*.txt） |
| 既存の試験が通る | vitest src/pages/super-admin 全件 pass |
| 規約 | tsc 0・eslint 0・i18n 欠け 0・UI governance gate 緑 |
| e2e | CI の e2e 緑 |
| 本番 | 反映後、本番の画面の JS に変わった画面の LoadingBlock 呼び出しが入っている |
- 守り手: 2-6 と同じ（UI governance gate と Opus の件数記録）。
- 戻し方: 本便の PR を revert。

## 2-10 便3 第1組（買取相場・ダッシュボード・管理・受信箱など 32 件）
- 直し方: card-4.md の規則 A〜D。便2の規則に、文言が違うキーは label で渡す（C）と、入力欄の注記だった 2 件は size="sm"（D）を足した。
- 追補1: もともとあった lint 警告 4 件（recon C6）を、表示を変えずに直す（依存配列に t、defaultValue を外す、「万」を t("common.unitMan") から渡す）。
- 触らない: excluded の 22 件、第2組・第3組、CSS・辞書。
- 受入条件
| 基準 | 検証方法 |
|---|---|
| 対象 25 ファイルの件数が 34→2（32 減） | countLoadingText の前後（/tmp/CC報告ファイル/loading-stage2-bin3/count-*.txt） |
| 試験 | vitest の対象 6 ディレクトリが全件 pass |
| 規約 | tsc 0・eslint 警告 0・i18n 欠け 0・UI governance gate 緑 |
| 本番 | 反映後、買取相場の画面を再読み込みすると読み込み中に丸が出る（PO 目視） |
- 弊害: InventoryPage 系の試験は負荷が高いと時々落ちる（未変更のファイル。原因は未確認、再実行で pass）。
- 守り手: 2-6 と同じ（UI governance gate と Opus の件数記録）。
- 戻し方: 本便の PR を revert。

## 2-11 便3 第2組（仕入元・単位・チーム・スタッフなど 18 画面 28 件）
- 直し方: card-5.md の規則 A・B。全件 common.loading なので label・size は渡さない。RolesPage は外側の `<div className="page">` を残す（規則 E、recon C7）。
- 触らない: excluded の件、第3組、CSS・辞書。
- 受入条件
| 基準 | 検証方法 |
|---|---|
| 対象 28 ファイルの件数が 41→13（28 減） | countLoadingText の前後（/tmp/CC報告ファイル/loading-stage2-bin3-g2/count-*.txt） |
| 試験 | 対象ページを読み込む試験 10 本が pass（対象ディレクトリの試験は 0 本） |
| 規約 | tsc 0・eslint 警告 0・i18n 欠け 0・UI governance gate 緑 |
| 本番 | 反映後、本番の画面の JS で仕入元一覧の読み込み枝が LoadingBlock 呼び出しになっている |
- 弊害: ButtonMigration 系の試験は負荷が高いと 5 秒の時間切れで落ちる（未変更の試験。単独・時間延長の再実行で pass）。
- 守り手: 2-6 と同じ（UI governance gate と Opus の件数記録）。
- 戻し方: 本便の PR を revert。

## 2-12 便3 第3組（顧客・見込み客・商品・見積・請求・受注・登録など 17 画面 24 件）
- 直し方: card-6.md の規則 A・B・E・F。枠の div は残し中だけ替える（E）、枠の div 自身が文字を持つ 1 件は枠を残して文字だけ替える（F、recon C8）。label・size は渡さない。CommissionsPage の読み込み中の上の余白（marginTop）は金型の見た目にそろって消える（便2のインライン style と同じ扱い）。
- 触らない: excluded の件、features/・components/、CSS・辞書。
- 受入条件
| 基準 | 検証方法 |
|---|---|
| 対象 23 ファイルの件数が 25→1（24 減） | countLoadingText の前後（/tmp/CC報告ファイル/loading-stage2-bin3-g3/count-*.txt） |
| 試験 | 対象ページを読み込む試験 14 本が pass |
| 規約 | tsc 0・eslint 警告 0・i18n 欠け 0・UI governance gate 緑 |
| 本番 | 反映後、本番の画面の JS で見積詳細と登録画面の読み込み枝が LoadingBlock 呼び出しになっている |
- 弊害: ButtonMigration 系の試験は負荷が高いと 5 秒の時間切れで落ちる（未変更の試験。単独・時間延長の再実行で pass）。
- 守り手: 2-6 と同じ（UI governance gate と Opus の件数記録）。
- 戻し方: 本便の PR を revert。

## 2-13 便4（features/・components/ の 24 件・23 ファイル）
- 直し方: card-6.md の規則 A・E・F に、card-7.md の判断 1〜3 を加える。
  - 判断1（文言を変えない）: キーが common.loading でない 3 件（ExtractionAttemptHistory・ProductMasterDrawer・ReviewSection）は `label` で今の文言を保つ。理由: 画面に出る文言を便の中で変えないため。
  - 判断2（認証待ちの全画面配置を保つ）: ProtectedRoute は `div.loading-screen` を残し中だけ `<LoadingBlock />` にする。理由: 全画面の中央寄せを保つため。
  - 判断3（一覧の行の高さと data-testid を保つ）: ChannelTypeCombobox・CountryCombobox・InventorySearchBar は枠（div・li・style・data-testid）を残し中を `<LoadingBlock size="sm" inline />` にする。理由: 選択肢の一覧の行の高さと試験用 data-testid を保つため。
- 触らない: excluded の 10 件、CSS・辞書・金型・scripts/。
- 受入条件
| 基準 | 検証方法 |
|---|---|
| 対象 24 件が消える（対象 23 ファイル 25→1、本体 31→7） | countLoadingText の前後（/tmp/CC報告ファイル/loading-stage2-bin4/impl/count-*.txt） |
| 試験 | 対象ディレクトリの vitest 全件 pass |
| 規約 | tsc 0・eslint 警告 0・i18n 欠け 0・UI governance gate 緑 |
- 弊害: 小さい丸（sm）は読み込み中の文字より小さく見える。
- 守り手: 2-6 と同じ。
- 戻し方: 本便の PR を revert。

# 段階3: ボタンの中の読み込み中を金型 Button の丸＋元の言葉へ（2026-10-24 Opus）

参照: recon.md「段階3 の調査」C10 ／ 実装カード card-8.md（便1）／ ADR-027・ADR-067・ADR-144

## 3-1 KGI（PO 2026-10-23「1」）
PO の選択: 押すと丸と元の言葉が並ぶ（例: 丸＋「保存」）。ボタンの部品を1か所直すと全部のボタンが同じ見た目になる。
- K1: ボタンの中で押すと文字が読み込み中系の文言に変わる箇所（recon C10 の targets 134 件）が 0 件になる。測り方は便ごとの抽出スクリプト（/tmp/CC報告ファイル/loading-button-recon/targets.cjs）の再実行件数。
- K2: 押している間、ボタンには丸（金型 Spinner）と元の言葉が並ぶ。言葉は変わらない。置き換えたボタンの試験で「押下中も元の言葉・aria-busy=true・disabled」を確かめる。
- K3: 金型 Button の丸の見た目を1か所（Button.tsx の loading 表示）で変えると全部のボタンが変わる。文言差し替えの口（loadingText）は無くす。

## 3-2 直し方
- 金型 Button（Button.tsx:28-29,46,68-69）: `loading` は今のまま（丸＋children、disabled||loading、aria-busy）。`loadingText` を props から削除し、69 行を `{children}` にする。理由: 丸＋元の言葉に揃え、文言差し替えを型で書けなくする（K3）。
- 金型 HeaderButton（HeaderButton.tsx:25-28,39,46-57）: テキスト用の TextButtonProps に `loading?: boolean` を足し、Button へ素通しする。icon 用（生 `icon-btn`）には足さない（対象 38 件はすべてテキスト用。recon C10）。
- 各ボタン: `{busy ? t(読み込み中キー) : t(元のキー)}` や `{t(busy ? 読み込み中キー : 元のキー)}` を `loading={busy}` ＋ `{t(元のキー)}` に替える。disabled の条件はそのまま残す（Button が disabled||loading で重ねる）。
- 生 `<button>` 9 件は金型 Button へ移す便を分ける（見た目が変わるため単独で確かめる）。

## 3-3 便（1便ずつ、合流・反映・確認のあとで次へ）
- 便1（card-8.md）: 金型2つの変更（loadingText 削除・HeaderButton に loading）、loadingText を使う 8 件、loading と三項を併用している 7 件、金型の試験・stories。
- 便2（card-9）= pages/super-admin 22・pages/integrations 12。
- 便3（card-10）= pages/admin ほか 34 か所。
- 便4（card-11）= pages の残りと features ほか 34 か所。
- 便5（card-12）= components と残り 8 か所。
- 便2〜5: 金型経由の残り（Button・HeaderButton）を 40 件以下ずつ。ディレクトリ順（pages/super-admin → pages/integrations・admin → pages の残り → features・components）。
- 便6: 生 `<button>` 9 件を金型 Button へ。
- 便7: 再発防止の検査（金型ボタンの children に読み込み中系キーの三項を書くと UI ガバナンス検査が赤）と、使われなくなった辞書キーの整理。

## 3-4 代替案
- loadingText を残し、各所で loadingText を外す: 文言差し替えを後から書けてしまい K3 を満たさない。不採用。
- HeaderButton をやめ Button に置き換える: ADR-069 のヘッダーボタン SSoT を崩す。不採用。
- 丸だけにして言葉を消す: PO が選ばなかった（2026-10-23 選択肢2）。

## 3-5 受入条件（便1）
| 基準 | 検証方法 |
|---|---|
| Button から loadingText が無くなり、使う箇所 0 | `git grep -n "loadingText" -- frontend/src` で Button 系 0（AsyncCombobox の loadingText は別部品で対象外） |
| 便1 対象 15 件が丸＋元の言葉 | 対象の試験で押下中の textContent が元の言葉・aria-busy=true |
| HeaderButton の loading | HeaderButton.test.tsx に loading=true で Spinner・aria-busy・disabled を確かめる試験 |
| 規約 | tsc 0・eslint 警告 0・i18n 欠け 0・UI governance gate 緑・Storybook build 緑 |

## 3-6 弊害とリスク
- 押下中の言葉が「保存中…」から「保存」に変わる。読み上げは aria-busy で「処理中」が伝わる。
- 今まで押下中も押せたボタンがあれば押せなくなる（Button が disabled||loading）。便ごとに disabled の条件に busy が入っているかを確かめ、入っていない箇所は差分として報告する。二重押しを防ぐ向きの変化。
- 試験の期待（押下中の文字）を直す必要がある: recon C10 の A群 7 ファイル 12 点。

## 3-7 維持の仕組み
- 型: Button に loadingText が無いので文言差し替えはコンパイルで止まる。
- 検査: 便7 で UI ガバナンス検査に三項の計数を足すまでは、便ごとの抽出スクリプトの件数で見張る。

## 3-8 外部・過去事例の参照と我々への応用
- 段階2（LoadingBlock 108 件）と同じ「金型を1つにして 40 件以下ずつ置換・便ごとに本番の配信 JS で確かめる」型を使う。外部事例は使わない（社内の金型移行で、段階2の実測で足りるため）。

## 3-9 戻し方
- 便ごとの PR を revert。便1 を戻すと loadingText が復活するため、便2 以降を先に戻す。
