# Fable 設計審査記録（在庫の閲覧専用ページ）

r1〜r4 は REVISE、r5 で APPROVE（Blocking 0）。r5 の N-34〜N-39 は design.md に反映済み。各回の全文を下に転記する。

---

```text
# Architect 設計審査 — 在庫の閲覧専用ページ（gas-viewer-fresh-fast）

対象: docs/handoff/gas-viewer-fresh-fast/design.md（worktree release-gas-viewer-fresh-fast、2026-10-15 時点）
根拠: 同フォルダ recon.md / security-recon.md、/tmp/CC報告ファイル/viewer_security/fable_review.txt
照合基準: origin/main = 0c7852fd98d1650c3282d9284593a2eea7ed098d（git fetch origin 後。`git show origin/main:<path>` で全件照合）
生の照合出力: /tmp/CC報告ファイル/viewer_design_review/（self_tokens / dependencies / tcg_distribution_svc / tasks_dashboard / tasks_tcg_extraction / celery_app / cache / products_rls の cat -n 全文）
読み取りのみ。編集・commit・push は行っていない。

====================================================================
判定: REVISE
Blocking: 2 件 / Non-blocking: 11 件
====================================================================

--------------------------------------------------------------------
0. 事実照合（依頼 1）— 設計書の file:line と origin/main の実物
--------------------------------------------------------------------
【事実】
| 設計書の記述 | origin/main の実物 | 判定 |
|---|---|---|
| `backend/app/auth/self_tokens.py:86-98` にある既存の仕組み | :86-98 = create_access_token。claims は iss/sub/email/jti/iat/exp（+amr）。**種類（typ/aud）のクレームは無い**。:110-132 decode_access_token は issuer=ISSUER("salesanchor") と kid で検証 | 行番号は一致。ただし「流用できるか」の答えは実物から出る（§1 参照） |
| `backend/app/auth/dependencies.py:598-622` 既存 require_* は get_current_user 起点 | :598-624 require_permission。checker の依存 :612 get_current_user、:613 get_current_tenant | 一致（終端は 624） |
| distribution_rows_parts | `backend/app/services/tcg_distribution_svc.py:274-371`。引数 include_flag_single / age_condition / merge_same_post。DB・認証に依存しない SQL 文字列 | 一致 |
| fetch_output_rows | 同 :390-412。merge_same_post=False 固定、14列（_GAS_COLUMNS :251-254）。db.execute するだけで、テナント文脈（SET app.tenant_id）は自分では設定しない | 一致（recon の 390-411 は終端が1行ずれ、影響なし） |
| 「定期的に作って Redis に置く」前例 = `backend/app/tasks/dashboard.py`、600秒 | celery_app.py:68-71 "refresh-dashboard-kpis" schedule 600.0。dashboard.py:26-40 は **同期 psycopg2 エンジン**（create_engine）、:51 で set_tenant_context_sync を呼ぶ | 周期は一致。ただし fetch_output_rows は AsyncSession 前提（:390-391）なので、この前例の型はそのまま使えない。Celery から fetch_output_rows を呼ぶ実在の前例は `backend/app/tasks/tcg_extraction.py:725-757` _run_auto_distribution（ワンショット async engine + asyncio.run、テナント文脈なし） |
| celery beat に 60 秒周期は無い | celery_app.py:60-178。最短 300.0（:137）、600.0（:70,:176）、900.0（:119）、1800.0（:106） | 一致 |
| 614 本中 74 本 | fable_review §1-d, 付記（live app.routes 614、matrix と diff 0） | 一致（Fable 検証済み） |
| 元データはすべて public | tcg_distribution_svc.py:41 TCG_SCHEMA="public"、:317-331 の JOIN は全て public | 一致 |
| ADR-1014「distribution_rows_parts と fetch_output_rows の1か所」 | ADR-1014 本文は `distribution_rows_sql` の1か所と書く。parts は sql の分割版（:384-387 で sql が parts を呼ぶ） | 実質一致。設計書は ADR の語（distribution_rows_sql）も併記するとよい |
| 本番 JS 2,577,818 byte・非圧縮 | recon 追加 §6（本番への HEAD の記録） | 【未確認】本審査では本番へ接続していない。recon の記録のまま |
| Q1「GAS の今の 11 列」 | ~/tcg-viewer-1hc-release/Code.js:10-24 ALLOWED_HEADERS は **13 列**（投稿日時, Mark, Japanese Title, English Title, Condition, Unit Price, Quantity, Note_JA, Status, Release Date, 提供者, Series, Search Keywords。Ship_JA 無し）。recon §1 も「13列の許可リスト」 | **不一致**（§3 N-7）。なお ~/ 配下が本番 GAS と同一かは【未確認】 |

--------------------------------------------------------------------
1. 閲覧者とアプリユーザーの分離（依頼 2）
--------------------------------------------------------------------
【事実】get_current_user（dependencies.py:116-239）の受付経路は4本:
  (a) :143-157 SMOKE_SERVICE_TOKEN 一致 → 環境変数未設定なら不活性
  (b) :169-177 Redis の `jwt:<sha>` キャッシュにヒット → **署名検証なしに** cached["email"] で public.users を引いて返す
  (c) :187-188 peek_issuer(token) == "salesanchor" → _authenticate_self_token（:86-113）。sub で public.users を引き、claims["email"] == row.email を要求（:103）
  (d) それ以外 → Firebase verify_id_token（:192）。失敗で 401

これを閲覧者トークンに当てると:

### B-1【Blocking】トークンの「種類」の分け方が設計で未決。実物には種類の欄が無く、分け方を誤ると (b)(c) 経由で閲覧者がアプリに入れる
- 根拠:
  - self_tokens.py:86-98 の claims に typ/aud は無い。decode_access_token（:110-132）は iss と kid だけで判定。
  - 閲覧者トークンを **同じ ISSUER・同じ AUTH_JWT_SECRET** で発行すると、(c) に入る。public.users に `id = viewer.sub` かつ `email = viewer.email` の行があれば、そのユーザーとして通る（:97-104）。id と email の両方が一致する必要があるので確率は低いが、仕組みとしては塞がっていない。
  - 閲覧者の dependency が既存の `cache_jwt_result(token, {"email": ...})`（cache.py:53-59、キー `jwt:<sha>`）を流用すると、(b) で **署名を見ずに** email 一致の public.users が返る。同じ email を持つ社内ユーザーが閲覧者としても登録されていれば、閲覧者トークンでアプリの全 API に入れる。これは id の一致すら不要。
  - 設計書 D1 は「種類の値と署名の分け方は【実装前に確認】」とし、計画票 0 で Sonnet に委ねている。分離はこの設計の中核（KGI 5、技術選択の理由）であり、Generator に判断させる粒度ではない（CLAUDE.md「Planner が file:line＋変更前後まで設計」）。
- 直し方（設計書に固定する）:
  1. 閲覧者トークンの iss を別値にする（例 `salesanchor-viewer`。self_tokens.py:22 ISSUER とは別の定数）。これで get_current_user は (c) に入らず (d) Firebase 検証に落ちて 401 になる（:187, :192-198）。
  2. 閲覧者用の decode は issuer=閲覧者 iss を必須にし、逆方向（アプリのトークンを get_current_viewer に渡す）も 401 にする。
  3. 署名鍵は別の環境変数（例 AUTH_VIEWER_JWT_SECRET）にする。同じ鍵を使うなら「iss 検査だけが壁」になるので、鍵を分けて二重にする。
  4. Redis キャッシュは `jwt:` 名前空間を**使わない**（`viewer_jwt:` 等）。cache_jwt_result / get_cached_jwt を閲覧者側から呼ばないことを test_viewer_isolation で固定する（grep でも可）。
  5. ブラックリスト（:160-164 is_token_blacklisted）は閲覧者 logout でも同じ関数を使ってよい（拒否側なので安全）。
  6. 受け入れ基準に「閲覧者トークンが (b)(c) に入らない」を足す（§3 参照）。

### B-2【Blocking】受け入れ基準「614 本が全て 401/403」の検証方法が実行可能な形で定義されていない（守り手の中身が決まっていない）
- 根拠:
  - 設計書「CI pytest（全ルートを列挙して閲覧者トークンで叩く。test_viewer_isolation）」とあるが、
    (i) 既存テスト 38 本は `dependency_overrides[get_current_user]` で本物を差し替えている（`git grep -ln` 38 件）。本物の get_current_user を通すテストは test_self_auth.py:352 のように `_init_firebase` / is_token_blacklisted / get_cached_jwt / check_auth_rate_limit を patch している（test_line_import_devices.py:53 も同形）。test_viewer_isolation は **get_current_user を override しない** こと、何を patch してよいか（get_cached_jwt を patch すると (b) の検査が消える）を設計で決めないと、Generator が「通るテスト」を作る。
    (ii) パスパラメータ付きルート（/{company_id}/conv-logs 等）に何を埋めるか、期待ステータス集合（401/403 のみか、HTTPBearer 不備の 403 や 422 を許すか）が未定義。
    (iii) 守り手 `backend/tests/test_viewer_isolation.py` は新規ファイル。scripts/check-process-artifacts.js:549-554 は守り手ファイルの実在を検査するため、設計書だけの PR ではゲートが落ちる（process_artifacts gate）。
- 直し方:
  - 設計書 D1 または受け入れ基準に次を書く: 「app.routes の APIRoute 614 本（badges/buddy は未登録）を列挙し、path param は `1`/UUID 固定値で埋め、閲覧者トークン（正しい署名・有効期限内）で全 method を叩く。期待は allowlist 以外 **すべて 401**（get_current_user の 401 が param 検証より先に出る）。patch は _init_firebase と Redis 系（is_token_blacklisted→False、check_auth_rate_limit→False）のみ。**get_cached_jwt は patch せず**、事前に閲覧者 dependency を1回通した後でも 401 のままであることを別ケースで確認する（B-1 の (b) 対策）」。
  - 守り手の実在要件: 設計 PR の段階では「守り手: 人手で守る（test_viewer_isolation.py を段1で作る）」とし、段1の PR で守り手をファイルパスに書き換える。あるいは設計 PR に空の失敗するテスト（xfail）を同梱する。

--------------------------------------------------------------------
2. D3（60 秒の作り置きを Redis に置く）と SSOT（依頼 3）
--------------------------------------------------------------------
【事実】
- 正本は public.analysis_results ほか（tcg_distribution_svc.py:317-331）。Redis の作り置きは fetch_output_rows の結果の一時的な写し（TTL 付き・書き手はタスク1つ）で、既存の dashboard KPI（tasks/dashboard.py、TTL 660）と同じ型。DB にもシートにも写しを増やさない。
- 判定: **SSOT には反しない**（派生キャッシュ。読み手が書き戻さない限り正本は1つ）。

### N-1【Non-blocking】fetch_output_rows はテナント文脈を自分では持たない。Celery で呼ぶと products の RLS で「共通行（tenant_id IS NULL）」しか見えない。これは今の GAS 配信と同じ条件だが、アプリ在庫表（/inventory）とは条件が違う
- 根拠:
  - migrations/20260626_130000_force_rls_public_products.sql:5-13: products は FORCE RLS、SELECT は `tenant_id IS NULL OR tenant_id = app.tenant_id`。
  - tasks/tcg_extraction.py:725-757 _run_auto_distribution: ワンショット async engine で run_distribution(db) を呼ぶ。SET app.tenant_id は無い。
  - routers/tcg_distribution.py:166-172 POST /tcg/distribution/run: 依存は require_super_admin のみ（get_current_tenant を通らない → app.tenant_id 未設定）。
  - routers/inventory_offers.py:282-285 /inventory は require_permission("products.view") → get_current_tenant（dependencies.py:280-283）で app.tenant_id が入る。
  - dependencies.py:330-349 set_tenant_context_sync の docstring: 「app.tenant_id を設定しないと RLS が tenant_id IS NULL として評価し SELECT 0件」。
  - recon 追加 §未確認 4: 配信行が参照する products の tenant_id 分布は未確認。
- 影響: 配信行の product_id が tenant 固有の products 行を指していれば、Celery 作り置き（＝GAS 配信）では p.name 等が空になり、アプリ在庫表とは行の見え方が違う。GAS と同じ見え方にはなる。
- 直し方:
  - D3 に「テナント文脈は設定しない（GAS 配信 _run_auto_distribution と同じ条件）」または「tenant_004 を設定する（notify の :1074 と同じ）」のどちらかを明記する。
  - 受け入れ基準「作り置きの行が fetch_output_rows と同じ」を「**同じ接続条件（テナント文脈なし）で呼んだ** fetch_output_rows と同じ」に直す。
  - 計画票 0 に「本番で配信行の products.tenant_id 分布を1回 SELECT（人間実行、memory cc_db_path_backlog）」を足し、NULL 以外があれば PO に見え方の差を報告する。

### N-2【Non-blocking】D3 の「前例」の参照先が違う
- 根拠: §0 の表。dashboard.py は同期 psycopg2、fetch_output_rows は AsyncSession。Celery から async の run_distribution を呼ぶ実装は tcg_extraction.py:725-757。
- 直し方: D3 の前例を `backend/app/tasks/tcg_extraction.py:725-757` に差し替え、エンジン生成と dispose の型をそのまま使うと書く。dashboard.py は「Redis に JSON を置く・TTL を周期+余裕にする」部分の前例として残す。

### N-3【Non-blocking】max_age_hours 未設定時・安全装置 #8/#8b の扱いが D3 に無い
- 根拠: run_distribution は analysis_runs 未完了（:864-888）・extraction_jobs 未完了（:893-916）・max_age_hours 未設定（:921-930）で配信を止める。fetch_output_rows 単体にはこの判定が無い。/inventory は未設定時に空を返す（inventory_offers.py:323-328）。
- 直し方: 作り置きタスクが「再解析中でも作るか（在庫表と同じ）」「max_age_hours 未設定は空＋最終更新を更新しない」のどちらかを明記する。

--------------------------------------------------------------------
3. 受け入れ基準の機械判定性と抜け（依頼 4）
--------------------------------------------------------------------
| 基準 | 判定 | 指摘 |
|---|---|---|
| 614 本が 401/403 | 不可（現状） | B-2 |
| allowlist 照合 | 可 | allowlist の中身（viewer の API と「認証系」の具体パス）を設計に列挙すること |
| 期限切れ 403 | 可 | suspended 状態の 403 も同じ行に足す |
| 返す列に仕入元識別子・原価・買取価格が無い | **曖昧** | N-7: 「原価」が何の列か（GAS の Unit Price は閲覧者に見せている列）。除外キー・包含キーを両方列挙し、`set(response.keys()) == 固定集合` の等値で判定する |
| 作り置きが fetch_output_rows と同じ | 条件付き可 | N-1 の接続条件を書く |
| 本番中央値 1 秒 | 条件付き可 | 「開いてから」の始点（navigationStart）と終点（表の行が DOM に出た時刻）、キャッシュ有無（初回/2回目）、計測場所を書く。5 回の中央値なら奇数回で可 |
| 金型とトークン | 可 | — |

### N-4【Non-blocking】抜けている基準（追加案。いずれも CI pytest または Playwright で判定できる）
1. 逆方向: アプリのユーザーのトークンで /api/v1/viewer/inventory が 401（B-1 の 2）。
2. Redis 経由の抜け道: 閲覧者 dependency を通した直後に、同じトークンで既存 API を叩いても 401（B-1 の 4）。
3. 60 秒周期が登録されている: celery_app.beat_schedule に該当エントリがあり schedule == 60.0。
4. 失敗時に前回値が残る: タスクが例外を出した後、Redis キーの値と「最終更新」が変わらない。
5. 3 回連続失敗で警告が出る: 通知関数が1回呼ばれる（mock）。
6. 申込の honeypot と回数制限: 隠し欄に値があれば 200 を返すが行を作らない／同一 email の連投が 429。
7. 本人確認前の行が放置されない: 未確認のまま N 日経った viewer_accounts を消す定期タスクがある（D5 に無い。契約表と公開フォームの組み合わせはゴミ行が溜まる）。
8. i18n: ja.json と en.json のキー集合が一致（既存チェックに乗るなら「既存 CI」と書く）。
9. viewer.html の大きさ: 【実装前に計測】のままでは基準にならない。上限（例 300KB gzip 前）を置き、`ls -l dist/viewer*.js` で判定する。
10. /viewer/ の到達: frontend/nginx.conf:23-25 は全パスを index.html にフォールバックするため、`app.salesanchor.jp/viewer/` はそのままではアプリ本体を返す。Vite の入力を `viewer/index.html` にする（dist/viewer/index.html が $uri/ で当たる）か、frontend/nginx.conf に location を足すかを D4 で決め、Playwright で「/viewer/ が viewer の title を返す」を基準にする（設計書の【実装前に確認：nginx】はこれで解消できる。外側 nginx/nginx.conf:237 は `/` を frontend に proxy するだけで変更不要）。

--------------------------------------------------------------------
4. 様式（依頼 5）
--------------------------------------------------------------------
【事実】scripts/check-process-artifacts.js の検査項目との照合:
- 受け入れ基準の表（:477）: あり。検証方法の空欄（:489）: なし。
- recon パスの記載（:494）: あり。ADR 参照（:500）: 「ADR-1016（新規・草案）」。ADR-1016 は origin/main に存在しない（docs/adr/ は ADR-1015 まで）。textHasAdrReference が未存在 ADR をどう扱うかは【未確認】。
- 外部・過去事例の欄（:506-516）: あり、「該当なし＋理由」記入済み。
- 維持の仕組み・守り手（:528-554）: あり。守り手パスは新規ファイル → **実在検査で落ちる**（B-2 (iii)）。
- 様式の「## 継続」（完了後の監視・次フェーズ引き継ぎ）: 設計書に無い。ゲートは検査しない（grep に無し）が、様式の必須欄として欠けている。

### N-5【Non-blocking】「## 継続」欄が無い
- 直し方: 「完了後の監視: 作り置きタスクの失敗回数（既存の監視経路）、閲覧 API の p50」「次フェーズ: GAS 停止（Q4）と、別件の社内権限の穴」を書く。

### N-6【Non-blocking】ADR-1016 が未起案のまま設計書が ADR を指している
- 根拠: docs/adr/ に ADR-1016 無し。CLAUDE.md「設計判断は docs/adr で起案」「ADR 変更後は generate-adr-index.js」。
- 直し方: 設計 PR に ADR-1016 草案（Status: Proposed）を同梱し、README 再生成をコミットに含める。

--------------------------------------------------------------------
5. 設計本文のその他の指摘
--------------------------------------------------------------------
### N-7【Non-blocking】列数・列名の不一致（11 列 vs 13 列 vs 14 列）
- 根拠: §0 の表。GAS ALLOWED_HEADERS は 13 列（Ship_JA 無し）、DIST_HEADERS は 14 列（:47-62）、設計 Q1 は「11 列」。
- 直し方: Q1 を「GAS の 13 列（列名を列挙）＋ Ship_JA を足すか」の形に直す。Unit Price と Quantity を閲覧者に見せる前提（GAS で見せている）を明記し、「原価」の語は使わない（何を指すか不明）。

### N-8【Non-blocking】D1 の「ログインの資格情報」列は ADR-1013 の表と噛み合わない
- 根拠: ADR-1013 のパスワード・パスキー・再設定鍵は public.users.id に紐づく（recon 追加 §1、self_tokens.py:224 も public.users を引く）。viewer_accounts は users と別表なので、password_reset_tokens / webauthn_credentials / auth_refresh_tokens を流用できない。
- 直し方: Q2 の答えに応じて「閲覧者用の資格情報表（または列）を新設する」「更新用トークン（refresh）は持たず短命トークン＋再ログインにする」等を D1 に書く。更新用トークンを持つなら viewer 用の表が要る。

### N-9【Non-blocking】D5 の公開 signup は「外部から DB に書く」初の公開入口。回数制限は既存の未認証 60 回/分（rate_limit.py:31-33、Redis 不通で fail-open）と nginx 30r/s しか無い
- 直し方: email 単位・IP 単位の上限値と、本人確認前の行の削除（N-4 の 7）を D5 に書く。honeypot は書いてある。

### N-10【Non-blocking】rate_limit / session_guard は JWT の payload を無検証で読む。閲覧者トークンの email クレームが社内ユーザーと同じだと、同じバケット・同じセッション追跡になる
- 根拠: middleware/rate_limit.py:39-50、session_guard.py:45-55。
- 直し方: 閲覧者トークンの email クレーム名を変える、または sub を `viewer:<id>` にする等で識別子を分ける。重大ではないが、B-1 の「別 iss・別キャッシュ」と合わせて決める。

### N-11【Non-blocking】「3 回連続失敗で既存の監視に警告」の経路が未定
- 根拠: 配信失敗の既存経路は send_discord_notification(tenant_id=4, event_type="tcg_distribution_error")（tcg_distribution_svc.py:1066-1081）。
- 直し方: 同じ関数・同じ tenant_id を使うと書く（新しい経路を作らない）。

--------------------------------------------------------------------
6. PO へ確認すべき未決事項（Q1〜Q4 以外）（依頼 6）
--------------------------------------------------------------------
- Q5. 申込は自動承認か（メール確認だけで 14 日間、仕入元名・単価を含む表が誰でも見える）、人の承認を挟むか。今の GAS は ANYONE_ANONYMOUS（recon §1）なので「誰でも」は現状と同じだが、申込者の個人情報を自社 DB に保存する点が新しい。
- Q6. 再トライアル防止の方針（同じ会社が別メールで再申込したら通すか。ドメイン単位で止めるか）。
- Q7. 閲覧者の個人情報（氏名・会社・メール）の保存期間と削除方法。LP の privacy ページ（lp/src/pages/privacy）に閲覧者向けの記載を足すか。
- Q8. 閲覧用ページの置き場所: app.salesanchor.jp/viewer/（同一オリジン。ADR-1013 Decision 5b のオリジン制限に乗る）で確定してよいか。別サブドメインにするなら CORS/CSP と 5b の扱いが変わる。
- Q9. Unit Price / Quantity を閲覧者に見せ続けてよいか（GAS で見せている列。N-7 と同じ行で聞く）。

--------------------------------------------------------------------
7. 推測・未確認の一覧
--------------------------------------------------------------------
【推測】
- B-1 の (c) 経路での id+email 一致は、運用上は起きにくい。ただし「仕組みで塞ぐ」設計方針（KGI 5、技術選択の理由）と矛盾するため Blocking にした。
- FastAPI では dependency の HTTPException が path param の 422 より先に出る（solve_dependencies の順序）。B-2 の「全て 401」はこの前提。test_viewer_isolation の最初の実行で確認すること。
【未確認】
- 本番 JS の大きさ（recon の記録のまま）。
- 本番の products.tenant_id 分布（N-1）。
- 本番 SMTP 設定（設計書の【未確認】と同じ）。
- ~/tcg-viewer-1hc-release/Code.js が本番 GAS と同一か。
- check-process-artifacts.js が未存在 ADR 番号の参照をどう扱うか（N-6）。

--------------------------------------------------------------------
8. 総括
--------------------------------------------------------------------
設計の方向（閲覧者をアプリユーザーと分け、作り置きを Redis に置き、軽い別入口で出す）は recon・security-recon・Fable 検証の事実と整合しており、SSOT にも反しない。
差し戻す理由は 2 点: (B-1) 分離の中核であるトークンの種類・鍵・キャッシュ名前空間が設計で決まっておらず、実物には種類の欄が無い（流用すると Redis キャッシュ経由の抜け道がある）。(B-2) 守り手テストの実行条件が未定義で、設計 PR の段階でゲートが落ちる。
この 2 点を設計書に書き切り、N-1 / N-7 / N-5 / N-6 を直せば APPROVE できる。
```

