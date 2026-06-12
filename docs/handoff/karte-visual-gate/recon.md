# recon.md — 受信箱カルテ 見た目の忠実度ゲート（順序⑤）

> 作成: 2026-06-11 | STANDARD-WORKFLOW Phase ① recon | 担当: architect  
> 参照設計書: 設計：受信箱カルテ 見た目の忠実度ゲート（順序⑤）（Planner: Web Claude）

---

## 1. 前提確認

| 前提 | 状態 |
|------|------|
| develop 同期完了 | ✅ PR #1953 (sync-main-develop-adr128) マージ済み・PR #1958/#1959 main 反映済み |
| KarteLayoutReference | ⚠️ repo 未配置 — `docs/adr/karte_reference.html` が唯一の正本 |

KarteLayoutReference ファイルは存在しないため、設計フェーズで `docs/adr/` に px 値表として同梱する。

---

## 2. 対象ファイル（完全パス）

| 種別 | ファイル | 行数 |
|------|---------|------|
| カルテメインコンポーネント | `frontend/src/pages/inbox/InboxKartePanel.tsx` | 797 行 |
| モーダル（デスクトップ） | `frontend/src/pages/inbox/InboxProfileModal.tsx` | 274 行 |
| スタイル | `frontend/src/pages/inbox/InboxPage.css` | 1,533 行 |
| デザイントークン | `frontend/src/tokens.css` | — |
| ビジュアル正本 | `docs/adr/karte_reference.html` | 214 行 |
| E2E spec（既存） | `frontend/tests-e2e/karte-visual-gate.spec.ts` | 376 行 |
| Playwright 設定 | `frontend/playwright.config.ts` | 70 行 |
| CI ワークフロー | `.github/workflows/karte-gate.yml` | 90 行 |

---

## 3. Phase 5a — 寸法差分（現状 vs 正本）

### 3-1. パネル幅

| | 正本 (`docs/adr/karte_reference.html`) | 実装値 |
|---|---------------------------------------|-------|
| デスクトップ | `width: 396px` (`.panel` line 27) | `width: var(--drawer-width)` = **300px** (`frontend/src/pages/inbox/InboxPage.css:747`) |
| タブレット (≤1279px) | 396px | `var(--inbox-collapsed-panel-w)` = **360px** (`frontend/src/tokens.css:269`, `frontend/src/pages/inbox/InboxPage.css:996`) |

**差分：デスクトップ -96px / タブレット -36px**。`--drawer-width` は user drawer 用変数（`frontend/src/tokens.css:155`）を誤用している。

### 3-2. ヘッダー

| プロパティ | 正本 | 実装 | Delta |
|-----------|------|------|-------|
| padding | `16px 18px 14px` (`.hd` line 28) | `var(--space-3) var(--space-3)` = `12px 12px` (`frontend/src/pages/inbox/InboxPage.css:868`) | -4px top, -6px sides |
| border-bottom | `0.5px solid` (line 28) | `1px solid` (`frontend/src/pages/inbox/InboxPage.css:869`) | 2× 太い |
| avatar size | `40×40px` (`.av` line 30) | `var(--right-panel-avatar-size)` = `40px` (`frontend/src/tokens.css:248`) | 一致 ✅ |
| name font-size | `15px` (`.nm` line 31) | `var(--font-base)` = `14.4px` (`frontend/src/tokens.css:16`, `frontend/src/pages/inbox/InboxPage.css:1152`) | -0.6px |
| sub font-size | `12px` (`.nm-sub` line 32) | variable — 確認要 | — |
| badge font-size | `11px` (`.badge` line 33) | — (確認要) | — |
| badge padding | `3px 9px; border-radius: 20px` | — (確認要) | — |
| header-meta margin-top | `11px` (`.hd-meta` line 34) | — (確認要) | — |

### 3-3. タブバー

| プロパティ | 正本 | 実装 | Delta |
|-----------|------|------|-------|
| tab padding | `11px 4px` (`.tab` line 39) | `var(--space-2) var(--space-1)` = `8px 4px` (`frontend/src/pages/inbox/InboxPage.css:1160`) | -3px 上下 |
| tab font-size | `13px` (line 39) | `var(--font-xs)` = `12px` (`frontend/src/tokens.css:14`, `frontend/src/pages/inbox/InboxPage.css:1162`) | -1px |
| active font-weight | `600` (`.tab.on` line 41) | なし（active は color/border のみ）(`frontend/src/pages/inbox/InboxPage.css:1168`) | **font-weight 未設定** |
| border-bottom | `0.5px solid` | `1px solid` (`frontend/src/pages/inbox/InboxPage.css:1157`) | 2× 太い |

### 3-4. コンテンツ body

| プロパティ | 正本 | 実装 | 確認要否 |
|-----------|------|------|---------|
| body padding | `14px 18px 8px` (`.body` line 42) | `.right-panel-tab-content` は `overflow-y: auto` のみ；実際の padding は `.right-panel-section` 等に分散 (`frontend/src/pages/inbox/InboxPage.css:808-814`) | 要確認 |

