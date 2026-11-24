本報告は PR 5718 の確認結果である

# eval-report — お客様の住所フォームの並び（customer-form-pc-layout）

- 確認役: Claude（evaluator）・2026-11-24（クラウド）
- 確かめた物: `origin/release/customer-form-pc-layout-impl`（3943c9c75）／比べる前: `origin/main`（71cae5cb7）
- 設計・KGI: `docs/handoff/customer-form-layout/design.md`（§6・§7・§9）・`docs/specs/customer-address-form/kgi.md`
- 判定: **PASS**（K1〜K9 すべて ○。K10〜K14 はこの確認の範囲外で未判定）
- 横幅 1280px・Chromium（環境の入り物 `/opt/pw-browsers/chromium`）・API は `page.route` で mock・画面は英語（`?lang=en`）

## 1. 試験の実行（K 系の自動試験）

`npx playwright test register-form-ux.spec.ts --project=chromium`（impl 側・frontend で `npm ci` の後）

- 結果: 21 件中 **10 件 ○・11 件 ×**
- ○: B-3（K3）・K1×3（/register・/register/address・/register/change-billing）・K2・K5・K6・K7・K8・K9
- ×（11 件）: B-1・B-2・A-1・A-2・A-3・C-1〜C-6。**main 側で同じ spec を流しても同じ 11 件が ×**（main は B-3 も × で計 12 件 ×）。つまり今回の変更で新しく壊れた物ではない。×の中身は「最初の fieldset の見出しが `担当者` を含む」などの日本語文言の期待に対し、画面が `Section 1 - Billing Address Registration`（英語）で、spec の期待と画面の文言が合っていない、という出力だった（生出力 `pw-impl.log`・`pw-base.log`）。原因の深掘りは未実施。
- 環境の注記: `npx playwright install chromium` はダウンロード失敗（exit 1）だったため、環境に入っている Chromium を `executablePath` で指す設定ファイルを scratchpad 内（リポジトリ外・未 commit）に作って流した。リポジトリの設定は変えていない。

## 2. 前後の幅（K5）— 1280px・getBoundingClientRect の幅（px）

| 画面 | 欄 | main（前） | impl（後） | 同じか |
|---|---|---|---|---|
| /register（請求先） | 住所1 | 600 | 600 | ○ |
| /register | 住所2 | 600 | 600 | ○ |
| /register | 外枠（.page-container） | 600 | 600 | ○ |
| /register/address | 住所1 | 600 | 600 | ○ |
| /register/address | 住所2 | 600 | 600 | ○ |
| /register/address | 外枠 | 600 | 600 | ○ |
| /register/change-billing（請求先） | 住所1 | 600 | 600 | ○ |
| /register/change-billing | 住所2 | 600 | 600 | ○ |
| /register/change-billing | 外枠 | 600 | 600 | ○ |

→ K5 ○（差 0px。基準は 1px 以内）。生データ: `eval/measure-width.json`。

## 3. K ごとの判定（画面の数値）

