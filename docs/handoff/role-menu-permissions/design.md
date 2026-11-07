# 役割の画面をメニューごとの3択にする — 設計（design）

| 項目 | 内容 |
|------|------|
| 状態 | 設計案（Opus 作成・自己審査は §10）。クラウドの設計審査の結果は §11 |
| 現在地 | `docs/handoff/role-menu-permissions/recon.md` |
| ADR | 新規なし。理由: サーバー・DB・許可の意味を変えない画面の作り直しで、新しい仕組みの決定を含まないため。部品の追加は ADR-144 の手順に従う |
| PO の決定 | ①Discord の権限画面の形で ✕／✓ の3択（2026-11-07）②完成イメージの見た目は「イメージ通り」（2026-11-07）③メニューごとに設定。同じ許可のメニューは1行にまとめる案2（2026-11-07「2」）④営業ロールの許可は AI が変えない。PO が自分で設定する（2026-11-07「2」） |
| 完成イメージ | https://claude.ai/artifact/EpTEWEwpePki7C52Krcdb3 の「案2」 |
| 危険 PR か | いいえ。`migrations/`・`deploy.yml`・本番 `scripts/` を含まない |

## 0. 目的（PO の言葉）

- 「ロールページだけどDiscordのチャンネルロールみたいに出来る？非表示、表示のみ、編集可の３択」
- 「今のページとやれることは一緒だけど、UI/UXをDiscordの権限のレイアウトにしたい」
- 「このUIでメニューごとに設定ができるようにしたい」
- 目的（2回問い直し）:
  - 役割ごとに、どのメニューが見えて何ができるかを、一目で分かるようにしたい。
  - その先で、PO が技術の言葉を読まずに、スタッフの見える範囲を自分で正しく決められるようにしたい。

## 1. 受入の基準と検証方法（○×で見る）

| # | 基準 | 検証方法 |
|---|---|---|
| 1 | 役割の画面に、メニューの行が並び、各行の右に ✕ ／ ✓ の3つの切替が出る | 自動試験（3つのボタンが出る）＋本番で PO が目で見る |
| 2 | ✕ を押して保存すると、その行の許可が全部外れる | 自動試験（保存で送る一覧にその行の許可が 0 件） |
| 3 | ／ を押して保存すると、その行の「見る」許可だけが付く | 自動試験（送る一覧 = 見る許可だけ） |
| 4 | ✓ を押して保存すると、その行の許可が全部付く | 自動試験（送る一覧 = 行の許可すべて） |
| 5 | 一部だけ持つ行は「個別」と出る。開くと許可1つずつを ✕ ／ ✓ で切り替えられる | 自動試験＋本番で営業ロールの「リード・顧客」行が「個別」と出ることを目で見る |
| 6 | 画面を開いて何も触らないと「保存」は押せない。送る一覧も変わらない（画面に出ない `menu.*` 19 件も残る） | 自動試験（未変更で保存ボタン無効・1行変えて戻すと未変更に戻る・保存の一覧に `menu.*` が残る） |
| 7 | 本番の許可 135 件のうち `menu.*` 19 件を除く 116 件が、どれか1つの行に必ず出る。2つの行に重ねて出る許可は 0 件 | 自動試験（本番と同じ 135 件の一覧を入れて数える） |
| 8 | まとめた行の名前は、左の列と管理センターのメニュー名をそのままつないだものになる | 自動試験（行の名前の鍵が左の列・管理センターと同じ鍵） |
| 9 | 左の列（PC・スマホ）と管理センターのメニューの出方は今と1つも変わらない | 既存の試験が緑＋新しい試験（許可の組み合わせごとに出るメニューが前と同じ） |
| 10 | オーナーなどシステムのロールと、編集の許可が無い人には、切替が押せない（今と同じ） | 自動試験 |
| 11 | 色・寸法の直書き 0 件、画面の日本語の直書き 0 件、`ja.json` と `en.json` の鍵が一致 | CI（UI 金型の関所・ESLint・言葉の鍵の検査）が緑 |
| 12 | 新しい切替部品がカタログ（Storybook）に出る | `SegmentedToggle.stories.tsx` があり、Storybook のビルドが緑 |
| 13 | 本番で営業ロールを開いて何も保存しなければ、営業の許可の数は変わらない | 本番の読み取り専用 DB で、開く前と後の `role_permissions` の件数が同じ |
| 14 | スマホの幅（390px）でも行が横にはみ出さない | 自動の画面試験か本番で目で見る |