### 3-5. セクション見出し

| プロパティ | 正本 | 実装 | Delta |
|-----------|------|------|-------|
| font-size | `11px` (`.sec` line 43) | `var(--font-2xs)` = `11.2px` (`frontend/src/tokens.css:265`) | 誤差程度 |
| font-weight | `500` | `var(--font-weight-bold)` (`frontend/src/pages/inbox/InboxPage.css:1173`) | **bold 過剰** |
| text-transform | なし（通常テキスト） | **`uppercase`** (`frontend/src/pages/inbox/InboxPage.css:1175`) | **大文字強制 — 正本と不一致** |
| letter-spacing | なし | `0.8px` (`frontend/src/pages/inbox/InboxPage.css:1176`) | 正本にない |
| margin | `14px 0 7px` (first-child: `2px 0 7px`) | `padding: var(--space-3) 0 var(--space-2)` = `12px 0 8px` + border-top | padding/border 方式 |

### 3-6. 入力フィールド

| プロパティ | 正本 | 実装 | Delta |
|-----------|------|------|-------|
| padding | `7px 9px` (`.fbox` line 48) | `var(--space-1) var(--space-2)` = `4px 8px` (`frontend/src/pages/inbox/InboxPage.css:1136`) | **-3px 上下** |
| font-size | `13px` (line 48) | `var(--font-sm)` = `13.6px` (`frontend/src/tokens.css:15`) | +0.6px（誤差程度） |
| min-height | `32px` (line 48) | なし（通常 input は height で自然）| 実測要 |
| border | `0.5px solid var(--bd2)` | `1px solid var(--border)` (`frontend/src/pages/inbox/InboxPage.css:1135`) | 2× 太い |
| border-radius | `6px` (line 48) | `var(--radius-sm)` = `4px` (`frontend/src/tokens.css:90`) | -2px |

### 3-7. アクションバー

| プロパティ | 正本 | 実装 | Delta |
|-----------|------|------|-------|
| padding | `12px 18px` (`.bar` line 60) | `var(--space-3)` = `12px` (全辺) (`frontend/src/pages/inbox/InboxPage.css:1199`) | -6px 左右 |
| gap | `8px` (line 60) | `var(--space-2)` = `8px` (`frontend/src/pages/inbox/InboxPage.css:1198`) | 一致 ✅ |
| border-top | `0.5px solid` (line 60) | `1px solid` (`frontend/src/pages/inbox/InboxPage.css:1200`) | 2× 太い |

### 3-8. Primary ボタン

| プロパティ | 正本 | 実装 | Delta |
|-----------|------|------|-------|
| padding | `10px` (`.primary` line 61) | `var(--space-2) var(--space-4)` = `8px 16px` (`frontend/src/pages/inbox/InboxPage.css:1208`) | -2px 上下 |
| font-size | `13px` (line 61) | `var(--font-sm)` = `13.6px` (`frontend/src/pages/inbox/InboxPage.css:1213`) | +0.6px |
| border-radius | `8px` (line 61) | `var(--radius-md)` = `6px` (`frontend/src/tokens.css:91`) | -2px |

### 3-9. Overflow ボタン

| プロパティ | 正本 | 実装 | Delta |
|-----------|------|------|-------|
| padding | `10px 13px` (`.more` line 63) | `var(--space-2) var(--space-3)` = `8px 12px` (`frontend/src/pages/inbox/InboxPage.css:1224`) | -2px 上下/-1px 左右 |
| font-size | `15px` (line 63) | `var(--font-md)` — 確認要 | — |
| border-radius | `8px` (line 63) | `var(--radius-md)` = `6px` | -2px |

---

## 4. Phase 5a — 修正箇所サマリー

優先度順（視覚インパクト大 → 小）：

1. **パネル幅**: `frontend/src/pages/inbox/InboxPage.css:747` で `--drawer-width` を inbox 専用変数に変更（例 `--inbox-karte-panel-w: 396px`）し `frontend/src/tokens.css` に追加。タブレット `360px → 396px` も `frontend/src/pages/inbox/InboxPage.css:996` で同様。
2. **セクション見出し**: `frontend/src/pages/inbox/InboxPage.css:1175` `text-transform: uppercase` を削除、`font-weight: 500` に修正、`letter-spacing: 0` に。
3. **ヘッダー padding**: `frontend/src/pages/inbox/InboxPage.css:868` を `16px 18px 14px` に。
4. **フィールド padding**: `frontend/src/pages/inbox/InboxPage.css:1136` を `7px 9px` に。`border-radius` を `6px`、`border` を `0.5px` に。
5. **タブ padding/font**: `frontend/src/pages/inbox/InboxPage.css:1160` を `11px 4px`、font-size `13px`、active に `font-weight: 600` 追加。
6. **アクションバー padding**: `frontend/src/pages/inbox/InboxPage.css:1199` を `12px 18px` に。
7. **Primary ボタン padding/radius**: `frontend/src/pages/inbox/InboxPage.css:1208` を `10px`、`border-radius: 8px` に。
8. **各所 border 0.5px**: 視覚的に重要なら `border-top/border-bottom` を `0.5px` に変更（ただし一部ブラウザで `0.5px` は `1px` 相当になるため、実描画で確認）。

