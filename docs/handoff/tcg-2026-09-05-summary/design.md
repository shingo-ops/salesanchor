# design — 確認工程のボタン表示と案内文の修正

**仕事名**: tcg-2026-09-05-summary
**日付**: 2026-09-06
**対象ADR**: ADR-067
**担当**: 設計パートナー

---

## 設計方針

LINE取り込みの確認工程で、ボタンが画面上ほぼ見えない状態になっていた。
原因は、インライン style が参照する CSS 変数 --color-primary / --color-disabled が
リポジトリのどこにも定義されていないこと。未定義の変数を参照した宣言は無効化され、
背景が透明になるため、白い文字が淡い背景の上に置かれる形になっていた。

色の値を直接書く対処は ADR-067 で禁止されているため、変数名を差し替えるのではなく、
金型 frontend/src/components/Button.tsx に置き換える。色の指定自体が不要になり、
同じ間違いが再発しない。

あわせて、全員解決後も残っていた案内文を条件付き表示にする。

根拠となる現状把握: docs/handoff/tcg-2026-09-05-summary/recon.md

---

## 変更箇所と設計根拠

| 変更箇所 | 変更内容 | 根拠 |
|---------|---------|------|
| ReviewSection.tsx の生 button 4箇所 | 金型 Button に置換 | ADR-067（インライン style 禁止） |
| 抽出開始ボタン | variant="primary" | 金型の規格: 本文主操作は1画面1個 |
| 既存割り当てトグル | variant="tab" + active | 金型の規格: 切替はtab |
| 新規登録・割り当てパネル内 | variant="secondary" | 主操作以外は補助 |
| 案内文の p 要素 | !allResolved で条件付き | 全員解決後も表示され続けていたため |
| actionBtnStyle 定数 | 削除 | 参照がなくなったため |

---

## 受け入れ条件と検証方法

| 基準 | 検証方法 |
|------|---------|
| ReviewSection.tsx に --color-primary の参照が残らない | git grep で0件を確認 |
| ReviewSection.tsx に --color-disabled の参照が残らない | git grep で0件を確認 |
| 抽出を開始ボタンが濃色で表示される | 本番デプロイ後の画面目視 |
| 全員解決後に案内文が消える | 本番デプロイ後の画面目視 |
| ボタンの活性条件が変わっていない | diff で disabled 式が同一であることを確認 |
| 文言が変わっていない | diff で t() の呼び出しが同一であることを確認 |
| 変更が1ファイルに収まる | git diff origin/main --name-only の出力行数 |

---

## 外部・過去事例の参照と我々への応用

- 社内の過去事例: 同じ未定義トークン --color-primary / --color-disabled は
  TcgLineImportPage.tsx と RegisterPage.tsx にも残っている（CV-05 で件数を実測）。
  本便では対象を1ファイルに絞り、残りは別便に切り出す。大きな変更をまとめると
  回帰の切り分けが難しくなるという本リポジトリの教訓による。
- 金型 Button.tsx の冒頭コメントに「フォルム上書き・インライン style 禁止」
  「primary は1画面1個」と規格が明記されており、本便はその規格に従った。

---

## 追補（2026-09-06）: アップロード画面の未定義トークン

確認工程と同じ壊れ方が `TcgLineImportPage.tsx` にも残っていた。
アップロードボタンは有効時 --color-primary・無効時 --color-disabled を参照し、
どちらも未定義のため常に背景が透明だった。ドロップゾーンも
ドラッグ中の色に --color-primary / --color-primary-subtle を使っており、
ドラッグしても見た目が変わらなかった。

ボタンは金型 Button に置換する。ドロップゾーンはボタンではないため金型が使えず、
実在するトークン --accent / --accent-bg-subtle に差し替える。
根拠となる現状把握: docs/handoff/tcg-2026-09-05-summary/recon.md

| 基準 | 検証方法 |
|------|---------|
| TcgLineImportPage.tsx に --color-primary の参照が残らない | git grep で0件を確認 |
| TcgLineImportPage.tsx に --color-disabled の参照が残らない | git grep で0件を確認 |
| TcgLineImportPage.tsx に --color-primary-subtle の参照が残らない | git grep で0件を確認 |
| アップロードボタンが濃色で表示される | 本番デプロイ後の画面目視 |
| ファイル未選択のときボタンが押せない | 本番デプロイ後の画面操作 |
| 確認するボタンの見た目が変わらない | 本番デプロイ後の画面目視 |
| 変更が1ファイルに収まる（書類を除く） | git diff origin/main --name-only の出力 |

ADR-067 の禁止は色の直値であり、未定義の変数名を参照することは検査されない。
既存の関所4本はいずれも定義側を見ており、使用側が実在する名前を指しているかを
見る仕組みが無い（CV-15 で実測）。逆向きの照合を行う番人の新設は別テーマとする。