## 2. 外部・過去事例の参照と我々への応用

- 外部の事例: Discord のロールの権限画面。PO が画面の写真で示した。各権限の右に「✕ ／ ✓」の3つの切替が並ぶ。
  - 我々への応用: 並べ方と3つの切替の形だけを写す。中身の意味（非表示・表示のみ・編集可）は PO の言葉で決める。
  - 成功を外部の数値で示す直接の根拠は無い。外部の数値は使わない。成功は §1 の○×だけで判定する。
- 社内の事例: 今の役割の画面に「メニュー表示」の切替がある（`frontend/src/pages/roles/RolesPage.tsx:197-217`）。区分ごとに「見る」許可だけを付け外しする。本件の「表示のみ」は、この考え方を全部の行に広げたもの。

## 3. 対象と対象外

- 対象（画面だけ）:
  - `frontend/src/pages/roles/RolesPage.tsx` の右側（許可の並べ方と切替）。
  - 新しい部品 `frontend/src/components/SegmentedToggle.tsx` / `.css` / `.stories.tsx` / `.test.tsx`。
  - 新しい設定 `frontend/src/constants/menuPermissions.ts`（メニューと許可の対応の正本）。
  - 左の列（`DesktopShell.tsx` / `MobileShell.tsx`）と管理センター（`ManagementCenterPage.tsx`）の「許可で出す条件」を、上の正本から読むように置き換える。出方は変えない。
  - `frontend/src/constants/icons.tsx` に斜め線のアイコンを1つ登録する。
  - `ja.json` / `en.json` に言葉の鍵を足す。
- 対象外:
  - サーバー（`backend/`）、DB、`migrations/`、`deploy.yml`、本番 `scripts/`。
  - どのロールの許可も変えない（営業の会話の許可は PO が自分で付ける）。
  - 左側のロールの一覧・ロールの作成/編集/削除の窓。今のまま。
  - 管理センターへの入口を出す条件（`frontend/src/components/DesktopShell.tsx:186-191`）。11 個の許可の一覧で、管理センターの中の条件と完全には一致しない（例: `conditions.view` だけの人は入口が出ない）。出方が変わるため今回は触らない。§9 の「次の課題」に記す。
  - `menu.*` 19 件の整理・削除。画面に出さず、保存のときはそのまま残す。
  - 使わなくなる言葉の鍵（`roles.categoryPagePerm` など）と `CATEGORY_ICONS` の削除。他から使われていないか確かめる手間が要るため、今回は残す。

## 4. 変更前と変更後

- 変更前: 区分（顧客・リード・注文など）ごとの箱。箱ごとに「全部」「メニュー表示」の2つの欄と、許可1つずつのチェック欄が並ぶ。
- 変更後:
  - 上に凡例「✕ 非表示　／ 表示のみ　✓ 編集可　｜　「個別」は一部だけ許可（開くと1つずつ選べる）」。
  - 区切りごとに、メニューの行が並ぶ。各行の右に3つの切替。
  - 一部だけ持つ行は名前の横に「個別」と出る。押すと下に許可1つずつの行が開く。
  - 右上の「元に戻す」「保存」、未保存の帯は今のまま。

## 5. メニューと許可の対応（正本 `frontend/src/constants/menuPermissions.ts`）

### 5-1. メニューを出す条件（今の実物をそのまま写す）

