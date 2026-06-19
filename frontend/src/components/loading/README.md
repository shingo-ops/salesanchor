# Sales Anchor — ローディング & フィードバック部品パッケージ

Sales Anchor デザインシステム準拠の共用パーツ一式。色・余白・角丸・影・モーションはすべて
既存トークン（`tokens/*.css` の `var(--*)`）を参照しています。**生の値は一切ハードコードしていません** —
トークンを1か所で変えれば全部品に反映され、ダークモード（`:root.force-dark`）も自動で追従します。

> 仕様の早見表は `Component Spec.dc.html`（部品カタログ）を参照。本パッケージはその実装です。

---

## 取り込み手順（開発者向け）

1. `components/` を 本体リポジトリの `frontend/src/components/loading/` などに配置。
2. `loading-animations.css` を `frontend/src/` に置き、**エントリで1回だけ** import：
   ```ts
   // main.tsx（index.css の後）
   import './loading-animations.css';
   ```
3. アプリ最上位に **Toaster** を1つ設置：
   ```tsx
   import { Toaster } from './components/loading';
   // <App> の末尾に
   <Toaster />
   ```
4. 以降はバレル経由で利用：
   ```ts
   import { Spinner, Skeleton, ProgressBar, toast, Drawer, Modal, EmptyState, SaveIndicator, SplashScreen } from './components/loading';
   ```

前提：React 18+ / `react-dom`（`createPortal`）。`<svg>` 利用のため TSX。追加依存なし。

---

## 部品別の配線

### Spinner
```tsx
{isLoading && <Spinner size="md" />}
<Button>{saving ? <Spinner size="sm" onAccent /> : null} 保存</Button>
```

### Skeleton（→ 実データ）
```tsx
{isLoading ? <Skeleton variant="table" rows={5} /> : <OrderTable data={data} />}
```
※ react-query なら `isLoading` をそのまま渡すだけ。

### ProgressBar
```tsx
<ProgressBar value={uploadedPct} variant="striped" label="CSVインポート中" />
<ProgressBar value={syncPct} variant="circular" />
```
100% で自動的に成功色＋✓表示。

### SplashScreen
```tsx
import favicon from '@/assets/favicon.png';
{!appReady ? <SplashScreen logo={<img src={favicon} alt="" width={84} height={84} />} /> : <App />}
```

### Toast（通知）
```tsx
const mutation = useMutation({ mutationFn: ship,
  onSuccess: () => toast.success('発送が完了しました', { description: '受注 #1042・3点' }),
  onError:   () => toast.error('発送に失敗しました'),
});
```
`toast.success | warning | error | info`。どこからでも呼べます（`<Toaster/>` が1つあれば可）。

### SaveIndicator（インライン保存）
```tsx
const [status, setStatus] = useState<SaveStatus>('idle');
// 入力 → debounce → setStatus('saving') → 完了で setStatus('saved')
<SaveIndicator status={status} />
```

### Drawer / Modal
```tsx
<Drawer open={!!selected} onClose={() => setSelected(null)} title={`受注 #${selected?.id}`}>
  …詳細…
</Drawer>

<Modal open={confirm} onClose={() => setConfirm(false)} title="見積を発行しますか？"
  footer={<><Button variant="secondary" onClick={() => setConfirm(false)}>キャンセル</Button>
           <Button onClick={issue}>発行</Button></>}>
  この内容で見積書PDFを作成し、顧客に共有します。
</Modal>
```
オーバーレイクリック / Esc で閉じます。

### EmptyState
```tsx
{rows.length === 0 && (
  <EmptyState icon={<InboxIcon />} title="受注がありません"
    description="新規登録から作成できます"
    action={<Button>新規登録</Button>} />
)}
```

---

## 既存部品を“拡張”するもの（新規ファイル不要）

これらは新コンポーネントを足さず、**既存の仕組みにCSS/propを少し足すだけ**が最適です。

### ① Button の `loading`
既存 `Button` に `loading?: boolean` と `loadingText?: string` を追加し、`true` のとき
`disabled` + 先頭に `<Spinner size="sm" onAccent={variant==='primary'} />` を差し込むだけ。
```tsx
<Button variant="primary" loading={isPending} loadingText="保存中">保存</Button>
```

### ② StatusBadge＝既存 `Badge`
専用部品は不要。業務ステータス→variant を呼び出し側で決めるだけ（**赤は問題系のみ**）。
切替を滑らかにするには Badge に `transition: opacity .4s, transform .4s;` を足すと
クロスフェード＋ポップになります。
```tsx
<Badge variant={paid ? 'success' : 'warning'}>{paid ? '入金済' : '支払待ち'}</Badge>
```

### ③ 行の更新ハイライト（RowHighlight）
CSS は `loading-animations.css` に同梱（`.sa-row` / `tr.sa-flash`）。
更新された行に約2秒だけ `data-flash` を付与し、その後外すフックを用意：
```tsx
function useFlash(timeout = 1800) {
  const [id, setId] = useState<string | null>(null);
  const flash = (rowId: string) => { setId(rowId); setTimeout(() => setId(null), timeout); };
  return { flashedId: id, flash };
}
// <tr className="sa-flash" data-flash={flashedId === row.id}> … </tr>
```
リアルタイム更新（WS/ポーリング）で値が変わった行に `flash(row.id)` を呼ぶ。

### ④ サイドバー展開
`DesktopShell` の既存サイドバーに CSS のみ：
```css
.sidebar { width: var(--sidebar-width-collapsed); transition: width var(--transition-sidebar); }
.sidebar:hover { width: var(--sidebar-width-expanded); }
```
JS 不要。アクティブ項目は `border-left: 3px solid var(--accent); background: var(--link-active-bg);`。

---

## 原則（SSOT / デザイントークン）

- 各部品は**色・余白・角丸・影・モーションを直書きしない** → 必ず `var(--*)`。
- 定義の保管庫は `tokens/*.css` の**1か所のみ**（single source of truth）。
- 同梱 CSS（`loading-animations.css`）もトークン参照のみ。配色変更・ダークモードに自動追従。
- `prefers-reduced-motion` に配慮済み（ループ系アニメは停止、状態表示は維持）。
