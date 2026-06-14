# recon — セキュリティ三層トリアージ（②DB/Redis露出・③秘密情報のgit混入・④古いドメイン残存）

| 項目 | 内容 |
|------|------|
| 実施日 | 2026-06-14 |
| 実施者 | Terminal CC（architect recon） |
| ブリーフ | 「recon brief — セキュリティ三層トリアージ」（2026-06-14, Web Claude 発行） |
| 範囲 | 観点A=②DB(5432)/Redis(6379)外部露出 / 観点B=③秘密情報のgit混入 / 観点C=④旧ドメイン残存 |
| 性質 | **read-only の現在地把握のみ**。設定書換・FW操作・再起動・migration・PR・本番操作は一切行っていない |
| 環境制約 | 本reconはリポジトリのフレッシュクローン上で実施（VPS シェル非接続）。実機状態（`ss`/`ufw`/外部到達性/Firebase Console）は本環境から取得不能 → 該当行は「不明（VPS/手動確認要）」と明記し、創作で埋めていない |
| ①RLS | テナント分離（RLS）の深掘りは本ブリーフ範囲外（別ブリーフ） |

---

## 白黒判定表

| 観点 | 確認方法（file:line / コマンド） | 結果 | 証拠（引用・出力／伏字） | 緊急度 |
|------|------------------------------|------|----------------------|--------|
| A-1 | `docker-compose.yml` の db/redis `ports:` を確認 | **白**（本番compose） | `docker-compose.yml:318-348` postgres・`docker-compose.yml:288-316` redis いずれも `ports:` 無し。両者 `networks: - backnet`（内部のみ）。ホスト公開は nginx の `docker-compose.yml:7-9` `"80:80" "443:443"` のみ | — |
| A-1補 | 他 compose の 5432/6379 公開 | **灰（要確認）** | `docker-compose.test.yml:12-13` が `"5432:5432"`（0.0.0.0公開）＋ `POSTGRES_PASSWORD=password`（`:10`）。ただしテスト専用構成・`tmpfs`データ・`deploy.yml` から不参照（本番デプロイ経路で起動されない）。`docker-compose.exporters.yml:17,34,51,69` は exporter メトリクスを公開IP `${APP_VPS_IP:-49.212.137.46}` の 9100/9187/9113/9121 に bind（DB/Redis ソケット自体ではないが postgres/redis の **メトリクス**を公開面に出す＝VPS FW依存） | 中（後述§Shingo判断） |
| A-2 | `sudo ss -tlnp` の待受 | **不明** | 本reconはVPS非接続のため未取得。VPS閲覧系コマンドでの確認が必要 | — |
| A-3 | `sudo ufw status verbose` | **不明** | 同上。FW実状態は本環境から取得不能 | — |
| A-4 | VPS外端末から `nc -zv 49.212.137.46 5432`/`6379` | **不明** | 本reconの安全プロトコル下（VPS閲覧系限定・本環境はVPS外スキャン手段なし）のため未実施 | — |
| A-5 | redis 認証設定 | **白（弱い既定値あり=灰寄り）** | `docker-compose.yml:291` `redis-server ... --requirepass ${REDIS_PASSWORD:-changeme}` → `requirepass` 有効。`.env.example:34` `REDIS_PASSWORD=（安全なランダム文字列を設定）`。redis は published port 無し＋`backnet` 隔離＋`read_only: true`(`:312`)。**留意**: env 未設定時の fallback `changeme` は弱い（本番 `.env` で必ず上書きされている前提。実値は本環境から確認不能=不明） | 低 |
| B-1 | `.gitignore` の .env 系除外 | **白** | `.gitignore:24-27` `.env` / `.env.local` / `.env.*.local` / `*-password.txt`、`.gitignore:30-31` `firebase-credentials.json` / `*-credentials.json` 除外済み。他に `:114` prometheus secrets、`:117` htpasswd.d、`:120` `.claude-access.env` も除外 | — |
| B-2 | `git ls-files` の秘密ファイル＋履歴 | **白** | `git ls-files | grep -iE '\.env$\|secret\|credential\|\.pem$\|\.key$'` のヒットは全て**コード/ドキュメント/migration**（例 `backend/app/services/carrier_credentials.py`=Fernet暗号化＋env利用の**サービス実装**、`docs/runbooks/secret-rotation.md` 等）で**実値ファイルではない**。追跡中の `.env*` は `.env.example` / `.env.monitoring.example` / `frontend/.env.example` の**テンプレートのみ**。`git log --all --diff-filter=A` で `.env`/`firebase-credentials`/`*.pem`/`*.key`/htpasswd が**履歴上一度も追加されていない**ことを確認（NONE ever added） | — |
| B-3 | gitleaks 全履歴スキャン | **白** | `gitleaks v8.21.2 detect --source . --config .gitleaks.toml`（**171 commits scanned / no leaks found / 0 findings**）。allowlist 影響排除のため **default ルールのみ**でも再スキャン → 同じく **0 findings**（allowlist が実害を隠蔽していない）。CI でも `.github/workflows/secret-scan.yml:15-27` が `gitleaks/gitleaks-action@v2` を `fetch-depth: 0`（全履歴）で毎PR強制 | — |
| B-4 | ソース直書きの当たり付け | **白** | `grep -rniE '(secret\|api[_-]?key\|password\|token)[[:space:]]*[:=][[:space:]]*["'\''][A-Za-z0-9_/+=-]{16,}["'\'']' backend/app`（env参照/Field/Depends 除外）= **0件**。`.env.example` 内の非空値は**公開情報のみ**: Google OAuth Client ID `.env.example:81`（`.gitleaks.toml:19-20` で allowlist＝公開ID）・`GHA_APP_ID=3890309`(`.env.example:121`/GitHub App ID は公開)・公開IP `.env.example:115-116`。秘密値は全て空欄プレースホルダ | — |
| B-5 | 実行時注入経路 | **白** | `docker-compose.yml:64-107,181-195,225-229` 全 secret を `${ENV}` 経由で注入。`backend/app/main.py:159-166` は `os.getenv("ALLOWED_ORIGINS", ...)`。GHA 秘密鍵は**ファイルマウント方式**（`docker-compose.yml:362-366`、`.env` に PEM 直書きしない）。リポジトリ内ファイルに実値なし | — |
| C-1 | Firebase authorized domains | **不明（手動確認要）** | Firebase Console の運用確認事項（コードrecon対象外）。ブリーフ§7 既知: `jarvis-claude.uk` 残存・手動削除待ち。Shingo の Console 確認が必要 | — |
| C-2 | コード内の旧ドメイン参照 | **灰（意図的・既知）** | `grep -rniE 'jarvis-claude'` ヒットあり。コード実体は `nginx/nginx.conf:13,31,33-34`（server_name・証明書パス）、`backend/app/main.py:163`（CORS fallback 既定値）、`.env.example:43`。**ただし並行稼働が意図的**: `CLAUDE.md:14` `README.md:26` `docs/external-state-contract.yml:75`「並行稼働中、PO 確認前に削除禁止」。切替は `docs/PHASE5_DOMAIN_CUTOVER_RUNBOOK.md` で計画済み。残りは docs 参照が大半 | 低 |
| C-3 | バックエンド CORS 許可オリジン | **白** | `backend/app/main.py:159-174` 明示オリジン list（`jarvis-claude.uk` + `app.salesanchor.jp` + `salesanchor.jp`）。**ワイルドカード `*` なし**。`allow_credentials=True` だが `allow_methods`/`allow_headers` も限定列挙。本番は `ALLOWED_ORIGINS` env で上書き（`docker-compose.yml:69`） | — |
| C-4 | フロント Firebase authDomain | **白** | `frontend/src/lib/firebase.ts:20` `authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN`。`frontend/.env.example:6` / `.env.example:30` とも `auth.salesanchor.jp`（現行・ADR-032）を指す。旧ドメインを指していない | — |

