# ADR-139: ファネル型目標対比ダッシュボード フロントエンド（第1弾）

**ステータス**: Accepted  
**日付**: 2026-06-12  
**担当**: Hikky-dev  
**承認**: shingo-ops  
**関連ADR**: ADR-138（全体設計・バックエンド: `docs/adr/ADR-138-funnel-dashboard-stage1.md`）  
**正本ハンドオフ**: `docs/handoff/funnel-dashboard-stage1/`（design.md §4〜5 がフロント仕様）

---

## 背景

営業KPIを一画面で把握できる「ファネル型目標対比ダッシュボード」のフロントエンド実装。
バックエンドAPIのPR2/3が未マージの段階でも、モックデータで開発・E2E検証を進める必要があった。

## 決定

1. **3状態フラグ `VITE_FUNNEL_DASHBOARD`** を導入
   - `unset/false`: セクション非レンダリング（本番デフォルト・APIなしで壊れない）
   - `mock`: モックフィクスチャで表示（ローカル開発・E2E）
   - `live`: 実API結線（バックエンドPR2/3マージ後）

2. **第1層 8カード構成**（`/`）
   - ファネル4枚（リード獲得・商談化率・進行中商談・成約/失注）
   - 売上目標対比 1枚
   - サイド2枚（新規顧客獲得・アクティブ既存顧客）
   - 要フォロー顧客 1枚

3. **下層4ルート**
   - `/dashboard/follow-ups` — 要フォロー顧客一覧（セグメントフィルタ + DataTable + Drawer）
   - `/dashboard/leads` — リード流入分析（チャネル別DataTable）
   - `/dashboard/revenue` — 売上・粗利内訳（4カードグリッド）
   - `/dashboard/reasons` — 成約・失注理由（タブ切替 + ランキング + 顧客の声）

4. **Playwright `toHaveScreenshot()` 視覚回帰** をベースライン5枚で実装

## 根拠

- `MOCK_MODE` デフォルトONパターンは本番でモックデータが表示されるリスクがあるため3状態フラグに変更
- i18n必須（ADR-027）・デザイントークン必須（ADR-067）を完全準拠
- バックエンドAPI結線はPR2/3マージ後に `VITE_FUNNEL_DASHBOARD=live` に切替える小PRで対応

## 影響

- `frontend/src/api/funnel.ts` — API層
- `frontend/src/pages/dashboard/` — 新規5コンポーネント
- `frontend/src/locales/ja.json` / `en.json` — 約57キー追加
- `frontend/src/tokens.css` — `--opacity-faint` / `--size-drawer-label-min` / `--size-split-label-min` 追加
