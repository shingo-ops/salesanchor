# ADR-1042: クラウドから本番を読むだけの HTTPS 窓口を、読む人の接続だけを持つ専用コンテナで作る

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（2026-10-25。採用の根拠: 便1 #4687 が本番に入り（Deploy to VPS run 39910774734 が 2026-10-23T06:23:59Z に成功）、design.md §2 の K1〜K9 を確かめた。K8 は死活監視の前後比較の記録が無く、メモリだけを測った。詳細は design.md §12） |
| 備考 | PO 2026-10-22「クラウドでもいまと変わらない環境を構築したい、本番への読み取りも、hookも」。PO 2026-10-23 チャット「1」：本番を読むだけの窓口を設計し、設計書と確かめ方の表を見てから本番に手を入れる。PO 2026-10-23 チャット「1」：確かめ方 K1〜K9 で進め、実装・確認・本番反映まで行う |
| 起案日 | 2026-10-23 |
| 方針の決定者 | Shingo（PO）。方式の選択は Opus（PO の委任に基づく。ADR-1003） |
| 関連 | ADR-1024（AI の本番 DB 読み取りの道）、ADR-1025（専用鍵の受け口）、ADR-1017（fail-closed）、ADR-1003（GO 委任）、ADR-1052（本 ADR を改める。ADR-1052 が Accepted になったときに効く） |
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

## 改訂

### 改訂（クラウドの相談係の窓口、2026-10-30）

- 経緯: Discord の投稿を合図に、クラウドの相談係 AI が本番を読む（ADR-1052）。設計: [design.md](../handoff/cloud-case-ai/design.md)。
- 今の窓口（`ai-reader-http`・`api.salesanchor.jp` の入口・`READ_WINDOW_TOKEN`）は変えない。
- 相談係専用に、同じ作りの容器 `ai-reader-cloud-http` を足す。接続はロール ai_reader_cloud（読むのは伏せたビュー ai_cloud だけ）。鍵は `CASE_AGENT_TOKEN`（正本は GitHub secret・90 日更新）。compose のプロジェクト名は今の窓口と分ける。
- 受けるヘッダの名前と値の頭は、環境変数 `READ_WINDOW_TOKEN_HEADER`・`READ_WINDOW_TOKEN_PREFIX` で選べるようにする。既定は今と同じ（`X-Read-Window-Token`・頭なし）。相談係の容器だけ `Authorization`・`Bearer `。クラウドの network secret が 1 つのホストに 1 つ・ヘッダ 1 行だったため（ADR-1052 段0）。記録の印も環境変数 `READ_WINDOW_AUDIT_VIA` で分ける（既定 `https`、相談係は `https-case`）。
- 不採用の案「新しいサブドメイン」を、相談係の道に限って採る。理由: api.salesanchor.jp には公開の書き込み口があり、パス分けでは相談係 AI から隠せない。相談係 AI が届くのは `case-api.salesanchor.jp` の決まった 3 つの道だけにし、今の 443 の server ブロック全部で TLS の名前が case-api なら 421 を返す。DNS はプロキシなし（グレー雲）で作る。プロキシを入れる場合はこの守りを作り直す。
- 値を返す口は backend にも本窓口にも置かず、専用容器 `ai-unmask-http` に置く（本 ADR の「値を返す口を backend に置かない」の考えを保つ）。
- 戻し方: ADR-1052 の「戻し方」の順で行う。今の窓口は変えていないので、戻しても今の窓口の利用者に影響しない。
- 本改訂は ADR-1052 が Accepted になったときに効く。
