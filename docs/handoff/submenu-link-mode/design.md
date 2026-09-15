# design: submenu-link-mode

**対象:** PR #2650 — SubMenu にリンク型（ドア型）対応を追加
**対象ADR:** ADR-149
**recon:** docs/handoff/submenu-link-mode/recon.md

---

## 外部・過去事例の参照と我々への応用

- react-router-dom v7 の NavLink は className に isActive を渡すコールバック形式をサポートしており、active 判定をルーターに委ねる本設計はその標準パターンに沿う。
- 同リポジトリ内の既存の遷移型メニュー（`frontend/src/pages/management-center/ManagementCenterPage.tsx:94` の NavLink）と同一の土台を用いるため、新規依存は導入しない。
- ルーティング検査テストは既存 `frontend/src/components/NavItemList.test.tsx:47`（MemoryRouter ラップ）の作法を踏襲する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| リンク型が実際に別ページへ遷移する | `SubMenu.test.tsx`「door item navigates」: to を持つ項目が link として描画され、href 一致＋クリックで遷移先が表示される。vitest green |
| 既存のコールバック型が壊れない | `SubMenu.test.tsx`「remote item calls onChange」: to を持たない項目のクリックで onChange(key) が呼ばれる。vitest green |
| 単一テーマ（巻き込みなし） | `git diff --name-only origin/develop...HEAD` が SubMenu.tsx / SubMenu.test.tsx の2件のみ |
| 型・lint | `tsc --noEmit` / `eslint` がともに EXIT=0 |

---

## 技術 How・KPI

SubMenuItem に任意フィールド `to?: string` を追加する。描画時に `item.to` の有無で分岐する。

- `to` あり: NavLink として描画。active 判定はルーター（NavLink の isActive）に委ねる。disabled 時は onClick で preventDefault。
- `to` なし: 従来どおり `<button>` ＋ onClick で onChange を呼ぶ（既存挙動を完全維持）。

併せて props の `onChange` を任意化する（リンク専用メニューでは onChange 不要なため）。既存呼び出しは全て onChange を渡しているため挙動は不変。

変更ファイルは `frontend/src/components/SubMenu.tsx` と新規テスト `frontend/src/components/SubMenu.test.tsx` の2点のみ。CSS・デザイン見本・置換対象3ページには本PRでは触れない。

---

## 弊害・トレードオフ

- リンク型は `<a>` で描画されるため、ブラウザ既定の下線等が出る可能性。本PRのスコープ外とし、置換側PR（管理センター・顧客ハブ）の画面確認で検証する。
- onChange 任意化により型シグネチャが変わるが、既存呼び出しは全て onChange を渡しており非回帰。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | SubMenu に `to?` フィールドと NavLink 分岐を追加 | Generator |
| 2 | SubMenu.test.tsx でリンク型・コールバック型の両ケースを検証 | Generator |
| 3 | 管理センター・顧客ハブを SubMenu に置換（次PR） | Generator |
| 4 | ロールを SubMenu に置換（次PR） | Generator |

---

## 継続

注文の絞り込みメニューは段階移行の後続で個別に判断。develop 上の生UI部品（ADR-144関連・6ファイル）は本PRと無関係の別件として切り出し、別途対処する。
