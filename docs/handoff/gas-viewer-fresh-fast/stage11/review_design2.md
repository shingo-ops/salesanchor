# 再審査: 段11 閲覧者向け文面のテンプレートページ（design_stage11.md 11-10 追記版）

- 審査者: Architect（読み取りのみ。ファイル編集は本書のみ）
- 基準: `git fetch -q origin main` 後の origin/main = 38613d7d7（前回と同じ。差なし）
- 前回: /tmp/CC報告ファイル/viewer_templates/tpl_page/review_design.md（REVISE、Blocking 5・Non-blocking 9・未確認 1）

## 判定: APPROVE（実行の前提条件つき。下の「Generator への指示」の G-1 を必ず守る）

## 前回の指摘への対応の確かめ

| 指摘 | 11-10 の対応 | 判定 |
|---|---|---|
| B-1 本番の初期値の入れ方 | CLI に dry_run・verify を足した（ADR-1007:36 の DRY-RUN→COMMIT・記録を満たす）。Sonnet には無制限鍵を使わせない。実行者は Opus、根拠は本セッションの PO 原文 | ○（条件つき。下記「B-1 の判断」） |
| B-2 判定の順番 | 前回の文案をそのまま採用（6か所すべて） | ○ |
| B-3 作り直し案内の書き出し | `{line_name}さん、` で始まらなければ 422、名前が空なら今と同じく頭を外す。代わりの言葉を持たない理由（正本が2か所になる）も書いてある | ○ |
| B-4 行が無い環境 | GET は台帳の9件を必ず返し、無い鍵は body=null。PUT は null かつ行なしで INSERT、行ありは SQL の WHERE で比べて0件なら 409。updated_at は SQL の now()、trigger なし | ○ |
| B-5 送れなかったことを画面に出す | room_notice="no_template"、新キー roomNoticeNoTemplate（ja/en）、openapi.json の再生成 | ○ |
| N-1〜N-9 | 全部採用（GRANT に SEQUENCE なし、`public.users`、長さ 2000 の検査、Formatter の4点、テストと生成物の列挙、表示名、記録と 10-3 の注記、T7 の式・T8 の戻し・T9 新設） | ○ |
| 未確認4 gateway の起動し直し | 便2 の観測項目 T10（gateway の起動時刻が deploy 後） | ○ |

### B-1 の判断
- 【事実】CLAUDE.md の無制限鍵の決まりは「人間の明示許可があるタスクでのみ」「許可は都度・タスク単位」「permit-danger.sh 相当の明示承認が必要」。Q12=n（docs/handoff/gas-viewer-fresh-fast/design.md:606）は「Opus に常時委任しない、毎回 PO 本人の GO」で、タスクごとの PO 本人の許可を禁じてはいない。
- 【事実】ADR-1033（docs/adr/ADR-1033-conversation-consent-ticket.md:15-20）では、危険な操作は許可券（permit-danger.sh）か同意票（`[同意票]`＋コマンド全文＋PO が打ち込んだ「1」）を1コマンドずつ通す。サブエージェントの報告や貼り付けは同意にならない（:18）。
- 【未確認】11-10 に引用されている PO 原文「GO記録やSSHへの無制限鍵へのアクセス等、必要な権限は全て…完走させてくれ。」は、審査者には coordinator からの伝言でしか届いておらず、会話記録で確かめていない。
- 判断: 引用が本物なら、この段11 のタスクに限った PO 本人の明示許可として、CLAUDE.md・Q12=n と矛盾しない。ただし、実際の無制限鍵のコマンドは ADR-1033 または許可券の見張りが1コマンドずつ止めるので、設計の文面だけでは通らない。だから設計のやり直しは求めず、G-1 を実行の前提条件にする（見張りが強制するので、ここで往復しない）。

