# ロール画面の配置の直し — 設計（design）

| 項目 | 内容 |
|------|------|
| 状態 | 設計案（Opus 作成）。自己審査は §9 |
| 現在地 | `docs/handoff/role-page-layout/recon.md` |
| ADR | 新規なし。理由: 画面の配置だけの直しで、新しい仕組みの決定を含まない。高さの作り方は `frontend/src/tokens.css:247-254` の既存の決まりに従う |
| PO の決定 | 2026-11-08 の3点（recon §0）。スマホは Android 側が対応し、ここでは記録だけ |
| 完成イメージ | https://claude.ai/artifact/EpTEWEwpePki7C52Krcdb3（案2。左の一覧は最初の案と同じ） |
| 危険 PR か | いいえ。`migrations/`・`.github/workflows/deploy.yml`・本番 `scripts/` を含まない。DB・API・許可の意味は変えない |

## 0. 目的

- 役割を選ぶ一覧を、完成イメージの「色の丸＋名前」が平らに並ぶ形にする。
- 権限の表が長くても、表の中だけで上下に動かせるようにする。見出しと左の一覧は動かない。
- 保存の操作を、表を見終わった位置（表の下）で行えるようにする。

## 1. 受入の基準と検証方法

| # | 基準 | 検証方法 |
|---|---|---|
| 1 | 左の一覧は字下げ無しで平らに並び、各行の左にそのロールの色の丸が出る | 本番の画面で目で見る＋DOM で各行の丸の背景色が `/roles` の `color` と同じ（色が空の行は `--border` の色） |
| 2 | 選ばれた行は背景が塗られ、文字が太い。他の行は背景なし | 本番の画面で目で見る（管理センターの左メニューの選ばれた行と同じ見た目） |
| 3 | 行を押すとそのロールに切り替わる。未保存の変更があれば今と同じ確認が出る | 本番で別の行を押して右の見出しのロール名が変わる |
| 4 | `/management-center/roles` で、権限の表の中だけが上下に動く。画面全体・右の見出し・左の一覧は動かない | 本番で表の上でホイールを回し、表の `scrollTop` が増え、`.hub-content` と `.app-content` の `scrollTop` が 0 のまま |
| 5 | 単独の道 `/roles` でも #4 と同じ | 本番の `/roles` で同じ確認 |
| 6 | 表の一番下の行まで見られる（切れない） | 表を一番下まで動かし、最後の区分の最後の行が見える |
| 7 | 「変更を保存」は表の下に出る。「変更をキャンセル」も並んで表の下に出る。見出しの右には編集・削除だけが残る | 本番の画面で目で見る＋DOM で保存ボタンが表の入れ物より下にある |
| 8 | 保存の下の段は表を動かしても常に見える | 表を動かしても保存ボタンの位置が変わらない |
| 9 | 変更があるときの黄色の注意書きは、保存の段の左に出る | 1つ切り替えて目で見る（保存はしない） |
| 10 | 許可の件数は変わらない | 本番の読み取り専用 DB で、確認の前後の役割ごとの許可の件数 37 行が同じ |
| 11 | 色・寸法の直書き 0 件、日本語の直書き 0 件 | CI（UI 金型の関所・ESLint・文言の鍵・CSS の直書き検査）が緑 |
| 12 | スマホ幅（767px 以下）は今の動き（右側全体が動く）のまま | 記録だけ（PO 決定: Android 側が対応）。CSS でスマホ幅は高さの固定を外す |

## 2. 変更する場所と変更しない場所

変更する:

- `frontend/src/pages/roles/RolesPage.tsx` — 左の一覧を `SubMenu` に置き換え。保存の段を表の下へ移す。
- `frontend/src/pages-layout.css:441-547` と `:624-634` — ロール画面の高さの連鎖と、保存の段。使わなくなる `.roles-list`・`.role-item*` を消す。
- `frontend/src/pages/roles/RolesPage.css` — 色の丸と保存の段の決まりを足す。
- `frontend/src/tokens.css` — 色の丸の大きさ `--role-color-dot-size` を1つ足す。
- `frontend/src/responsive.css:25-36` — スマホ幅で高さの固定を外す。

変更しない:

- API・DB・許可の一覧・保存の中身（`savePermissions`・`cancelEdits` の処理）。
- 3択の切替と表の中身（`frontend/src/pages/roles/RolesPage.tsx:379-458`）。
- 管理センターの外枠（`frontend/src/hub-shell.css`）と `PageLayout`。
- 新規作成・編集・削除の小窓。
- 左の見出しの文言（今の「ロール・権限管理」）と「＋新規」の位置。