| メニューの名前の鍵 | 出す条件（どれか1つを持つ） | 今の場所 |
|---|---|---|
| `nav.dashboard` | `dashboard.view` | DesktopShell 231 / MobileShell 128 |
| `nav.inventory` | `products.view` | DesktopShell 273 / MobileShell 302 |
| `nav.quotesInvoices` | `quotes.view` `invoices.view`（各自の設定の条件は画面側に残す） | DesktopShell 179-181 / MobileShell 121-122 |
| `nav.leads` | `leads.view` `customers.view` | DesktopShell 177 / MobileShell 118 |
| `nav.orders` `nav.sales` `nav.commissions` | `orders.view` | DesktopShell 318/331/344 / MobileShell 316 |
| `nav.commissionSettings` | `orders.view` | ManagementCenter 41 |
| `nav.staff` | `staff.view` | ManagementCenter 37 |
| `nav.roles` | `roles.view` `roles.create` | ManagementCenter 38 |
| `nav.teams` | `teams.view` | ManagementCenter 39 |
| `nav.shifts` | `shifts.view` | ManagementCenter 40 |
| `nav.tenantPolicy` `nav.tenantProfile` `nav.discordConfig` `nav.discordAnnounce` | `tenant.profile.edit` `tenant.profile.view` | ManagementCenter 43-44 / 70-73 / 80-81 |
| `nav.suppliers` `nav.statusMaster` `nav.units` `nav.noteMaster` | `suppliers.view` | ManagementCenter 51/52/55/56 |
| `nav.conditionsMaster` | `conditions.view` | ManagementCenter 53 |
| `nav.productCategories` | `product_categories.view` | ManagementCenter 54 |
| `nav.dataManagement` `nav.integrationGoogleDrive` `nav.integrationFedex` `nav.integrationDhl` `nav.integrationUps` `nav.integrationPaypal` | `erp.view` | ManagementCenter 57 / 65-69 |
| `nav.channels` | `channels.view` | ManagementCenter 82 |
| `nav.channelMasters` | `tenant.profile.edit` | ManagementCenter 83 |
| `nav.bots` | `bots.view` | ManagementCenter 84 |
| `nav.notifications` | `notifications.manage` | ManagementCenter 85 |

- 形（例）:

```ts
export type MenuId = "dashboard" | "inventory" | "quotesInvoices" | "crm" | "orders" | "sales" | "commissions" | /* …表の全部… */;
export const MENUS: Record<MenuId, { labelKey: string; anyOf: readonly string[] }> = {
  dashboard: { labelKey: "nav.dashboard", anyOf: ["dashboard.view"] },
  // …
};
export function canSeeMenu(id: MenuId, hasAny: (...keys: string[]) => boolean): boolean {
  return hasAny(...MENUS[id].anyOf);
}
```

- 置き換え: 上の表の「今の場所」の条件を `canSeeMenu("…", hasAny)` に替える。各自の設定（`prefs.show_sales_menu` / `prefs.show_chat_menu`）・`isTenantOwner`・`visible: true`・行き先の選び分け（`salesLinkTo`）は今のまま画面側に残す。
- `MobileShell.tsx` は今 `hasAny` を取り出していない（`frontend/src/components/MobileShell.tsx:79`）。`usePermissions()` から `hasAny` も取り出す。

### 5-2. 役割の画面の行（同じ正本に書く）

- 行の形: `{ id, section, menus: MenuId[] | null, keys: string[], fixed?: "always" | "ownerOnly", noteKey?: string }`。
- 行の名前: `menus` の `labelKey` を `t()` して「・」でつなぐ。下の表の日本語の行名は説明用。画面に出る名前は今の nav の文言になる（2026-11-07 の `ja.json`: 受信箱・在庫表・見積・請求管理・顧客管理・受注管理・売上管理・報酬管理・報酬設定・ステータスマスタ・状態マスタ・商品カテゴリ・発行者情報・テナントポリシー・Discord 連携設定・Discordアナウンス・チャンネル・チャネル管理・通知設定・ログインの許可待ち）。`menus` が2つ以上なら下に「N つのメニューが1つの許可で一緒に出たり消えたりします」。