---

```text
# Architect 設計審査 r2 — 在庫の閲覧専用ページ（gas-viewer-fresh-fast）

対象: /Users/tanizawashingo/worktrees/salesanchor/release-gas-viewer-fresh-fast/docs/handoff/gas-viewer-fresh-fast/design.md（r2、189 行、2026-10-15。worktree では未コミット = `??`）
前回: /tmp/CC報告ファイル/viewer_design_review.txt（r1 REVISE、B-1/B-2、N-1〜N-11）
照合基準: origin/main = f005b623fe2a68a3035f7fd51c692a7c44b23fea（git fetch origin 後）。
  設計書が照合に使った 0c7852fd9 との差分を `git diff --stat 0c7852fd9 origin/main -- backend/app/auth backend/app/middleware backend/app/services/tcg_distribution_svc.py backend/app/celery_app.py backend/app/tasks frontend/nginx.conf nginx/nginx.conf frontend/vite.config.ts scripts/check-process-artifacts.js docs/adr` で取ったところ **差分なし**。よって r2 の file:line は origin/main 現在値と同じ土台。
生の照合出力: /tmp/CC報告ファイル/viewer_design_review_r2/（dependencies / frontend_nginx / nginx_nginx / celery_app / self_tokens / rate_limit / session_guard / audit / cache / tcg_distribution_svc / tasks_tcg_extraction / check_process_artifacts / vite_config / send_discord_def の cat -n 全文）
読み取りのみ。編集・commit・push は行っていない。

====================================================================
判定: REVISE
Blocking: 1 件（新規 B-3）／ Non-blocking: 9 件（新規 N-12〜N-20）
r1 指摘の解消状況: 解消 11 ／ 一部 2（N-4、N-6）／ 未解消 0
====================================================================

--------------------------------------------------------------------
1. r1 指摘の解消判定（依頼 1）
--------------------------------------------------------------------
| 指摘 | 判定 | 根拠（design.md r2 の行） |
|---|---|---|
| B-1 トークンの種類・鍵・キャッシュ名前空間が未決 | **解消** | :50-57 で iss "salesanchor-viewer"（1）、別 secret AUTH_VIEWER_JWT_SECRET（2）、sub "viewer:<id>"・email クレームなし（3）、get_current_viewer が iss と鍵の両方を要求しアプリのトークンは 401（4）、`jwt:` 不使用・cache_jwt_result/get_cached_jwt 不呼出（5）、ブラックリスト流用（6）。受け入れ基準 :104-106 に (b) 抜け道なし・逆方向 401・不呼出検査を追加。r1 の直し方 1〜6 が全部入っている |
| B-2 守り手テストの実行条件が未定義 | **解消** | :103 で「app.routes 列挙／path param は 1 か固定 UUID／get_current_user を override しない／patch は _init_firebase・is_token_blacklisted→False・check_auth_rate_limit→False のみ／get_cached_jwt は patch しない」を固定。:166 守り手は「人手で守る（段1で test_viewer_isolation.py を作る）」→ check-process-artifacts.js:544 は「人手で守る」で実在検査をスキップ（【事実】origin/main の同ファイル :544-554） |
| N-1 テナント文脈 | **解消** | :72「テナント文脈は設定しない（_run_auto_distribution と同じ）」、:109 受け入れ基準に「テナント文脈なしで呼んだ」、:148 計画票 0 に products.tenant_id 分布の人間 SELECT |
| N-2 前例の参照先 | **解消** | :36・:71 で tcg_extraction.py:725-757 を前例に差し替え、dashboard.py は Redis/周期の前例として残置 |
| N-3 max_age_hours 未設定・再解析中 | **解消**（ただし B-3 で別の穴） | :75-77 で両方を明記 |
| N-4 抜けている基準 10 件 | **一部** | 1 逆方向(:105)、2 (b)抜け道(:104)、3 beat(:110)、4 失敗時前回値(:111)、5 3回失敗通知(:111)、6 honeypot/429(:112)、7 pending 掃除(:94,:113)、8 i18n(:114)、9 JS 上限 300KB(:85,:115)、10 /viewer/ 到達(:82,:116) — 10 件すべて記載あり。**ただし 10 の「nginx は変えなくてよい」は実物と食い違う（N-13）**。また 8 の「既存の CI（i18n チェック）」は実在する（frontend/package.json:28 check:i18n-missing-keys、frontend-check.yml:38 check:all 経由）ので可 |
| N-5 「## 継続」欄 | **解消** | :169-172 |
| N-6 ADR-1016 未起案 | **一部** | :6「本便で同梱して起案する」と宣言。しかし worktree にも origin/main にも docs/adr/ADR-1016* は無い（`ls docs/adr | grep 1016` 空、origin/main は ADR-1015 まで）。設計 PR に同梱されるまで「一部」 |
| N-7 列数 11/13/14 | **解消** | :27「13 列」、:178 Q1 に 13 列名を列挙し単価・数量・提供者を含むと明記。「原価」の語は消えた |
| N-8 ADR-1013 資格情報の流用不可 | **解消** | :49「流用できない。閲覧者用の表を別に作る」、:57「refresh は持たない。12 時間＋再ログイン」 |
| N-9 公開 signup の上限と掃除 | **解消** | :90 email 3回/h・IP 10回/h・429、:94 7 日で掃除、:112-113 基準 |
| N-10 rate_limit/session_guard の識別子 | **解消** | :53 sub "viewer:<id>"・email クレームなし。【事実】rate_limit.py:95-107 は email 無しなら IP バケット、session_guard.py:159-164 は token hash のみで email 不要 → 閲覧者トークンでも中断しない |
| N-11 3回失敗の通知経路 | **解消** | :79 send_discord_notification(tenant_id=4, event_type="tcg_distribution_error")、tcg_distribution_svc.py:1066-1081 |

--------------------------------------------------------------------
2. r2 で新しく書いた事実の照合（依頼 2）— すべて `git show origin/main:<path>`
--------------------------------------------------------------------
【事実】
| r2 の記述 | origin/main の実物 | 判定 |
|---|---|---|
| :51 「(d) の Firebase 検証で 401 になる（dependencies.py:187-198）」 | :187 `if self_tokens.peek_issuer(token) == self_tokens.ISSUER:` → :188 _authenticate_self_token。:191-198 Firebase verify_id_token、例外で record_auth_failure → 401 | **一致**。iss が "salesanchor-viewer" なら :187 は偽 → :192 で Firebase が失敗 → 401 |
| :82 「frontend/nginx.conf の `$uri/` で当たる」 | frontend/nginx.conf:23-25 `location / { try_files $uri $uri/ /index.html; }` | **一致**（`/viewer/` は `$uri/` で dist/viewer/ ディレクトリ → index.html）。ただし「nginx を変えなくてよい」は N-13・N-14 の理由で不正確 |
| :91 「IP は nginx が付ける X-Real-IP から取る」 | nginx/nginx.conf:102,115,135,157,231（backend への各 proxy）と :240（frontend）で `proxy_set_header X-Real-IP $remote_addr;` | **一致**。X-Forwarded-For は :103 等で `$proxy_add_x_forwarded_for`（クライアント送信値に追記）なので先頭要素は外部制御可。既存 backend は XFF 先頭を使っている（dependencies.py:69、rate_limit.py:54、session_guard.py:59、audit.py:66）→ r2 の選択は正しい。`set_real_ip_from` / `real_ip_header` は無し（grep 0 件） |
| :36 「beat の最短は 300 秒（celery_app.py:137）」 | :135-138 "review-mail-discord-notifier" schedule 300.0。全 schedule を grep: 300/600/900/1800 と crontab のみ | **一致** |
| :79 send_discord_notification(tenant_id=4, event_type=...) | backend/app/routers/notifications.py:108 `async def send_discord_notification(db: AsyncSession, tenant_id: int, event_type: str, title: str, message: str)`。呼び出し例 tcg_distribution_svc.py:1072-1081 | **一致**。注意: 第1引数 db（AsyncSession）が必須。Celery タスク側はセッションを持っていないと呼べない（D3 は tcg_extraction.py の型でセッションを作るので満たせるが、DB 自体が落ちている失敗では通知も失敗する。既存も同じ :1082-1083 で握りつぶし） |
| :36 tcg_extraction.py:725-757 の型 | :725-757 _run_auto_distribution、create_async_engine → async_sessionmaker → finally dispose | **一致** |
| :26 fetch_output_rows(:390-412)・テナント文脈を設定しない | :390-412。db.execute のみ | **一致** |
| :32 self_tokens.py:86-132 | :86-98 create_access_token、:101-107 peek_issuer、:110-132 decode_access_token（issuer=ISSUER、kid 照合） | **一致** |
| :22 ISSUER | self_tokens.py:22 `ISSUER = "salesanchor"` | **一致** |
| :114 「既存の CI（i18n チェック）」 | frontend/package.json:28 check:i18n-missing-keys、:46 check:all に含む、.github/workflows/frontend-check.yml:38 `npm run check:all` | **一致** |
| :118 `node scripts/check-ui-governance.js` | scripts/check-ui-governance.js 実在、.github/workflows/ui-governance-gate.yml:39 | **一致** |
| :166 「人手で守る」でゲート通過 | scripts/check-process-artifacts.js:544 `if (/人手で守る/.test(guardianValue))` → 実在検査スキップ | **一致** |
| :26 ADR-1014 の distribution_rows_sql | ADR-1014:12,14 に `distribution_rows_sql` | **一致** |
| :82 「Vite の入力に viewer/index.html を足す」 | frontend/vite.config.ts に rollupOptions.input は無し（grep 0 件） | 変更として妥当（現状は単一入力） |

--------------------------------------------------------------------
3. r2 の決定に対する新しい穴（依頼 3）
--------------------------------------------------------------------

### B-3【Blocking】D3「失敗時は前回の値を残す」と「Redis TTL 180 秒」が両立しない。キーが消えたときの GET /viewer/inventory の応答が未定義
- 根拠【事実】: design.md:73 TTL 180 秒、:76 max_age_hours 未設定時「値を更新せず前回の値を残す」、:78 失敗時「前回の値を残す。updated_at も変えない」、:66 「inventory は Redis の作り置きをそのまま返す。DB は読まない」。
- 何が起きるか【推測・仕組みから導出】: タスクが 3 回（180 秒）続けて失敗、または max_age_hours 未設定が 3 分続くと、TTL でキーが消える。D2 は DB を読まないので、閲覧者には何も返せない。受け入れ基準 :111 は mock で「値が変わらない」を見るだけなので、この状態を検出しない。
- また、max_age_hours 未設定時に「前回の値を残す」のは、アプリの /inventory が同じ条件で空を返す（r1 N-3、inventory_offers.py:323-328）のと食い違う。GAS 配信は止まる（tcg_distribution_svc.py:921-930）のに閲覧ページだけ古い表を出し続ける。
- 直し方（どちらかを D3 に書く）:
  (A) TTL を付けない（または 24 時間など「失敗が続いても消えない」長さ）。失敗時は値も TTL も触らない。「最終更新」が古いことで閲覧者に鮮度が伝わる。
  (B) TTL 180 のまま、キーが無いときの応答を決める（例: 503 と i18n の「準備中」表示）。
  加えて、max_age_hours 未設定時は「空の rows と updated_at を書く」（/inventory と同じ見え方）に揃えるか、「残す」を選ぶなら、その理由（GAS 配信と違う扱い）を 1 行書く。受け入れ基準に「キーが無い／TTL 切れのときの応答」の行を足す。

### N-12【Non-blocking・中】ログアウトのブラックリスト TTL が既定 3600 秒。12 時間トークンでは残り 11 時間が無効化されない
- 根拠【事実】: cache.py:141 `async def blacklist_token(token: str, ttl: int = 3600)`。design.md:56 「既存のブラックリストをそのまま使ってよい」、:57 寿命 12 時間。
- 直し方: D1-6 に「blacklist_token には exp までの残り秒数を ttl に渡す」と書く。受け入れ基準に「ログアウト後 2 時間（時刻固定）に同じトークンで inventory が 401」を足す。

### N-13【Non-blocking・中】D4「nginx は変えなくてよい」は不正確。/viewer/index.html が no-cache にならず、デプロイ後に古い index が残る
- 根拠【事実】: frontend/nginx.conf:7-12 は `location = /index.html` だけに `Cache-Control: no-cache, must-revalidate` を付け、理由を「デプロイ後にブラウザが必ず新しいアセット URL を参照できる」と書いている。`/viewer/` と `/viewer/index.html` は :23-25 の `location /` に落ち、Cache-Control ヘッダが付かない。:16-20 でハッシュ付き資産は 1 年 immutable。
- 影響【推測】: ブラウザの経験的キャッシュで古い /viewer/index.html が使われ、消えた旧ハッシュの JS を参照して白画面になる（本体の index.html がこの対策を入れた理由と同じ事故）。
- 直し方: D4 に「frontend/nginx.conf に `location = /viewer/index.html`（および `/viewer/`）へ同じ no-cache を足す」を書く。受け入れ基準に「GET /viewer/ の応答ヘッダに Cache-Control: no-cache がある」を足す（Playwright か curl）。

### N-14【Non-blocking・低】`/viewer`（末尾スラッシュ無し）の挙動
- 根拠【事実】: frontend/nginx.conf:1-5 は `listen 8080; server_name localhost;`、外側 nginx:239 は `proxy_set_header Host $host`。`try_files $uri $uri/` でディレクトリに当たると nginx は末尾 `/` 付きへ 301 を返す。
- 【推測】port_in_redirect が既定 on のため、Location が `https://app.salesanchor.jp:8080/viewer/` または `http://...` になり得る。実機で確認していない【未確認】。
- 直し方: 配布する URL を `/viewer/` 固定にし、受け入れ基準 :116 に「`/viewer`（スラッシュ無し）でも同じページに着く」を足して Playwright で判定する。落ちたら `port_in_redirect off; absolute_redirect off;` を D4 に加える。

