# design: LP 運営者表示に正式名称（漢字）と日本語住所を足す

> この文書は何か: ホームページの運営者欄に「谷澤 伸吾」と日本語の住所を足す設計。
> 親: [recon.md](recon.md)　関連 ADR: docs/adr/ADR-1044-lp-meta-application-only.md

## 目的
Meta ビジネス認証で「ウェブサイトに正式なビジネス名『谷澤 伸吾』が表示されている必要がある」と却下された。LP の運営者表示に正式名称（漢字）と許可証どおりの日本語住所を足す。PO 承認 2026-10-27（選択肢1）。

## 変更内容
- 代表者名を「Shingo Tanizawa (谷澤 伸吾)」にする（漢字は旧字の澤、姓名の間に半角スペース1つ）。recon.md の全箇所（Footer・index・privacy・terms・data-deletion）に同表記。
- 英語住所が出る 3 か所（Footer・privacy 1.2・terms 末尾）の直後に「〒444-2141 愛知県岡崎市桑原町字緑陽台8番地312」を足す。英語住所は残す。
- 共通定数・辞書が無いため直書きのまま（新しい仕組みは作らない）。

## 触らない範囲
frontend/、backend、noindex/robots、電話番号、メールアドレス、デザイン（色・レイアウト）、og-image.html、deploy.yml。

## 受入条件
|基準|検証方法|
|---|---|
|運営者表示がある全ページに「谷澤 伸吾」が出る|ビルド後 lp/dist の HTML を grep、ページごとの件数を /tmp/CC報告ファイル/lp-legal-name/grep.txt に保存|
|「〒444-2141 愛知県岡崎市桑原町字緑陽台8番地312」が出る|同上（Footer 経由で全 7 ページ、privacy/terms は 2 件）|
|既存の英語表記・電話・メールが消えていない|git diff で削除行が代表者名行のみ・電話/メール行に差分なし|
|LP 以外に差分がない|git diff main...HEAD --name-only が lp/ と docs/handoff/whatsapp-intake/lp-legal-name/ のみ|

## 外部・過去事例の参照と我々への応用
事例調査 /tmp/CC報告ファイル/wa-verify-cases/report.md：名前を書類・Meta・サイトで同一にすることを約10件の解説が通過要因に挙げる。

## 戻し方
このPRを revert（main マージで自動デプロイされるため、revert のマージで元に戻る）。

## 維持の仕組み
- 守り手: .github/workflows/deploy.yml（main への push で LP をビルドして配信。ビルド失敗なら配信されない）
- 対象: 運営者表示が Meta 登録名とずれる、または一部ページだけ旧表記に戻ること
- 点検: 今後 LP に運営者名を足す際は recon.md の箇所一覧と同じ表記にする（ADR-1044 の住所表記と併せて）
