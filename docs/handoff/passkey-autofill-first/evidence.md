# 顔・指紋のログインと「自動で出る画面」の根拠（2026-11-23 取得）

## A. 今のアプリ（origin/main を読んだ事実）
| 項目 | 事実 | 根拠 |
|---|---|---|
| 顔・指紋のログインの正体 | パスキー（WebAuthn）。部品 @simplewebauthn/browser 14.0.0 | frontend/package.json:80, frontend/src/lib/auth/passkey.ts:27-29 |
| ログイン画面の出し方 | 「パスキーでログイン」ボタンを押したときだけ呼ぶ | frontend/src/pages/login/LoginPage.tsx:235-245, 424-435 |
| メール欄の自動入力設定 | autoComplete="email"（webauthn が無い） | LoginPage.tsx:401 |
| 自動で出す設定（useBrowserAutofill） | 使っていない（0件） | git grep 結果 |
| パスワードで入った後の自動登録 | 有る（useAutoRegister: true） | passkey.ts:87 |
| サーバーの登録設定 | 端末に名前ごと保存（resident_key REQUIRED）・本人確認必須（UV REQUIRED） | backend/app/auth/passkeys.py:76-77, 84-87 |
| 知らない機械の確認 | パスキーで入るときは不要 | ADR-1055 What 5 |

→ 自動で出る画面に要るのは、画面側の2か所（メール欄に webauthn を足す・開いたときに待ち受けを始める）。サーバーは今の設定のままで条件を満たす（【推測ではなく】部品の説明書: "requires an input with autocomplete=webauthn"、Context7 /websites/simplewebauthn_dev）。

## B. ブラウザの対応（MDN browser-compat-data・2026-11-23 取得）
- 自動で出す仕組み（isConditionalMediationAvailable）: Chrome 108〜・Edge 同じ・Safari 16〜（iPhone も同じ）・Firefox 119〜。

## C. 成功事例（5W2H）
| 誰が | いつ | どこで | 何を | なぜ | どうやって | どれだけ（数値） | 出典 |
|---|---|---|---|---|---|---|---|
| 業界団体の調査（参加15社: Amazon・Google・LY・メルカリ・Microsoft・ドコモ・PayPal・KDDI ほか） | 2026-09-21 集計・10-15 公表 | 世界の一般向けサービス | パスキーのログイン | 乗っ取りと SMS 費用を減らす | 各社の実測を集計 | 成功率 93%（パスワード等 78%）・2.8倍速い・1回27秒短縮・ログインの36%がパスキー・フィッシング被害が減った 8社中8社 | https://fidoalliance.org/wp-content/uploads/2026/10/Passkey-Index-October-2026.pdf |
| 同 2025年版（9社） | 2025-10-14 | 同上 | 同上 | 同上 | 同上 | 成功率 93%（他 63%）・8.5秒（従来の2段 31.2秒・73%短縮）・ログイン関連の問い合わせ最大81%減 | https://fidoalliance.org/wp-content/uploads/2025/10/FIDO-Passkey-Index-October-2025.pdf |
| Microsoft | 2024-05 開始・2024-12-12 公表 | 個人向けアカウント（10億人超） | パスキーを標準のログインに | パスワード攻撃が毎秒7,000件 | 持っている人にはパスキーだけを表示・ログイン直後に登録を勧める | 成功率 98%（パスワード 32%）・パスワードの3倍速い・登録開始者の99%が完了・勧めに25%が反応・設定画面からの登録は1%未満・新画面でパスキー利用 +987% | https://www.microsoft.com/en-us/security/blog/2024/12/12/convincing-a-billion-users-to-love-passkeys-ux-design-insights-from-microsoft-to-boost-adoption-and-security/ |
| Yahoo! JAPAN（LY） | 2019 開始・2023-10-27 更新 | 月5,500万人のログイン | パスキー | SMS 費用と問い合わせを減らす | ログイン直後に登録を勧める・画面に「Face ID」等を明記 | ログインの11%（スマホ18%）・2.6倍速い・ID/パスワード忘れの問い合わせ25%減・登録の97%は勧めの画面から（設定画面は3%）・Windows で明記により押す率 +15.35pt | https://web.dev/case-studies/yahoo-japan-passkeys |
| Dashlane | 2023-10-24 公表 | ウェブ（1,800万人） | 自動で出る画面（conditional UI）で保存済みパスキーを提案 | ログインの成功を上げる | 拡張機能で提案 | 提案からの成功 92%（パスワード自動入力 54%・70%増） | https://developers.googleblog.com/en/password-manager-dashlane-sees-70-increase-in-conversion-rate-for-signing-in-with-passkeys-compared-to-passwords/ |
| adidas | 〜2026-04 世界展開 | 通販サイト | 自動登録＋自動で出す | 打ち間違い・忘れの失敗を減らす | パスワードで入った後に裏で自動作成・Signal API | 作成率47%（スマホ52%・PC34%）・成功率99%超（パスワード70%）・自動作成で +8%・「パスキーが無い」エラー0.3%未満 | https://web.dev/case-studies/adidas-passkeys |