### N-15【Non-blocking・中】閲覧者ログインの総当たり対策が D1/D5 に無い。nginx の login ゾーンは /api/v1/auth/ だけ
- 根拠【事実】: nginx/nginx.conf:6 `limit_req_zone ... zone=login rate=10r/m`、:96-98 は `location /api/v1/auth/` にのみ適用。`/api/v1/viewer/login` は `/api/` の zone=api 30r/s（:8）の側に入る。backend 側の既存部品: self_tokens.py:28-29 LOGIN_FAIL_LIMIT=10 / LOGIN_LOCK_DURATION=15 分、cache.py:292 check_auth_rate_limit(ip) / :309 record_auth_failure(ip)。design.md:64 は「方式は Q2 で決める」だけ。
- 直し方: Q2 の答えに関わらず「viewer/login と verify-email は check_auth_rate_limit / record_auth_failure を通し、email 単位の失敗回数は LOGIN_FAIL_LIMIT と同じ 10 回/15 分ロック」を D1 に書く。nginx 側は「`location /api/v1/viewer/login` に zone=login を足す」か「足さない理由」を D4/D5 に書く。

### N-16【Non-blocking・低】KPI「DB の読み取りは 1 分に 1 回で一定」と、D1「リクエストのたびに DB の状態と trial_expires_at を見る」が矛盾する
- 根拠【事実】: design.md:58 と :127。
- 直し方: KPI を「在庫の読み取りは 1 分に 1 回」に直す（閲覧者 1 人あたり 1 リクエスト 1 行の主キー検索は残る）。または状態を `viewer_jwt:` に短 TTL で置く（:55 の名前空間はこれのためにある）。どちらかを明記。

