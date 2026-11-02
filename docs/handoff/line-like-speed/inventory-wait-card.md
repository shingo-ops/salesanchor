# 在庫表の読み直しの待ちを縮める実装カード（ADR-1016 改訂 2026-11-02・ADR-1054 K4）

- 対象: docs/handoff/line-like-speed/design.md §5「K4 と在庫表」・§3-4-16。ADR-1016 改訂 2026-11-02。ADR-1054（Accepted）の K4。
- 根拠の写し: S=origin/main c072e3f39。行番号はすべてこの sha。2026-11-02 に設計担当が S の写しで行を読んだ。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第 1 版（2026-11-02 設計担当 Claude Opus）。
- 受領確認: 実装役は着手の最初の報告に「在庫表の待ちのカード 第 1 版を受け取った・S=c072e3f39」と書く。

## 0. 決まったこと
- PO 選択 2026-11-02「1」: 在庫表の読み直しの待ちを、ほかの画面と同じ 1.5 秒＋0〜1 秒のずれにする。変更が出るまで最大で約 4.3 秒（1.5＋1.0＋読み込み 1.8 秒）。
- 根拠の数（design.md §3-4-16）: 6 日半で在庫表の読み込み 180 回・10 秒以内に同時に読んだ接続元は最大 2。
- 待ちの仕組み（S frontend/src/hooks/useRealtimeRefresh.ts:38-41）は「最初の合図で時計を 1 つだけ置き、鳴るまでの合図は数えない」。縮めても 1 画面の読み直しは 1.5 秒に 1 回まで。
- 行が外れる時刻の読み直しのずれ（expiryJitterMs）は今の 0〜3 秒のまま変えない。PO が決めたのは合図の待ちだけだから。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更 |
|---|---|---|
| 1 | frontend/src/pages/inventory/InventoryPage.tsx | §4-A |
| 2 | frontend/src/pages/inventory/InventoryPage.autorefresh.test.tsx | §4-B |
| 3〜6 | docs/adr/ADR-1016-realtime-change-signal-standard.md・docs/adr/ADR-1054-screen-data-cache.md・docs/handoff/line-like-speed/design.md・このカード | 設計担当が push 済み。実装役は触らない |

## 2. 触らない範囲
- frontend/src/hooks/useRealtimeRefresh.ts（REALTIME_DEBOUNCE_MS は読むだけ）・backend・migrations・deploy.yml・scripts・ほかの画面。
- InventoryPage.tsx の §4-A に無い行。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) `git diff --stat c072e3f39 origin/main -- frontend/src/pages/inventory frontend/src/hooks/useRealtimeRefresh.ts` が空であること。空でなければ、§4 の変更前の文が grep で 1 行ずつ見つかる時だけ続ける。見つからなければ BLOCKED:。
- (b) `grep -n "export const REALTIME_DEBOUNCE_MS = 1_500;" frontend/src/hooks/useRealtimeRefresh.ts` が 1 行。違えば BLOCKED:。
- (c) `grep -n "INVENTORY_REFRESH_JITTER_MS" frontend/src/pages/inventory/InventoryPage.tsx` が S と同じ 3 行（114・121・123）。違えば BLOCKED:。

