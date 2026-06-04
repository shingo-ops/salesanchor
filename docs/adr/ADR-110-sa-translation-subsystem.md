# ADR-110: 会話ログ翻訳サブシステム

| 項目 | 内容 |
|------|------|
| **状態** | Accepted |
| **起案日** | 2026-06-04 |
| **起案者** | Web Claude (Planner) |
| **決定者** | しんごさん (PO) |
| **関連** | ADR-025 (3点セット) / ADR-088 (受信箱翻訳基盤) / ADR-100 (取り込み・分析パイプライン) / ADR-107 (分析エージェント(A)) |

---

## 背景

多言語の問い合わせ（TCG 輸出・海外バイヤー）を扱う Sales Anchor では、2 大フローが存在する。

1. **受信（inbound）**: 顧客メッセージ（主に英語）→ 担当者が日本語で読む
2. **送信（outbound）**: 担当者の日本語下書き → 相手言語（主に英語）に翻訳して送る

ADR-088 で受信→日本語翻訳の基盤（`message_translator.py` + `message_translations` キャッシュ）は構築済み。しかし以下が未解決のまま残っている:

- **誤訳リスク**: 専門用語・商品名・スラング/略語を AI が直訳して信頼を損なう
- **送信フロー未実装**: 担当者が日本語で書いた下書きを英訳・確認する仕組みがない
- **グロッサリ未整備**: 用語の正しい訳を登録・管理する仕組みがない

---

## 決定（What / Why）

### What — 何を作るか

| フロー | 機能 |
|--------|------|
| 受信 | 顧客メッセージ → 日本語翻訳（原文必ず保持・原文言語自動判定） |
| 送信 | 日本語下書き → 相手言語（主に英語）の **"下訳"** 生成（人が確認・修正して送信） |
| グロッサリ | 用語集：専門用語/商品名/スラング → 正しい訳、または「訳さない」で登録 |
| 商品 seed | 商品マスタ（`public.products`）の `name_en` / `name_ja` からグロッサリを自動 seed |
| 確信度 | 翻訳ごとに `confidence 0–1` を記録。低確信度語をフラグ |
| 監視 | 失敗率・遅延・低確信度多発を Discord 通知（ADR-025 3点セット） |

### Why — なぜ作るか

- 海外顧客とのやり取りを、誤訳リスクを構造的に抑えて行える
- 専門用語（PSA, BGS, TCG グレード, カード名, 型番）の直訳による信頼毀損を防ぐ
- 担当者が英訳に不慣れでも、確認フローを通じて品質を保証できる

---

## 誤訳対策 — 3 層の安全網

1. **グロッサリで元を断つ**: 登録語は AI が自由直訳しない。`訳さない` 登録で原語保持。
2. **原文を必ず残す**: 翻訳は原文を置き換えない。受信は「原文 + 和訳」を並列表示。
3. **送信は人が確認してから送る**: AI は下訳のみ。確認ステップなしの送信経路は存在しない。

---

## Scope 外（v1 でやらないこと）

- 商談解析（要約・意図・温度感）— 将来 ADR-107 分析エージェント(A)に相乗り
- 逆翻訳（英→和）プレビュー — Phase 2
- 自動送信 — 永久禁止
- 完全自動グロッサリ成長 — Phase 2

---

## 事業上の制約・原則

| 原則 | 内容 |
|------|------|
| 原文不変 | `content_text` / `message_text` は書き換えない。翻訳は別フィールド。 |
| グロッサリ遵守 | 登録語は登録通りに出力（訳す / 訳さない）。AI の自由裁量を許さない |
| 送信ガード | 担当者の「確認して送信」ボタンが唯一の送信経路。確認を飛ばすパスを作らない |
| テナント分離 | データもグロッサリも他テナントと混在しない |
| 外部 AI = ADR-025 | 3点セット（本体・状態検証・監視/通知）必須 |
| コスト最適化 | 受信=安いモデル既定（低確信度・長文は上位エスカレート）/ 送信=最上位モデル必須 |
| 冪等 | 翻訳済み行の再処理なし。再翻訳は明示トリガーのみ |

---

## データ設計

### 既存テーブル（ADR-088 基盤）

```sql
-- {schema}.message_translations（migration 094 既存 + 本 ADR で拡張）
id, message_id, target_language, translated_text, engine,
confidence REAL,          -- ← ADR-110 追加: 0.0–1.0
original_language VARCHAR(10),  -- ← ADR-110 追加: 判定言語 'en', 'zh', etc.
created_at
```

```sql
-- {schema}.conversation_logs（migration 20260604_090000 既存）
id, tenant_id, lead_id, contact_id, company_id, deal_id,
channel_type, direction, sender, content_text,
original_language,  -- ← 既存列
translated_text,    -- ← 既存列
analysis, occurred_at, created_at
```

### 新規テーブル（本 ADR）

