# 添付ファイルの保管 理想の設計図（To-Be）

> この文書は何か（専門用語なしの1行）:
> 顧客から届いた画像を自分たちのサーバーに保管し、あとから見返せるようにするための、作り方の設計図。

親（表紙）へのリンク: [README.md](./README.md)
あるべき姿: [ideal-state.md](./ideal-state.md)
KGI: [kgi.md](./kgi.md)
日付: 2026-09-01
承認: PO（shingo-ops）2026-09-01

## 1. 全体の流れ

顧客がDiscordのチケットチャンネルに画像を送る。
Botがそれを受け取り、画像の実体をサーバーにダウンロードして保存する。
保存した場所と大きさをDBに記録する。
スタッフが受信箱を開くと、SalesAnchorのAPI経由で画像が表示される。
Discord CDN には二度とアクセスしない。

## 2. PO決定（2026-09-01・全11件）

| # | 決定 |
|---|---|
| 1 | 画像は自社保存する（A案） |
| 2 | リード削除時に画像も削除する（マスト） |
| 3 | 容量上限を設け、超えたら古い順に削除する |
| 4 | 上限値はテナントあたり 8GB |
| 5 | 保存先パスは tenant_006/lead_1049/{message_id}.{拡張子} |
| 6 | 新しい表を作る（meta_messages に列を足さない） |
| 7 | 探す・数える・並べるはDBが担当する |
| 8 | 配信は認証つきAPI経由（静的公開しない） |
| 9 | 表はテナントごとに置く（tenant_XXX.lead_attachments） |
| 10 | 上限超過は保存のたびに確認し、古い順に削除する |
| 11 | 画像のバックアップ先は prod2（既存 rsync に乗せる） |

対象外: Meta（Messenger / Instagram）。規約上の理由から自社保存せず既存方式を維持する。

## 3. 保存先の構成

コンテナ内のパス: `/data/attachments/tenant_006/lead_1049/{message_id}.{拡張子}`

ボリューム名: `attachments_data`

パスがテナント別・リード別になっている理由は、DBが壊れたときに
人が目で見て所有者を判別できるようにするため。
探す・数える・並べる処理はDBが行うため、パス構成に依存しない。

## 4. DBの表

配置: 各 `tenant_XXX` スキーマ（既存の leads / meta_messages と同じ場所）

| 列 | 型 | 用途 |
|---|---|---|
| id | SERIAL PRIMARY KEY | 行の識別 |
| tenant_id | INTEGER NOT NULL | KGI5の容量集計 |
| lead_id | INTEGER NOT NULL | KGI4の削除対象特定 |
| message_id | VARCHAR(64) NOT NULL | 受信箱表示時の突き合わせ |
| platform | VARCHAR(32) NOT NULL | 将来のLINE等と区別 |
| file_path | TEXT NOT NULL | 実体の場所 |
| file_size | BIGINT NOT NULL | KGI5の容量集計 |
| content_type | VARCHAR(128) | ブラウザへ返す際のMIME型 |
| original_filename | TEXT | ダウンロード時の名前 |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT NOW() | KGI6の古い順削除 |
| updated_at | TIMESTAMPTZ NOT NULL DEFAULT NOW() | 既存表と揃える |

索引:

| 索引 | 用途 |
|---|---|
| (lead_id) | リード削除時の高速検索 |
| (tenant_id, created_at) | 容量集計と古い順削除 |
| (message_id) UNIQUE | 同一添付の二重保存を防ぐ |

作成方法は `migrations/20260814_120000_create_tenant_link_templates.sql` の
DO ブロック方式を踏襲する（pg_namespace を走査して全テナントに一括作成）。

## 5. 配信

エンドポイント: `GET /api/v1/leads/{lead_id}/attachments/{attachment_id}`

既存の認証（Authorization: Bearer）を必須とする。
テナント文脈を set_tenant_context で設定し、他テナントの行を返さない。
StreamingResponse または FileResponse で実体を返す。

画面側は Authorization ヘッダーを必ず付ける。
2026-09-01 の実測で、既存の attachment-url API が
Authorization を送らず 401 で失敗していた事例があるため、本設計では明示する。

## 6. 削除

KGI4（リード削除時）:
リード削除は論理削除（status='deleted'）だが、
画像の実体は同時に物理削除する。PO決定による。
実装箇所は backend/app/routers/leads.py の delete_lead。

KGI6（上限超過時）:
保存のたびに当該テナントの file_size 合計を求め、8GB を超えていれば
created_at の古い順に削除する。上限を下回るまで繰り返す。

## 7. 実装の分割（5便）

| 便 | 内容 | 危険度 | PO自筆GO |
|---|---|---|---|
| 1 | docker-compose.yml にボリューム追加 | 高（インフラ） | 必要 |
| 2 | migration で lead_attachments 作成 | 高（DB） | 必要 |
| 3 | 受信時に画像を保存する処理 | 中 | 必要 |
| 4 | 配信API（認証つき） | 中 | 必要 |
| 5 | 削除（リード削除時・上限超過時） | 中 | 必要 |

便1と便2を先に行う。置き場所と記録先が無いと便3以降が動かない。

## 8. 弊害・トレードオフ

- 弊害: docker-compose.yml の記述を誤ると全コンテナが起動しなくなる。
  変更前後を逐語で指定し、既存の postgres_data と同じ形に揃えることで抑える。
- 弊害: Meta と Discord で方式が分かれ、受信箱に2系統が併存する。
  Meta は規約上の理由から自社保存できないため許容する（PO決定）。
- 弊害: 画像を毎回API経由で返すため、静的配信より負荷が高い。
  現在の添付は3件であり、当面問題にならない。
- 弊害: リードを誤削除した場合、リード情報は論理削除で戻せるが画像は戻らない。
  prod2 のバックアップからの復旧に依存する。
- トレードオフ: 保存先を prod2 のみとし AWS への多重化を含めない。
  3-2-1ルールは未達だが、別テーマとして起票済み。

## 9. 維持の仕組み

- 守り手: 各便の実装で追加するテストと、KGI 7項目の実測
- 理由: 保存・削除・上限判定はいずれも自動テストで検証できる
- 人手で守る部分: KGI2（24時間経過後の表示）とKGI3（元投稿削除後の表示）は
  時間経過と外部操作を伴うため、PO による実機確認とする
