# 設計doc — 設計図書サイト（SA設計のHTML可視化）v2

| 項目 | 内容 |
|------|------|
| 発行日 | 2026-06-12（**v2: 配信方式の変更を反映**。v1同日） |
| 状態 | **設計確定**（KGI承認 2026-06-12／J1〜J4すべて決定済み） |
| 相互参照 | recon brief: `recon-brief-design-site.md`／第1次recon（MGMT VPS実機確認・2026-06-12）／**第2次recon: `docs/handoff/design-site/recon.md`**（file:line・2026-06-12）／ADR-095〜106／`docs/plans/sa-progress/00-SA-OVERVIEW.md` |
| 宛先 | Terminal CC（Generator） |

---

## 1. 目的（Why）

ADR-095〜106（SAシリーズ）の設計意図を、技術知識のない読者でも理解できる図解中心のHTML図書として配信する。正本はADRのまま（矛盾時はADR優先）。

第2次reconの結論：**アプリVPSの既存nginxと既存deploy.ymlに乗せるのが最小工事**。新サーバーの建設・手動転送・専用デプロイのすべてが不要になり、初日から完全自動更新が成立する。

## 2. 確定済み判断（この設計の前提。変更はShingo承認が必要）

| # | 判断 | 決定 |
|---|------|------|
| KGI | G1〜G4 | 承認済み（2026-06-12。recon brief §2参照） |
| 公開方針 | パスワード付き非公開配信 | 確定（2026-06-12。GitHub Pagesは公開されるため不採用） |
| J1 | 配信方式 | **アプリVPSで直接配信**。`www/design-site/` をAPP VPS nginxが静的配信し、既存deploy.ymlの配信フローに包含。当初の「管理VPS配置」から**変更**（Shingo 2026-06-12承認）。根拠: 第2次recon — APP VPS nginxはMGMT VPSへの取り次ぎ実績あり（nginx.conf:162/179）、かつ直接配信なら既存デプロイに自動包含 |
| J2 | URL | `app.salesanchor.jp/design/`（確定済み。新サブドメイン案は不採用） |
| J3 | htpasswd管理 | **VPS直接管理・git追跡禁止**（B-11準拠、Planner既定）。受け入れ基準: **デプロイ（--force-recreate含む）やコンテナ再作成で消えない場所に置く** |
| J4 | HTML生成タイミング | **HTML＝リポジトリに静的コミット**。`progress.json` のみデプロイ時に `00-SA-OVERVIEW.md` §1表から毎回自動生成。**変換失敗＝デプロイ失敗**として停止 |
| v1進捗機能 | バッジ自動化＋GitHub PR一覧リンクのみ | 確定（2026-06-12）。PR実績のサイト内表示はv2 |

**廃止された判断**（J1変更に伴い不要化）: 初回ローカルMac手動rsync／MGMT VPSへのnginx新設／専用デプロイworkflow（deploy-design-site.yml）の新設。

## 3. v1スコープ（What）

1. **リポジトリ**: `docs/design-site/` 新設。素のHTML＋CSS、図はSVG直埋め込み、ビルドツールなし。共通テンプレ7項目・色の意味ルールはrecon brief §3のとおり。
2. **アプリVPS nginx**: `/design/` の静的配信location＋Basic認証（auth_basic）を**追加のみ**で実装。既存ブロックと非衝突であることは第2次reconで確認済み。
3. **htpasswd作成**: APP VPS上の永続位置に1回だけ作成（J3）。
4. **deploy.yml工程追加**: ①進捗表→`progress.json` 変換（失敗＝デプロイ停止）②`docs/design-site/` → 配信ディレクトリ同期。
5. **smoke（毎デプロイ自動確認）**: ①認証なしアクセス＝401 ②認証ありアクセス＝200 ③`progress.json` の生成日時が当該デプロイのもの ④アプリ本体と `/grafana/` の疎通が変更前後で変わらない。
6. **ページ制作**: Stage 1＝パイロット3ページ（トップ・SA-01・SA-02）→Shingoレビュー（G4判定）→Stage 2＝残り6ページ。

## 4. 弊害対策（ポカヨケ）

- **公開事故**: デフォルトdeny（認証設定が外れたら全拒否になる構成）＋smoke①を毎デプロイ実行（FedEx Stage 1のsmoke監視の型を流用）。
- **パスワード平文流出**: HTTPS必須（既存Let's Encrypt流用・第2次reconで確認済み）。htpasswdはgit外・平文/ハッシュともリポジトリ保管禁止（B-11）。
- **進捗の嘘**: `progress.json` は人が書かずデプロイ時に毎回生成。変換失敗＝デプロイ失敗で「古い進捗が黙って表示され続ける」事故を構造で防止。
- **本番nginx変更リスク**: 追加のみのlocationブロックに限定し、smoke④で既存経路（アプリ・/grafana/）の無事故を毎回確認。
- **デプロイでの消失**: htpasswd・配信ディレクトリは `--force-recreate` を含むデプロイで消えない配置にする（受け入れ基準）。
- **陳腐化**: 全ページに正本ADRリンク＋最終更新日＋「矛盾時はADR優先」を明記。ADR変更時に設計図書も更新するルールを**CLAUDE.mdへインライン追記**（Stage 2）。

