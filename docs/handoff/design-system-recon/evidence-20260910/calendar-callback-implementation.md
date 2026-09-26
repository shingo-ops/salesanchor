# 接続状態通知の依存修正・実装検収（2026-09-11）

[設計§AF](../../../specs/design-system/design.md) / [正式カード](../CARD-CALENDAR-CALLBACK-01.txt)。基準eefa9143df4ba47b5f3854b222df595b302b503c。Icon公開API・CSS変更は本便へ持ち込んでいない。

## 結果と範囲

製品はGoogleCalendarStatusBar.tsxの依存配列1行のみ変更、同名test.tsxを追加。通知関数が差し替えられると新しい取得結果を新しい関数に通知し、状態再取得とintervalの再登録を行う。色/配置/業務分岐/API仕様/30秒間隔/再接続finallyは維持。未解決リクエストの取消機能は追加していない。

## 実行・確認の区別

Generator frontend_definition_auditが実装と試験を実行。rootは差分、test原稿、赤/緑ログを読み、製品2hashを計算・確認した。rootが全試験を再実行したとは称しない。

| 検査 | 結果 | 根拠 |
|---|---|---|
| 変更前の新規回帰試験 | 7件中6成功/1失敗。通知先差替え後、新関数へのdisconnected通知の期待1回に対し0回 | [赤ログ](calendar-callback-red.txt) |
| 変更後の全単体 | 19ファイル168試験成功、新規7件を含む | [緑ログ](calendar-callback-checks.txt) |
| 保存前と同じ厳格lint | 対象2ファイル、--max-warnings=0でexit0 | 同上 |
| 既存静的検査/ビルド | check:all/build各exit0、全体は既存218warnings/0errors | 同上 |
| 製品差分 | 既存TSX 1追加/1削除、新test1ファイル、製品ファイル削除0 | [manifest](calendar-callback-manifest.json) |

新規試験はconnected/disconnected/not_linkedとboolean通知の互換、callback省略、通知先差替えとinterval1本、依存不変再描画、30秒ごとのGET、解決済み状態でunmount後のtimer0/追加定期GET0、再接続のdisabled/終了後再取得を検査。未解決GET完了時の通知まで取り消すという保証はしていない。

見た目を変えない依存修正のため、この便に新しいブラウザー表示試験は追加していない。現在の部品利用はstoriesのみ。全画面SSOT完了やPOの理解速度向上を本試験の結果としない。

設計自己審査済み・限定製品実装/ローカル検証済み。限定第二レビューの最終判定、commit/PR/リモートCI/番号付きGO/マージは後続。以前のIcon便に対するGO/レビューを本便へ流用しない。


最終限定第二レビューci_preflight_readonly: APPROVE。2hashと現物一致、依存1行/赤→緑/タイマー契約を確認。担当は試験を再実行せず原稿と保存ログを確認した。rootも2hash一致を確認。これをGitHub CIやマージ承認へ読み替えない。
