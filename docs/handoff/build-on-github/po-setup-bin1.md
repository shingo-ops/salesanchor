# 便1 の前に PO が行う設定（鍵・組織・置き場の値）

- 書いた日: 2026-11-04（Opus）。根拠: design.md §3-2・§7-3・§8・§23・§24-8。
- 2026-11-11 追記（Opus）: 1：・4：と、2：の `GHCR_PUSH_TOKEN`・3：の `GHCR_NAMESPACE`／`GHCR_USER` は PO が済ませた（名前を `gh secret list`・`gh variable list` で確認）。本線が 2026-11-05 に Firebase を外したので、2：の `VITE_FIREBASE_API_KEY` と 3：の `VITE_FIREBASE_AUTH_DOMAIN`・`VITE_GCP_PROJECT_ID`・`VITE_AUTH_PROVIDER` は**登録しなくてよい**（design.md §25-9 D1）。下の表は当時の記録として残す。指紋の照らし合わせ（2：の 2 つめの点）も行わない（§25-9 D4）。
- この設定が終わるまで、便1 の PR はマージしない（マージすると組み立てが動き、値が無いので赤になる）。
- 値（鍵の中身）はこのファイル・チャット・PR に書かない。

## 1：鍵を作る（GitHub の個人の画面・shingo-ops で入る）

（１）次を開く: https://github.com/settings/tokens/new?scopes=write:packages
（２）Note（名前）に `build-on-github GHCR push` と書く。
（３）Expiration（期限）は Custom を選び、2027-05-03 にする（今日から 180 日）。
（４）印は `write:packages` だけにする。`read:packages` は自動で付く。`repo` には印を付けない。
（５）一番下の「Generate token」を押す。出た文字列をコピーする（この画面を閉じると二度と見えない）。

## 2：置き場に鍵を登録する（shingo-ops/salesanchor）

場所: https://github.com/shingo-ops/salesanchor/settings/secrets/actions の「Secrets」タブ →「New repository secret」。

| 名前 | 中身 |
|---|---|
| `GHCR_PUSH_TOKEN` | 1：で作った鍵 |
| `VITE_FIREBASE_API_KEY` | Firebase の画面 → 計画 `sales-ops-with-claude` → 歯車「プロジェクトの設定」→「全般」の「ウェブ API キー」 |

- `VITE_FIREBASE_API_KEY` は今は置き場に無い（2026-11-04 `gh secret list` で確認）。本番の画面の中に入っている値と同じものを入れる。
- 照らし合わせ: 本番の画面の値の指紋（sha256 の頭 16 字）は `ef457eddf9b65693`。初回の組み立ての後に、Opus が完成品の中の値の指紋と比べる（値は出さない）。

## 3：置き場に値を登録する（同じ画面の「Variables」タブ）

場所: 同じ画面の「Variables」タブ →「New repository variable」。

| 名前 | 中身 | 出どころ |
|---|---|---|
| `GHCR_NAMESPACE` | `gen-ryu-system` | design.md §5-1 |
| `GHCR_USER` | `shingo-ops` | 1：の鍵の持ち主（§23） |
| `VITE_FIREBASE_AUTH_DOMAIN` | `auth.salesanchor.jp` | 本番の画面の中の値（2026-11-04 公開ファイルで確認） |
| `VITE_GCP_PROJECT_ID` | `sales-ops-with-claude` | 本番の画面の中の値（同上） |
| `VITE_AUTH_PROVIDER` | `self` | `.github/workflows/deploy.yml:380`（本番へ書く値） |

## 4：組織の設定（GEN-RYU-System の画面）

場所: 右上の顔 → Organizations → GEN-RYU-System → Settings。

（１）左の「Packages」→「Package Creation」で **Private だけ**を選ぶ。Public は選ばない。Save。
（２）左の「Personal access tokens」→「Settings」→「Tokens (classic)」タブ →「Allow access via personal access tokens」のままにする。Save。
（３）同じ「Tokens (classic)」タブの「Set maximum lifetimes for personal access tokens」を 180 日にする。Save。

- 出典: GitHub 公式「Setting a personal access token policy for your organization」「Configuring a package's access control and visibility」（2026-11-04 に読んだ）。
- 注意: 完成品を Public にすると戻せない（公式「Once you make a package public, you cannot make it private again.」）。Danger Zone は触らない。

## 5：終わったら

チャットで「設定した」とだけ伝える。Opus が名前の有無だけを確かめる（`gh secret list`・`gh variable list`）。組織の設定は PO の画面でしか見えないので、PO の返事を正とする。
