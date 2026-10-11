# recon — product-code-collision-warning

**仕事名**: product-code-collision-warning（型番が既存商品と重なったら警告と除外ワードの推奨を返す・バックエンド）  
**日付**: 2026-10-09  
**対象ADR**: ADR-155  
**担当**: 実装担当（Sonnet）  
**実測の基準**: worktree の起点 08f59418c772fab0bed6137e818d5e87de5c91f2（origin/main の祖先）。行番号は `git show HEAD:<path>` の変更前の値

---

## 既存 ADR の検索結果

- `git grep -il "除外ワード\|exclude_keywords\|型番.*重複\|mark.*重複" -- docs/adr` の該当: ADR-093・ADR-1001・ADR-1002・ADR-155
- ADR-155（`docs/adr/ADR-155-product-master-ssot-csv-app.md:31` に `product_exclude_keywords` の記述）: 商品マスタの正本と CSV・アプリ編集の方針。本便はこの範囲の警告追加で、表は変えない
- ADR-144（`docs/adr/ADR-144-ui-component-governance.md`）: UI 部品の金型。本便は画面を触らないため対象外（2/2 で扱う）
- ADR-027（`docs/adr/ADR-027-ui-internationalization.md`）: UI 文字列は t() 経由。本便はコードだけ返し、文言は 2/2 で足す
- `docs/adr/FEATURE-INDEX.md`: 型番重複・除外ワードに直接当たる行は無い（商品マスタは ADR-099 / ADR-093 / ADR-014 の行、i18n は ADR-027 の行）

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/tcg_product_master.py:210` | POST /tcg/products（create_product_master）。force を受けて create_product を呼ぶ |
| `backend/app/routers/tcg_product_import.py:373` | POST /tcg/products/create（create_product_standalone）。force=True で create_product を呼ぶ |
| `backend/app/services/tcg_product_master_svc.py:324` | create_product。新規登録の唯一の入口（Claude の登録スクリプトも直接呼ぶ）。返り値は `{"ok": True, "product_id": ...}` |
| `backend/app/routers/tcg_product_import.py:294` | PUT /tcg/products/detail/{product_id}（save_product_detail）。update_product_detail を呼ぶ |
| `backend/app/services/tcg_product_detail_svc.py:111` | update_product_detail。重複チェック無し。返り値は product / revision / lookups |
| `backend/app/services/tcg_product_import_svc.py:218` | load_existing_marks。mark の完全一致・正規化なし・相手1件だけ（dict で後勝ち） |
| `backend/app/services/tcg_product_import_svc.py:290` | MARK_ALREADY_USED_BY_<id> を出す唯一の場所 |
| `backend/app/services/tcg_product_import_svc.py:382` | CSV 新規 preview。commit_import も preview を呼び直す |
| `backend/app/services/tcg_product_roundtrip_svc.py:181` | CSV 更新 inspect_update |
| `backend/app/services/tcg_product_roundtrip_svc.py:227` | 行の warnings が常に空（`"warnings": []`） |
| `backend/app/services/extraction_judgement_svc.py:31` | normalize_for_match（NFKC・小文字・カタカナ→ひらがな・空白と記号除去） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 型番を CSV 更新で変えられる列は mark だけか | `backend/app/services/tcg_product_roundtrip_svc.py:19` の COLUMNS は `product_id, revision, *CSV_COLUMNS`。CSV_COLUMNS に product_code は無い | 解消済み |
| 2 | create_product が渡す product_code は何か | 採番した PM コード（`_next_pm_code`）。型番の重なりが起きるのは主に mark | 解消済み |
| 3 | 実データで型番が公式でも重なる組がある | カード記載の事実（ST01〜ST24・EB01 など。除外ワードで見分けている）。件数は社外秘のため書かない | 解消済み（カード記載） |

**未解決ゼロ確認**: 全て解消済み

---

## 画面（2/2）

**実測の基準**: worktree の起点 e51dceba7（origin/main）。行番号は変更前の値

### 既存 ADR の検索結果（画面分）

- ADR-144（`docs/adr/ADR-144-ui-component-governance.md`）: UI 部品の金型。`docs/CC_UI_GOVERNANCE.md:11-14` に「金型が無ければ PO 許可を得て `components/` に登録（Xxx.tsx + Xxx.css + Xxx.stories.tsx）」とある。PO 許可は取得済み（「登録する」2026-10-09）
- ADR-027（`docs/adr/ADR-027-ui-internationalization.md`）: UI 文字列は t() 経由。ja.json・en.json 同一キー
- ADR-067（`docs/adr/ADR-067-design-token-enforcement.md`）: 色・余白は CSS 変数のみ

### file:line 引用表（画面分）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/components/` | Alert / Banner / Callout 相当のファイルが無い（Badge.tsx・Card.tsx・Modal.tsx 等のみ） |
| `frontend/src/components/Badge.tsx:1` | 既存の金型の作法（comp-* クラス・variant・CSS は var() のみ）。同じ作法で Callout を作る |
| `frontend/src/components/loading/index.ts` | components/ の下位フォルダは loading・master-list-editor の2つのみ。他の部品は components/ 直下に平置き |
| `frontend/scripts/check-stories-count.js:21` | check:stories は components/ 直下の tsx ファイルだけを走査する（下位フォルダは対象外） |
| `frontend/src/tokens.css:560` | `--color-warning-bg` / `--color-warning-border`（ダークは `tokens.css:605`）。警告の枠の色に使う |
| `frontend/src/index.css:109` | `--info-bg` / `--info-text`（ダークは `index.css:302`）。案内の枠の色に使う |
| `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:150-175` | 新規 saveCreate。保存後に onClose する |
| `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:127-149` | 編集 saveEdit。応答で detail を差し替える |
| `frontend/src/features/tcg-product-import/TcgProductImportPreview.tsx:19` | 行の messages 列。warnings を importMessages.ts で文言化 |
| `frontend/src/features/tcg-product-import/importMessages.ts:19` | `MARK_ALREADY_USED_BY_` → `productCsv.messages.markUsed` |
| `backend/app/schemas/tcg_product_code_collision.py:13-34` | CodeCollision の形（画面はこの形を読む） |

