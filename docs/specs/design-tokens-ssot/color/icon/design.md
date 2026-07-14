# design — アイコン色の用途別トークン集約

親: [../README.md](../README.md)

> 1行要約: 10箇所に分散したアイコン色指定を、用途カテゴリ別の `--icon-*` トークンに集約し、値は既存土台色を参照する。各カテゴリ1トークンを直せばそのカテゴリの全アイコンに届く状態にする。

> 現状把握: docs/handoff/color-tokens-ssot/recon.md
> 準拠ADR: ADR-067（デザイントークン強制システム・docs/adr/ADR-067-design-token-enforcement.md）

## 1. あるべき姿

親テーマ `ideal-state.md` を正本とする。アイコン色は `index.css` に集約され、コンポーネント側は `--icon-*` 参照だけを持つ。色の意味は用途カテゴリごとに保ち、実装箇所の色選択を減らす。

## 2. KGI（○×）

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| ① | アイコンの固定色指定（`color="white"` 等）が 0 件になったか | grep 件数 | 0 |
| ② | 用途別アイコン色トークン（`--icon-*`）が `index.css` に定義されたか | 定義数 ÷ 必要数 | 満数 |
| ③ | 10 箇所の色決定ポイントが用途別トークンを参照する形に集約されたか | 集約済み ÷ 10 | 満数 |
| ④ | 新規 `--icon-*` トークンの値がすべて既存土台色の参照か | 新規 hex 数 | 0 |
| ⑤ | 同一用途カテゴリ内でアイコン色が統一されたか | カテゴリ内不整合数 | 0 |

## 3. design（技術 How）

### 3-1. 用途別アイコン色トークンの定義（`index.css`）

#### 基本カテゴリ

| `--icon-*` | 参照先 | 役割 |
|---|---|---|
| `--icon-nav` | `var(--text-secondary)` | ナビゲーションの既定色 |
| `--icon-nav-active` | `var(--sidebar-item-active-color)` | ナビゲーションの hover / active |
| `--icon-action` | `var(--text-secondary)` | 押せる操作アイコンの既定色 |
| `--icon-action-hover` | `var(--text-primary)` | 操作アイコンの hover 色 |
| `--icon-action-danger` | `var(--danger)` | 危険操作のアイコン色 |
| `--icon-decorative` | `var(--accent)` | 見出し装飾・セクション先頭 |
| `--icon-search` | `var(--text-secondary)` | 検索欄の補助アイコン |
| `--icon-empty` | `var(--text-muted)` | 空状態の補助アイコン |
| `--icon-platform-mail` | `var(--on-solid)` | ブランド / プラットフォームの白アイコン |

#### 状態表示カテゴリ

| `--icon-*` | 参照先 | 役割 |
|---|---|---|
| `--icon-status-neutral` | `var(--neutral-text)` | neutral バッジの先頭アイコン |
| `--icon-status-info` | `var(--info-text)` | info バッジの先頭アイコン |
| `--icon-status-success` | `var(--success-text)` | success バッジ / lock の先頭アイコン |
| `--icon-status-warning` | `var(--warning-text)` | warning バッジの先頭アイコン |
| `--icon-status-danger` | `var(--danger-text)` | danger バッジの先頭アイコン |
| `--icon-status-calendar-ok` | `var(--calendar-status-ok-text)` | Google Calendar 接続正常の先頭アイコン |
| `--icon-status-calendar-error` | `var(--calendar-status-error-text)` | Google Calendar 切断の先頭アイコン |

#### ライト / ダーク

- 上記 `--icon-*` は両テーマで値を変えず、参照先の土台トークンが `:root` と `:root.force-dark` で切り替わる前提とする。
- 新規 hex は追加しない。

### 3-2. 10 箇所の集約対応表