### N-17【Non-blocking・中】verify-email の確認トークンの作りが未定義
- 根拠【事実】: design.md:92 「確認メールを送る。verify-email が成功したら trial に変える」。トークンの生成（乱数長・DB にはハッシュだけ保存か）・有効期限・一回限りかが無い。:160 で ADR-097/126/127 を「署名トークン付き公開登録フォーム」の前例に挙げているが、どの作りを使うかを書いていない。
- 直し方: 「secrets.token_urlsafe(32)、DB には sha256 だけ、24 時間で失効、使用後に消す」の粒度で D5 に書く（ADR-1013 の password_reset_tokens と同じ型なら、その旨を書いて揃える）。

### N-18【Non-blocking・低】D2 の allowlist 4 本に logout が無いのに、D1-6 でログアウト（ブラックリスト）を使う
- 根拠【事実】: design.md:61-65 と :56。
- 直し方: POST /api/v1/viewer/logout を allowlist に足す（5 本）か、ログアウト機能を持たない（トークンは 12 時間で切れる）と書く。守り手テストの allowlist 集合に直結するので、曖昧にしない。

### N-19【Non-blocking・低】signup の応答で登録済み email の存在が分かる（列挙）
- 根拠【事実】: design.md:88-92 で email 一意（:47）だが、重複時の応答が未定義。
- 直し方: 「重複でも 200 を返し、既存の行には何もしない（メールも送らない、または『既に登録済み』メールを送る）」を D5 に 1 行書く。

### N-20【Non-blocking・低】X-Real-IP が有効なのは「外側 nginx が最前段」のときだけ
- 根拠【事実】: nginx/nginx.conf に set_real_ip_from が無い（grep 0 件）。app.salesanchor.jp は certbot（:58-60, :73-74）で直接 TLS 終端。
- 【未確認】Cloudflare 等のプロキシが DNS 上で前段にいるか。いる場合は $remote_addr が全部プロキシの IP になり、IP 10 回/h の制限が閲覧者全員で共有される。
- 直し方: 計画票 0 に「app.salesanchor.jp の DNS が proxied か（dig／Cloudflare GUI、PO 確認）」を足す。proxied なら `set_real_ip_from` ＋ `real_ip_header CF-Connecting-IP` を D4 に書く。

### 穴なしと判定した決定（根拠付き）
- iss・鍵・sub の分け方: get_current_user の 4 経路（dependencies.py:143-198）すべてで 401 に落ちる。(a) は環境変数一致のみ、(b) は `jwt:` を書かないので当たらない、(c) は iss 不一致、(d) は Firebase 失敗。逆方向は get_current_viewer が iss＋別鍵を要求するので app トークンは kid 不一致で JWTError。【事実】
- refresh なし 12 時間: 期限は毎リクエスト DB 参照（:58）で suspended を即時反映できる。N-12 だけ直せば可。
- Redis キー `viewer:inventory:v1`: 既存名前空間（jwt:/blacklist:/rate:/session_ip:）と衝突しない。【事実】cache.py・rate_limit.py・session_guard.py の grep。
- テナント文脈なし: GAS 配信と同条件（tcg_extraction.py:725-757 に SET app.tenant_id 無し）。差は計画票 0 で測る。可。
- rate_limit: 閲覧者トークンは email 無し → IP 単位 60 回/分（rate_limit.py:95-107）。ページ 1 回の読み込みで 1〜2 リクエストなので足りる。N-20 の共有 IP の場合のみ注意。
- 受け入れ基準: :103 の「全て 401」は r1【推測】のとおり dependency の 401 が path 検証より先に出る前提。最初の pytest 実行で確認すること（変更なし）。

--------------------------------------------------------------------
4. Q1〜Q8 の過不足（依頼 4）
--------------------------------------------------------------------
- Q1〜Q8 は r1 の Q1〜Q4 と §6 の Q5〜Q9 を取り込んでおり、Q9（単価・数量を見せ続けるか）は Q1 の文に統合済み。重複なし。
- 不足（追加を勧める）:
  - **Q9（新）**: 今の GAS を見ている既存の取引先を、申込なしで `active` として最初に登録するか（誰が・何件・どの email で）。Q3（切り替え操作の担当）と Q4（GAS 停止時期）の間に落ちている。初期データを migration で入れない方針（:46、memory shared_master_ssot_policy）なので、投入手段（管理 API か人間の SQL か）も同時に決める必要がある。
  - Q5 に 1 語足す: トライアル 14 日の起点を「本人確認の時刻」（:92 で設計が決めた）でよいか。PO が「申込日から」を想定している可能性がある。
- 過剰なし。Q8（置き場所）は N-13/N-14/N-20 の前提なので実装前に必要。

--------------------------------------------------------------------
5. 様式・その他【事実】
--------------------------------------------------------------------
- 受け入れ基準の表・検証方法の空欄なし・recon パス・外部事例欄・維持の仕組み・継続: すべてあり。
- 対象 ADR: ADR-1016 は未存在（N-6 一部）。check-process-artifacts.js:500 textHasAdrReference は設計書本文に ADR 番号があるかを見る。未存在 ADR の扱いは r1 と同じく【未確認】。
- design.md は worktree で未追跡（`??`）。コミット時に recon.md / security-recon.md と一緒に git add すること（CLAUDE.md）。
- worktree ブランチは origin/main より古い土台（`git diff origin/main --stat` で 41 files、8774 行の削除差）。設計 PR 起票前に main を取り込むこと（照合対象ファイルには差分が無いので設計内容への影響はない）。

--------------------------------------------------------------------
6. 推測・未確認の一覧
--------------------------------------------------------------------
【推測】B-3 の「3 分で消える」は TTL の仕組みからの導出。N-13 のブラウザ経験的キャッシュによる白画面。N-14 のリダイレクト先ホスト・ポート。
【未確認】/viewer のリダイレクト実機挙動。app.salesanchor.jp の前段プロキシ有無。check-process-artifacts.js が未存在 ADR 番号をどう扱うか。本番 SMTP（設計書の記載どおり）。

--------------------------------------------------------------------
7. 総括
--------------------------------------------------------------------
r1 の Blocking 2 件は設計書で固定され、実物（dependencies.py:187-198、self_tokens.py、cache.py、check-process-artifacts.js:544）と整合している。r2 で新たに書かれた事実（X-Real-IP、$uri/、300 秒、send_discord_notification の引数）も origin/main と一致した。
差し戻しは 1 点: D3 の「前回の値を残す」と TTL 180 秒が両立せず、キー消失時の閲覧 API の応答が未定義（B-3）。これは 2〜3 行の追記で解消できる。N-12（ブラックリスト TTL）・N-13（/viewer/index.html の no-cache）・N-15（閲覧者ログインの総当たり対策）・N-17（確認トークンの作り）は実装前に書いておかないと Generator が決めることになる粒度なので、同じ r3 で直すこと。残り（N-14/N-16/N-18/N-19/N-20、Q9 追加、ADR-1016 同梱）は同便で可。
```

---

```text
# Architect 設計審査 r3 — 在庫の閲覧専用ページ（gas-viewer-fresh-fast）

対象: /Users/tanizawashingo/worktrees/salesanchor/release-gas-viewer-fresh-fast/docs/handoff/gas-viewer-fresh-fast/design.md（r3、205 行、2026-10-15。worktree では未コミット = `??`）
前回: /tmp/CC報告ファイル/viewer_design_review_r2.txt（r2 REVISE、B-3、N-12〜N-20）
照合基準: origin/main = f005b623fe2a68a3035f7fd51c692a7c44b23fea（git fetch origin 後。r2 と同じコミット）
生の照合出力（`git show origin/main:<path> | cat -n` の全文）: /tmp/CC報告ファイル/viewer_design_review_r3/
  cache.txt（backend/app/cache.py 359 行）／ self_tokens.txt（247 行）／ nginx_nginx.txt（nginx/nginx.conf 487 行）／ inventory_offers.txt（636 行）／ frontend_nginx.txt（26 行）／ dependencies.txt ／ auth_router.txt（backend/app/routers/auth.py 478 行）／ rate_limit.txt ／ tcg_distribution_svc.txt
読み取りのみ。編集・commit・push は行っていない。

====================================================================
判定: REVISE
Blocking: 1 件（新規 B-4）／ Non-blocking: 7 件（新規 N-21〜N-27）
r2 指摘の解消状況: B-3 解消 ／ N-12〜N-20 解消 9（うち N-15・N-18 は解消したが派生の穴あり → N-21・N-22）
段の着手可否（依頼 4）: 段 0・段 2 は Q2〜Q9 未決のまま着手可。段 1 は Q2・Q5 待ち（列の確定）。段 3 は Q8（＋ログイン画面は Q2）待ち。段 4 は Q2・Q3・Q5・Q6・Q7・Q9 待ち。
====================================================================