```sql
-- public.translation_glossary（グロッサリ: テナント共通ベース + テナント追加）
id SERIAL PRIMARY KEY,
tenant_id INTEGER,          -- NULL = 全テナント共有
source_term TEXT NOT NULL,  -- 翻訳前の語
target_text TEXT,           -- NULL = 「訳さない」（原語のまま保持）
language_pair VARCHAR(20) NOT NULL DEFAULT 'en->ja',
term_type VARCHAR(30) NOT NULL DEFAULT 'general',
  -- 'product_name' | 'brand' | 'grade' | 'abbreviation' | 'jargon' | 'general'
is_active BOOLEAN NOT NULL DEFAULT TRUE,
source_ref VARCHAR(50),     -- 'product_master' = 自動 seed
notes TEXT,
created_at, updated_at,
UNIQUE (tenant_id, source_term, language_pair)

-- {schema}.outbound_translation_drafts（送信下訳 + 人確認状態管理）
id SERIAL PRIMARY KEY,
tenant_id INTEGER NOT NULL,
lead_id INTEGER,
original_text TEXT NOT NULL,  -- 担当者の日本語下書き
draft_text TEXT NOT NULL,     -- AI 生成英訳下訳
confidence REAL,
flagged_terms JSONB,          -- [{term, reason}]
model VARCHAR(50) NOT NULL,
confirmed_at TIMESTAMPTZ,     -- NULL = 未確認（人が確認済みは NOT NULL）
final_text TEXT,              -- 人が編集した最終テキスト（confirmed_at と同時に設定）
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

### モデル設定（config 化）

環境変数で切り替え可能。既定値は固定方針に従う。

| 変数名 | 既定値 | 用途 |
|--------|--------|------|
| `TRANSLATION_MODEL_RECEIVE` | `gemini-2.5-flash` | 受信和訳（安い） |
| `TRANSLATION_MODEL_SEND` | `gemini-2.5-pro` | 送信英訳（最上位必須） |
| `TRANSLATION_CONFIDENCE_THRESHOLD_RECEIVE` | `0.70` | 受信低確信度閾値 |
| `TRANSLATION_CONFIDENCE_THRESHOLD_SEND` | `0.85` | 送信低確信度閾値（厳しめ） |

---

## API 設計

### 既存（ADR-088、拡張）

```
POST /api/v1/leads/{lead_id}/messages/{message_id}/translate
  body: { target_language }
  → { translated_text, cached, engine, confidence, original_language, flagged_terms }
```

### 新規（本 ADR）

```
POST /api/v1/translation/outbound-preview
  body: { lead_id?, draft_text, target_language? }
  → { draft_id, draft_text, confidence, flagged_terms, model }
  ※ 送信しない。下訳を生成して返すのみ。

POST /api/v1/translation/outbound-confirm/{draft_id}
  body: { final_text }   ← 人が編集済みのテキスト
  → { confirmed: true, final_text }
  ※ 送信経路はこのエンドポイントで "確認済み" にマークするだけ。
    実際の送信は既存の /leads/{lead_id}/messages POST を使う。

GET  /api/v1/translation/glossary?page=1&per_page=50
POST /api/v1/translation/glossary
  body: { source_term, target_text, language_pair, term_type, notes }
PATCH /api/v1/translation/glossary/{id}
DELETE /api/v1/translation/glossary/{id}
```

---

## ADR-025 3点セット

| セット | 内容 |
|--------|------|
| **本体** | 翻訳ワーカー（受信和訳 + 送信英訳下訳）＋グロッサリ適用 |
| **状態検証** | `translated_text = NULL` 未処理検知 / グロッサリ外の自由直訳語検出 |
| **監視/通知** | 失敗率・遅延・低確信度多発が閾値超で Discord 通知 |

---

## Codebase Referent（file:line 突合済み）

| 参照 | ファイル | 行 |
|------|----------|-----|
| message_translations 既存 | `migrations/094_create_message_translations.sql` | 25-44 |
| conversation_logs | `migrations/20260604_090000_create_conversation_logs.sql` | 34-56 |
| 商品マスタ (public.products) | `migrations/062_create_inventory_movements_and_budget.sql` | 30-70 |
| テナント products | `migrations/005_add_phase2_tenant_tables.sql` | 22-39 |
| message_translator.py (ADR-088) | `backend/app/services/message_translator.py` | 1-283 |
| llm_budget.py | `backend/app/services/llm_budget.py` | 1-150 |
| discord_notifier.py | `backend/app/services/discord_notifier.py` | 1-204 |
| 翻訳 endpoint (ADR-088) | `backend/app/routers/leads.py` | 887-970 |
| inbound 翻訳 UI | `frontend/src/pages/inbox/InboxMessageThread.tsx` | 91-344 |
| translateMessage API | `frontend/src/lib/messages.ts` | 216-236 |
| celery_app.py | `backend/app/celery_app.py` | 1-98 |

---

## 受け入れ条件（テストで担保）

1. 原文（`content_text` / `message_text`）は一切変更されない
2. グロッサリ登録語を勝手に直訳しない。固有名詞/型番/グレード/カード名を保持
3. 送信フロー（固定）: 日本語下書き → 英訳プレビュー → 人が編集可 → 「確認して送信」のみ。確認ステップを飛ばした送信経路は存在しない（テストで担保）
4. 受信は原文 + 和訳を併記表示
5. 確信度 0–1 を翻訳ごとに記録。低確信度をフラグ（受信 < 0.70 / 送信 < 0.85、config 化）
6. モデル方針（固定）: 送信英訳 = 最上位モデル必須 / 受信和訳 = 安いモデル既定 + エスカレート
7. 翻訳済み行を再処理しない（冪等。再翻訳は明示トリガーのみ）
8. テナント分離（データもグロッサリも他テナントと混ざらない）
9. 失敗は non-fatal + 再試行。言語判定不能は graceful degrade

---

## Phase

| Phase | 内容 |
|-------|------|
| **v1（本 ADR）** | 受信→和訳 + 送信→英訳下訳(人確認) + グロッサリ(商品マスタ seed) + 原文併記 + 確信度フラグ + Celery バックグラウンド + Discord 監視 |
| **Phase 2** | 逆翻訳（英→和）プレビュー / グロッサリ自動成長 / 対応言語拡張 |
