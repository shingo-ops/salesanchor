# UI標準化 分割PR計画

**作成日**: 2026-06-13  
**ブランチ**: feature/morimoto/ui-std-pr0-recon  
**前提資料**: `recon.md`（同ディレクトリ）

---

## KGI

> **全 UI raw要素（button/input/select/textarea）を標準コンポーネントへ置換し、**  
> **デザインシステム準拠率を現在の推定 30% → 90% 以上に引き上げる**

| 指標 | 現在値 | 目標値 |
|------|--------|--------|
| raw `<button>` | 501 | ≤ 50（非置換可能な数のみ） |
| raw `<input>` | 470 | ≤ 30 |
| raw `<select>` | 124 | ≤ 10 |
| raw `<textarea>` | 51 | ≤ 5 |
| `btn-*` クラス直接付与 | 419 | ≤ 20 |
| インラインスタイル警告 | 30+ | 0 |

---

## スコープ

### 対象

- `frontend/src/pages/` 配下全ページ（認証系除く）
- `frontend/src/components/` 配下全コンポーネント（design-preview除く）

### 対象外

- `**/*.stories.tsx` — Storybook専用
- `components/design-preview/**` — プレビュー専用
- `pages/RegisterPage.tsx` / `pages/LoginPage.tsx` — 認証フロー（別ADR）
- `error-banner` クラス — 既に統一済み、変更不要

---

## 必須制約（全PRで守ること）

1. **ADR-067**: CSS変数・デザイントークン準拠。`color: red` 等の直接指定禁止
2. **ADR-027**: 全UI文字列を `t("key")` 経由。ハードコード日本語絶対禁止
3. **型安全**: `ButtonVariant` / `TextFieldSize` 等、TypeScript型で規格外をコンパイルエラーに
4. **アクセシビリティ**: `aria-label` / `role` / `htmlFor` を維持または追加
5. **動作保証**: 既存のクリックハンドラ・フォーム送信・バリデーションを壊さない
6. **i18n必須チェック**: 変更前後で `rg -g "*.tsx" 'label=|aria-label=|placeholder=' <file>` で対象を確認

---

## PR分割計画

### PR-0（このPR）— recon + 計画ドキュメント

| 項目 | 内容 |
|------|------|
| 対象 | `docs/handoff/ui-standardization/recon.md` + `plan.md` |
| 変更 | ドキュメントのみ。frontend実装変更なし |
| 目的 | 全体把握・計画共有・PO承認 |
| リスク | ゼロ |

---

### PR-A — Contact系コンポーネント 標準化（LOW リスク）

**目的**: 既に `<Button>` / `<Modal>` 部分採用済みのファイルを完全標準化。影響範囲が狭い。

**対象ファイル**:

| ファイル | button→Button | input→TextField | select→Select | textarea→Textarea |
|----------|:---:|:---:|:---:|:---:|
| `components/CompanyContactsTab.tsx` | 7 | 9 | - | - |
| `components/ContactChannelForm.tsx` | 5 | 4 | - | - |
| `components/MergeContactModal.tsx` | 3 | 3 | - | - |

**合計**: button 15件、input 16件

**受入条件**:
- [ ] `rg "<button" frontend/src/components/CompanyContactsTab.tsx frontend/src/components/ContactChannelForm.tsx frontend/src/components/MergeContactModal.tsx` → 0件
- [ ] `rg "<input" ...同上...` → 0件
- [ ] TypeScriptビルドエラーなし（`npm run type-check`）
- [ ] `rg 'label=|aria-label=|placeholder=' ...対象ファイル...` で i18n 対応確認
- [ ] 連絡先追加・マージ・チャンネル追加フローを手動確認

**視覚確認ポイント**:
- 連絡先一覧タブのボタン並び
- コンタクトマージモーダルの警告表示（インライン→トークン置換）
- チャンネル追加フォームの入力フィールド

**危険フラグ**: なし

---

### PR-B — Company系コンポーネント 標準化（LOW-MEDIUM）

**対象ファイル**:

| ファイル | button→Button | input→TextField | select→Select | 備考 |
|----------|:---:|:---:|:---:|------|
| `components/MergeCompanyModal.tsx` | 4 | 3 | - | インライン警告スタイル置換も |
| `components/CompanyAddressModal.tsx` | 3 | 4 | - | Modal既使用 |
| `components/CompanyDetailPage.tsx` | 14 | 5 | 2 | 規模大きめ・段階確認 |

**受入条件**:
- [ ] `rg "<button|<input|<select" ...対象ファイル...` → 0件
- [ ] インラインスタイル警告（`style=.*color`）→ 0件（対象ファイル内）
- [ ] TypeScriptビルドエラーなし
- [ ] 会社詳細ページ・マージ・住所編集フローを手動確認

**危険フラグ**: `CompanyDetailPage.tsx` はbutton 14件と規模大。単独サブPRも可。

---

### PR-C — ChannelsPage + InboxSettingsModal 標準化（MEDIUM）

**対象ファイル**:

| ファイル | button→Button | select→Select | 備考 |
|----------|:---:|:---:|------|
| `pages/ChannelsPage.tsx` | ~8 | ~5 | インライン警告スタイル多数 |
| `components/InboxSettingsModal.tsx` | 3 | 2 | Button既使用・完全移行 |

