# 便3b 手順書 — 読み上げの鍵を作り、本番に置く（PO 本人の作業）

親: [design.md](./design.md)（142・143・146 行の申し送り）・前の便: [card-bin3a2.md](./card-bin3a2.md)
作成: 2026-11-18 Opus（設計担当）。状態: 手順書作成済み・PO の作業待ち。

この便は鍵（Google の合鍵ファイル）を扱うため、AI は鍵を作らず・中身を見ない。作るのも置くのも PO 本人。

## 0. 確かめ済みの事実（2026-11-18・読み取りのみ）

| 事実 | 根拠 |
|---|---|
| アプリは環境の値 `GOOGLE_TTS_SA_KEY_FILE` の場所にある鍵を読む。無い・読めないと 503 `tts_not_configured` | `backend/app/services/secretary_tts.py` |
| 本番の backend は入れ替え手順が作る。`.env` に場所があり、ファイルが在るときだけ鍵を箱の /run/google-tts-sa.json に読み取り専用でつなぐ | `scripts/blue-green-cutover.sh`（便3a-2・2026-11-18 10:09 本番反映） |
| 本番の反映（`.github/workflows/deploy.yml` の Step 2）は `.env` のうち決まった名前の行だけ消して書き直す。`GOOGLE_TTS_SA_KEY_FILE` はその一覧に無いので、手で足した行は反映で消えない | `.github/workflows/deploy.yml` 342〜395 行（`sed -i.bak -e '/^KEY=/d'` の一覧） |
| 反映は `git reset --hard origin/main` を使うが、未追跡のファイルは消さない（`git clean` は 0 件）。`.gitignore` の `/*.json` で鍵の置き場所は追跡外 | `deploy.yml` の grep（`git clean`・`rm -rf` 0 件）・`.gitignore` 89 行 |
| 今ある Google の鍵 tcg-sheets-sa.json は事業 `sales-ops-with-claude`・権限 `644 ubuntu:ubuntu` | 本番 VPS で `ls -l` と `project_id` だけを読んだ |
| 本番の箱は `uid=100(appuser)` で動く。644 なら読める | design.md 146 行 |
| 本番 `.env` に `GOOGLE_TTS_SA_KEY_FILE` の行は今 0 件 | 本番 VPS で `grep -c` |
| Google の公式手順: 事業を選ぶ → 請求を有効 → Text-to-Speech を有効 → 認証の用意 | Context7 `/websites/cloud_google_python_reference_texttospeech`（Quick Start） |
| 鍵の作り方（画面）: サービスアカウント → 対象のメール → 「鍵」タブ → 「鍵を追加」→「新しい鍵を作成」→ JSON → 作成。落とした鍵は二度と落とせない | Context7 `/websites/cloud_google_iam`（https://docs.cloud.google.com/iam/docs/keys-create-delete） |
| 無料は毎月 100 万字まで・超えたら自動で請求。アプリは月 90 万字で止める | recon.md 76〜77 行・`secretary_tts.py` の `MONTHLY_CHAR_CAP` |

## 1. 未確認（手順の中で確かめる）

- `sales-ops-with-claude` で Text-to-Speech が有効か・請求がつながっているか（手元の gcloud の認証が切れていて読めなかった）→ 手順 2-(2)(3) で PO が画面で確かめる
- 鍵に役（権限）が要るか（公式に専用の役は無い・design.md 142 行）→ 手順 4 の 1 回目の読み上げで 200 か 403 かで決める

## 2. Google の画面での作業（PO）

(1) Google Cloud の画面で事業 `sales-ops-with-claude` を選ぶ（今の鍵と同じ事業。台本はこれ以外の事業の鍵を止める）
(2) 請求（Billing）の画面で、請求先のアカウントがつながっていることを確かめる
(3) 「API とサービス」で「Cloud Text-to-Speech API」を検索し、「有効にする」（有効なら「管理」と出る）
(4) 「IAM と管理」→「サービスアカウント」→「サービスアカウントを作成」。名前は `secretary-tts`。役は付けずに「完了」
   - 今の表計算用の鍵を使い回さない理由: 片方だけ止められるようにするため
(5) 作った `secretary-tts@...` を開く →「鍵」タブ →「鍵を追加」→「新しい鍵を作成」→ JSON →「作成」。Mac の「ダウンロード」に落ちる
   - 「鍵の作成が許可されていません」と出たら、会社の決まりで止められている。そこで止めて Opus に伝える

## 3. 本番に置く（PO が Mac で 1 行流す）

台本: `~/CC報告ファイル-keep/place-tts-key.sh`（リポジトリ外・PO の ! 実行用）

```
! bash ~/CC報告ファイル-keep/place-tts-key.sh ~/Downloads/<落ちた鍵の名前>.json
```

台本がすること（順に）:
(1) 鍵が Google のサービスアカウントの鍵の形か・事業が `sales-ops-with-claude` かを確かめる。画面に出すのは事業名と利用者のメールだけ（秘密の部分は出さない）
(2) 本番 `.env` にもう行があれば何も変えずに止める
(3) 鍵を /home/ubuntu/salesanchor/google-tts-sa.json に送り、権限を 644 にする
(4) `.env` の控え（.env.bak-tts-日時）を取ってから、`GOOGLE_TTS_SA_KEY_FILE=/home/ubuntu/salesanchor/google-tts-sa.json` を 1 行足す
(5) 置いた鍵・足した行・控えの名前を表示する

この時点ではまだ箱につながらない。つながるのは次の本番反映のとき（入れ替え手順が `.env` を読む）。

## 4. つながったかの確かめ（Opus）

| 基準 | 確かめ方 |
|---|---|
| 反映の記録に「読み上げの鍵: つなぐ」の行が出る（今は「.env に場所が無いのでつながない」） | 次の反映の記録を読む |
| 箱に `GOOGLE_TTS_SA_KEY_FILE=/run/google-tts-sa.json` が 1 件・つなぎが 1 本 | 本番で `docker inspect` |
| 本番から 1 回読み上げて 200・音が返る（403 なら役が足りない → 手順 5） | 本番の箱の中から 1 回だけ呼ぶ |
| PO が秘書の窓で声を聞ける | PO の目視 |

## 5. うまくいかないとき・戻し方

- 403: Google の画面で `secretary-tts` に役を足す必要がある。Opus が公式の資料で役の名前を確かめてから PO に示す（推測で付けない）
- 503 のまま: 箱がファイルを読めていない。権限（644）とつなぎを Opus が読み取りで確かめる
- 戻し方: 本番 `.env` から `GOOGLE_TTS_SA_KEY_FILE` の行を消し（控えの .env.bak-tts-日時 で戻せる）、次の反映で箱から外れる。Google の画面で鍵を削除すれば鍵そのものが使えなくなる
- 手元の鍵ファイル: 声が出るのを確かめた後に「ダウンロード」から消す
