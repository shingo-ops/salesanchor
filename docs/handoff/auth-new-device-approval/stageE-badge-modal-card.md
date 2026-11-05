# 段E 実装カード: 鈴のバッジをインスタの大きさに・ログインの依頼を真ん中の小窓で完結（ADR-1055）

状態: 設計案作成済み・Opus 自己審査済み（§10。同じAIによる審査で、独立した第三者の審査ではない）。実装承認: PO 2026-11-05「1」と「確立したなら進める」。クラウドの Sonnet が実装する。

## 1. 目的（PO の言葉）

- 「鈴の大きさと通知の赤バッジの大きさがアンマッチしているのでインスタと同じ仕様にできる？」→ PO は「1」（数字入りの赤い丸。インスタのメッセージのバッジと同じ形）を選んだ。
- 「この通知に関してはポップアップで完結させられる？例えば通知内容をクリックしたら中央にポップアップ出してそのポップアップ内で完結させる」
- 共通の決まり（PO 原文の要旨）: 推測禁止・配線と DB の正本を守り分散させない・デザイントークンと金型を守り、金型登録の無い直書き禁止。

## 2. 根拠（実測と実物）

### 2-1. インスタの実測（2026-11-05、PC の Chrome、PO のログイン状態、OS はダーク）

記録: `/tmp/CC報告ファイル/staged2/instagram-measure.md`（拡大写真 `instagram-badges-zoom.png`）。リポジトリ外の作業記録で、ここに数値を写す。

| 項目 | 値 |
|---|---|
| 横の帯のアイコン | 24×24 |
| メッセージの数のバッジ 外寸 | 22×22（content-box・min-width 18px・padding 0・枠 2px solid・角 50px） |
| 枠の色 | 3 か所とも、バッジの真後ろの背景色と同じ（rgb(12,16,20) が 2 回、rgb(33,35,40) が 1 回） |
| 塗り | rgb(255,48,64) |
| 文字 | 11px・行の高さ 18px・太さ 400・白 |
| アイコンからの位置 | バッジの外枠の左上が、アイコンの左上から 右 +11・下 +9（右下に重なる） |
| 確かめていない | ライト表示の値・2 桁以上のときの幅・スマホのアプリ |

### 2-2. アプリの今（origin/main）

- 鈴のボタン `frontend/src/components/NoticeBell.css:32-45` は 40×40（`--notice-bell-size` = `--avatar-zone-width`、`frontend/src/tokens.css:238`）。
- 鈴の絵は `frontend/src/components/NoticeBell.tsx:220` で `BellOutline size={ICON.base}`（20px、`frontend/src/tokens.css:257`）。
- バッジは `frontend/src/components/NoticeBell.tsx:222` で `<Badge variant="danger" appearance="solid" size="sm">`。
  - `frontend/src/components/Badge.css:55-58` の `.comp-badge--sm` は padding `2px 8px`・min-height 20px（`frontend/src/tokens.css:544`）。
  - 文字は `--font-xs` 12px・太さ medium（`frontend/src/components/Badge.css:26-27`）。
  - 位置は `frontend/src/components/NoticeBell.css:51-55` で右上 4px。
  - このため、横長のピル型が鈴の右上に乗り、インスタと形・大きさ・位置が違う。
- 赤は `--comp-badge-danger-solid`（`frontend/src/index.css:122` で `var(--danger)`、ダークは `:311` で #dc2626）。文字は `--on-solid`。
- 鈴の真後ろは `.app-body`（`frontend/src/sidebar.css:273-282`）。`background-color: var(--bg-surface)`（:279）の上に `--inbox-bg-gradient`（`frontend/src/index.css:171`・ダーク :371）が重なる。本番で `elementsFromPoint` で確かめた（2026-11-05）。
- 依頼の行を押すと `frontend/src/components/NoticeBell.tsx:134-137` で `/account/login-requests/:id` へ移る（元の画面から離れる）。
- 詳しい画面は `frontend/src/features/auth/LoginRequestDetailPage.tsx`（152 行）。経路は `frontend/src/App.tsx:110`（import）と `:299`（Route）。
- 金型の小窓 `frontend/src/components/Modal.tsx` は `{open,onClose,title,size,dismissOnOverlay,children,footer}` を持ち、Esc で閉じる・中に操作を閉じ込める・portal で真ん中に出す。
- 知らせのメールは詳しい画面へのリンクを持たない（`backend/app` に `account/login-requests` の文字列なし。段Dの審査で確認済み）。詳しい画面を消しても外から入る道は無い。

## 3. 決めたこと（選んだ理由）

