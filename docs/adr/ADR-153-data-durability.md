# ADR-153: データ保全を独立テーマとして立て、時点復旧10分・復旧半日・3拠点を目標に置く

| 項目 | 内容 |
|------|------|
| ステータス | Accepted |
| 作成日 | 2026-09-01 |
| 起案 | しんごさん（PO） |
| 関連 | docs/specs/data-durability/ |

---

## ひとことで

営業データが消えたら商売が止まる。消えない仕組みと戻す手順を、1つのテーマとして正本化する。

## 背景（2026-09-01 実測）

- prod1 の crontab に S3 転送のジョブは登録されているが、AWS CLI が prod1 に存在しない。転送が成功したのは 2026-05-26 と 05-27 の2回のみで、2026-05-28 から 09-01 まで成功0回である（2026-09-01 に s3_backup.log 全256行の先頭を実測。初版の「10日連続」は末尾40行のみを根拠とした誤記であり訂正した）。
- 失敗時の通知は DISCORD_WEBHOOK_OPS が設定されているときのみ動くが、prod1 の .env にも crontab にも当該変数は無く、約3か月の失敗は通知されなかった。
- 添付ファイル用ボリューム attachments_data は docker-compose.yml に定義済みだが、backup.sh は pg_dump のみを行うためバックアップ対象外である。
- prod1 の .env は GitHub の追跡下に無く（追跡されているのは .env.example のみ）、METADATA_FERNET_KEY を含む約55の鍵名を持つ。
- prod2 に crontab は無く、バックアップ関連ディレクトリも存在しない。
- したがって同一時点のコピーは prod1 ローカルの1箇所のみである。
- PostgreSQL は archive_mode = off であり、時点復旧の土台が無い。
- prod1 と prod2 はいずれも AS9371 SAKURA Internet Inc.・Osaka である（事業者・都市単位の情報。同一建物か否かは未確認）。
- バックアップ・復旧を主題とする既存 ADR は存在しない（docs/adr/ のファイル名検索および docs/adr/FEATURE-INDEX.md 全文確認による）。

## 決定

1. データ保全を docs/specs/data-durability/ として独立テーマに立てる。
2. 目標を次の3つに置く。障害の10分前まで戻せること、復旧を12時間以内に完了すること、同一時点のコピーを3つ以上・うち1つをさくらインターネット大阪の外に置くこと。
3. 対象は営業データベース本体・添付画像・環境設定と鍵の3層とする。
4. 上記を満たす技術手段（時点復旧の設定を入れるか、取得頻度を上げるか。保管先に何を選ぶか）は本 ADR では決めず、recon 完了後の design で比較して決める。

## 理由

アプリのコードは GitHub にあり再構築できるが、データは失えば戻らない。目標値は PO 自筆のあるべき姿（docs/specs/data-durability/ideal-state.md）に由来する。

## 弊害・トレードオフ

- 決定2の「10分前まで」は現在の1日1回のダンプでは達成できず、本番データベースへの設定変更または取得頻度の引き上げを伴う。前者は再起動を要する可能性があり、後者はディスクを消費する。
- 決定2の「大阪の外」は新たな保管先の契約・鍵管理を増やし、鍵の漏洩面が広がる。docs/specs/secrets-permission-ssot/ と接点を持つ。

## 参照

- あるべき姿: docs/specs/data-durability/ideal-state.md
- KGI: docs/specs/data-durability/kgi.md
- recon: docs/handoff/data-durability-spec/recon.md