--------------------------------------------------------------------
1. B-3・N-12〜N-20 の解消判定（依頼 1）
--------------------------------------------------------------------
| 指摘 | 判定 | 根拠（design.md r3 の行）と補足 |
|---|---|---|
| B-3 TTL 180 秒と「前回の値を残す」が両立しない。キー消失時の応答が未定義 | **解消** | :75 TTL 24 時間、:76 キー無しは 503＋i18n「準備中です」、:79 max_age_hours 未設定は空 rows を書く（inventory_offers.py:323-328 に揃えた）、:81 失敗時は値も updated_at も TTL も変えない、:125 受け入れ基準に「キー無し→503」「未設定→空 rows」。r2 の直し方 (A)＋未設定時の揃え、の両方が入った。派生の穴は §3-(1) |
| N-12 ブラックリスト TTL 既定 3600 秒 | **解消** | :56「exp までの残りの秒数を必ず渡す」、:126「2 時間進めても 401」。cache.py:141 と一致（§2） |
| N-13 /viewer/index.html が no-cache にならない | **解消** | :86 `location = /viewer/index.html` と `location = /viewer/` に同じ Cache-Control、:130 受け入れ基準（curl）。【事実】frontend/nginx.conf:9-12 と同型 |
| N-14 `/viewer`（スラッシュ無し） | **解消** | :87 配布 URL を `/viewer/` 固定、Playwright で確認、落ちたら `port_in_redirect off; absolute_redirect off;`。:130 受け入れ基準 |
| N-15 閲覧者ログインの総当たり対策 | **解消（派生 N-21・N-22）** | :58 check_auth_rate_limit／record_auth_failure を通す、email 単位 10 回／15 分、nginx login ゾーンを login と verify-email に当てる。:127 受け入れ基準。ただし email 単位ロックの置き場（列）が D1 に無い（N-21）、nginx の location の書き方が prefix のままだと inventory まで 10r/m になる（N-22） |
| N-16 KPI「DB 読み取り 1 分 1 回」と毎リクエスト DB 参照の矛盾 | **解消** | :141「在庫の読み取りは 1 分に 1 回」「閲覧者の状態の確認（主キー 1 行）はリクエストのたび」 |
| N-17 確認トークンの作り | **解消** | :100 token_urlsafe(32)・sha256 だけ保存・24 時間・一度きり。【事実】ADR-1013 の前例 auth.py:398-404（token_urlsafe(32)、_hash_token=sha256、expires_at）・:432-438（used_at IS NULL AND expires_at > now で 1 回限り）と同じ型。差: 前例は used_at を立てる、設計は「消す」。どちらでも可（§3-(4)） |
| N-18 allowlist 4 本に logout が無い | **解消（派生 N-23）** | :62-67 で 5 本に固定。ただし受け入れ基準 :111 が「allowlist の4本を除く」のまま → 守り手テストの集合がズレる（N-23） |
| N-19 signup の email 列挙 | **解消（派生 B-4）** | :98 登録済みでも同じ 200、行に触らない、メールも送らない。ただし pending の行に対しても「何もしない」ため、確認トークン失効後に 7 日間詰む（B-4） |
| N-20 前段プロキシ | **解消** | :162 計画票 0 ④（DNS が proxied か PO 確認、いるなら set_real_ip_from／real_ip_header） |

r1 からの持ち越し: N-6 ADR-1016 は worktree にも origin/main にも無い（`ls docs/adr | grep 1016` 空）。:6「本便で同梱」の宣言のまま。設計 PR に同梱されるまで「一部」。

--------------------------------------------------------------------
2. r3 で新しく書いた事実の照合（依頼 2）— すべて `git show origin/main:<path>`
--------------------------------------------------------------------
【事実】
| r3 の記述 | origin/main の実物 | 判定 |
|---|---|---|
| :56 「blacklist_token の ttl の既定値は 3600 秒（cache.py:141）」 | backend/app/cache.py:141 `async def blacklist_token(token: str, ttl: int = 3600) -> bool:`。:155 `setex(f"blacklist:{token_h}", ttl, "1")`、:156 `delete(f"jwt:{token_h}")`。:146 Docstring「False - Redis未接続または書き込み失敗（呼び出し元で503を返すこと）」 | **一致**。補足: 戻り値 False のときの logout の応答（503）が設計に無い（N-24）。パスは backend/app/auth/cache.py ではなく backend/app/cache.py（設計は「cache.py」とだけ書いているので誤りではないが、Generator 向けにフルパスを書くとよい） |
| :58 「check_auth_rate_limit と record_auth_failure（cache.py:292、:309）」 | :292 `async def check_auth_rate_limit(ip: str) -> bool`（:301 キー `auth_fail_ip:<sha256(ip)[:16]>`、:303 `>= AUTH_FAIL_MAX`=10、:295 Redis 不通は fail-open）。:309 `async def record_auth_failure(ip: str) -> None`（:316 incr、:318 expire 900 秒） | **一致**。補足: どちらも **IP 単位だけ**。email 単位の回数はこの部品では数えられない（N-21） |
| :58 「LOGIN_FAIL_LIMIT と同じ 10 回失敗で 15 分ロック（self_tokens.py:28-29）」 | self_tokens.py:28 `LOGIN_FAIL_LIMIT = 10`、:29 `LOGIN_LOCK_DURATION = timedelta(minutes=15)` | **一致**。補足: この定数を使う実装は auth.py:263-278 で、`public.users.failed_login_count` / `locked_until` の 2 列に書く（:266、:275）。viewer_accounts の列（:47）にこの 2 列が無い（N-21） |
| :58 「nginx の login ゾーン（10r/m）… nginx/nginx.conf:96-98 と同じ書き方」 | :6 `limit_req_zone $binary_remote_addr zone=login:10m rate=10r/m;`、:96 `location /api/v1/auth/ {`、:97 `limit_req zone=login burst=5 nodelay;`、:98 `limit_req_status 429;` | **一致**。補足: :96 は **prefix 一致**。同じ書き方で `location /api/v1/viewer/` と書くと inventory と logout も 10r/m に入る（N-22）。`$binary_remote_addr` なのでヘッダ偽装は効かない |
| :79 「アプリの /inventory が同じ条件で空を返す（inventory_offers.py:323-328）」 | :322 `settings = await load_distribution_settings(db)`、:323 `max_age_hours = _max_age_hours(settings)`、:324 `if max_age_hours is None:`、:325-328 `InventoryListResponse(items=[], total=0, ..., window_hours=None, ...)` | **一致**。補足: GAS 配信側も同条件で止まる（tcg_distribution_svc.py:921-930）。3 者が揃う |
| :69 「fetch_output_rows の 14 列から Ship_JA を除いたもの」 | tcg_distribution_svc.py:47-62 DIST_HEADERS 14 個（投稿日時, Mark, Japanese Title, English Title, Condition, Unit Price, Quantity, Note_JA, Status, Release Date, Series, 提供者, Search Keywords, Ship_JA）、:251-254 _GAS_COLUMNS 14 個、:412 で _GAS_COLUMNS 順に返す | **一致**（集合として）。設計 :69 の列挙順は「提供者・Series」、実物は「Series・提供者」。キー集合で検査する（:116）ので影響なし。Generator が JSON のキー名に何を使うか（日本語ヘッダか _GAS_COLUMNS の英字か）は未指定（N-25） |
| :100 確認トークンの作り | auth.py:398 `secrets.token_urlsafe(32)`、:404 `self_tokens._hash_token(raw)`＝self_tokens.py:141-142 `hashlib.sha256(raw.encode()).digest()`、:342 `PASSWORD_RESET_TTL = timedelta(minutes=30)`、:432-438 1 回限り | **前例と同型**。TTL は前例 30 分・設計 24 時間（用途が違うので差があってよい） |

--------------------------------------------------------------------
3. r3 の決定に対する新しい穴（依頼 3）
--------------------------------------------------------------------

### B-4【Blocking】N-19 の直し方と「確認トークン 24 時間失効」「pending 掃除 7 日」が組み合わさると、確認を逃した申込者は 7 日間やり直せない
- 根拠【事実】: design.md:98「すでに登録されている email で申し込まれても…既存の行には何もしない。メールも送らない」、:100「24時間で失効し、一度使ったら消す」、:102「7日たった pending の行は…消す」。再送の入口（resend）は allowlist :62-67 に無い。
- 何が起きるか【推測・仕組みから導出】: 申込 → 確認メールが迷惑メールに入る → 25 時間後に気付いて verify-email → 失効で失敗 → もう一度 signup → :98 により行にもメールにも触らない → 8 日目まで何もできない。KGI 3「閲覧者はフォームで申し込む」の導線が、ごく普通の遅れで止まる。
- 直し方（D5 に 2 行）: 「既存の行が **pending** のときは、古いトークンを無効化して新しい確認メールを送る（email 3 回/h の制限の内側）。trial／active／suspended のときは何もしない。応答はどの場合も同じ 200」。これなら列挙対策（応答は同じ・メールは本人の受信箱にしか届かない）は保てる。受け入れ基準に「pending の email で再 signup すると新しいトークンのメールが送られ、古いトークンは使えない」を足す。

### N-21【Non-blocking・中】email 単位のロック（10 回／15 分）の置き場が D1 に無い。既存部品は IP 単位しか数えない
- 根拠【事実】: cache.py:292-320 は IP 単位（`auth_fail_ip:`）だけ。self_tokens.py:28-29 の定数を使う既存実装は auth.py:263-278 で `public.users.failed_login_count` / `locked_until` に書く。design.md:47 の viewer_accounts の列に相当する 2 列が無い。
- 直し方: :47 の列に `failed_login_count`・`locked_until` を足す（Q2 がパスワード方式のとき必須。マジックリンク方式でも verify-email の失敗回数の置き場として使える）。または「email 単位は Redis キー `viewer_login_fail:<sha256(email)>` で数える」と決める。どちらかを D1 に書く。

### N-22【Non-blocking・中】nginx の login ゾーンを「:96-98 と同じ書き方」にすると、prefix 一致で inventory・logout まで 10r/m に入る
- 根拠【事実】: nginx/nginx.conf:96 `location /api/v1/auth/ {` は prefix 一致。:6 のゾーンは `$binary_remote_addr` 単位で 10r/m、burst=5。閲覧ページは 1 回の読み込みで inventory を 1〜2 回叩く（r2 §3）。同じ事務所（同一 IP）で数人が開くと、`location /api/v1/viewer/` と書いた場合に 429 になる。
- 直し方: D1-8／D4 を「`location = /api/v1/viewer/login` と `location = /api/v1/viewer/verify-email` の **完全一致**（`=`）で 2 ブロック」と書く。既存の完全一致の前例は :112 `location = /api/v1/conversations/stream`。受け入れ基準に「GET /api/v1/viewer/inventory を 1 分に 20 回叩いても 429 にならない（Evaluator curl）」を足す。

### N-23【Non-blocking・中】受け入れ基準 :111 が「allowlist の4本を除く」のまま。D2 :62 の 5 本とズレている
- 根拠【事実】: design.md:62「次の5本だけ」、:111「allowlist の4本を除く」。
- 直し方: :111 を「5本」に直す。守り手テストの allowlist 集合は D2 の 5 本を 1 か所の定数にして、テストと router の両方がそれを参照する（集合を 2 か所に書かない）と 1 行足す。

### N-24【Non-blocking・低】logout で blacklist_token が False を返したときの応答が無い
- 根拠【事実】: cache.py:146「False - Redis未接続または書き込み失敗（呼び出し元で503を返すこと）」。design.md:56・:66 は成功時しか書いていない。
- 直し方: D2 の logout に「blacklist_token が False なら 503（既存 auth と同じ）」を 1 行。受け入れ基準に「Redis 不通時の logout は 503」（mock）。

### N-25【Non-blocking・低】inventory の JSON のキー名が未指定（日本語ヘッダか _GAS_COLUMNS の英字か）
- 根拠【事実】: design.md:69 は列名を日本語ヘッダ（DIST_HEADERS 相当）で列挙。:116 は「キーの集合が完全に一致」。tcg_distribution_svc.py:412 は _GAS_COLUMNS（posted_at, mark, …）の順の **リスト** を返し、辞書ではない。
- 直し方: 「キーは _GAS_COLUMNS の英字 13 個（ship_ja を除く）。表示名は i18n で付ける」と書く（JSON を英字キーにすれば ja/en の表示名切替が :90 の i18n と整合する）。受け入れ基準の集合をその 13 個で固定する。

### N-26【Non-blocking・中】「3 回続けて失敗」の回数の置き場が無い。Celery worker は --concurrency=2 なので、プロセス内の変数では数えられない
- 根拠【事実】: docker-compose.yml:209 `celery -A app.celery_app worker --loglevel=info --concurrency=2`（既定 pool=prefork → 2 プロセス）。design.md:82 は通知の経路だけで、回数の保持先を書いていない。:119 の受け入れ基準は mock なので、プロセス内変数でも通ってしまう。
- 直し方: 「失敗回数は Redis キー `viewer:inventory:fail_count` に incr で持ち、成功（空 rows の書き込みを含む）で 0 に戻す。通知は 3 回目に 1 回だけ送り、以後は回復するまで送らない（毎分の再通知をしない）」を D3 に書く。あわせて「タスクが **走らない**（worker 停止）場合は失敗が数えられず通知が出ない」ので、§継続の監視に「updated_at の経過時間が 10 分を超えたら知らせる」を 1 行足す（経路は既存のどれでも可。無ければ次便）。