## 4-A. #1 InventoryPage.tsx
変更前（S 33 行）:
```
import { useRealtimeRefresh } from "../../hooks/useRealtimeRefresh";
```
変更後:
```
import { REALTIME_DEBOUNCE_MS, useRealtimeRefresh } from "../../hooks/useRealtimeRefresh";
```
変更前（S 110-114 行）:
```
// ADR-1016 改訂 2026-10-18: 在庫が変わった合図で読み直す。抽出が続く時間帯でも 5 秒に 1 回まで。
// 同じ合図が全員に同時に届くので、ページごとに 0〜3 秒ずらして読み直しが一度に集まらないようにする
const INVENTORY_TOPICS = [TOPICS.tcgInventory] as const;
const INVENTORY_REFRESH_DEBOUNCE_MS = 5_000;
const INVENTORY_REFRESH_JITTER_MS = 3_000;
```
変更後:
```
// ADR-1016 改訂 2026-11-02: 在庫が変わった合図で、ほかの画面と同じ 1.5 秒待って読み直す。
// 同じ合図が全員に同時に届くので、ページごとに 0〜1 秒ずらして読み直しが一度に集まらないようにする
const INVENTORY_TOPICS = [TOPICS.tcgInventory] as const;
const INVENTORY_REFRESH_JITTER_MS = 1_000;
// 行が外れる時刻の読み直しのずれは改訂 2026-10-19 のまま 0〜3 秒
const INVENTORY_EXPIRY_JITTER_MS = 3_000;
```
変更前（S 120-123 行）:
```
  const [refreshDebounceMs] = useState(
    () => INVENTORY_REFRESH_DEBOUNCE_MS + Math.floor(Math.random() * INVENTORY_REFRESH_JITTER_MS),
  );
  const [expiryJitterMs] = useState(() => Math.floor(Math.random() * INVENTORY_REFRESH_JITTER_MS));
```
変更後:
```
  const [refreshDebounceMs] = useState(
    () => REALTIME_DEBOUNCE_MS + Math.floor(Math.random() * INVENTORY_REFRESH_JITTER_MS),
  );
  const [expiryJitterMs] = useState(() => Math.floor(Math.random() * INVENTORY_EXPIRY_JITTER_MS));
```

## 4-B. #2 InventoryPage.autorefresh.test.tsx
- describe の名前 `'InventoryPage auto refresh (ADR-1016 revision 2026-10-18)'` を `'InventoryPage auto refresh (ADR-1016 revision 2026-11-02)'` に。
- 1 つ目の it を次に置き換える（名前と秒）:
```
  it('tcg.inventory signal -> one more /inventory fetch after 1.5 seconds', async () => {
    const before = await renderLoaded();
    act(() => handler({ topic: 'tcg.inventory', origin: null }));
    await act(async () => { await vi.advanceTimersByTimeAsync(1_400); });
    expect(inventoryCalls()).toBe(before);
    await act(async () => { await vi.advanceTimersByTimeAsync(200); });
    expect(inventoryCalls()).toBe(before + 1);
  });
```
- 2 つ目の it を次に置き換える:
```
  it('three signals within 1.5 seconds -> one reload', async () => {
    const before = await renderLoaded();
    act(() => handler({ topic: 'tcg.inventory', origin: null }));
    await act(async () => { await vi.advanceTimersByTimeAsync(500); });
    act(() => handler({ topic: 'tcg.inventory', origin: null }));
    await act(async () => { await vi.advanceTimersByTimeAsync(500); });
    act(() => handler({ topic: 'tcg.inventory', origin: null }));
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000); });
    expect(inventoryCalls()).toBe(before + 1);
  });
```
- 2 つ目の it の後に、ずれがいちばん大きい時の試験を足す:
```
  it('largest page offset -> reload by 2.5 seconds, not before 2.4 seconds', async () => {
    vi.spyOn(Math, 'random').mockReturnValue(0.999);
    const before = await renderLoaded();
    act(() => handler({ topic: 'tcg.inventory', origin: null }));
    await act(async () => { await vi.advanceTimersByTimeAsync(2_400); });
    expect(inventoryCalls()).toBe(before);
    await act(async () => { await vi.advanceTimersByTimeAsync(100); });
    expect(inventoryCalls()).toBe(before + 1);
  });
```
- ほかの it（own origin・tcg.review）は変えない。

## 4-M. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. 作業場所を作り、push 済みの枝の先頭に合わせる。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/inventory-refresh-wait
  cd <W> && git fetch origin release/inventory-refresh-wait
  cd <W> && git switch -C release/inventory-refresh-wait origin/release/inventory-refresh-wait
  cd <W> && git rev-parse HEAD origin/release/inventory-refresh-wait
  （2 行が同じこと。違えば BLOCKED:。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/inv-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/inv-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/inv-preflight.txt | head -3
  （FAIL が `GitHub API に到達不可` 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗 1 件・その結果の `PREFLIGHT FAIL` 行のどれかだけなら、`[OK]   origin/main は存在` を確かめて続ける。ほかの FAIL があれば BLOCKED:。）
  cd <W> && git fetch origin main