---

## recon結論（事実と判断を分離）

### 即対応が必要な穴（黒・緊急度つき）

- **該当なし。** 本トリアージのコードreconで確認できた範囲に「黒（明確な穴）」は無し。
  - 特に③（秘密情報のgit混入）は **gitleaks 全履歴 0 件・秘密ファイル履歴上ゼロ・ソース直書きゼロ** で白を強く確認。「家が燃えている」級の現役秘密ヒットは**なし**（鍵ローテーション/履歴スクラブの起票は不要）。

### 設定改善候補（灰・任意改善／本reconでは変更しない）

1. **A-1補: `docker-compose.test.yml:12-13` の `5432:5432`（0.0.0.0公開）＋弱パスワード `password`**
   テスト専用・`deploy.yml` 不参照のため本番リスクは低いが、ネットワーク到達可能なホストで誤起動すると 5432 を平文公開する。`127.0.0.1:5432:5432` への bind 限定を任意改善候補として記録（変更可否は Shingo 判断）。
2. **A-1補: `docker-compose.exporters.yml:17,34,51,69` の exporter 公開IP bind（9100/9187/9113/9121）**
   exporter メトリクス（postgres/redis/node/nginx）を公開IPに出す設計。DB/Redis ソケット自体ではないが、**VPS ファイアウォール（A-3, 本recon不明）が唯一の防御層**。FW で 9100/9187/9113/9121 が遮断されているか **A-3 の実機確認が前提**。