### N-27【Non-blocking・低】login／verify-email で check_auth_rate_limit に渡す IP の取り方が未指定。既存の _get_client_ip は X-Forwarded-For の先頭（外から偽装可）
- 根拠【事実】: dependencies.py:67-72 と auth.py:241（`_get_client_ip`）は `X-Forwarded-For` の先頭要素を使う。nginx は :103 `$proxy_add_x_forwarded_for` でクライアント送信値に追記するので、先頭は外部制御可。design.md:97 は **signup だけ** X-Real-IP と書いている。
- 直し方: D1-8 に「IP は D5 と同じく X-Real-IP から取る」を 1 行。nginx 側の `$binary_remote_addr` ゾーン（N-22）が真の IP で効くので、二重になる。既存 auth と同じ弱さを閲覧者側に持ち込まないための記述。

### 穴なしと判定した決定（根拠付き）
- **TTL 24 時間と 503**: 失敗が続いても 24 時間は前回値が残り、「最終更新」で鮮度が伝わる（:75）。24 時間失敗し続ければキーが消えて 503 になるが、:76 で応答が決まっており未定義ではない。成功のたびに setex で TTL が延びる前提（:81「失敗時は TTL を変えない」＝成功時は書き直す）は自明なので可。Redis 再起動直後の 503 は次の beat（最長 60 秒）で解消する。N-26 の監視だけ足せばよい。【事実＋仕組みからの導出】
- **max_age_hours 未設定時に空を書く**: inventory_offers.py:324-328（アプリ）・tcg_distribution_svc.py:922-930（GAS 配信）と同じ条件・同じ見え方。空の書き込みは「成功」として扱う（N-26 で明記を勧める）。updated_at が進むので「準備中」と誤認しない。可。
- **logout を足して 5 本**: ブラックリストは拒否側の仕組みで、`blacklist:<token hash>` の名前空間をアプリと共有しても、ハッシュが衝突しない限り互いに影響しない。cache.py:156 の `jwt:` 削除は閲覧者側では存在しないキーを消すだけで無害。N-23・N-24 の記述を足せば可。
- **確認トークンの作り**: ADR-1013 の前例（auth.py:398-404、:432-438）と同型。256 ビット乱数なので総当たりは現実的でなく、verify-email に login ゾーン（10r/m）と record_auth_failure を当てる（:58）ので、推測攻撃の入口も塞がる。「消す」と「used_at を立てる」の差は、前例に揃えて used_at（監査の痕跡が残る）を勧めるが、Blocking ではない。B-4（再送）だけが欠けている。
- **総当たり対策の構造**: nginx（真 IP・10r/m）→ backend IP 単位（10 回／15 分、fail-open）→ email 単位（10 回／15 分ロック）の 3 層。N-21（置き場）・N-27（IP の取り方）を書けば、既存 auth（auth.py:241-281）と同じ強さになる。

--------------------------------------------------------------------
4. Q2〜Q9 が未決でも設計として合格にできるか（依頼 4）
--------------------------------------------------------------------
結論: **設計の骨（トークン分離・allowlist・SSOT の作り置き・閲覧ページの置き方）は Q2〜Q9 に依存しない**ので、B-4 と N-21〜N-27 を r4 で直せば、Q2〜Q9 が未決のまま APPROVE にできる。ただし各段の着手は次の表のとおり止まる。

| 未決 | 内容 | 止める段 | 理由【事実: design.md の行】 |
|---|---|---|---|
| Q2 | ログイン方法・申込項目 | **段 1**（migration の列）・**段 3**（ログイン画面）・**段 4** | :49「資格情報の列や表は Q2 の答えで決める」。段 1 の migration を Q2 抜きで切ると、後で列追加の migration がもう 1 本要る（ADR-135 で migrations は PO GO 待ち）。段 1 のトークン発行・守り手テストそのものは Q2 に依存しない（テストでは行を直接作って署名すればよい）ので、「migration を除く段 1」は着手可 |
| Q3 | active 切替・停止の操作主 | **段 4** のみ | :103 |
| Q4 | GAS 停止時期 | 止めない（リリース後） | :195、§継続 |
| Q5 | 自動トライアルか人の承認か・起点日 | **段 1**（状態の enum）・**段 4** | :47 の状態は pending／trial／active／suspended の 4 値。人の承認を挟むなら「確認済み・承認待ち」の 5 値目が要り、migration に戻る。Q5 を待てないなら「状態は 5 値（verified を含む）で切り、自動の場合は verified を経由せず trial へ」と設計で先に決めれば、段 1 は Q5 を待たずに進める |
| Q6 | 同じ会社の再トライアル | **段 4** のみ（未決なら「認める＝検出しない」が既定） | :197 |
| Q7 | 個人情報の保存期間・削除・LP の文言 | **段 4** と本番公開 | :153、:198。段 1〜3 は止めない |
| Q8 | 置き場所 app.salesanchor.jp/viewer/ | **段 3**（Vite 入力・nginx location・配布 URL）と段 0 ④（DNS） | :85-87、:162。段 1・2 は止めない |
| Q9 | 既存取引先の初期登録 | **段 4**（管理の操作の有無）とリリース判断 | :200 |

- 今すぐ着手できる段: **段 0**（SMTP・所要時間・tenant_id 分布・DNS）と **段 2**（D2・D3。ただし login の 1 本は Q2 待ちなので、段 2 は signup／verify-email／login を除く logout・inventory・作り置きタスクまで）。
- Q2 と Q5 の 2 つだけ先に決まれば、段 1 の migration を 1 本で切れる。PO に聞く順番は Q2 → Q5 → Q8 → 残り、を勧める（:190「1つずつ聞く」の順を入れ替える提案）。

--------------------------------------------------------------------
5. 様式・その他【事実】
--------------------------------------------------------------------
- 受け入れ基準の表・検証方法の空欄なし・recon パス・外部事例欄・維持の仕組み・継続: すべてあり。
- ADR-1016: worktree・origin/main とも未存在（N-6 一部のまま）。
- design.md・recon.md・security-recon.md は worktree で未追跡（`git status --short` = `?? docs/handoff/gas-viewer-fresh-fast/`）。コミット時に 3 つとも git add すること。
- worktree ブランチ HEAD 0fd56307e は origin/main より 30 コミット古い（`git rev-list --count HEAD..origin/main` = 30、逆は 0）。照合対象ファイルは r2 で差分なしを確認済み（同じ origin/main コミット）なので設計内容への影響はないが、設計 PR 起票前に main を取り込むこと。

--------------------------------------------------------------------
6. 推測・未確認の一覧
--------------------------------------------------------------------
【推測】B-4 の「迷惑メール→25 時間後」のシナリオは利用者行動の想定。N-22 の「同一 IP で数人が 429」は 10r/m・burst=5 からの導出。N-26 の「プロセス内変数では数えられない」は prefork 2 プロセスからの導出（pool 指定が無いので既定 prefork と判断）。
【未確認】/viewer のリダイレクト実機挙動（r2 N-14 と同じ）。app.salesanchor.jp の前段プロキシ有無。本番 SMTP。check-process-artifacts.js が未存在 ADR 番号をどう扱うか。GAS 側 ALLOWED_HEADERS の実物（リポジトリ外）。

--------------------------------------------------------------------
7. 総括
--------------------------------------------------------------------
r2 の Blocking（B-3）は TTL 24 時間・503・空 rows の 3 点で解消し、N-12〜N-20 もすべて本文に入った。r3 で新しく引用した事実（cache.py:141／:292／:309、self_tokens.py:28-29、nginx.conf:96-98、inventory_offers.py:323-328、14 列−Ship_JA）は origin/main と一致した。
差し戻しは 1 点: N-19 の「登録済みは何もしない」が pending にも効くため、確認トークン失効後に 7 日間やり直せない（B-4）。D5 に 2 行足せば解消する。
同じ r4 で直すべき粒度（Generator に決めさせない）: N-21（email ロックの置き場）、N-22（nginx は完全一致）、N-23（受け入れ基準 4 本→5 本）、N-26（失敗回数の置き場と通知 1 回）。N-24・N-25・N-27 は 1 行ずつ。
Q2〜Q9 は設計の骨を止めない。段 0 と段 2（login 除く）は今から着手できる。段 1 の migration は Q2・Q5 を先に決めるか、状態を 5 値で切ると決めれば進められる。
```

---

```text
# Architect 設計審査 r4 — 在庫の閲覧専用ページ（gas-viewer-fresh-fast）

対象: /Users/tanizawashingo/worktrees/salesanchor/release-gas-viewer-fresh-fast/docs/handoff/gas-viewer-fresh-fast/design.md（r4、218 行、2026-10-15。worktree では未コミット = `??`）
前回: /tmp/CC報告ファイル/viewer_design_review_r3.txt（r3 REVISE、B-4、N-21〜N-27）
照合基準: origin/main = f005b623fe2a68a3035f7fd51c692a7c44b23fea（r2・r3 と同じ）。生の照合出力は r3 の /tmp/CC報告ファイル/viewer_design_review_r3/ を再利用（r4 で新しく引用された行はすべて r3 で取得済みの範囲）。
読み取りのみ。編集・commit・push は行っていない。

====================================================================
判定: REVISE
Blocking: 1 件（新規 B-5。リンクのトークン交換を GET で行うと、メールのリンク検査（Safe Links 等）が 1 回限りのトークンを先に消費する。交換の入口と方法を設計で固定する必要がある）
Non-blocking: 6 件（N-28〜N-33）
r3 指摘の解消状況: B-4 解消 ／ N-21 一部（意味が変わった。N-28）／ N-22〜N-27 解消 6
PO 条件（Q2a）の 4 点: 未登録に送らない=満たす ／ 15 分・1 回=満たす ／ 転送=15 分・未使用の間は防げない（残余リスクを本文に明記すべき。N-29）／ suspended 即時=満たす（状態をキャッシュしない旨を 1 行足す。N-30）
====================================================================

--------------------------------------------------------------------
1. B-4・N-21〜N-27 の解消判定（依頼 1）
--------------------------------------------------------------------
| 指摘 | 判定 | 根拠（design.md r4 の行）と補足 |
|---|---|---|
| B-4 pending の再 signup で 7 日間詰む | **解消** | :104「行が pending なら、古い確認トークンを無効にして新しい確認メールを送る」「verified・trial・active・suspended なら何もしない」。:126 受け入れ基準。応答は同じ 200（列挙対策も維持） |
| N-21 email 単位ロックの置き場 | **一部** | :62 Redis `viewer_login_fail:<sha256(email)>` で 10 回／15 分、login のメール送信は email 3 回／h。置き場は決まった。ただし Q2a でパスワードが無くなったため「login の失敗」が何を指すか決まっていない（N-28） |
| N-22 nginx は完全一致 | **解消** | :62 `location = /api/v1/viewer/login` と `= /api/v1/viewer/verify-email` の 2 ブロック、前方一致は使わない。前例 nginx/nginx.conf:112（【事実】`location = /api/v1/conversations/stream`）。:127 受け入れ基準「1 分に 20 回で 429 にならない」。交換の入口を別パスにするなら（§3 の案 C）3 ブロック目が要る |
| N-23 受け入れ基準 4 本→5 本 | **解消** | :117「VIEWER_ROUTE_ALLOWLIST の5本」、:71 定数 1 か所。様式: :71 の箇条書きが logout と inventory の間に挟まり、inventory（:72）が allowlist の列挙から切れて見える。:71 を :72 の後ろへ移すこと（意味は通るので Non-blocking 扱いにせず、ここに記す） |
| N-24 logout の 503 | **解消** | :70、:128。cache.py:146 と一致 |
| N-25 JSON のキー名 | **解消** | :74 _GAS_COLUMNS の英字 13 個（ship_ja 除く）、表示名は i18n。【事実】tcg_distribution_svc.py:251-254 |
| N-26 失敗回数の置き場・通知 1 回・worker 停止の監視 | **解消** | :87 Redis `viewer:inventory:fail_count`、成功（空 rows 含む）で 0、docker-compose.yml:209 の 2 プロセス（【事実】一致）。:88 3 回目に 1 回だけ。:125 受け入れ基準「4 回目では呼ばれない」。:197 updated_at 10 分超の監視 |
| N-27 login の IP の取り方 | **解消** | :62「X-Real-IP から取る。既存の _get_client_ip は使わない」 |