| 区切り | 行（メニュー） | 行の許可 | 補足 |
|---|---|---|---|
| 左の列 | ダッシュボード | `dashboard.view` | 編集の許可が無いので ✓ は押せない |
| 左の列 | スケジュール | なし | 固定「誰にでも出ます」 |
| 左の列 | 会話（`nav.leadChat`） | `messaging.view` `messaging.send` | 注記「メニューは各自の表示設定でも切り替わります」 |
| 左の列 | 在庫 | `products.view/create/update/delete` | |
| 左の列 | 見積・請求 | `quotes.view/create/update/delete/approve` `invoices.view/create/update/void` | 注記「メニューは各自の表示設定でも切り替わります」 |
| 左の列 | リード・顧客（`nav.leads`） | `leads.*`（10 件）`customers.*`（4 件） | |
| 左の列 | 受注・売上・報酬・報酬設定 | `orders.view/create/update/delete` | 4つのメニュー |
| チーム | スタッフ | `staff.view/create/update/delete` | |
| チーム | ロール | `roles.view/create/update/delete/assign` | |
| チーム | チーム | `teams.view/create/update/delete/manage_members` | |
| チーム | シフト | `shifts.view/manage` | |
| チーム | レポート | `reports.view` `reports.export` | 注記「メニューはいつも出ます。中の数字の見え方が変わります」 |
| データ | 仕入先・ステータスマスタ・単位・メモマスタ | `suppliers.view/create/update/delete` | 4つのメニュー |
| データ | 状態マスタ | `conditions.view/create/update/delete` | |
| データ | 商品区分 | `product_categories.view/edit/delete` | |
| データ | データ管理・Googleドライブ・FedEx・DHL・UPS・PayPal | `erp.view` `erp.sync` | 6つのメニュー |
| 事業 | 会社情報・会社ポリシー・Discord設定・Discordお知らせ・連絡手段の名簿 | `tenant.profile.view` `tenant.profile.edit` | 注記「連絡手段の名簿は編集可のときだけ出ます」 |
| 事業 | 連絡手段 | `channels.view` `channels.manage` | |
| 事業 | Bot | `bots.view/create/update/delete` | |
| 事業 | 通知 | `notifications.view` `notifications.manage` | 注記「メニューは編集可のときだけ出ます」 |
| 事業 | ログイン申請 | なし | 固定「オーナーだけに出ます」 |
| メニュー以外の許可 | 残りを区分（`category`）ごとに1行 | 上のどの行にも入らず `menu.` で始まらない許可 | 行の名前は DB の区分名（今の画面と同じ） |

- 「メニュー以外の許可」は自動で作る。正本に書くのは「上の行に入れた許可」だけ。新しい許可が DB に増えても、この区切りに自動で出る。
- 本番の 135 件で、この区切りに入る見込みの許可: `deals.*` `goals.*` `analytics.*` `archive.*` `badges.*` `buddy.*` `central.*` `inventory.visibility.*` `tenant.inventory_visibility.edit` `phase.switch` `purchase_orders.*` `shipping.*` `staff_reports.*` `system.*`。

## 6. 3択のきまり

- 「見る」許可: 名前の最後の部分が `view` か、`view_` で始まるか、`_view` で終わるもの。
  - 例: `orders.view`、`buddy.view_own`、`staff_reports.view_team`、`system.audit_view`。
- 行の許可のうち、持っているものの数で状態を決める。

| 持っている許可 | 状態 | 画面 |
|---|---|---|
| 0 件 | 非表示 | ✕ が選ばれている |
| 見る許可だけ全部（他は 0） | 表示のみ | ／ が選ばれている |
| 全部 | 編集可 | ✓ が選ばれている |
| それ以外 | 個別 | どれも選ばれていない。名前の横に「個別」 |