### 不明点リスト（画面分）

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 4 | 部品の置き場所（カードは `components/feedback/`） | 既存は平置きが主で、check:stories は直下のみ走査（上表）。下位フォルダに置くと stories の検査が効かない | 解消済み（`frontend/src/components/Callout.tsx` に平置き） |

**未解決ゼロ確認**: 全て解消済み

## 除外ワードの追加（3）

実測時の origin/main: fb036a238（d88bc73b6 の worktree 起点）

### 事実

| 引用先 | 確認内容 |
|-------|---------|
| backend/app/services/tcg_product_master_svc.py:560 | add_exclude_keyword は audit_log を書かない（INSERT と commit のみ）。変更の記録が語まで残らないため使わない（設計者判断 2026-10-09） |
| backend/app/middleware/audit.py:200-222 | POST/PUT 等は data_access_events に method・path・user_email のみ記録。追加した語は残らない |
| backend/app/routers/tcg_product_import.py:260-269 | GET /tcg/products/detail/{product_id}。応答は product・revision・lookups |
| backend/app/routers/tcg_product_import.py:275-316 | PUT /tcg/products/detail/{product_id}。body は ProductDetailUpdate（revision・全欄・search_keywords・exclude_keywords） |
| backend/app/services/tcg_product_detail_svc.py:122-123 | revision が合わなければ PRODUCT_DETAIL_CONFLICT（409） |
| backend/app/services/tcg_product_detail_svc.py:196-203 | audit_log に変更前後（old_values・new_values）と actor を記録 |
| backend/app/services/tcg_product_detail_svc.py:182-186 | 語の表は、送った語が現状と同じなら触らない（違うときだけ削除して入れ直す） |
| backend/app/services/tcg_product_master_svc.py:482 | 新規作成の応答に product_id（文字列）と code_collisions |
| frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx（変更前の135-141） | saveEdit が PUT する body の作り方。本便で productDetailModel.ts の buildUpdateBody に移し、ドロワーの保存と除外ワード追加で共用 |

### 確認した範囲と注意

- PUT は商品の他の欄を GET で得た今の値のまま送る。値を消す形ではない。ただし english_title・mark が NULL の商品は PUT で空文字になる（ドロワーの通常保存と同じ挙動。draftFrom が null を空文字にする既存仕様）
- 外部事例: 該当なし（自社マスタの編集画面に既存の保存経路を使うだけで、新しい方式を導入しないため）

## ADR 検索（3）

- 既存 ADR: ADR-155・ADR-144・ADR-027・ADR-067（本ディレクトリ冒頭と同じ）。除外ワード追加の追加 ADR は無し