手順2. §3(a)〜(c) を確かめ、依存を入れる。
  cd <W>/frontend && npm ci > /tmp/inv-ci.txt 2>&1
  cd <W> && tail -5 /tmp/inv-ci.txt
手順3. §4-A・§4-B のとおり直す。直す前に変更前の文を grep -n で確かめる。
  cd <W> && grep -n "INVENTORY_REFRESH_DEBOUNCE_MS\|5_000\|3_000" frontend/src/pages/inventory/InventoryPage.tsx | head
  （直した後は INVENTORY_REFRESH_DEBOUNCE_MS が 0 行・3_000 は INVENTORY_EXPIRY_JITTER_MS の 1 行だけ。）
手順4. 試験・型・lint・組み立て。
  cd <W>/frontend && npm run generate:api-types > /tmp/inv-gen.txt 2>&1
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/pages/inventory src/hooks/useRealtimeRefresh.test.tsx > /tmp/inv-unit.txt 2>&1
  cd <W> && tail -30 /tmp/inv-unit.txt
  cd <W>/frontend && npm run test:unit > /tmp/inv-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/inv-unit-all.txt
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/inv-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/inv-tsc.txt
  cd <W>/frontend && npx eslint src/pages/inventory/InventoryPage.tsx src/pages/inventory/InventoryPage.autorefresh.test.tsx > /tmp/inv-lint.txt 2>&1
  cd <W> && tail -20 /tmp/inv-lint.txt
  cd <W>/frontend && npm run build > /tmp/inv-build.txt 2>&1
  cd <W> && tail -15 /tmp/inv-build.txt
手順5. 変わったのが §1 の #1・#2 だけか確かめる。
  cd <W> && git status --short | head
  cd <W> && git diff origin/release/inventory-refresh-wait | head -200
手順6. commit・push（--no-verify は使わない。fast-forward でないと断られたら BLOCKED:）。
  cd <W> && git add frontend/src/pages/inventory/InventoryPage.tsx frontend/src/pages/inventory/InventoryPage.autorefresh.test.tsx
  cd <W> && git commit -m "feat: 在庫表の読み直しの待ちを1.5秒+0〜1秒に（ADR-1016 改訂 2026-11-02）"
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/inventory-refresh-wait
手順7. 報告を返す。PR は作らない（設計担当が作る）。1 つの発言は 600 文字以内。手順ごとの tail の出力（生のまま）と §3(a)〜(c) の結果を書く。

## 4. GO と承認・PO の操作
- PO の実装承認: 2026-11-02 PO 選択「1」（ほかの画面と同じ速さに縮める）。
- frontend の 1 画面と試験・書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と確認がすべて pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| W1 | 合図から 1.4 秒では読み直さず 1.6 秒で 1 回読み直す・1.5 秒以内の合図 3 つで 1 回・ずれ最大の時は 2.4 秒で読まず 2.5 秒で読む・自分の合図と別の話題では読まない | /tmp/inv-unit.txt で InventoryPage.autorefresh.test.tsx の 5 件が passed、PR の CI の unit-run が success |
| W2 | 全部の試験・型・lint・組み立てが通る | /tmp/inv-unit-all.txt・inv-tsc.txt・inv-lint.txt・inv-build.txt と PR の確認がすべて pass |
| W3 | 変わったのは §1 の 6 ファイルだけ。行が外れる時刻のずれは 0〜3 秒のまま | gh pr diff --name-only と diff（INVENTORY_EXPIRY_JITTER_MS = 3_000 が在る） |
| W4 | マージの後、deploy が成功し、本番の在庫表が開く。prod-ui-check で /inventory の K2 が 2 秒以内・403 と 5xx が 0 件 | deploy.yml の結論と時刻・prod-ui-check の要約（設計担当） |
| W5 | サーバーが混んでいない: マージの後に在庫表の読み込みの 1 時間の最大回数と backend の CPU・メモリを測り、§3-4-16 の基準と並べて記録する。1 時間の読み込みが基準の最大 21 回の 3 倍（63 回）を超えたら PO に報告する | 設計担当が Loki の記録（GET /api/v1/inventory?）と docker stats を読む |