## 5. 受け入れ基準（KGI対応）

| KGI | 基準 | 検証 |
|-----|------|------|
| G1 | `https://app.salesanchor.jp/design/` がPC・スマホで閲覧可。認証なし＝401が100% | smoke①②（自動） |
| G2 | Stage 1＝3ページ、Stage 2＝全8ページ＋トップがテンプレ7項目で全て埋まっている | 検証ゲート＋Shingoレビュー |
| G3 | 全ページに正本ADRリンク＋最終更新日＋ADR優先の明記 | 検証ゲート |
| G4 | 非技術者がトップだけで4原則・2本背骨・全SAの位置づけを説明できる | Shingoレビュー（パイロット確認時） |

## 6. 段階分けとGO条件（2026-06-10合意の線引きに準拠）

| 段階 | 内容 | GO条件 |
|------|------|--------|
| Stage 0（インフラ・**要GO**） | nginx `/design/`＋auth_basic追加／htpasswd作成／deploy.yml工程追加（変換＋同期） | deploy.yml＋本番nginxに触るため、**実行直前に設定差分をShingoへ提示し、明示GOを得てから実行** |
| Stage 1（パイロット） | トップ・SA-01・SA-02の3ページPR | docs配下のみ＝ゲート自動スキップ。CI緑で進行可。完成後**Shingoレビュー**（G4判定） |
| Stage 2（展開） | 残り6ページ量産／CLAUDE.mdインライン追記 | CI緑で進行可（専用workflow新設は不要になったためGO対象なし） |

## 7. 外部・過去事例

- **社内**: APP VPS nginxの取り次ぎ実績（Grafana nginx.conf:162／Uptime Kuma :179）＝同じ玄関での運用実績。FedEx Stage 1のsmoke自動監視の型。Suppliersドロワーのパイロット→展開方式。
- **外部**: 「静的HTML＋リバースプロキシのBasic認証」による社内ドキュメント配信は標準的な構成。ビルドツール不使用のため本件はさらに保守が単純。

## 8. 継続（リリース後）

- smoke①〜④を毎デプロイ実行。失敗時は既存Discord通知の型でアラート。
- ADR更新→設計図書更新のルール運用（CLAUDE.mdインライン）。
- v2候補: PR実績のサイト内自動表示（作者・マージ日時・PR数・リードタイム）／ページ内検索／英語版。

## 9. Generatorへの委任境界

nginx設定の具体・変換スクリプトの実装言語・同期方法等のHowはGenerator裁量。ただし以下は受け入れ基準であり譲れない: **デフォルトdeny／/grafana/とアプリ本体の疎通維持／変換失敗＝デプロイ失敗／htpasswd・配信物のデプロイ耐性（消えない）**。

---

## 10. インシデント記録

### 10-1. Basic認証欠落インシデント（2026-06-12 — Shingo事後承認）

| 項目 | 内容 |
|------|------|
| 発生日時 | 2026-06-12（PR #2019 develop→main マージ〜`f2a33605` デプロイ完了まで） |
| 分類 | 緊急セキュリティ対応（認証欠落 — `/design/` が認証なし 200 を返却） |
| 原因 | PR #2021（Stage 0）で `docker-compose.yml` に `./nginx/htpasswd.d:/etc/nginx/htpasswd.d:ro` ボリュームを追加したが、`docker compose up -d` が既存nginxコンテナを自動再作成しなかったため、htpasswd.d がコンテナ内未マウントのまま稼働。nginx は `/etc/nginx/htpasswd.d/design-site` を読めず、Basic認証が機能しなかった |
| 影響 | `app.salesanchor.jp/design/` が認証なしで 200 を返した（PR #2019 デプロイ 15:35〜ホットフィックスデプロイ完了 ~16:30 の約55分間） |
| 修正内容 | `deploy.yml` に `docker compose up -d --no-deps --force-recreate nginx` ステップを追加（コミット `ca0531c0`、PR `f2a33605`）。デプロイ run #27401107031 で smoke ①②③ PASS 確認 |
| 事後承認 | **Shingo 承認済み（2026-06-12）**。deploy.yml 変更（通常は事前GO必須）を緊急セキュリティ対応として事後承認 |
| 再発防止 | PR #2035（`feature/morimoto/design-site-smoke-autoblock`）にて smoke ④ FAIL 時の自動遮断を実装予定 |
