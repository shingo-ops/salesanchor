# 実装カード 段階3 便6a — 金型 Button の入れ子の三項 7 か所と文字の三項 1 か所を「丸＋元の言葉」へ

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 方針 2026-10-23「1」、設計 2026-10-24「1」、便6 着手 2026-10-25「1」（「形が違うボタンの直し方を書いた指示書を先に作り、自分で点検してから直す」）
- 起点: 最新の origin/main（便5 #4750 合流 cd2af3eb4 を含む）。ブランチ `release/loading-button-bin6a`
- 根拠: /tmp/CC報告ファイル/loading-button-bin6/recon/rows.md（origin/main c233ec8f6 時点の実物）・targets-now.tsv
- 対象ADR: ADR-144・ADR-067・ADR-027
- 便6 の分け方: 便6a＝金型 Button の 8 か所（見た目は変わらない）。便6b＝生 button 9 か所（見た目が変わる。card-14 で別に出す）

## 1. 対象（8 か所・8 ファイル。行は c233ec8f6 時点）
| # | ファイル:行 | 今の中身 | 直したあと |
|---|---|---|---|
| 1 | components/OrderFinancialPanel.tsx:294 | `{saving ? t("common.saving") : existing ? t("common.update") : t("common.register")}` | 要素に `loading={saving}`、中身 `{existing ? t("common.update") : t("common.register")}` |
| 2 | components/PurchaseDetailPanel.tsx:299 | 同上 | 同上 |
| 3 | components/ShippingDetailPanel.tsx:372 | 同上 | 同上 |
| 4 | features/supplier-master/SupplierDetailDrawer.tsx:307 | `{t(saving ? \`${s}.saving\` : mode === "create" ? "common.create" : "common.save")}` | `loading={saving}`、中身 `{t(mode === "create" ? "common.create" : "common.save")}` |
| 5 | features/tcg-product-import/TcgProductDetailDrawer.tsx:305 | `{t(saving ? "productDetail.saving" : mode === "create" ? "productDetail.create" : "productDetail.save")}` | `loading={saving}`、中身 `{t(mode === "create" ? "productDetail.create" : "productDetail.save")}` |
| 6 | pages/admin/DiscordConfigPage.tsx:374 | `{guildSaving ? t("common.saving") : isConnected ? t("common.save") : t("discordConfig.connect")}` | `loading={guildSaving}`、中身 `{isConnected ? t("common.save") : t("discordConfig.connect")}` |
| 7 | pages/products/ProductEditPage.tsx:189 | `{saving ? t("common.saving") : isNew ? t("common.register") : t("common.update")}` | `loading={saving}`、中身 `{isNew ? t("common.register") : t("common.update")}` |
| 8 | pages/buyback-prices/BuybackPricesPage.tsx:302 | `{fetching ? "..." : t("buybackPrices.fetchNow")}` | `loading={fetching}`、中身 `{t("buybackPrices.fetchNow")}`（直書きの "..." が消える） |

## 2. 置き換えの規則（規則3。card-9 の規則1・2 に足す）
- 規則3: `{X ? 読み込み中の言葉 : 選び分けの式}`（選び分けの式は三項でもよい）→ 要素に `loading={X}`、中身は「選び分けの式」を1文字も変えずに残す。`t(X ? L : 選び分け)` の形は `t(選び分け)` にする
- X は元の式のまま。disabled・variant・size・form・type・data-testid は変えない
- 理由: 外側の条件が読み込み中、内側は読み込みと関係のない言葉の選び分け。便4 TcgProductImportPreview:40 と同じ判断（審査で事実確認済み）
- 実物が §1 の「今の中身」と1文字でも違う → その行だけ直さずに外し、新旧を報告（全体は止めない）。行がずれただけで文面が同じなら進め、新旧の行を報告

## 3. 押せる・押せないの変化
- 8 か所とも disabled に X が入っている（rows.md の (b)）。変化なし。実物で違えば報告

## 4. 試験
- 変更するファイルを描く試験を `frontend/src` 全体から探す（import している試験・`*ButtonMigration.test.tsx`）。一覧を impl/tests-found.txt に保存し、全部を実行する
- 既知の期待の直し（rows.md (d)）: SharedButtonMigration.test.tsx:141（fin-save）と :156（pur-save・ship-save の it.each）が `textContent` に 'common.saving' を期待している。期待を「元の言葉（読み込み前の言葉と同じキー）のまま・そのボタンが aria-busy="true"」に直す。disabled の確認は残す。直した試験はファイル:行と前後を報告
- それ以外で落ちた試験は直さない。単独・`--testTimeout=30000` で再実行し、通れば負荷とみなして両方の生出力を残す。それでも落ちれば BLOCKED:
- 最後に `npx vitest run -c vitest.unit.config.ts` を全体で1回（tsc・eslint と同時に走らせない）。落ちたファイルは単独・`--testTimeout=30000` で再実行

## 5. 触らない範囲
- 生 `<button>` 9 か所（便6b）、辞書（使われなくなるキーも消さない＝便7）、CSS、scripts/、金型
- 対象ファイルにもともとある lint 警告で止まったら直さず BLOCKED:

## 6. 文書
- 本カードを docs/handoff/loading-indicator/card-13.md として同じ PR に入れる
- design.md 段階3 の 3-2 の最後の箇条の下に「- 規則3（便6a で追加）: 外側の条件が読み込み中で内側が言葉の選び分けの三項は、`loading={外側の条件}`＋内側の式をそのまま残す。」を1行足す
- design.md 3-3 の便5 の行の下に「- 便6a（card-13）= 金型 Button の入れ子の三項 7・文字の三項 1 の 8 か所。便6b（card-14）= 生 button 9 か所。」を1行足す
- 台帳 .claude-pipeline/active-work.d/release-loading-button-bin6a.md（便5 と同じ形）

## 7. 検証（生出力を /tmp/CC報告ファイル/loading-button-bin6a/impl/ へ）
| 基準 | 検証方法 |
|---|---|
| 対象が消える | targets.cjs（/tmp/CC報告ファイル/loading-button-recon/）を frontend/src で再実行し、§1 の 8 行が 0 件・残りが生 button 9 行だけ |
| 丸＋元の言葉 | tests-found.txt の試験と全体の unit 試験が pass（§4 の再実行を含む） |
| 型・lint・i18n・UI | tsc 0・eslint（変更ファイル --max-warnings=0）0・check-i18n-missing-keys.js exit 0・scripts/check-ui-governance.js exit 0（BASE_SHA/HEAD_SHA 指定） |
| 範囲 | `git diff origin/main...HEAD --name-only` が対象 8 ファイル＋直した試験＋§6 の文書・台帳だけ |

## 8. 想定分岐
- schema.d.ts が無い → `npm run generate:api-types` を先に
- 複数行に分かれた三項で機械置換が当たらない → 手で直し、元の式と1文字ずつ照らした結果を報告
