# design: LP 運営者表示に適格請求書発行事業者登録番号を足す

> この文書は何か: ホームページの運営者欄に登録番号を1行足す設計。
> 親: [recon.md](recon.md)（docs/handoff/whatsapp-intake/lp-invoice-number/recon.md）　関連 ADR: docs/adr/ADR-1044-lp-meta-application-only.md

## 目的
PO 承認 2026-10-27 PO「納税者識別番号 T3810449547408も加えておいて」。国税庁公表サイトで確認済みの登録番号を、運営者表示（Footer・privacy 1.2・terms 末尾）に1行足す。

## 変更内容
日本語住所行の直後に、同じ書き方で次の1行を足す。
`Invoice Registration No. (適格請求書発行事業者登録番号): T3810449547408`
- Footer: `<li>` を1行追加
- privacy 1.2: 住所行末に `<br>` を足し、次行に追加
- terms 末尾: `<br>` 付きの1行を追加

## 触らない範囲
他の文言・リンク・meta・noindex・スタイル、frontend/、backend、deploy.yml。

## 受入条件
|基準|検証方法|
|---|---|
|全 7 ページに登録番号が出る（privacy/terms は 2 件）|ビルド後 lp/dist の HTML を grep、件数を /tmp/CC報告ファイル/lp-invoice-number/grep.txt に保存|
|番号が公表サイトの T3810449547408 と一致|grep の文字列が T3810449547408|
|既存表記が消えていない|git diff の削除行は privacy 住所行の末尾 `</p>` の付け替えのみ|
|LP 以外に差分がない|git diff main...HEAD --name-only が lp/ と docs/handoff/whatsapp-intake/lp-invoice-number/ のみ|

## 外部・過去事例の参照と我々への応用
外部事例は不要。理由: 公表サイトで確認済みの番号を載せるだけで、判断を要する設計ではないため。

## 戻し方
このPRを revert（main マージで自動デプロイされるため、revert のマージで元に戻る）。

## 維持の仕組み
- 守り手: .github/workflows/deploy.yml（ビルド失敗なら配信されない）
- 対象: 一部ページだけ番号が欠ける、または番号の誤記
- 点検: 運営者表示を変えるときは recon.md の箇所一覧と同じ表記・同じ番号にする
