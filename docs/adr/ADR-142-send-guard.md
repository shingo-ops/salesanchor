# ADR-142: 送信ガード（Send Guard）Phase A

- **Status**: Accepted
- **Date**: 2026-06-24
- **Author**: Hikky-dev (Claude Code)
- **Supersedes**: ADR-110 §constraints 表 line 72 / 受け入れ条件 item 3 (line 211) — 「日本語直送りはゲート対象外」記述を廃止
- **Related**: ADR-110-sa-translation-subsystem.md, ADR-088-inbound-translation.md

---

## 背景

ADR-110 では「日本語直送り（既存送信ボタン）はゲート対象外」と明記していた（§constraints 表 line 72 / AC item 3 line 211）。
これは翻訳プレビューUI が存在しなかった時点の判断であり、Phase A 実装完了後は正確でなくなる。

本ADRはこの制約を廃止し、「かな検出 + 確認ダイアログ」による Phase A 送信ガードを正式に承認する。

### 事業リスク

- B2B TCG 輸出 CRM（HIGH LIFE JPN）の担当者が日本語文面を英語圏バイヤーにそのまま送信する事故
- CRM 稼働前（現在: 全テナント 0 rows）であっても、機能リリース後に即発生しうる
- Phase B（majority vote）に必要なデータ蓄積が未完のため、Phase A シンプル実装で先行保護する

---

## 決定

### 自動送信永久禁止原則（ADR-110 より継承・強化）

送信ボタン / Enter キーによる直接送信を廃止するのではなく、
**かな検出 + 受信者言語設定によるダイアログ介在** で誤送信を防止する。

「確認なし自動送信」は永久に禁止。常にユーザーが最終選択権を持つ。

### Phase A: かな検出 + スレッド言語トグル（本 ADR 対象）

バックエンド変更ゼロ。フロントエンドのみで実装。

#### 発火条件表（(P) 確定）

| recipientLanguageSetting | draftHasKana | ダイアログ発火 |
|--------------------------|:------------:|:--------------:|
| `auto`                   | あり          | **YES**        |
| `auto`                   | なし          | no             |
| `ja`（手動）             | あり          | no（日本語送信OK）|
| `ja`（手動）             | なし          | no             |
| `en`（手動）             | あり          | **YES**        |
| `en`（手動）             | なし          | no             |

かな判定正規表現: `/[\u3040-\u30FF]/`（平仮名 U+3040-U+309F + 片仮名 U+30A0-U+30FF）

#### ダイアログ選択肢

1. **「英訳して送る」** → 既存 OutboundTranslationPreview モーダルを開く（`target_language` = 受信者設定 or `"en"`）
2. **「原文で送る」** → `submitSend()` を直接呼び出す（確認後の意図的送信）

#### 言語トグル（スレッドヘッダ）

- 値: `"auto"` / `"ja"` / `"en"`
- 状態: `languageOverrideByLead: Record<number, "auto" | "ja" | "en">` — lead_id ごとに独立
- セッション内のみ保持（localStorage 永続化は Phase B 検討）

### Phase B: majority vote（将来・別 ADR）

`lang_judge.py` が CRM メッセージ履歴から受信者言語を多数決で判定。
CRM データ蓄積後に ADR-143 または ADR-110 改訂として起案。

---

## 代替案

### A. Phase B まで待つ

却下。CRM 稼働前の今がリリース適期。Phase A は 0 データでも機能する。

### B. サーバーサイドで自動検出・ブロック

却下。API ラウンドトリップ増加 + バックエンド変更が必要。Phase A スコープ外。

---

## 受け入れ条件

1. `auto` + かな → ダイアログ表示
2. `auto` + かななし → ダイアログなし・直送
3. `ja`（手動）→ かな有無問わずダイアログなし
4. `en`（手動）+ かな → ダイアログ表示
5. ダイアログ「英訳して送る」→ OutboundTranslationPreview が開く
6. ダイアログ「原文で送る」→ submitSend() が呼ばれ送信される
7. ヘッダーの言語トグル（auto/ja/en）でスレッドごとに設定変更可能
8. バックエンドファイル（leads.py / translation.py / message_translator.py）に変更なし

---

## 影響範囲

### 変更あり

- `frontend/src/pages/inbox/useInboxState.ts` — `languageOverrideByLead` state 追加
- `frontend/src/pages/inbox/InboxMessageThread.tsx` — ダイアログ UI + トグル UI + `checkAndSend` 追加
- `frontend/src/pages/inbox/OutboundTranslationPreview.tsx` — `target_language` prop 追加
- `frontend/src/locales/ja.json` / `en.json` — `sendGuard.*` キー追加

### 変更なし

- `backend/` — 全ファイル無変更
- `migrations/` — なし
- `deploy.yml` — なし
- `docker-compose.yml` — なし

---

## ADR-110 との関係

ADR-110 のうち以下の記述を本 ADR が**廃止**する:

> (constraints 表, line 72):「日本語直送り（既存送信ボタン）はゲート対象外」

> (acceptance criteria item 3, line 211):「日本語直送り（既存送信ボタン）はゲート対象外」

ADR-110 の残りの内容（翻訳プレビューフロー / 低確信度フラグ / グロッサリ / inbound翻訳等）は引き続き有効。