| # | 決めたこと | 理由 | 選ばなかった案 |
|---|---|---|---|
| D1 | 数のバッジは金型 `Badge` に新しい大きさ `count` を足して作る | 金型の外に直書きしない（ADR-144）。他の画面の数のバッジも同じ形で使える | 鈴の CSS だけで上書き → 金型の外の直書きになる |
| D2 | 赤はアプリの `--comp-badge-danger-solid` のまま | 色の正本を 2 つにしない。インスタの赤は使わない | インスタの rgb(255,48,64) を新しく足す |
| D3 | 文字は既存の `--font-2xs`（11.2px）、太さ `--font-weight-normal`（400） | 11px のトークンは無い。差は 0.2px で目に見えず、新しい段を足さない | 11px の新トークン |
| D4 | 枠の色は `--bg-surface`（`.app-body` の地の色） | インスタは真後ろの色。アプリの真後ろは `.app-body` で、その地の色が `--bg-surface`。グラデーションは淡く、地の色に一番近い単色がこれ | 枠なし → インスタと外寸が違う／グラデーションの色を直書き → 正本が分かれる |
| D5 | 鈴の絵は `ICON.lg`（24px） | インスタのアイコン 24 に合わせる。ボタン 40×40 は変えない（アバターと並びを崩さない） | ボタンも 44 にする |
| D6 | 位置はアイコンからの差 +11/+9 をトークンにし、`calc` で置く | 実測どおり。数字の直書きを CSS に置かない | 右上 4px のまま |
| D7 | 依頼は鈴の中から金型 `Modal` で真ん中に開き、その中で決め切る。URL は変えない | PO の依頼。中身は詳しい画面の本体を 1 つの部品に移し、同じものを使う（写しを作らない） | 詳しい画面を残して小窓と 2 つ持つ → 同じ動きが 2 か所になる |
| D8 | 詳しい画面と経路は消す | 入口は鈴だけになる。メールにもリンクが無い（§2-2） | 経路を残す |
| D9 | スマホの下のタブ（`variant="tab"`）の見た目は変えない。小窓で決め切る動きはスマホにも効く | 依頼は PC の鈴の見た目。動きは部品が 1 つなので両方同じになる | スマホも数の丸を変える → 範囲外（別の CSS `.mobile-tab-badge`） |

## 4. 触る範囲

### 4-1. 金型のトークン `frontend/src/tokens.css`（`--comp-badge-*` の並び、:541-548 の近く）

足す（値はこのとおり）:

```css
  --comp-badge-count-size:  18px;                 /* 数の丸の中身の高さ・最小幅（Instagram 実測 2026-11-05） */
  --comp-badge-count-ring:  var(--space-2px);     /* 2px — 数の丸の外枠の太さ（Instagram 実測） */
  --comp-badge-count-font:  var(--font-2xs);      /* 11.2px — Instagram 実測 11px に一番近い既存の段 */
```

`tokens.css` で 18px のトークンを探した結果（origin/main ab8a6f725）: `--size-toggle-knob`（:274 トグルのつまみ）・`--nav-badge-size`（:366 ナビの未読バッジ）・`--comp-chat-input-font-mobile`（:192）・`--karte-h-pad`（:346）。どれも別の意味の値なので参照しない。上のとおり `--comp-badge-count-size: 18px` を新しく置く。

鈴の位置（`--notice-*` の並び、:238-242 の近く）に足す:

```css
  --notice-bell-icon-size:        var(--icon-lg);   /* 24px — 鈴の絵（Instagram 実測 24） */
  --notice-bell-badge-offset-x:   11px;             /* 鈴の絵の左から数の丸の左まで（Instagram 実測） */
  --notice-bell-badge-offset-y:   9px;              /* 鈴の絵の上から数の丸の上まで（Instagram 実測） */
```

### 4-2. 色のトークン `frontend/src/index.css`（:120-122 の `--comp-badge-*-solid` の近く。ライトの `:root` の中だけ）

```css
  --comp-badge-count-ring-color: var(--bg-surface);  /* 数の丸の外枠＝後ろの地の色（Instagram は真後ろの色） */
```

ダークの塊には足さない（`--bg-surface` がダークで #1e293b に変わるので、そのまま追う）。足したあとダーク表示で枠の色が `--bg-surface` のダークの値になることを §7 の K2 で確かめる。

### 4-3. 金型 `frontend/src/components/Badge.tsx` と `Badge.css`

- `BadgeSize` を `'sm' | 'md' | 'count'` にする。コメントの説明に `count = 数の丸（Instagram 実測）` を足す。
- `Badge.css` の「2. サイズ」の後ろに足す:

```css
/* 数の丸（鈴などの未読数）。Instagram 実測: 中身 18・枠 2・外寸 22 */
.comp-badge.comp-badge--count {
  box-sizing: content-box;
  justify-content: center;
  min-width: var(--comp-badge-count-size);
  height: var(--comp-badge-count-size);
  padding: 0;
  border: var(--comp-badge-count-ring) solid var(--comp-badge-count-ring-color);
  font-size: var(--comp-badge-count-font);
  font-weight: var(--font-weight-normal);
  line-height: var(--comp-badge-count-size);
}
```

- `Badge.stories.tsx` に `count` の見本を 1 つ足す（1 桁・2 桁・99+ の 3 つを並べる）。
- `Badge` の試験ファイルがあれば `count` のクラスが付くことを 1 件足す。無ければ `NoticeBell.test.tsx` 側で確かめる。

### 4-4. 鈴 `frontend/src/components/NoticeBell.tsx` と `NoticeBell.css`

- `:220` の PC の鈴: `BellOutline size={ICON.lg}`。`:205` のスマホのタブは `ICON.base` のまま。
- `:222`: `size="sm"` → `size="count"`。
- `NoticeBell.css:51-55` を次に替える:

```css
.notice-bell-badge {
  position: absolute;
  top: calc((var(--notice-bell-size) - var(--notice-bell-icon-size)) / 2 + var(--notice-bell-badge-offset-y));
  left: calc((var(--notice-bell-size) - var(--notice-bell-icon-size)) / 2 + var(--notice-bell-badge-offset-x));
}
```

- 小窓:
  - `const [openRequestId, setOpenRequestId] = useState<string | null>(null);` を足す。
  - `handleRequestClick` は `setOpen(false); setOpenRequestId(req.id);` にする。`useNavigate` と `navigate` は使わなくなるので消す。
  - 両方の return（`variant === "tab"` と PC）で、`Popover` の外の同じ階層に次を置く（Fragment で包む）:

```tsx
<Modal
  open={openRequestId !== null}
  onClose={() => { setOpenRequestId(null); loadPending(); }}
  title={t("login.deviceApproval.detail.title")}
  size="sm"
>
  {openRequestId !== null && (
    <LoginRequestDecision requestId={openRequestId} onLeave={() => setOpenRequestId(null)} />
  )}
</Modal>
```

  - 型の import を `../features/auth/LoginRequestDecision` に替える。
  - 冒頭のコメント（:6）を「依頼の行を押すと真ん中の小窓が開き、その中で決め切る（URL は変えない）」に直す。

### 4-5. 本体の部品 `frontend/src/features/auth/LoginRequestDecision.tsx`（新規。詳しい画面の本体を移す）

- `LoginRequestDetailPage.tsx:18-149` をそのまま移す。違いは次の 4 つだけ:
  1. `export default function LoginRequestDecision({ requestId, onLeave }: { requestId: string; onLeave: () => void })`。`useParams` を使わず `requestId` で探す。
  2. `PageLayout` で包まず、`body` をそのまま返す。
  3. 「パスワードを変える」の `<Link to="/account/settings">` に `onClick={onLeave}` を付ける（移ったら小窓を閉じる）。
  4. 冒頭のコメントを「鈴の小窓の中身（ADR-1055 段E）」にする。
- `PendingLoginRequest` の型はこのファイルから export する。
- 新しい口・新しい保存先は作らない。読むのは `GET /login-approvals/pending`、送るのは `/auth/login-requests/{id}/approve` と `/reject`（今と同じ）。

### 4-6. 消すもの

- `frontend/src/features/auth/LoginRequestDetailPage.tsx`
- `frontend/src/features/auth/LoginRequestDetailPage.test.tsx`（中の試験は §4-7 の新しい試験へ移す）
- `frontend/src/App.tsx:110` の import と `:299` の Route
- 消したあと `git grep -n -e LoginRequestDetailPage -e "login-requests/:id"` が frontend・tests・scripts で 0 件になること（docs の過去の記録は残す）。

### 4-7. 試験

- `frontend/src/features/auth/LoginRequestDecision.test.tsx`（新規）: 今の `LoginRequestDetailPage.test.tsx` の 5 件を、`<LoginRequestDecision requestId="req-1" onLeave={...} />` を直に描く形に移す（経路の包みは要らない）。
- `frontend/src/components/NoticeBell.test.tsx:89-98` の「詳しい画面へ移る」試験を次に替える:
  - 行を押すと `role="dialog"` が出て、その中に `detail.title` と `detail.itsMe` のボタンがある。
  - `where`（今の URL）は最初のまま変わらない。
  - `api.post` は呼ばれていない。
