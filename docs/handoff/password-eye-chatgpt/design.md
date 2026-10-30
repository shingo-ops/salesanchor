# design: パスワード欄の目の印を見本（ChatGPT）に合わせる

区分: B-2（ADR-1015）。根拠は recon.md（同じフォルダ）。

## 目的
ログイン画面と再設定画面の目の印の大きさと位置を、ChatGPT の実測（recon.md の表）に合わせる。

## 対象と対象外
- 対象: frontend/src/components/PasswordField.tsx・PasswordField.css だけ
- 対象外: ボタンの押せる大きさ（PC 28px・狭い画面 44px のまま）、色、欄の高さ、アイコンの形、他の画面

## 変更（数値はすべて既存トークン。ADR-067・ADR-144）
| 箇所 | 変更前 | 変更後 |
|---|---|---|
| PasswordField.tsx アイコン | アイコン定数 md（16px） | アイコン定数 base（20px・`--icon-base`） |
| PasswordField.css ボタンの right（PC） | `var(--space-1)`（4px） | `var(--space-4)`（16px）→ 印の右端は 16+(28−20)/2 = 20px |
| 同（767px 以下） | なし（4px） | `var(--space-2)`（8px）→ 8+(44−20)/2 = 20px |
| 入力欄の右余白 | PC `calc(28px+8px)`・狭い画面 `calc(44px+8px)` | 両方 `var(--space-12)`（48px）→ 文字と印の間 約8px |

見本は 21px、変更後は 20px（使えるトークンでは 1px 差が最小）。

docs/handoff/login-round-inputs/design.md §6.2（:132-133）の余白と位置の決まりは、この設計で置き換える（同 §6.2 に追記済み）。

## 受入条件
|基準|検証方法|
|---|---|
| 目の印が 20x20px（1280px・390px） | Playwright で /login の getBoundingClientRect |
| 欄の外側右端 → 印の右端が 20〜22px（1280px・390px） | 同上 |
| 縦のずれ 0±1px | 同上 |
| 狭い画面のボタンが 44x44px のまま | 同上 |
| 生の px の追加なし | check:all（check:css-values）・stylelint が 0 エラー |
| 既存テスト合格 | PasswordField.test.tsx |
| 本番で PO が見て見本と同じに見える | PO の目視（○×） |

実測（変更後・ローカル）: /tmp/CC報告ファイル/auth-b4b/eye-icon/after-measure.md（1280px・390px とも 印 20x20・右端 20px・縦 0・狭い画面ボタン 44x44・文字と印の間 9px）。

## リスクと対処
- 狭い画面で入力欄の右余白（48px）がボタンの左端（右から 52px）より 4px 狭い。印の左端は右から 40px なので文字は印に重ならない。ボタンの透明な端 4px が文字の上に重なるだけで、押すと表示の切り替えになる。見本の ChatGPT もボタンは印と同じ 20px で、この差は受け入れる
- 戻し方: この PR を revert する

## 外部・過去事例の参照と我々への応用
ChatGPT（OpenAI）のパスワード入力画面を 2026-10-30 に実測した値だけを使う（recon.md）。他社の事例は、PO が見本を ChatGPT と決めたため不要。

## 維持の仕組み
- 寸法はトークンだけで書くので、check:css-values と ADR-067 の pre-commit が生の px を止める
- 目の印は PasswordField の金型 1 か所にあり、ログインと再設定の両画面が同じ金型を使う