- 見る許可しか無い行（例: ダッシュボード）: ✓ は押せない。全部持つと「表示のみ」と出る。
- 見る許可が無い行（例: 中央マスタ）: ／ は押せない。
- 押したとき:
  - ✕: 行の許可を全部外す。
  - ／: 見る許可だけを付け、他を外す。
  - ✓: 行の許可を全部付ける。
  - 「個別」の行でも3つは押せる。押すとその状態にそろう。
- 「個別」のボタン: 許可が2件以上ある行に出す。一部だけ持つときは注意の色の印（`Badge` warning）。それ以外は控えめなボタン（`Button` ghost sm）。押すと下に許可1つずつの行が開く。
  - 1つずつの行: 名前は `p.description`（今の画面と同じ）。右に ✕ ／ ✓ の2択（同じ部品）。
- 押せない条件は今と同じ（`frontend/src/pages/roles/RolesPage.tsx:172-173`）。
- 保存は今と同じ（編集中の一覧を丸ごと送る）。`menu.*` は画面に出ないが、一覧から消さないので残る。

## 7. 新しい部品 `SegmentedToggle`（ADR-144 の金型）

- 置き場: `frontend/src/components/SegmentedToggle.tsx` / `.css` / `.stories.tsx` / `.test.tsx`。
- 業務の意味は持たせない（許可という言葉を部品に入れない）。
- 形:

```ts
export type SegmentedTone = "danger" | "neutral" | "success";
export interface SegmentedOption<V extends string> {
  value: V;
  icon: Icon;               // constants/icons.tsx のもの
  label: string;            // 読み上げ用。呼び出し側で t() 済み
  tone: SegmentedTone;
  disabled?: boolean;
}
export interface SegmentedToggleProps<V extends string> {
  options: SegmentedOption<V>[];   // 2〜3 個
  value: V | null;                 // null = どれも選ばれていない（個別）
  onChange: (value: V) => void;
  "aria-label": string;            // 行の名前
  disabled?: boolean;
}
```

- 中身: `role="radiogroup"` の中に `<button type="button" role="radio" aria-checked>` を並べる。アイコンだけのボタンなので `aria-label` に `label` を入れる。
- 見た目（CSS は `var()` だけ）:
  - 外枠: `--border` の線と角丸の変数。
  - 選ばれていないボタン: 背景 `--bg-subtle`、アイコン `--text-muted`。
  - 選ばれたボタン: danger は `--color-error-bg` と `--color-error`、neutral は `--border-strong` 系と本文色、success は `--color-success-bg` と `--color-success`。
  - 押せないボタン: 薄くする変数（`--opacity-dim`）。
  - 大きさ: 既存の寸法の変数（`--size-icon-btn-sm` など）。直の数字は書かない。
  - フォーカス: `--focus-ring-shadow`。
- アイコン: ✕ は `STATUS_ICONS.error`、✓ は `STATUS_ICONS.check`。斜め線は `@heroicons/react/24/outline` の `SlashIcon` を `constants/icons.tsx` に登録して使う（今の `hi()` の包み方に合わせる）。
- カタログ: 3択・2択・どれも選ばれていない・押せない、の4つの見本。
- 試験: 押すと `onChange` が値つきで呼ばれる。押せないボタンでは呼ばれない。`aria-checked` が正しい。

## 8. 言葉の鍵（`ja.json` / `en.json` に同じ鍵）