## 3. 変更の中身

### 3-1. 左の一覧（RolesPage.tsx:314-336）

変更前: `<ul className="roles-list">` の中に字下げ付きの `<button className="role-item">`。

変更後:

```tsx
<SubMenu
  variant="flat"
  className="roles-list"
  groups={[{
    items: roles.map((r) => ({
      key: String(r.id),
      label: r.name,
      icon: (
        <span
          className="role-color-dot"
          style={{ background: r.color || "var(--border)" }}
          aria-hidden="true"
        />
      ),
    })),
  }]}
  activeKey={selectedRoleId == null ? "" : String(selectedRoleId)}
  onChange={(key) => selectRole(Number(key))}
/>
```

- `SubMenu` は `import { SubMenu } from "../../components/SubMenu";`。
- 字下げの計算（`level`）は消す。並び順は今と同じ（API `/roles` の順）。
- 色はデータ（`roles.color`）なので、インラインの `background` だけを使う。今の `frontend/src/pages/roles/RolesPage.tsx:327` と同じ扱い。

### 3-2. 色の丸の決まり

`frontend/src/tokens.css` の `--schedule-now-dot-size` の近くに足す:

```css
--role-color-dot-size: 12px;   /* ロール一覧の色の丸（完成イメージ実測 12px） */
```

`frontend/src/pages/roles/RolesPage.css` に足す:

```css
.role-color-dot {
  display: inline-block;
  flex-shrink: 0;
  width: var(--role-color-dot-size);
  height: var(--role-color-dot-size);
  border-radius: var(--radius-full);
}
```

- `--radius-full` は `frontend/src/tokens.css:102` にある（9999px）。`--border` は `frontend/src/index.css:29`（明るい）と `:235`（暗い）にある。

### 3-3. 高さの連鎖（表だけ動かす）

`frontend/src/pages-layout.css` を次の形にする（値は全部 CSS 変数）:

```css
.roles-page {
  padding: var(--space-5);
  height: 100%;
  display: flex;
  flex-direction: column;
}
.roles-page > .error-message { flex-shrink: 0; }
.roles-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 260px 1fr;   /* 既存の値のまま */
  gap: var(--space-5);
  align-items: stretch;
}
.roles-sidebar {
  /* 既存の background / radius / padding / shadow はそのまま */
  min-height: 0;
  overflow-y: auto;
  /* position: sticky と top は消す */
}
.roles-main {
  /* 既存の background / radius / padding / shadow はそのまま */
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.roles-main-header {
  flex-shrink: 0;
  /* position: sticky / top / z-index は消す。他の値はそのまま */
}
```

`frontend/src/pages/roles/RolesPage.css`:

```css
.role-perm-legend { flex-shrink: 0; /* 既存の値はそのまま */ }
.role-perm-sections {
  /* 既存の display / flex-direction / gap はそのまま */
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}
```

- `260px` は今のファイルにある値で、この直しでは触らない。
- 選択中のロールが無いとき（`roles.selectRoleHint` の表示）はこの形のままでよい。

### 3-4. 保存の段（表の下）

`frontend/src/pages/roles/RolesPage.tsx:369-376` の「変更をキャンセル」と「変更を保存」を見出しから外す。`frontend/src/pages/roles/RolesPage.tsx:460-465` の注意書きと一緒に、`.role-perm-sections` の閉じタグの直後に置く:

```tsx
<div className="role-perm-footer">
  {dirty && (
    <div className="unsaved-banner">
      <STATUS_ICONS.warning size={ICON.sm} aria-hidden="true" />
      {" "}{t("roles.unsavedChanges")}{t("roles.unsavedClickHint", { btn: t("roles.saveChanges") })}
    </div>
  )}
  <div className="role-perm-footer-actions">
    <Button variant="secondary" size="md" disabled={!dirty || savingPerms} onClick={cancelEdits}>
      {t("roles.cancelChanges")}
    </Button>
    <Button loading={savingPerms} variant="primary" size="md" disabled={!dirty || savingPerms || !canEditPerms} onClick={savePermissions}>
      {t("roles.saveChanges")}
    </Button>
  </div>
</div>
```