3. **A-5: `REDIS_PASSWORD` の fallback 既定値 `changeme`（`docker-compose.yml:291,296`）**
   本番 `.env` で上書きされていれば無害。上書きの実機確認（=不明）と、fallback を空＝fail にする等の堅牢化は任意改善候補。
4. **C-2: 旧ドメイン `jarvis-claude.uk` のコード/docs 残存**
   意図的な並行稼働（PO 管理下・削除禁止明記）。Phase 5 cutover 完了後の一括クリーンアップが既に runbook 化済み。recon としては「既知・計画済み」に分類。

### 問題なし確認済み（白）

- A-1（本番 compose）: postgres/redis ともホスト公開なし・内部ネットワーク隔離。
- A-5（設定面）: redis `requirepass` 有効・published port なし・`read_only`。
- B-1〜B-5（③秘密情報）: .env系除外・追跡中/履歴の秘密ファイルゼロ・gitleaks 0件（CI でも全履歴強制）・ソース直書きゼロ・env注入経路のみ。
- C-3: CORS にワイルドカードなし・明示オリジン限定。
- C-4: フロント authDomain は現行 `auth.salesanchor.jp`。

### Shingo判断が必要な事項（事実とは分離。修正可否・優先度・GO要否）

| # | 論点 | 必要なアクション（recon提案・実行は別作業） | GO要否 |
|---|------|--------------------------------------------|--------|
| S-1 | A-2/A-3/A-4 が**不明**（VPS非接続のため実機の待受/FW/外部到達性が未確定） | VPS 閲覧系コマンド（`sudo ss -tlnp`・`sudo ufw status verbose`）と VPS外端末からの `nc -zv 49.212.137.46 5432`/`6379` を**人が実施**し本表 A-2〜A-4 を確定。**②の白黒はこの実機確認が出るまで暫定** | 閲覧のみ＝GO不要。FW変更が要るなら別途GO必須 |
| S-2 | C-1 Firebase authorized domains の旧ドメイン残存（既知・削除待ち） | Firebase Console を Shingo が確認し、不要ドメイン削除の可否・時期を判断（外部GUI操作＝CLAUDE.md 上 PO確認必須） | GO/手動操作は Shingo |
| S-3 | 設定改善候補 1〜3（test compose bind / exporter 公開bind / redis 既定値） | 黒ではないため**任意**。修正する場合は FW/compose/本番設定に触れるため STANDARD-WORKFLOW に沿って KGI 設定→設計→GO | 修正実施時に GO必須 |
| S-4 | C-2 旧ドメイン最終処遇 | `docs/PHASE5_DOMAIN_CUTOVER_RUNBOOK.md:209-216` の「最終的な扱い（即停止/並行/301）」決定は PO 判断 | Shingo |

---

## 付録: 実行コマンドと出力サマリ（再現用）

- `gitleaks v8.21.2 detect --source . --config .gitleaks.toml --no-banner --redact` → `171 commits scanned` / `no leaks found` / **0 findings**
- `gitleaks detect --source .`（default ルールのみ・allowlist 不使用） → **0 findings**
- `git ls-files | grep -iE '\.env$|secret|credential|\.pem$|\.key$'` → ヒットは全てコード/docs/migration（実値ファイルなし）
- `git log --all --pretty=format: --name-only --diff-filter=A | grep -iE '\.env$|firebase-credentials|\.pem$|\.key$|htpasswd'` → **NONE ever added**
- `grep -rniE '(secret|api[_-]?key|password|token)[[:space:]]*[:=][[:space:]]*"…{16,}"' backend/app`（env参照除外） → **0件**

> 秘密の実値は本ファイルに一切記載していない（種別・場所・伏字のみ）。