持ち越し: N-6 ADR-1016 未存在（変わらず）。design.md は未追跡 `??`（変わらず）。

--------------------------------------------------------------------
2. マジックリンクが PO 条件を仕組みとして満たすか（依頼 2）
--------------------------------------------------------------------
PO 条件【事実: :49】「リンクを知っていれば誰でも見られる形にはしない。登録フォームに入力した情報で管理する」。

| 観点 | 判定 | 根拠と補足 |
|---|---|---|
| 登録されていない email にリンクを送らない | **満たす** | :50 送るのは viewer_accounts に登録済みで trial か active だけ。未登録・pending・suspended は送らず、応答は同じ 200。:139 受け入れ基準（メール送信を mock）。補足: verified（承認待ち）も送らない対象に入るが :50 の列挙に無い。また trial で trial_expires_at を過ぎた行にも :50 のままだと送る → 交換まで通ってから inventory が 403 になる（N-31） |
| 15 分で切れ、1 回しか使えない | **満たす** | :51 token_urlsafe(32)・sha256 だけ保存・15 分・一度使ったら消す。:140 受け入れ基準（2 回目は 401）。前例 auth.py:398-404・:432-438（r3 §2 で照合済み）と同型。補足: 「毎回新しく作る」が「前の未使用トークンを無効化する」を含むか書いていない。前例（auth.py:391-396）は発行時に未使用の旧トークンを used_at で潰す。email 3 回／h なので最大 3 本の有効リンクが同時に存在し得る（N-32） |
| 転送されたリンクの扱い | **15 分・未使用の間は防げない。残余リスクとして明記が要る（N-29）** | :51 は「使い終わった後や 15 分を過ぎた後には開けない」としか書いていない。裏返すと、本人が押す前に転送先が押せば転送先がログインできる（本人は「使用済み」で気付く）。これは PO 条件の「リンクを知っていれば誰でも見られる」の **15 分版** であり、仕組みで完全には塞げない。塞ぐ度合いを上げる手は 2 つ: (a) login 要求時にブラウザへ nonce の cookie（HttpOnly・SameSite=Lax・Path=/api/v1/viewer）を置き、交換時に一致を要求する＝「要求したブラウザでしか開けない」。ただし同じ人が PC で要求しスマホのメールで押す使い方が落ちる。(b) 交換時に email の再入力を求める。登録情報（email）を知らない転送先は入れない＝PO 条件「登録フォームの情報で管理する」に文字どおり沿う。どちらを採るか、または「15 分・1 回で十分」と PO が判断するかを Q2c として PO に聞くこと。設計側の既定案は (b) を勧める（PC→スマホの使い方を壊さず、実装は 1 項目の比較で済む） |
| suspended にしたら即時に止まる | **満たす** | :52・:63 毎リクエストで DB の状態を読む、:141 受け入れ基準「発行済みの 12 時間トークンでも 403」。補足: D1-5「キャッシュが要るときは viewer_jwt: を使う」が残っているので、Generator が状態をキャッシュすると即時性が崩れる。「アカウントの状態はキャッシュしない」を 1 行足す（N-30） |

--------------------------------------------------------------------
3. 新しい穴（依頼 3）
--------------------------------------------------------------------

### B-5【Blocking】リンクを押したときのトークン交換を「どの入口で・どの method で・トークンをどこに載せて」行うかが未定。GET で交換すると、メールのリンク検査が 1 回限りのトークンを先に消費し、本人が開けない
- 根拠【事実】: :69「verify-email と同じ入口で purpose によって分けるか、login に含める。どちらにしても入口の数は5本を超えない」（未決のまま）。:51 一度使ったら消す。:106 確認トークンも同じく一度きり。前例 auth.py:407 は `/reset-password?token=<raw>` のクエリでトークンを渡し、frontend は searchParams で読み（RegisterPage.tsx:82 等）、確定は POST /password-reset/confirm（auth.py:412-416）で行う＝**GET では消費しない**作り。
- 何が起きるか【推測・一般に知られた挙動】: Microsoft Defender Safe Links や Gmail のリンク先取得のような検査は、メール到着時にリンクを GET する。交換を GET で（例: `/api/v1/viewer/login?token=...` を直接リンクにして）行うと、検査が先にトークンを使い、本人が押したときには「使用済み」になる。verify-email の確認リンクも同じ。既存の reset は POST 確定なので問題が出ていないが、閲覧者側は設計で固定しないと Generator が GET で作り得る。
- 直し方（設計に書く。案は 3 つ、推奨は C）:
  - **共通の必須事項**（どの案でも）: ①リンク先は閲覧ページ `/viewer/#login=<raw>`（フラグメント。サーバーに送られないので nginx のアクセスログに残らない。nginx/nginx.conf・frontend/nginx.conf に log_format／access_log の指定は無く【事実: grep 0 件】、既定の combined 形式はクエリ文字列を含む $request を記録する）。②ページの JS が **POST** でトークンを本文に入れて交換する。GET では一切消費しない。③成功時の 12 時間トークンは JSON 本文で返し、URL には絶対に載せない。保管先（memory／sessionStorage／localStorage）も明記する（既存は firebase-auth.ts:47,77 で localStorage）。④確認リンク（verify-email）も同じく `/viewer/#verify=<raw>` → POST。受け入れ基準に「リンク先を GET してもトークンは消費されない（2 回 GET の後に POST で成功する）」を足す。
  - **案 A: login に含める**（本文 `{"email": …}` なら送信、`{"token": …}` なら交換）。入口は 5 本のまま。欠点: 1 つの入口に 2 つの挙動が同居し、回数制限（email 3 回／h と、IP 単位の失敗ロック）とテストが入り組む。
  - **案 B: verify-email で purpose を分ける**（purpose=verify_email なら状態遷移、purpose=login なら 12 時間トークン発行）。入口は 5 本のまま。欠点: 「メール確認」の入口がセッションを返すことになり、名前と挙動が食い違う。Q5 で人の承認を挟む場合、verify_email はトークンを返してはならず、分岐が増える。
  - **案 C（推奨）: 6 本目 `POST /api/v1/viewer/session` を足す**（本文 `{"token": …}`、応答 12 時間トークン）。「5 本」は KGI ではなく設計が自分で置いた数で、VIEWER_ROUTE_ALLOWLIST（:71）はまさに「足すときは明示的に」のためにある。login=送信だけ、verify-email=状態遷移だけ、session=交換だけ、と 1 入口 1 挙動になり、nginx の完全一致ブロックを `= /api/v1/viewer/session` に 1 つ足せば login ゾーン（10r/m）と check_auth_rate_limit／record_auth_failure を交換だけに正確に当てられる。:155「74 本から 4 本」は「6 本」に直す。
  - 任意（UX）: verify-email 成功で状態が trial になった場合に限り、その場で 12 時間トークンも返す（確認メール→ログインメールの 2 通を 1 通にする）。Q5 が「人の承認」のときは返さない。採るなら受け入れ基準に 1 行。

### N-28【Non-blocking・中】Q2a でパスワードが無くなったため、「login に 11 回失敗でロック」（:136）と `viewer_login_fail:<email>`（:62）の意味が定まらない
- 根拠【事実】: :69 login は「email を受け取り、リンクを送る。応答は常に 200」。失敗という状態が無い。交換（B-5 の入口）に来る無効トークンは email を伴わないので、email 単位では数えられない。
- 直し方: 「email 単位の失敗ロック」を捨て、①リンク送信は email 3 回／h（:62 後半）、②交換と verify-email の無効トークンは **IP 単位** の check_auth_rate_limit／record_auth_failure（10 回／15 分）、の 2 つに整理する。:136 を「無効なトークンで交換に 10 回失敗した IP の 11 回目は 429」に書き換える。トークンは 256 ビット乱数なので総当たりは成立せず、IP 単位で十分。

### N-29【Non-blocking・中】転送リンクの残余リスクが本文に無い（§2 の 3 行目）
- 直し方: :51 の後ろに「本人が押す前の 15 分間に転送先が押せば転送先がログインできる。これは仕組みで完全には防げない」と書き、Q2c（(a) ブラウザ結び付け／(b) email 再入力／(c) 15 分・1 回で足りる）を PO 決定待ちに足す。設計の既定案は (b)。

### N-30【Non-blocking・低】アカウントの状態をキャッシュしないことが明記されていない
- 根拠【事実】: :59「キャッシュが要るときは `viewer_jwt:` を使う」、:52・:63「リクエストのたびに DB を見る」。前者が後者を崩す余地を残す。
- 直し方: :59 を「署名の検証結果はキャッシュしてよいが、アカウントの状態と trial_expires_at はキャッシュせず毎回 DB を読む」に限定する。

### N-31【Non-blocking・低】login でリンクを送る条件に「trial は trial_expires_at > now のときだけ」と「verified には送らない」が無い
- 根拠【事実】: :50 は「trial か active」、:47 の 5 値に verified がある。:63 の 403 の列挙にも verified が無い（:121 も同じ）。
- 直し方: :50 を「active、または trial で期限内」に、:63・:121 の 403 の列挙に verified を足す。:139 も同じ条件に揃える。

### N-32【Non-blocking・低】ログイン用トークンを新しく作るとき、前の未使用トークンを無効化するか
- 根拠【事実】: :51「毎回新しく作る」。前例 auth.py:391-396 は発行時に未使用の旧トークンを used_at で潰す。:104 の確認トークンは「古い確認トークンを無効にして」と明記、login 側に無い。
- 直し方: :51 に「同じアカウントの未使用のログイン用トークンは、新しく作るときに消す（有効なリンクは常に 1 本）」を足す。viewer_login_tokens（:53）に id（主キー）が列挙されていないので足す。

### N-33【Non-blocking・低】様式: :71 の位置（§1 N-23 の補足）、:155「4 本」→ 5 本または 6 本、:206 Q2b は Q2a と同じ番号系で整理済みだが Q2c（N-29）を足す場所。
- 直し方: 上記のとおり。

### 穴なしと判定した決定（根拠付き）
- 5 値の状態（verified 追加）: Q5 を待たずに migration を 1 本で切れる。自動トライアルなら verified を通らない、と :47 に明記。可。
- viewer_login_tokens を verify と login で共用（purpose 列）: 1 表・1 発行関数・1 消費関数で済み、前例 password_reset_tokens（purpose 列あり。auth.py:401-402）と同型。可。ただし消費の SQL は「token_sha256 AND purpose AND expires_at > now」の 3 条件で引くこと（purpose を省くと、確認用トークンでログインできてしまう）。これは B-5 の直し方に 1 行として含めるとよい。
- 12 時間トークンに email クレーム無し・sub=viewer:<id>: Q2a で変わらない。r2 §3 の判定を維持。
- 総当たり: nginx 完全一致 10r/m（真 IP）→ backend IP 単位 10 回／15 分 → 256 ビット乱数。N-28 で email 単位を外しても十分。

--------------------------------------------------------------------
4. 段の着手可否（r3 §4 の更新）
--------------------------------------------------------------------
- Q2a 決定と 5 値化により、段 1 の migration は **Q5 を待たずに切れる**（viewer_accounts 5 値＋viewer_login_tokens）。段 1 を止めるのは B-5（交換の入口が allowlist＝守り手テストの集合に直結）だけ。
- 段 0・段 2（作り置き・inventory・logout）は今から着手可。login／verify-email／session は B-5 確定後。
- 段 3 は Q8 待ち（変わらず）。段 4 は Q2b・Q3・Q5・Q6・Q7・Q9 待ち（変わらず）。Q2c（N-29）は段 2 の交換の実装前に要る。

--------------------------------------------------------------------
5. 推測・未確認の一覧
--------------------------------------------------------------------
【事実】nginx/nginx.conf:112 の完全一致、docker-compose.yml:209、cache.py:146、tcg_distribution_svc.py:251-254、auth.py:391-407・:412-441、RegisterPage.tsx:82 の searchParams、firebase-auth.ts:47,77 の localStorage、nginx 2 ファイルに log_format／access_log の指定なし。
【推測】B-5 のメールリンク検査による GET 消費（一般に知られた挙動。本番の受信側メールサービスで実測していない）。既定の access_log がクエリを記録する（nginx 既定の combined 形式からの導出。本番の実ログは見ていない）。
【未確認】本番 SMTP。前段プロキシ。ADR-1016 の扱い。/viewer のリダイレクト実機挙動。