- ボタンの属性（`disabled`・`loading`・`onClick`）は1文字も変えない。
- 見出しの右 `roles-main-actions` には編集・削除だけが残る。編集の許可が無い人は見出しの右が空になる（今も編集・削除は同じ条件で出ない）。

`frontend/src/pages/roles/RolesPage.css`:

```css
.role-perm-footer {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border);
}
.role-perm-footer-actions {
  display: flex;
  gap: var(--space-2);
  margin-left: auto;
  flex-shrink: 0;
}
```

`frontend/src/pages-layout.css:624-634` の `.unsaved-banner` は、`position: sticky`・`bottom`・`margin-top` を消す（段の中に入るため）。色・余白・枠はそのまま。`flex: 1; min-width: 0;` を足す。

### 3-5. スマホ幅（記録のみの扱い）

`frontend/src/responsive.css` の `@media (max-width: 767px)` の中の既存のロール画面の決まりに足す:

```css
.roles-page { height: auto; }
.roles-main { overflow: visible; }
.role-perm-sections { overflow-y: visible; }
```

- 目的は、スマホ幅を今の動き（右側全体が動く）のままにすること。スマホの作りの直しは Android 側が行う（PO 2026-11-08）。

### 3-6. 消すもの

- `frontend/src/pages-layout.css` の `.roles-list`（469-473）、`.role-item`・`:hover`・`.active`・`.active:hover`・`.role-item-name`・`.role-item-meta`（474-508）。使うのはロール画面だけ（recon §3）。
- `frontend/src/pages/roles/RolesPage.tsx` の冒頭の説明（4-11 行）の「上部のキャンセル/保存ボタン」を「表の下の保存の段」に直す。

## 4. 代わりの案と選んだ理由

- 案A（選んだ）: ロール画面の外側の `div` に高さの連鎖を足す。見出しの見た目は変わらない。
- 案B: ロール画面を `PageLayout` で包む。兄弟のページと同じになるが、ページの題と説明の文が新しく出る。PO が頼んでいない見た目の変化なので選ばない。
- 左の一覧に `ListRow` を使う案: 丸い顔写真の大きさの部品で、12px の色の丸に合わないため選ばない（recon §5）。
- 「変更をキャンセル」を上に残す案: 完成イメージでは2つが1組なので、2つとも下へ移す。

## 5. 危ないことと対処

- 高さの連鎖が切れると、表が切れたまま残る。→ 受入 #4〜#6 を本番の両方の道で確かめる。
- 左の一覧の押し方が変わる（`<button>` → `SubMenu` の `<button>`）。→ 受入 #3。未保存の確認は `selectRole` をそのまま使うので変わらない。
- 新しい CSS 変数1つ。→ PR 本文に「デザイントークン変更時」の点検表を書く（色ではないのでダークの対は不要）。

## 6. 試験

- 新しい自動試験は作らない。理由: ロール画面に画面試験の土台が無く（recon §8）、配置の確認は本番の DOM で測るほうが確か。
- CI の型の確認・ESLint・CSS の検査・既存の試験が全部緑であること。

## 7. 維持の仕組み

- 色・寸法の直書きは CI の CSS 検査が止める。
- 左の一覧は `SubMenu` の金型に乗るので、見た目の直しは金型1か所で全部に効く。
- 守り手: CI の「Lint & Dark Mode Check (ADR-067)」（`npm run check:all` の css-values・stylelint・dark-parity）が毎回走り、直書きの色・寸法を止める。金型の見た目は `frontend/src/components/SubMenu.test.tsx` が CI の frontend 試験で毎回確かめる。

## 8. 外部・過去事例の参照と我々への応用

- 不要。理由: 管理センターの左メニュー（`SubMenu`）と、他の画面の高さの連鎖（`PageLayout`）という同じアプリの中の実物に合わせる直しで、外の事例で決める点が無い。

## 9. 自己審査（Opus・同じ AI による審査）

- 既存の決まりとの整合: 高さは `frontend/src/tokens.css:247-254` の形。金型は `SubMenu`。色はデータの値だけ。→ 合う。
- 根拠: 原因は `frontend/src/hub-shell.css:83-88` と `frontend/src/pages/roles/RolesPage.tsx:302` の実物で確かめた。
- 受入の検証: 全部が本番の画面・DOM・DB の数で○×を付けられる。
- 実装の範囲: §2 の5ファイル＋ docs。処理の中身は変えない。
- 判定: APPROVE（設計合格）。未解決: なし。