- `NoticeBell.test.tsx` に 1 件足す: 未読があるとき、バッジに `comp-badge--count` のクラスが付く。
- `tests/prod-check/device-accept.spec.ts`:
  - `:103-105` のコメントを「小窓の題名」に直す。
  - `openRequestFromBell`（:113-）は、題名を `page.getByRole("dialog")` の中で待つ。押す前と後で `page.url()` が同じことを確かめる。
  - `:283-286` の「私です」と「許可しました」も `getByRole("dialog")` の中で探す。
  - 本番では流さない（PO と後で流す）。

### 4-8. 文字（i18n）

- 新しいキーは足さない。`login.deviceApproval.detail.*` と `watcher.*` を今のまま使う。ja と en のキー数は今と同じであること。

## 5. 触らない範囲

- backend・DB・migrations・deploy.yml・secrets・workflow・本番の scripts
- スマホの下のタブのバッジ `.mobile-tab-badge`（`frontend/src/mobile-shell.css:160`）
- 知らせのメールの文面（「私ではない」とボタン「私ではありません」の揃えは別件）
- 使わないキー `watcher.title` の掃除（別件）
- `Popover` と `Modal` の金型の中身

## 6. 想定される分岐（迷ったら止まる）

- `Badge` の試験ファイルが無い → `NoticeBell.test.tsx` 側の 1 件で足りる。作らない。
- `Modal` を `Popover` の外に置くと `openOnHover` で一覧が開いたままになる → 止まって報告。勝手に `Popover` を変えない。
- 消した経路を指す箇所が §4-6 の 2 か所以外に見つかった（ページ一覧・速さの記録・メニューなど）→ 止まって報告。
- CSS の検査（デザイントークン・直書きの見張り）が §4-1 の `11px`・`9px`・`18px` を止めた → tokens.css の中はトークン定義なので通るはず。止めたら言い換えず、止まって報告。
- `check-nav-title-sync.js` などページの題名の検査が落ちた → 止まって報告。

## 7. 受入条件

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | PC の鈴の絵が 24×24 | 本番で `[data-testid=notice-bell] svg` の `getBoundingClientRect()` |
| K2 | 未読 1 桁のときバッジの外寸 22×22・枠 2px・文字 11.2px・太さ 400・塗りが `--comp-badge-danger-solid`・枠の色が `--bg-surface` と同じ（ライトとダークの両方） | 本番で `.notice-bell-badge` の `getBoundingClientRect()` と `getComputedStyle()` |
| K3 | バッジの左上が鈴の絵の左上から 右 11・下 9（±0.5） | 同上で 2 つの差を引く |
| K4 | 依頼の行を押すと真ん中に小窓が出て、URL が変わらない | 試験（NoticeBell.test）＋本番で PO の目視 |
| K5 | 小窓で「私です」→番号を選ぶと、小窓の中に「ログインを許可しました」 | 試験（LoginRequestDecision.test）＋本番の受入試験 K2〜K4 |
| K6 | 小窓で「私ではありません」を押すと、小窓の中に拒否の結果 | 試験（LoginRequestDecision.test） |
| K7 | `LoginRequestDetailPage` と経路 `/account/login-requests/:id` が frontend・tests・scripts から 0 件 | `git grep` |
| K8 | tsc・lint・vitest 全件・ja/en のキー数一致・必須 CI 緑 | 実装報告の生出力と CI |

## 8. 戻し方

frontend だけの変更。PR を revert すれば元の鈴と詳しい画面に戻る。DB の変更なし。

## 9. 外部事例

Instagram の Web 版の画面を 2026-11-05 に PC の Chrome で実測した値（§2-1）を見本にする。これは見た目の寸法の見本で、使われやすさの効果を示す根拠には使わない。確かめていないのはライト表示・2 桁以上・スマホのアプリ。

## 10. Opus 自己審査（同じAIによる審査。独立した第三者の審査ではない）

- 既存の仕様と食い違わないか: ADR-1055 の正本 `public.auth_login_requests` と口はそのまま。写しを作らない → 合う。
- 金型と直書き: 数の丸は金型 `Badge` に `count` を足す。数字は tokens.css の中だけ → ADR-067・ADR-144 に合う。
- 根拠: 大きさ・位置はインスタの実測。アプリの今は origin/main の行番号で示した。
- 受入条件: K1〜K3 は数で測る。K4〜K7 は試験と grep で ○× が出る。
- 残る不確かさ: 枠の色（D4）はグラデーションの上なので、インスタの「真後ろと同じ色」とは完全には一致しない。差は淡いグラデーションの分だけで、PO の目視で決める。合わなければ枠の色のトークン 1 つを替えるだけで直る。
- 判定: APPROVE（実装可）。未解決の前提なし。