--------------------------------------------------------------------
6. 総括
--------------------------------------------------------------------
r3 の Blocking（B-4）と N-22〜N-27 は解消。Q2a のマジックリンクは、未登録に送らない・15 分・1 回・suspended 即時の 3 点を仕組みで満たす。転送だけは「15 分・未使用の間」が残余リスクで、本文への明記と Q2c（email 再入力を既定案）が要る。
差し戻しは 1 点: トークン交換の入口・method・トークンの載せ方（B-5）。GET で消費する作りにするとメールのリンク検査で本人が開けなくなるので、「リンクは /viewer/#…、交換は POST、GET では消費しない」を設計で固定し、入口は 6 本目 `POST /api/v1/viewer/session`（案 C）を勧める。あわせて email 単位の失敗ロックを IP 単位に整理する（N-28）。
```

---

```text
# Architect 設計審査 r5 — 在庫の閲覧専用ページ（gas-viewer-fresh-fast）

対象: /Users/tanizawashingo/worktrees/salesanchor/release-gas-viewer-fresh-fast/docs/handoff/gas-viewer-fresh-fast/design.md（r5、227 行、2026-10-15。worktree では未コミット = `??`）
前回: /tmp/CC報告ファイル/viewer_design_review_r4.txt（r4 REVISE、B-5、N-28〜N-33）
照合基準: origin/main = f005b623fe2a68a3035f7fd51c692a7c44b23fea（r2〜r4 と同じ）。生の照合出力は /tmp/CC報告ファイル/viewer_design_review_r3/ を再利用。r5 で新しく引用された事実（firebase-auth.ts の localStorage、nginx.conf:112、cache.py:146・:292・:309、self_tokens.py:28-29、tcg_distribution_svc.py:251-254、docker-compose.yml:209）はすべて r3・r4 で照合済み。追加で auth.py:199-201 `_require_app_origin`（Origin ヘッダが rp_origin と一致しなければ 403）を確認した【事実】。
読み取りのみ。編集・commit・push は行っていない。

====================================================================
判定: APPROVE（条件付き。下の N-34〜N-39 は設計 PR のコミット前に同じ design.md へ反映すること。いずれも 1〜2 行の追記で、段 0〜2 の着手を止めない）
Blocking: 0 件 ／ Non-blocking: 6 件（N-34〜N-39）
r4 指摘の解消状況: B-5 解消 ／ N-28〜N-33 解消 6
====================================================================

--------------------------------------------------------------------
1. B-5・N-28〜N-33 の解消判定（依頼 1）
--------------------------------------------------------------------
| 指摘 | 判定 | 根拠（design.md r5 の行）と補足 |
|---|---|---|
| B-5 交換の入口・method・トークンの載せ方 | **解消** | :74 `POST /api/v1/viewer/session`（本文 token＋email、交換だけ）、:70 入口 6 本、:54 リンクは `/viewer/#login=`・`#verify=`、JS が POST、GET では消費しない、:55 12 時間トークンは JSON 本文・URL に載せない・localStorage（【事実】firebase-auth.ts:47,77 と同じ置き場）、:58 消費は token_sha256・purpose・expires_at の 3 条件。:62 nginx 完全一致 3 ブロック（session を含む）。受け入れ基準 :142（GET 2 回の後に POST で交換できる）・:144（verify_email の purpose では session に入れない）。案 C を正しく取り込んでいる |
| N-28 「login の失敗」の意味 | **解消** | :62 ①login は email 3 回/h、②session・verify-email の無効トークン／不一致 email は IP 単位 10 回/15 分（cache.py:292・:309）。email 単位の失敗ロックは消えた。:141 受け入れ基準 |
| N-29 転送の残余リスク | **解消** | :52 email 再入力（Q2c 既定案）、:53 残るリスクを明記、:216 Q2c。:143 受け入れ基準（email 不一致は 401） |
| N-30 状態をキャッシュしない | **解消** | :64「署名の検証結果だけ viewer_jwt:。状態と trial_expires_at は毎回 DB」 |
| N-31 verified・期限切れ trial | **解消** | :50 送る相手は active と期限内 trial のみ、:68 403 に verified 追加、:126・:148 受け入れ基準 |
| N-32 未使用トークンの無効化・id | **解消** | :51「新しく作るときに消す。有効なリンクは常に 1 本」、:58 id を列に追加、:145 受け入れ基準 |
| N-33 様式 | **解消** | :70・:77・:122「6 本」、:164「74 本から 6 本」、:77 が allowlist の列挙の後ろに移動 |

持ち越し: N-6 ADR-1016 未存在（変わらず）。design.md・recon.md・security-recon.md は未追跡 `??`（コミット時に 3 つとも git add）。worktree は origin/main より 30 コミット古い（r3 §5。設計 PR 起票前に main を取り込む）。

--------------------------------------------------------------------
2. 新しい穴（依頼 2）
--------------------------------------------------------------------

### N-34【Non-blocking・中】session で email が合わなかったとき、トークンを消費するかどうかが未定
- 根拠【事実】: :52「トークンと email の両方が合ったときだけログインできる」、:58「消費するときは 3 条件で引く」、:143「email が違えば 401」。「違った場合にそのトークンを消すか残すか」が無い。
- 何が起きるか【推測】: 消す作りにすると、転送先が間違った email で 1 回押しただけで本人のリンクが死に、本人はもう一度 login を要求する（3 回/h の枠を消費）。残す作りにすると、リンクを持つ相手が IP ごと 10 回まで email を試せる（256 ビットのトークンは既に手元にあるので、守りは email の秘匿と IP ロックだけになる）。
- 直し方: どちらかを :58 に 1 行で固定する。設計側の推奨は「**残す**（email 不一致ではトークンを消さず、IP の失敗だけ数える）」。理由: 本人の導線を転送先の誤操作で壊さない。email は登録者本人しか知らない前提（PO 条件）で、10 回/15 分の IP ロックが効く。受け入れ基準 :143 に「不一致の後、正しい email なら同じトークンで入れる」を足す。

### N-35【Non-blocking・低】D4「ページは在庫表と最終更新だけ」が D1 の導線（email 入力フォーム・リンク要求フォーム・使用済み表示・準備中表示）と食い違う
- 根拠【事実】: :103「ページは在庫表と『最終更新 HH:MM』だけにする」。一方 :52「ページは登録した email の入力を求め」、:53「本人は『使用済み』の表示で気付ける」、:85「準備中です」、login の要求も :73 では API だけで、email を入力する画面がどこにも書かれていない。
- 直し方: :103 を「ページの状態は 4 つ: ①ログイン要求（email 入力→POST login）②リンク到着後の email 確認（POST session）③在庫表＋最終更新 ④準備中／使用済み／期限切れの案内。②〜④の文言もすべて i18n」に書き換える。JS 300KB（:106）の上限はこの 4 状態を含めた数字であることを明記。

### N-36【Non-blocking・低】フラグメントのトークンを読み取った後に消すことが書かれていない
- 根拠【事実】: :54 リンクは `#login=<トークン>`。読み取り後の扱いが無い。
- 【推測】ブラウザの履歴・「URL をコピー」・ブックマークにトークン入りの URL が残る。15 分・1 回限りなので実害は小さいが、Generator が消さない作りにする余地がある。
- 直し方: :54 に「JS がフラグメントを読んだら直ちに history.replaceState で `#` 以降を消す」を 1 行。

### N-37【Non-blocking・低】verify-email の GET 非消費が受け入れ基準に無い
- 根拠【事実】: :142 は session だけ。:54 は「GET ではトークンを一切消費しない」と verify も含めて書いている。
- 直し方: :142 を「session と verify-email の両方」に広げる（検査は同じ型）。

### N-38【Non-blocking・低】Origin の検査が無い（既存 auth は Origin ≠ rp_origin を 403 にしている）
- 根拠【事実】: auth.py:199-201 `_require_app_origin`（Origin ヘッダが self_tokens.rp_origin() と一致しなければ 403）。login/password-reset 等で呼ばれている（:240・:316 ほか）。design.md の viewer 6 本には同等の記述が無い。
- 【推測】Bearer＋localStorage なので CSRF は成立しないが、他サイトからの POST login（メール連打）や POST signup（行の作成）は Origin 検査で安く落とせる。
- 直し方: D2 に「signup・login・session・verify-email は既存の _require_app_origin と同じ検査（Origin が rp_origin と一致しなければ 403）を通す」を 1 行。受け入れ基準に「Origin が違う POST login は 403」。

### N-39【Non-blocking・低】localStorage のキー名と、同一オリジンでアプリ本体と共存することの明記
- 根拠【事実】: :55「localStorage に置く（既存の firebase-auth.ts と同じ置き場）」。firebase-auth.ts:47 は storageKey で読む。/viewer/ は app.salesanchor.jp と同じオリジンなので、localStorage はアプリ本体と共有される。
- 直し方: :55 に「キー名は `viewer_access_token` のようにアプリ本体のキーと別にする。同一オリジンなのでアプリ本体の XSS は閲覧者トークンにも届く（逆も同じ）。これは受け入れる（閲覧者トークンで届く API は 6 本だけ）」を 2 行。受け入れ基準は不要。

### 様式（指摘番号なし）
- :160-161 KPI「表示までの時間：中央値 1.0 秒以下」が 2 行重複。1 行消す。

### 穴なしと判定した決定（根拠付き）
- 6 本の allowlist と守り手テスト: VIEWER_ROUTE_ALLOWLIST 1 か所、テストは app.routes 列挙（:122）。session が増えても検査対象に自動で入る。可。
- 3 条件の消費（token_sha256・purpose・expires_at）: 確認トークンでログインできない（:144）。前例 auth.py:432-438 と同型。可。
- nginx 完全一致 3 ブロック: login・verify-email・session だけ 10r/m（真 IP）。inventory・logout・signup は zone=api 30r/s（:8）。signup は app 側で email 3 回/h・IP 10 回/h。可。
- IP 単位ロック＋256 ビット乱数＋email 再入力: 総当たりは成立しない。N-34 の「残す」を採っても IP ロックが効く。可。
- GET 非消費＋フラグメント: Safe Links 等の先読みで消費されない。前例の reset は `?token=` クエリ（auth.py:407）だが、フラグメントのほうがログに残らない分だけ強い。可。
- localStorage 12 時間＋logout ブラックリスト（exp までの残り秒）: 既存と同じ型。可。
- 5 値の状態と verified の 403: Q5 の両方の答えに対応。可。

--------------------------------------------------------------------
3. 段の着手可否
--------------------------------------------------------------------
- 段 0・段 1（migration を含む）・段 2 は今から着手可（Q2〜Q9 のうち段 1〜2 を止めるものは無くなった。Q2c は既定案で進め、PO が変えたら session の email 比較を外すだけ）。
- 段 3 は Q8 待ち。段 4 は Q2b・Q3・Q5・Q6・Q7・Q9 待ち（変わらず）。
- N-34〜N-39 は段 2（session）と段 3（ページ）の実装前までに design.md に入っていればよいが、設計 PR のコミット前に入れておくこと（Generator に判断させない原則）。

--------------------------------------------------------------------
4. 推測・未確認の一覧
--------------------------------------------------------------------
【事実】auth.py:199-201・:240・:316、firebase-auth.ts:47、nginx/nginx.conf:8・:112、その他 r3・r4 で照合済みの行。
【推測】N-34 の転送先の誤操作シナリオ。N-36 の履歴・ブックマーク残り。N-38 の他サイトからの POST。
【未確認】本番 SMTP。前段プロキシ。ADR-1016 の扱い。/viewer のリダイレクト実機挙動。Safe Links 等の実挙動（r4 と同じ）。

--------------------------------------------------------------------
5. 総括
--------------------------------------------------------------------
r4 の Blocking（B-5）は案 C（6 本目 session・フラグメント・POST 交換・3 条件消費）で解消し、N-28〜N-33 もすべて本文と受け入れ基準に入った。設計の骨（トークン分離・allowlist・SSOT 作り置き・マジックリンク＋email 再入力・IP ロック）に Blocking の穴は無い。
残りは 6 件の 1〜2 行の追記（email 不一致時にトークンを残すか、ページの 4 状態、フラグメントの消去、verify の GET 非消費、Origin 検査、localStorage のキー名）と重複行 1 つ。設計 PR のコミット前に反映すれば、段 0〜2 は着手できる。
```