## 新たに見つけた点（いずれも Non-blocking。Generator がカードで明記すれば足りる）
- N2-1 PUT の INSERT を2人が同時に行う場合：`INSERT ... ON CONFLICT (key) DO NOTHING` の件数が0なら 409 と書く（B-4 の「ある時は 409」を SQL で守るため）。
- N2-2 台帳に無い key の PUT は 404（または 422）。GET で body=null の行は「コピー」を押せないようにする（copy_text が無いため）。
- N2-3 viewer_admin_cli.py の結果 JSON の room_notice にも "no_template" が入りうる。CLI のテスト（test_super_admin_viewers.py の CLI の試験）に1件足す。
- N2-4 便1 は migrations/ を含むので、ADR-136 の危険 PR の GO（「GO #PR番号」）が要る。これは同意票では代わりにならない（ADR-1033:20）。GO の扱いは本設計の範囲外で、既存の手順に従う。

## 承認する範囲
- 便1：migration（public.viewer_message_templates、構造だけ、RLS なし、GRANT SELECT/INSERT/UPDATE）・台帳 backend/app/services/viewer_message_templates.py・seed/verify CLI・`GET /api/v1/super-admin/viewer-templates`・ViewerTemplatesPage（表＋スライド＋コピー、読むだけ）・閲覧者管理の headerAction の「テンプレート」ボタン・i18n（ja/en）・openapi.json。送る側は変えない。
- 便2：`PUT /api/v1/super-admin/viewer-templates/{key}`（11-3＋11-10 の検査と 409）・スライドの編集と保存・送る側9件の DB 読み（11-10 B-2 の順番）・no_template・2000 の検査・定数9件と seed の削除・viewer_bot_texts.py の冒頭説明の直し・design.md への記録と 10-3 の注記。
- 範囲外：RECEPTION_MESSAGE ほか 11-2 の対象外、/templates（受信箱）、サイドバー、履歴の表、新しい金型。

## Generator への指示
- G-1（実行の前提条件）：本番の dry_run → seed → verify は Opus が行い、Sonnet には頼まない。各コマンドは ADR-1033 の同意票か許可券で1つずつ通す。見張りに止められたら言い換えて回り込まない。実行の前に、Opus が会話記録で PO 原文を自分で確かめる（伝言のままにしない）。原文・時刻・鍵ごとの○×は docs/handoff/gas-viewer-fresh-fast/ の段11 記録に残す。本文・名簿は出さない。
- G-2：便2 の本番反映の前に verify で9件すべて○を確かめる（T3）。1件でも×なら便2 を入れない。
- G-3：便2 の送る側は 11-10 B-2 の順番どおりにする。テンプレートを読む処理を、申込コードの照合・部屋の作成・申込コードの作り直し・commit の後に置かない。
- G-4：テストは review_design.md ③の4ファイルの行を直す。db_factory の結果を順番で返すモック（test_viewer_discord_trial.py:247 ほか）の順番を合わせ、PG テストの準備に新しい migration を足す。T9 と N2-3 を足す。
- G-5：UI は PageLayout・DataTable・Drawer・Textarea・Button だけを使う。色や寸法の直書きをしない。文字は全部 t()（ja/en 同一キー）。
- G-6：openapi.json を再生成する（.github/workflows/api-contract-check.yml:50-53）。ADR を足したり変えたりしたときは generate-adr-index.js を実行する。

## リスク
- B-1 の PO 原文は審査者が確かめていない（G-1 で Opus が確かめる）。
- 便1〜便2 の間に別の PR が定数を直すと、DB の写しが古くなる（G-2 の verify で拾う）。
- 便2 を戻しても、送る側は定数に戻るだけで表は残る。PO が画面で直した文は、送る側に効かなくなる（11-9 のとおり）。

## PO 承認: 要る（便1・便2 とも、PR の GO は ADR-136 の手順で行う）
## Generator へ渡せるか: はい（PO の承認の後。G-1 は本番での実行時の前提条件）

VERDICT: APPROVE