| 鍵 | 日本語 | 英語 |
|---|---|---|
| `roles.legend` | ✕ 非表示　／ 表示のみ　✓ 編集可　｜　「個別」は一部だけ許可（開くと1つずつ選べる） | ✕ Hidden / View only ✓ Can edit · "Custom" means some are allowed (open to choose one by one) |
| `roles.stateOff` | 非表示 | Hidden |
| `roles.stateView` | 表示のみ | View only |
| `roles.stateEdit` | 編集可 | Can edit |
| `roles.permDeny` | 許可しない | Deny |
| `roles.permAllow` | 許可する | Allow |
| `roles.individual` | 個別 | Custom |
| `roles.sectionSidebar` | 左の列のメニュー | Sidebar menus |
| `roles.sectionOther` | メニュー以外の許可 | Other permissions |
| `roles.menusTogether` | {{count}}つのメニューが1つの許可で一緒に出たり消えたりします | These {{count}} menus appear and disappear together with one permission |
| `roles.fixedAlways` | 誰にでも出ます | Shown to everyone |
| `roles.fixedOwner` | オーナーだけに出ます | Shown to the owner only |
| `roles.notePrefs` | メニューは各自の表示設定でも切り替わります | Each person's display setting can also hide this menu |
| `roles.noteReports` | メニューはいつも出ます。中の数字の見え方が変わります | The menu is always shown. This changes which numbers are visible |
| `roles.noteChannelMasters` | 連絡手段の名簿は編集可のときだけ出ます | The channel list menu is shown only with Can edit |
| `roles.noteEditOnly` | メニューは編集可のときだけ出ます | The menu is shown only with Can edit |

- 管理センターの区切りの名前は今の鍵（`managementCenter.sectionTeam` / `sectionData` / `sectionBusiness`）を使う。

## 9. 影響範囲・危険と対処・戻し方

- 呼び出し元:
  - `canSeeMenu` を使うのは `DesktopShell.tsx` / `MobileShell.tsx` / `ManagementCenterPage.tsx` / `RolesPage.tsx` の4つだけ。
  - `SegmentedToggle` を使うのは `RolesPage.tsx` だけ。
- 危険と対処:
  - メニューの出方が変わってしまう → §1 の 9。置き換え前の条件と置き換え後の条件を、許可の組み合わせごとに比べる試験を足す。既存の `DesktopShell.test.tsx` も緑のまま。
  - 保存で許可が消える → §1 の 6 と 13。画面に出ない `menu.*` を消さない試験。本番は保存しない確認だけ。
  - 自分が持たない許可を ✓ で付けようとすると、保存でサーバーが断る（403）。これは今の「全部」の欄と同じ動き。今回は変えない。
- 戻し方: この PR のマージを取り消す（revert）。サーバーと DB は変えていないので、画面が前に戻るだけ。
- 次の課題（今回はしない）:
  - 管理センターの入口を出す条件を正本から作る（`DesktopShell.tsx:186-191`）。出方が変わるので PO の確認が要る。
  - `menu.*` 19 件と、使わなくなった言葉の鍵の整理。

## 10. 自己審査（Opus・同じ AI による審査で、独立した審査ではない）

- 既存の仕様・ADR との整合: ADR-144 / 067 / 027 / 147 と食い違いなし。サーバーの置き換え保存（`backend/app/routers/roles.py:414-480`）をそのまま使う。
- 根拠: 行番号は recon の実物。許可 135 件は本番の読み取り結果。
- 受入の基準: 14 件すべて○×で判定できる。
- 実装の範囲: §3 の対象のファイルだけ。触らない場所も §3 に書いた。
- 判定: APPROVE（クラウドの設計審査に回す）。

## 11. クラウドの設計審査

- （審査の結果をここに書く）

## 12. 維持の仕組み（誰が・何が守るか）

- メニューと許可の対応は `menuPermissions.ts` の1か所だけ。左の列・管理センター・役割の画面が同じものを読むので、片方だけ変わることが無い。
- 新しいメニューを足す人は `MENUS` に1行足す。足さないと役割の画面に出ない。これを試験で止める（§1 の 7: 全部の許可がどこかの行に出る）。
- 新しい許可が DB に増えたときは「メニュー以外の許可」に自動で出る。消えて設定できない許可は出ない。
- 色・寸法・言葉は CI（UI 金型の関所・ESLint・言葉の鍵の検査）が止める。