| 現色決定ポイント | file:line | 現在の色指定 | 集約後の `--icon-*` | 種別 |
|---|---|---|---|---|
| `.icon-btn` | `frontend/src/components.css:736-754` | `var(--text-secondary)` / hover `var(--text-primary)` / danger `var(--danger)` | `--icon-action` / `--icon-action-hover` / `--icon-action-danger` | アクション/操作 |
| `.sidebar-item` | `frontend/src/sidebar.css:132-168` | `var(--text-secondary)` / hover・active `var(--sidebar-item-active-color)` | `--icon-nav` / `--icon-nav-active` | ナビゲーション |
| `.nav-item-list__item` | `frontend/src/mobile-shell.css:200-241` | `var(--text-secondary)` / hover・active `var(--sidebar-item-active-color)` | `--icon-nav` / `--icon-nav-active` | ナビゲーション |
| `.db-section-icon` | `frontend/src/pages/dashboard/DashboardPage.css:99-103` | `var(--accent)` | `--icon-decorative` | セクション装飾 |
| `.inbox-search-icon` | `frontend/src/pages/inbox/InboxPage.css:122-127` | `var(--text-secondary)` | `--icon-search` | 補助/検索 |
| `.karte-lock-icon` | `frontend/src/pages/inbox/InboxPage.css:1348-1350` | `var(--success-text)` | `--icon-status-success` | 状態表示 |
| `.comp-empty__icon` | `frontend/src/components/EmptyState.css:27-35` | `var(--text-muted)` | `--icon-empty` | 空状態/補助 |
| `.comp-badge` | `frontend/src/components/Badge.css:13-24`, `frontend/src/components/Badge.css:39-59` | `var(--neutral-text)` / `var(--info-text)` / `var(--success-text)` / `var(--warning-text)` / `var(--danger-text)` / solid は `var(--on-solid)` | `--icon-status-neutral` / `--icon-status-info` / `--icon-status-success` / `--icon-status-warning` / `--icon-status-danger` | 状態表示 |
| Google Calendar ステータスバー | `frontend/src/components/GoogleCalendarStatusBar.tsx:123-173` | inline `style.color` で `var(--calendar-status-ok-text)` / `var(--calendar-status-error-text)` | `--icon-status-calendar-ok` / `--icon-status-calendar-error` | 状態表示 |
| `PlatformIcon` mail/email 分岐 | `frontend/src/constants/icons.tsx:312-320` | `color="white"` | `--icon-platform-mail` | ブランド/プラットフォーム |

### 3-3. 生色指定の解消

- `PlatformIcon` の `color="white"` は `--icon-platform-mail` に置き換え、`var(--on-solid)` を参照する。
- Google Calendar ステータスバーは `cfg.color` を使った inline の `style.color` を保ちつつ、アイコン色としては `--icon-status-calendar-ok` / `--icon-status-calendar-error` を参照する形にそろえる。
- `PlatformIcon` と Google Calendar ステータスバー以外に、固定 hex / 固定色文字列は残さない。

### 3-4. 状態別（hover / active）の扱い

- `sidebar-item` と `nav-item-list__item` は、ベースを `--icon-nav`、hover / active を `--icon-nav-active` に分ける。
- `icon-btn` は、ベースを `--icon-action`、hover を `--icon-action-hover`、danger を `--icon-action-danger` に分ける。
- `comp-badge` は状態そのものが色意味なので、hover / active ではなく variant 別のサブトークン群で扱う。
- `karte-lock-icon` と Google Calendar ステータスバーは、状態そのものが単独トークンで成立するため、追加の hover / active サブトークンは置かない。

## 4. 弊害・トレードオフ

- 集約により触る箇所が広く、Visual Gate 差分が広範に出る可能性がある。ただし値は既存土台色参照のため、色値自体の差分は最小に抑えられる。
- 状態別サブトークンが増えると管理点が増えるため、用途カテゴリを崩さない範囲で必要最小限にとどめる。
- フロントのみ・バックエンド不変・GO 不要。

## 5. 受入基準

| 基準 | 検証方法 |
|---|---|
| `color="white"` 等の固定色指定が0件 | 変更後ファイルを grep -rn 'color="' frontend/src で確認し0件 |
| index.css に --icon-* が必要数そろっている | grep -n '\-\-icon\-' frontend/src/index.css で定義本数を確認 |
| 10箇所の色決定ポイントが --icon-* 参照に置換 | §3-2 対応表の10行を各ファイルで実測し全置換を確認 |
| 新規hexが増えていない | guard-hex-increase チェックが pass |
| 同一用途カテゴリ内の色不整合が0件 | カテゴリ別に参照トークンを目視突合し不整合0 |

## 外部・過去事例の参照と我々への応用

用途別セマンティックトークン（役割で色を束ねる）は Material/Primer 等の設計体系で確立した手法。これを --icon-*（nav/action/status/decorative）として応用し、生hex直書きを解消する。小規模なため深掘りは行わず、既存土台色の参照に限定する。

## 6. 維持の仕組み

- アイコン色は `--icon-*` 経由でしか使わない。
- 新規アイコンや新しい利用箇所を追加するときは、まず用途カテゴリを決め、対応する `--icon-*` を `index.css` に置く。
- `color="white"` / 直書き色の再発は grep で検出する。

## 7. 接触面分析（6 面）

| 面 | 事実 |
|---|---|
| 人 | 予定や状態を色で見分ける利用者に関わる |
| エージェント | 実装役は `index.css` と各利用箇所の参照を更新する |
| 機械 | 色差は Visual Gate と grep で確認する |
| データ | DB は変更しない |
| 本番 | migration は不要 |
| 外部 | 連携先 API や外部 GUI の変更はない |