**受入条件**:
- [ ] `rg 'style=.*color' frontend/src/pages/ChannelsPage.tsx` → 0件
- [ ] チャンネル設定の保存・キャンセル動作確認
- [ ] WhatsApp/LINE/Instagram チャンネル表示切替確認

**危険フラグ**: ChannelsPage のインライン状態表示（接続済/未接続）は CSS クラスへの移行が必要。デザイントークン変数を確認すること（`--color-success` / `--color-warning` 等）。

---

### PR-D — Order/Lead/Knowledge系（HIGH 規模）

**対象ファイル（例）**:

| ファイル | button | input | select | textarea |
|----------|--------|-------|--------|----------|
| `pages/OrderDetailPage.tsx` | 9 | ~8 | 6 | - |
| `pages/LeadsPage.tsx` | 11 | ~7 | ~4 | - |
| `components/KnowledgeAliasesTab.tsx` | 13 | ~5 | ~3 | - |
| `components/SuppliersAdminTab.tsx` | 12 | ~6 | ~4 | - |

**受入条件**:
- [ ] 受注詳細・リード管理の既存フロー（ステータス変更・保存）を手動確認
- [ ] E2Eテストが存在する場合は実行してグリーン確認

**危険フラグ**: 受注周りはビジネスロジック密着度が高い。PR-Aの完了・承認後に着手。

---

### PR-E — 大規模ページ（CompaniesPage / InboxKartePanel / ProductEditPage）

**対象ファイル**:

| ファイル | button | input | select | textarea | 規模 |
|----------|--------|-------|--------|----------|------|
| `pages/CompaniesPage.tsx` | ~6 | 28 | 12 | - | 最大 |
| `components/InboxKartePanel.tsx` | 14 | 21 | 9 | 8 | 最大 |
| `pages/ProductEditPage.tsx` | ~4 | 25 | 8 | 5 | 大 |

**受入条件**:
- [ ] 会社一覧の検索・フィルタ動作確認
- [ ] カルテパネルの全入力フィールド・保存動作確認
- [ ] 商品編集の全フィールド・保存動作確認
- [ ] TypeScriptビルドエラーなし
- [ ] `npm run test:frontend` グリーン（存在する場合）

**危険フラグ**:  
- `CompaniesPage.tsx` の input 28件は検索バー・フィルタ・一括操作等が混在。機能ごとのサブPR分割を推奨
- `InboxKartePanel.tsx` はリアルタイム更新UIを含む可能性。動作確認に受信箱テストデータ必要

---

## PR実行順序

```
PR-0（このPR）← 現在
    ↓ PO承認後
PR-A（Contact系）— 最小リスクで効果確認
    ↓ CI緑 + Reviewer APPROVE + Evaluator APPROVE
PR-B（Company系）
    ↓ 同上
PR-C（Channels系）
    ↓ 同上
PR-D（Order/Lead系）
    ↓ 同上
PR-E（大規模ページ）
```

---

## 各PRの共通チェックリスト

```markdown
### 置き換え後チェック
- [ ] rg "<button" <対象ファイル> → 0件
- [ ] rg "<input" <対象ファイル> → 0件（typeのみ残可）
- [ ] rg "<select" <対象ファイル> → 0件
- [ ] rg "<textarea" <対象ファイル> → 0件
- [ ] rg 'style=.*color' <対象ファイル> → 0件（トークン変数使用に変更）
- [ ] rg 'btn-' <対象ファイル> → 0件（Buttonコンポーネント経由に変更）

### ビルド
- [ ] npm run type-check → エラーなし
- [ ] npm run build → エラーなし

### i18n
- [ ] ハードコード日本語なし（rg '>[ぁ-ん一-龯]' <対象ファイル>）
- [ ] 新規 label/placeholder/aria-label は t() 経由

### アクセシビリティ
- [ ] ボタンに aria-label または テキストコンテンツあり
- [ ] input に htmlFor と対応 label あり
- [ ] エラーメッセージに role="alert" あり
```

---

## リスク・軽減策

| リスク | 対象PR | 軽減策 |
|--------|--------|--------|
| フォームのバリデーション破壊 | PR-A〜E全般 | `...rest` スプレッドで既存propsを維持 |
| ラベル・プレースホルダーのi18n漏れ | PR-A〜E全般 | PR前後でrg確認必須 |
| CSS競合（btn-* と comp-btn の混在） | PR-A〜C | 1ファイル1PR内で全置換。混在コミット禁止 |
| インラインスタイル → トークン変換の色ズレ | PR-B,C | 変更前のスクリーンショット + 変更後の視覚確認 |
| 大規模ページの動作回帰 | PR-D,E | 受入前に主要ユーザーフロー手動テスト |
| Modal内のフォーカストラップ干渉 | PR-A,B | Modalの標準実装はフォーカストラップ内蔵済み。二重適用に注意 |

---

## 参照

- `docs/handoff/ui-standardization/recon.md` — 調査データ詳細
- `docs/specs/component-standard.md` — コンポーネント仕様
- `frontend/src/components/Button.tsx` — 標準Button実装
- `frontend/src/components/TextField.tsx` — 標準TextField実装
- `frontend/src/components/Select.tsx` — 標準Select実装
- `frontend/src/components/Textarea.tsx` — 標準Textarea実装
- `frontend/src/components/Modal.tsx` — 標準Modal実装
- `docs/adr/ADR-067-*.md` — デザイントークン強制
- `docs/adr/ADR-027-*.md` — UI国際化
