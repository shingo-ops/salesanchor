# 設計: 実ページ標準化パイロット — TeamsPage Modal 置換

> **作成日**: 2026-06-09  
> **ステータス**: Accepted  
> **参照**: recon = `docs/handoff/realpage-standardization/recon.md` / ADR-122

---

## KGI

| | before | after |
|--|--------|-------|
| TeamsPage の modal-overlay | **2件** | **0件** |
| 標準 Modal コンポーネントの実ページ採用 | 0件 | 1件（テンプレ確立） |
| a11y（Esc・フォーカストラップ・aria）| なし | あり（Modal 標準） |

---

## 技術 How

### 前提: Modal.css のバグ修正（必須）

`frontend/src/components/Modal.css:29` に未定義トークン使用を確認:

```css
/* 現状（バグ）*/
background: var(--surface-primary);

/* 修正後 */
background: var(--bg-surface);
```

`--surface-primary` はトークン定義なし（`grep -rn "surface-primary" frontend/src/tokens.css` → 0件）。  
`--bg-surface` は `frontend/src/index.css:10` で `#ffffff`（ライト）/ `:188` で `#1e293b`（ダーク）定義済み。  
この修正がないと Modal ダイアログの背景が透明になる。

---

### Modal 1: チーム作成・編集フォーム（TeamsPage.tsx:159–180）

#### before（現状）

```tsx
{showForm && (
  <div className="modal-overlay" onClick={() => setShowForm(false)}>
    <div className="modal" onClick={(e) => e.stopPropagation()}>
      <h3>{editId ? t("teams.editTeam") : t("teams.newTeam")}</h3>
      <form onSubmit={handleSubmit}>
        {/* フォームフィールド */}
        <div className="form-actions">
          <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>{t("common.cancel")}</button>
          <button type="submit" className="btn-primary">{editId ? t("common.update") : t("common.create")}</button>
        </div>
      </form>
    </div>
  </div>
)}
```

#### after（置換後）

```tsx
import { Modal } from "../../components/Modal";  // 追加

<Modal
  open={showForm}
  onClose={() => { setShowForm(false); setEditId(null); setForm(emptyForm); }}
  title={editId ? t("teams.editTeam") : t("teams.newTeam")}
  size="md"
>
  <form onSubmit={handleSubmit}>
    {/* フォームフィールドはそのまま */}
    <div className="form-actions">
      <button type="button" className="btn-secondary" onClick={() => { setShowForm(false); setEditId(null); setForm(emptyForm); }}>{t("common.cancel")}</button>
      <button type="submit" className="btn-primary">{editId ? t("common.update") : t("common.create")}</button>
    </div>
  </form>
</Modal>
```

**マッピング**:

| 旧 | 新 | 備考 |
|---|---|------|
| `modal-overlay` div | `<Modal open={showForm}>` | open prop で制御 |
| `modal` div | Modal 内部の `comp-modal-dialog` | 自動レンダリング |
| `<h3>` タイトル | `title` prop → Modal ヘッダ | Modal が h2 で描画 |
| overlay click 閉じ | `onClose` prop → `dismissOnOverlay` 機能 | デフォルト true |
| `form-actions` 中 cancel | form-actions に残す | Modal ヘッダの × と併存 |
| `form.onSubmit` | `<form onSubmit>` のまま | footer prop は使わない |

**`onClose` の中身**:  
現状の overlay click は `setShowForm(false)` のみ。  
これを `setShowForm(false); setEditId(null); setForm(emptyForm);` に拡張する。  
理由: Esc 閉鎖が追加されるため、閉鎖時に状態をリセットする必要がある。

---

### Modal 2: メンバー管理パネル（TeamsPage.tsx:182–217）

#### before（現状）

```tsx
{membersPanel && (
  <div className="modal-overlay" onClick={() => setMembersPanel(null)}>
    <div className="modal" onClick={(e) => e.stopPropagation()}>
      <h3>{t("teams.manageMembersTitle", { name: membersPanel.name })}</h3>
      {/* メンバー追加フォーム + テーブル */}
      <div className="form-actions">
        <button type="button" className="btn-secondary" onClick={() => setMembersPanel(null)}>{t("common.close")}</button>
      </div>
    </div>
  </div>
)}
```

#### after（置換後）

```tsx
<Modal
  open={!!membersPanel}
  onClose={() => setMembersPanel(null)}
  title={membersPanel ? t("teams.manageMembersTitle", { name: membersPanel.name }) : ""}
  size="md"
>
  {membersPanel && (
    <>
      {hasPermission("teams.manage_members") && (
        <form onSubmit={addMember} className="teams-add-member-form">
          {/* メンバー追加フォームフィールド（そのまま） */}
        </form>
      )}
      <table className="data-table">
        {/* メンバーテーブル（そのまま） */}
      </table>
    </>
  )}
</Modal>
```

**マッピング**:

| 旧 | 新 | 備考 |
|---|---|------|
| `modal-overlay` div | `<Modal open={!!membersPanel}>` | null チェックは `!!` で |
| `<h3>` タイトル | `title` prop | `membersPanel` null 時は `""` |
| overlay click 閉じ | `onClose={() => setMembersPanel(null)}` | Esc も同動作 |
| 末尾の「閉じる」 button | **削除**（Modal ヘッダ × ボタンで代替） | `form-actions` div ごと削除 |