| K | 判定 | 数値 | 根拠 |
|---|---|---|---|
| K1 言語切替が見出しと同じ行の右 | ○ | /register: 見出し y=8〜38（高さ30）・切替 y=0〜36（中心 18）・見出しの右端 599.4 < 切替の左端 831。/register/address: 見出し y=8〜38・右端 489.7 < 831。/register/change-billing: 見出し y=8〜38・右端 609.4 < 831 | 3 画面とも「切替の縦中心が見出しの上端〜下端の間」かつ「切替の左端が見出しの右端より右」。spec の K1×3 も ○。前（main）は見出し y=36〜87 で切替中心 18 が範囲外（×だった） |
| K2 国番号は番号だけ・欠けない・幅 80px | ○ | 国番号の欄の幅 80px（前 140px）・表示 `+1`（前 `+1 BS`）。spec K2: `COUNTRIES` 全件を順に選び `scrollWidth <= clientWidth` と値＝番号だけを確認し ○（22.3s） | 欄の中身は番号だけ。191 件の網羅は spec のループによる |
| K3 City 1行・State と ZIP 同じ行 | ○ | /register 請求先: City 幅 600（住所1と同じ）・State y=948.5・ZIP y=948.5・幅 292 ずつ。/register 送り先（Proceed）: City 600・State/ZIP とも y=1276.3・292。/register/address: City 600・State/ZIP とも y=824.9。/register/change-billing: City 600・State/ZIP とも y=948.5 | 4 か所すべて、上端の差 0・City が1行 |
| K4 「jap」で Japan (JP) | ○ | 請求先・送り先の国の欄に `jap` → 候補 `Japan (JP)` の1件 → 選ぶと欄の値が `Japan (JP)` | `eval/measure-rules.json`（k4_billing・k4_shipping） |
| K5 住所1・2 は今のまま | ○ | §2 の表のとおり前後とも 600px | 上記 |
| K6 送り先は35文字まで | ○ | 送り先（/register で Proceed 選択・/register/address）の住所1・2・3 すべてで、36文字 → 「Please enter 35 characters or fewer.」が1件出る。35文字 → 出ない。36文字時の枠色 rgb(229,62,62)（赤）・35文字（入力中）rgb(30,58,138)・初期 rgb(226,232,240)。spec K6: 36文字だと送信 0 回・35文字だと送信 1 回で完了画面 | 画面の数値と spec。「画面を通さず直接送って断られる」側は backend の pytest の範囲で、この確認では未実施 |
| K7 英字等以外は断る | ○ | 送り先の住所1・2・3 すべてで「東京」「Café」→「Please use English letters, numbers and symbols only.」が1件出る。spec K7: 送信 0 回 | 同上 |
| K8 請求先は「同じ」を選んだ時だけ決まりが効く | ○ | spec K8: 請求先の住所1に36文字 → 既定（Ship to the same address.）では赤文が出る → Proceed に切替で赤文が 0 件 → 送信 1 回で完了画面・送った中身の billing 住所1 は36文字のまま | spec の出力（○） |
| K9 請求先に住所3 | ○ | /register と /register/change-billing の請求先に Address Line 3 の欄あり（欄の数: 前 0 → 後 1。/register/address は前から 1）。spec K9: 送る中身の billing `address_line_3` = `Building C`（/register）、change-billing の `address.address_line_3` = `Floor 9` | 画面の数値と spec。「会社の住所の住所3として保存」は backend 側で、この確認では未実施 |

K10〜K14 は範囲外（見積書 PDF・社内画面・本番の読み取り・コード検索・CI）。

## 4. 撮影の場所（1280px・ページ全体）

`docs/handoff/customer-form-layout/eval/`（前＝main・後＝impl）

| 画面 | 前 | 後 |
|---|---|---|
| /register | `before-register.png` | `after-register.png`（送り先を出した状態は `after-register-proceed.png`） |
| /register/address | `before-register_address.png` | `after-register_address.png` |
| /register/change-billing | `before-register_change-billing.png` | `after-register_change-billing.png` |

測定の生データ: `eval/measure-width.json`（前後の幅・位置）・`eval/measure-rules.json`（impl の送り先の決まり・国の候補）。

## 5. 見た目で変わった所（PO 目視の材料。design §7 の予告と照らす）

撮影した前後の画像と数値から確認できた違い:

- 見出し（h1）が小さくなり、言語切替と同じ行になった。見出しの高さ 51px → 30px、見出しの上の余白が減り、全体の開始位置が上がった。
- 国番号の欄が 140px → 80px になり、表示が `+1 BS` → `+1` になった（電話番号の欄が右に広がった）。
- State と ZIP が1行で左右に並んだ（前は City・State・ZIP が縦に1行ずつ）。
- 請求先に Address Line 3 の欄が増えた（/register・/register/change-billing）。
- 住所1〜3 のラベルの字が小さく灰色になった（`TextField` の型）。他の欄のラベルは今までの字。住所1〜3 の欄どうしの縦の間隔が広がった（住所1→2 の間 65px → 93px。design §7 が予告した「下の間隔が他より広い」と一致）。
- 必須の印（*）が赤になり、ヒント文（Please enter store name… など）の字が小さくなった。各欄の縦の間隔が全体に広がり、ページが縦に長くなった（/register: 1292px → 1555px・/register/address: 892px → 1006px・/register/change-billing: 943px → 1129px）。
- 「Contact Person」の見出しの位置が左端から約 8px ずれた（/register 後の画像）。
- 国の欄の位置・Proceed の選択肢の周りの間隔も広がった。
- 幅が変わらなかった物: 住所1・2・外枠（600px）。

上のうち、必須の印の赤・縦の間隔の広がり・見出しの大きさ・住所1〜3 のラベルの字・ヒント文の小ささは、design §7 に予告されていた変化の範囲に見える。「Contact Person」の約 8px のずれは §7 に書かれておらず、意図した変化かは未確認（設計担当へ確認が必要）。

## 6. 未実施・限界

- 実機の本番 Chrome・スマホ幅は確かめていない（PC 先行の設計）。
- K6・K9 の「受け口（backend）で断る・保存される」側は pytest の範囲で、この確認では流していない。
- 11 件の既存 spec の × は main と同じため今回の判定には入れていないが、CI で Playwright が止まっている（`.github/workflows/e2e.yml` の `if: false`）ため放置されている状態に見える。