---

## 5. Phase 5b — 視覚ゲートの現状と実装方針

### 5-1. 既存 karte-gate の状態

- `frontend/tests-e2e/karte-visual-gate.spec.ts:1-376` — 機能テスト（`toHaveScreenshot()` ゼロ）
- `.github/workflows/karte-gate.yml:59-65` — `npx playwright test karte-visual-gate.spec.ts --project=chromium` を実行
- `karte-gate` は **既に PR 必須チェック**（PR #1953 の statusCheckRollup で確認済み）

### 5-2. `playwright.config.ts` の現状

`frontend/playwright.config.ts:38-41` のみ:
```ts
screenshot: "only-on-failure",
video: "retain-on-failure",
trace: "retain-on-failure",
```
`expect.toHaveScreenshot` オプション未設定（しきい値・maxDiffPixels など）。

### 5-3. 「隔離レンダリング」の状態

設計書が求める「ログイン不要で描画できる隔離テストページ」は専用 HTML 不要。  
`frontend/tests-e2e/karte-visual-gate.spec.ts:64-109` の `renderKarte()` ヘルパーが:
- `installAuthBypass(page)` — 認証バイパス済み (`frontend/tests-e2e/karte-visual-gate.spec.ts:71`)
- `mockApi(page, mocks)` — 全 API モック済み (`frontend/tests-e2e/karte-visual-gate.spec.ts:92`)
- 固定フィクスチャ: `karte-lead-kisonkosaku-with-deal.json` 等 (既存顧客=正本と同条件)

**追加の HTML テストページは不要**。既存 `renderKarte()` を `toHaveScreenshot()` テストでも再利用する。

### 5-4. ベースライン生成方針（CI 環境）

- ベースライン画像は `--update-snapshots` フラグで `ubuntu-latest` 上で生成
- 生成ファイルは `frontend/tests-e2e/__snapshots__/karte-visual-gate.spec.ts-snapshots/` に保存
- 生成後 `git commit` してリポジトリに含める
- 通常 CI では `--update-snapshots` なし → 差分があれば失敗

### 5-5. 実装手順（Generator 向け）

1. `frontend/playwright.config.ts` に `expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.005, threshold: 0.15 } }` を追加
2. `frontend/tests-e2e/karte-visual-gate.spec.ts` に新テストスイート追加（`"Visual regression"` describe ブロック）:
   - 既存顧客 + 顧客タブ: `await page.locator('.right-panel-card').screenshot()` → `toHaveScreenshot('karte-kisonkosaku-company.png')`
   - リード + 商談タブ
3. `.github/workflows/karte-gate.yml:65` の `run` ステップに artifact として `**/*.png` を含む
4. ベースライン生成 step を karte-gate.yml に追加（`if: github.event_name == 'workflow_dispatch'` で手動トリガー用）

---

## 6. 制約・リスクのまとめ

| 項目 | 詳細 | 関連 file:line |
|------|------|--------------|
| パネル幅変更の影響範囲 | `--drawer-width` はタブレット responsive ブロックでも使われる可能性 | `frontend/src/pages/inbox/InboxPage.css:747`, `996` |
| セクション見出し uppercase 削除 | `text-transform: uppercase` は既存テスト `[ADR-108-1]` で文字列マッチに影響しない（data-testid ベース） | `frontend/tests-e2e/karte-visual-gate.spec.ts:182-220` |
| border 0.5px | Safari/Webkit で `0.5px` = `1px` 描画になる場合あり。chromium 専用なら実用的 | `frontend/src/pages/inbox/InboxPage.css:869` |
| ベースライン Mac 生成禁止 | フォント描画差で誤検知。`ubuntu-latest` 必須 | `.github/workflows/karte-gate.yml:30` |
| `--max-diff-pixel-ratio 0.005` | アンチエイリアス差を吸収しつつ配置ズレ（5px+）を検知。Phase 5a 完了後に調整 | `frontend/playwright.config.ts` |
| snapshot 画像サイズ | chromium `Desktop Chrome` = 1280×720。右パネルのみ clip して容量削減推奨 | `frontend/playwright.config.ts:48-50` |
| InboxKartePanel.tsx 変更なし（スタイルのみ） | Phase 5a は CSS のみ変更（`.tsx` の data-testid は既存テストと整合） | `frontend/src/pages/inbox/InboxPage.css` |