**`style={{ marginBottom: "var(--space-4)" }}`（TeamsPage.tsx:187）**:  
`add-member-form` CSS クラスを設けるか、`form-actions` の慣習クラスを流用。  
Generator は `className="teams-add-member-form"` を追加し、CSS クラスで余白を持つこと（インライン style は残さない）。

---

## 視覚パリティ分析

### 同等トークンの確認

| 属性 | 旧 `.modal` / `.modal-overlay` | 新 `Modal` コンポーネント |
|------|-------------------------------|--------------------------|
| 背景色 | `var(--bg-surface)` | `var(--bg-surface)`（バグ修正後） |
| 影 | `var(--shadow-modal)` | `var(--shadow-modal)` |
| 角丸 | `var(--radius-lg)` | `var(--radius-lg)` |
| オーバーレイ背景 | `var(--overlay-bg)` | `var(--overlay-bg)` |
| 最大幅 | `var(--modal-max-w)` = 500px | `--modal-max-w-md` = 600px |
| 最大高 | `90vh` | `calc(100vh - var(--space-8))` ≈ `90vh` |

**⚠️ 差分1（幅）**: 旧 `--modal-max-w` = 500px、新 `--modal-max-w-md` = 600px。  
TeamsPage は通常フォームのため 600px で問題なし。Evaluator ビジュアル確認必須。

**⚠️ 差分2（パディング）**:  
旧 `.modal`: `padding: var(--space-6) var(--space-8) var(--space-8)` （一体型スクロール）  
新 `.comp-modal-body`: `padding: var(--space-5) var(--space-6)` （ヘッダ/ボディ/フッタ分離）  
フォームの余白感が若干変わる可能性あり。Evaluator で確認。

**⚠️ 差分3（タイトル要素）**:  
旧: `<h3>` が body 内に配置。`margin: 0 0 var(--space-5)` で下余白  
新: `<h2>` がヘッダ区画に配置（`border-bottom: 1px solid var(--border-subtle)` 区切り線付き）

**追加挙動（改善）**:
- Esc でモーダルを閉じる（既存なし → 追加）
- 背景クリックで閉じる（`dismissOnOverlay=true`、既存と同動作）
- フォーカストラップ（既存なし → 追加）
- フォーカス復帰（既存なし → 追加）
- X ボタンが Modal ヘッダに追加（既存なし → 追加）

---

## CSS 追加（TeamsPage 用）

`frontend/src/pages/teams/TeamsPage.css`（新規作成、またはインライン style の CSS クラス化）:

```css
/* TeamsPage: メンバー追加フォームの下余白 */
.teams-add-member-form {
  margin-bottom: var(--space-4);
}
```

TeamsPage に専用 CSS ファイルがない場合は `frontend/src/pages/teams/TeamsPage.css` を新規作成し、  
`TeamsPage.tsx` 冒頭で `import "./TeamsPage.css"` する。

---

## import 変更

```tsx
// before
import ConfirmModal from "../../components/ConfirmModal";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";

// after
import ConfirmModal from "../../components/ConfirmModal";
import { Modal } from "../../components/Modal";           // ← 追加
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
```

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `modal-overlay` が TeamsPage から消える（0件） | `grep "modal-overlay" TeamsPage.tsx` → 0件 |
| `<Modal` が TeamsPage に 2件ある | `grep "<Modal" TeamsPage.tsx` → 2件 |
| `--surface-primary` が Modal.css から消える | `grep "surface-primary" Modal.css` → 0件 |
| 見た目が現状と同等 | Evaluator ビジュアル差分（parity） |
| チーム作成・編集・削除・メンバー管理が動作する | 動作確認 |
| Esc でモーダルが閉じる（新機能） | 手動確認 |
| フォーム送信後にモーダルが閉じ状態リセットされる | 手動確認 |
| 他ページのコード変更 0件 | `git diff` で TeamsPage + Modal.css + TeamsPage.css のみ |

---

## 置換テンプレ（他24ファイル用）

```
# modal-overlay → Modal 置換チェックリスト（共通手順）

1. import に `import { Modal } from "../../components/Modal";` を追加
2. `<div className="modal-overlay" onClick={closeFn}>` → `<Modal open={...} onClose={closeFn} title={t("...")} size="md">`
3. `<div className="modal" onClick={(e) => e.stopPropagation()}>` → 削除（Modal が自動挿入）
4. `<h3>タイトル</h3>` → title prop に移動（Modal ヘッダで描画される）、h3 削除
5. 閉じるボタンのみの form-actions → 削除（Modal ヘッダの × ボタンで代替）
   フォームアクション（submit/cancel）は form-actions に残す
6. `onClose` の中身: 状態リセットを追加（Esc 閉鎖でも同動作させるため）
7. インライン style を CSS クラスに変換（任意）
8. Evaluator 確認（幅・パディングの微差あり）
```

---

## 外部・過去事例の参照と我々への応用

shadcn/ui の Dialog コンポーネント設計（portal + フォーカストラップ + Esc + aria）は本 Modal コンポーネント（Task 7C）の参照パターン。raw div モーダルからの脱却は React エコシステムでの標準的な段階移行パターン。TeamsPage を最小単位のパイロットとして成功させ、他24ページへ展開する戦略は「仕様を固めてからスケール」の原則に合致する。

過去の失敗: `Modal.css` が `var(--surface-primary)` という未定義トークンを使用していたことで、実ページ採用前のバグが隠蔽されていた。Storybook では問題が顕在化しにくい（独立レンダリング環境のため）。実ページ統合時に必ずバグ修正を先行させること。