## D. 失敗事例・つまずき（5W2H）
| 誰が | いつ | 何が起きたか | 原因 | 数値 | 出典 |
|---|---|---|---|---|---|
| 業界調査の参加2社 | 2026 | パスキーを持つ人にもパスワードや番号を先に出した | 画面の順番 | パスキーを先に出せば利用が約2倍と1社が見積もり・10社中8社で「持っているのに使われない」 | Passkey Index 2026 p.6, p.10 |
| Yahoo! JAPAN（Android） | 2019→2022 | 使い続けた人が少なかった | 機械を替えると消える方式（同期なし）だった | 継続38%・62%は SMS 等へ戻った | web.dev 同上 |
| Microsoft | 2024 | 設定画面だけでは登録されない | 自分から設定に行く人が少ない | 設定画面経由は登録の1%未満 | Microsoft 同上 |
| 調査会社 Corbado（売り手の資料・参考） | 2026 Q1 | 自動で出る画面でも最初の提案で入れない人がいる | 別の機械にパスキーがある・欄の設定ミス・パスワード管理ソフトの割り込み | 最初の提案での完了 55〜90%・やり直しを含め 90〜95%・Windows の Chrome では提案が出たのが 11% | https://www.corbado.com/passkey-benchmark-2026/conditional-ui-usage.md |
| 同（売り手の資料・参考） | 2026 | 技術は正しいのに広まらない | 勧め方を設計しない | 採用5%未満の例・3か月で作成10%未満・ログイン5%未満は失敗の目安 | https://www.corbado.com/blog/passkey-day-2-problems |

## 未確認
- KAYAK・eBay の数値は二次資料しか見つからず、元の発表を確かめていない（使わない）。
- 自動で出る画面が、このアプリの本番のログイン画面と PO の機械（Mac の Chrome・iPhone・Android）で実際に出るか（作って確かめるまで不明）。
- 社員がすでに登録したパスキーが、各機械の間で同期される方式か（Google パスワードマネージャー・iCloud キーチェーン等、登録した場所による）。

## E. 「すぐ出す」仕組み（Immediate UI mode）の事実（2026-11-24 00:10 JST 取得）
| 項目 | 事実 | 出典 |
|---|---|---|
| 対応 | Chrome 149 から。2026-05 時点で対応は Chrome だけ | https://developer.chrome.com/blog/webauthn-immediate-ui ・ https://developer.chrome.com/docs/identity/immediate-ui-mode |
| 呼び方 | navigator.credentials.get に uiMode: 'immediate'（mediation:'immediate' は効かなくなった） | 同上 |
| 押す操作が必須 | "You must initiate the API call with a user gesture, such as a click"。画面を開いただけでは出せない | docs/identity/immediate-ui-mode |
| 無いとき | パスキーが無ければ何も出さず NotAllowedError | 同上 |
| シークレット窓 | 常に NotAllowedError | 同上 |
| Apple | WebKit: Negative | https://groups.google.com/a/chromium.org/g/blink-dev/c/iSxAYX0hCwI |
| 部品 | @simplewebauthn/browser の説明書（Context7）に uiMode/immediate の記載なし | Context7 /websites/simplewebauthn_dev |

→ 訂正: 前の返事の「Chrome では開いた時点で顔・指紋の画面も出ます」は誤り。1回押す操作が要る。

## F. 本番の今の値（2026-11-24 00:06 JST・reader 鍵・過去30日）
- 生のファイル: baseline-30d.tsv / baseline-by-user.tsv / passkeys-by-user.tsv / users-5.tsv（同じフォルダ）
- パスワードでのログイン成功（人ごと）: PO 10回・ほか試験用の人。自動点検の係 1,310回。
- パスキーでのログイン成功: 2回（2026-10-31 のみ・11/1 以降 0回）。
- パスキーの登録: PO 1件（一度も使っていない）・試験用の管理者 2件。
