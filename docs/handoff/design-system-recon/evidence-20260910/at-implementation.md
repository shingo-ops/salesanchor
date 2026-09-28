# AT フォームButton移管・実装検収

設計: docs/specs/design-system/design.md §AT。基準a1cd9ea379cc7d85b797cca6b1cc092192296bc3。Astra設計/自己審査、Sol調査・分離実装。POの条件付き続行・担当委任指示に基づく。代理GOは未有効。

## 変更と境界

9製品11ボタンを既存Buttonへ移管。変換はimport/タグ/className→variant/sizeのみ。root直接監査で9file全byte逆変換、対象11、対象外221、共有18不変、構文0を確認。AT単独で共通265→276、旧232→221。API/DB/権限/handler/配線/翻訳/CSS/共有部品/CI変更0、新データ保存先0。元からあるPO supplier複製とpublic master書込は変更せず、本番への実保存試験は実施しない。

## 検証

root直接実行: 関連既存4suite59試験成功。全体coverage46files631試験成功（statement26.79/branch23.01/function23.36/line27.83%）。check:all成功（既存warning140/error0）、Storybook成功。初回buildは新規Admin試験のHTMLElement.value型エラー5件で失敗、製品障害とは区別し原ログを保存。修正後の結果は追記する。

Sol担当実行原ログ: Commerce11試験、Account/Company/Admin14試験、strict ESLint成功。rootがrawと実試験内容を確認し、不足していた非空/数値変換/guard分岐/再取得/required/再試行の期待を補完。型検査・交差レビュー・最新main統合後の最終結果をもって検収確定する。

## 調査・検証中の訂正

- bare btn-smのsecondary推測を撤回し60件を対象外へ。
- Invoice submitは非JPY時外部FX APIを参照するため対象外。Roles権限保存も別便。
- Buttonはtype既定値なし。商品payloadは34キー。誤記を実ソースで訂正。
- Company/Profileの実hook/providerを利用。refreshをnoopにするmockは禁止。
- Sol2初回4fail/6passはAuth mock参照とselector曖昧さ。実物根拠で試験fixtureだけ補正しログを保持。
- rootレビューで「試験成功」だけでは計画受入を満たさない不足を発見し、送信全項目/変換/空値/再試行/pending/GET差分を補完。

## 状態と残件

設計案・設計自己審査済み、11件実装済み。最終検収/PR/番号付き本人GO/マージ/本番反映は未完了。画面・本番ログインフォーム・PO目視はPO指示で省略・未検証。残旧221、表、報酬3件、カレンダー色、最後のCI補強は別設計。営業効果や全KGI達成は主張しない。

初回buildの5型エラーは実input配列の型指定2箇所で解消し、root再build成功。Sol2→Sol1交差レビューAPPROVE。Sol1→Sol2の予備指摘（再試行payload/成功callback/再GETの不足）を試験だけ補完、14試験とstrict再成功。rootの追加25件再実行と逆変換、最新main統合後の最終品質を確認する。

root追加25件再実行成功、最終逆変換監査pass。Sol両方向交差レビューは最終hashでAPPROVE。最新main統合と全体最終品質のため保存へ進む。
