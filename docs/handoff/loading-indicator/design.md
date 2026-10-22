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
