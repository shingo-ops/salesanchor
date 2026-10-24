# ADR-1042: クラウドから本番を読むだけの HTTPS 窓口を、読む人の接続だけを持つ専用コンテナで作る

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（2026-10-25。採用の根拠: 便1 #4687 が本番に入り、design.md §2 の K1〜K9 がすべて合格（K7・K2 の DELETE/DROP は 2026-10-25 に実測。結果は design.md §12）） |
| 備考 | PO 2026-10-22「クラウドでもいまと変わらない環境を構築したい、本番への読み取りも、hookも」。PO 2026-10-23 チャット「1」：本番を読むだけの窓口を設計し、設計書と確かめ方の表を見てから本番に手を入れる。PO 2026-10-23 チャット「1」：確かめ方 K1〜K9 で進め、実装・確認・本番反映まで行う |
| 起案日 | 2026-10-23 |
| 方針の決定者 | Shingo（PO）。方式の選択は Opus（PO の委任に基づく。ADR-1003） |
| 関連 | ADR-1024（AI の本番 DB 読み取りの道）、ADR-1025（専用鍵の受け口）、ADR-1017（fail-closed）、ADR-1003（GO 委任） |
| 設計 | `docs/handoff/cloud-read-window/design.md`、現状 `docs/handoff/cloud-read-window/recon.md` |

---

## What（何を決めたか）

1. クラウドの AI は `https://api.salesanchor.jp/api/v1/ops/read-window/query` に SQL を POST して本番を読む。
2. 受けるのは新しい専用コンテナ `ai-reader-http`。持つ環境変数は `AI_READER_DATABASE_URL` と `READ_WINDOW_TOKEN` だけ。read_only・cap_drop ALL・no-new-privileges・ports なし。frontnet と backnet に置く。
3. SQL の検査・上限・秘密列の伏せ字は `backend/app/ops/readonly_query.py` の関数を呼ぶ。規則の正本はこの1か所。
4. 鍵は `READ_WINDOW_TOKEN`（ヘッダ `X-Read-Window-Token`・32バイト乱数・90日更新・B-11 に記載）。正本は GitHub secret。クラウドではネットワークシークレットに登録し、環境変数には置かない。未設定なら全員 401。
5. 窓口の同時実行は1本（手元の SSH の道と合わせて全体で2本。ai_reader の接続上限は2）・nginx で2回/秒。1回ごとに AUDIT 行を /dev/log へ送り、送れなければ結果を返さない。
6. 書き込みの窓口は作らない。

## Why（なぜ）

- クラウドは SSH で外に出られず、HTTPS だけが使える。ADR-1024 の SSH の道はクラウドから使えない。
- backend に窓口を足す案は、ADR-1024 が不採用にした「書ける接続・復号鍵と同じ場所に台本を置く」形になる。専用コンテナなら、漏れても読めるのは ai_ro（秘密列なし）だけで、守りの本体（DB の GRANT・GO 境界）は ADR-1024 のまま変わらない。
- クラウドの出口 IP は固定と書かれていないため、IP 許可では守れない。鍵・速度・同時数・監査・即停止で守る。
- ネットワークシークレットは、鍵を VM の環境変数にもファイルにも出さない（公式 cloud-environments）。環境変数は環境を使う全員が読めるので使わない。

## 不採用の案

| 案 | 不採用の理由 |
|---|---|
| backend に窓口を足す | ADR-1024:59 と同じ理由（書ける接続・暗号鍵と同居）。blue-green 切替中に消える |
| 要求ごとに ai-reader を起動する | docker の操作口をコンテナに渡すことになる |
| 新しいサブドメイン | DNS・証明書の外部操作が増え、得るものがパス分けと変わらない |
| IP 許可 | クラウドの出口 IP が固定と確認できない |

## 戻し方

1. 即停止: `docker stop ai-reader-http`。止め続けるには GitHub secret `READ_WINDOW_TOKEN` も消す（空なら全員 401。サーバーの鍵だけ空にしても次の deploy で書き戻される）。
2. 撤去: compose・台本・nginx の変更を git revert、GitHub secret とクラウドのネットワークシークレットを削除。DB は変えていない。

## 検証

design.md §2 の K1〜K9。
