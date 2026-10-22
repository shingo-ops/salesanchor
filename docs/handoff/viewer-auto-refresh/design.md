<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# 設計 — 閲覧ページを再読み込みなしで1分ごとに新しくする

**対象ADR**: ADR-1019（閲覧ページ）、ADR-1016（即時反映。閲覧ページはその対象外であることの確認）、ADR-144・ADR-067（金型）、ADR-027（i18n）
**recon**: `docs/handoff/viewer-auto-refresh/recon.md`
**日付**: 2026-10-22
**担当**: Planner（Opus）

---

## 0. 目的と PO 承認
- PO「新規投稿があり解析が完了した後に画面を再読込しなくても情報が更新される仕組みに出来る？」（2026-10-21）。対象は閲覧ページ（PO「1」2026-10-22）。
- **成功条件（KGI）**: PO「1」（2026-10-22）で承認済み。解析が終わってから2分以内に、閲覧ページを開いたまま（再読み込みなしで）新しい在庫が表に出る。そのとき検索の文字・タブ・絞り込み・並べ替え・ページは変わらない。
- 前の決め（`docs/handoff/gas-viewer-fresh-fast/design.md:590`「最新はページの再読み込みで出る」）を変える。「更新ボタンは付けない」はそのまま守る（ボタンは足さない）。

## 1. 方式の選択
| 案 | 中身 | 判定 |
|---|---|---|
| A（採用） | 画面を開いている間、1分ごとに今の入口 `GET /api/v1/viewer/inventory` を読み直し、表の中身だけ差し替える | 入口は7本のまま（ADR-1019 決定5 は変えない）。サーバーと nginx の設定は変えない。最大の遅れは「作り置き最大60秒＋確認60秒＝120秒」で、KGI の2分に収まる |
| B | 閲覧者用のすぐ知らせる仕組み（SSE）を新しく作る | 入口が8本になり、ADR-1019 決定5 を改める必要がある。nginx の追加は危険な変更。KGI が2分なので要らない。不採用 |
| C | 作り直しの間隔を短くする | サーバーの負担が増える。KGI の2分なら要らない。不採用 |

- 負担: 1人が開いている間、1分に1回取りに行く。この取得は Redis の作り置きを返すだけで、DB は読まない（ADR-1019 決定7）。回数の制限は IP 単位で 60回/分（`backend/app/middleware/rate_limit.py:34`）。同じ IP から開く人が60人未満なら、制限にかからない。
- 軽い確認（変わったかどうかだけを聞く）にしない理由: 作り置きの updated_at は中身が同じでも毎分変わる（`backend/app/services/viewer_inventory_cache.py:87`）。軽い確認では「中身が変わったか」を見分けられず、そのための新しい入口も要る。全文を取り直すほうが単純で、入口も増えない。

## 2. 対象と対象外
- 対象: 次のファイル。
  - `frontend/src/pages/viewer/ViewerApp.tsx`
  - `frontend/src/pages/viewer/InventoryView.tsx`（`now` と冒頭の注記）
  - `frontend/src/pages/viewer/useViewerAutoRefresh.ts`（新規）
  - テスト `frontend/src/pages/viewer/useViewerAutoRefresh.test.ts`（新規）・`frontend/src/pages/viewer/ViewerApp.test.tsx`（新規）
- 文書: `docs/adr/ADR-1019-inventory-viewer-separate-accounts.md` に「改訂」1行を足す。`docs/handoff/gas-viewer-fresh-fast/design.md:590` の1文に改訂注記を付ける。ADR の目次（`docs/adr/README.md`）を作り直す。
- 対象外（触らない）:
  - backend 全部（viewer.py・作り置き・Celery・回数の制限）
  - nginx
  - 本体アプリの在庫表と即時反映
  - 閲覧ページのログイン・申込・パスワードの各画面
  - 文言の辞書（新しい文言は足さない。最終更新の時刻が変わるだけ）

## 3. 変更前後

### 3-1. 新規 `frontend/src/pages/viewer/useViewerAutoRefresh.ts`
前例 `frontend/src/hooks/useExpiryRefresh.ts` の作りに揃える（裏のタブでは保留し、表に戻ったら1回だけ呼ぶ）。

```ts
/**
 * 閲覧ページの在庫を1分ごとに読み直す（docs/handoff/viewer-auto-refresh/design.md）。
 * - enabled が false の間は何もしない（在庫表を出していない間）
 * - 裏のタブの間は呼ばずに保留し、表に戻ったとき保留があれば 1 回だけ呼ぶ
 */
import { useEffect, useRef } from "react";

export const VIEWER_REFRESH_MS = 60_000;

export function useViewerAutoRefresh(enabled: boolean, refresh: () => void): void {
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;

  useEffect(() => {
    if (!enabled) return;
    let pending = false;
    const timer = setInterval(() => {
      if (document.hidden) {
        pending = true;
        return;
      }
      refreshRef.current();
    }, VIEWER_REFRESH_MS);
    const onVisible = () => {
      if (!document.hidden && pending) {
        pending = false;
        refreshRef.current();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [enabled]);
}
```

### 3-2. `frontend/src/pages/viewer/ViewerApp.tsx`
- import に `useViewerAutoRefresh` を足す。
- load()（:65-80）の後に、裏で読み直す refresh を足す。load() は変えない。

```ts
  // 1分ごとの読み直し（docs/handoff/viewer-auto-refresh/design.md）。読み込み中の画面にはしない。
  // 成功したら在庫表の data だけ差し替える（InventoryView は残るので検索・タブ・ページは保たれる）。
  // 失敗しても今の表を出したまま次の回を待つ。ただしトークンが無効（401）ならログイン画面へ戻す。
  const refreshing = useRef(false);
  const refresh = useCallback(async () => {
    if (refreshing.current) return;
    const token = readToken();
    if (!token) return;
    refreshing.current = true;
    try {
      const data = await fetchInventory(token);
      setScreen((prev) => (prev.name === "inventory" ? { name: "inventory", data } : prev));
    } catch (err) {
      if (err instanceof ViewerApiError && err.status === 401) {
        if (err.detail === "invalid viewer token") clearToken();
        setScreen((prev) => (prev.name === "inventory" ? { name: "login" } : prev));
      }
    } finally {
      refreshing.current = false;
    }
  }, []);
  useViewerAutoRefresh(screen.name === "inventory", () => void refresh());
```
- 401 以外の失敗（503 準備中・429・ネットの切れ・停止中 403 など）は、今の表を出したままにする。理由: 一時的な失敗のたびに案内画面へ切り替わると、見ている途中の表が消えるため。停止・期限切れは次の再読み込みかログインで今と同じ案内画面になる（load() は変えない）。
- `setScreen((prev) => ...)` で、読み直しの途中に利用者がログアウトするなど画面が替わっていたら上書きしない。
- 冒頭の注記（:1-4）に1行足す:「在庫表を出している間は1分ごとに裏で読み直し、表の中身だけ差し替える（useViewerAutoRefresh）。」

### 3-3. `frontend/src/pages/viewer/InventoryView.tsx`
- :55 を変える。

```ts
// 変更前
  const [now] = useState(() => Date.now());
// 変更後（data が差し替わるたびに「今」を取り直す。24時間以内の判定を新しい時刻で行うため）
  const now = useMemo(() => Date.now(), [data]);
```
- `useMemo` は既に import 済み（:2）。lint（`cd frontend && npx eslint src/pages/viewer`）が依存の指摘や純粋さの指摘を出したら、勝手に書き換えず停止して Opus へ。
- :1 の注記を変える。
  - 変更前:「更新ボタンは無い」
  - 変更後:「更新ボタンは無い。中身は ViewerApp が1分ごとに差し替える」
- タブの初期値（:57-59）・ページ（:71・:104）・rowKey（:323）は変えない。差し替えたあとに今のタブのシリーズが無くなっていたら、表は0件になる（利用者がタブを選び直す）。既存の絞り込みで0件になるときと同じ扱い。

### 3-4. 文書
- ADR-1019 の What の 7 の後に、次の1行を足す。
  - 「7-2.（改訂 2026-10-22、PO「1」）閲覧ページは、在庫表を出している間、1分ごとに同じ入口（inventory）を裏で読み直して表の中身だけ差し替える。入口は7本のまま。解析が終わってから表に出るまでは最大2分（作り置き最大60秒＋読み直し60秒）。設計: docs/handoff/viewer-auto-refresh/design.md」
- ADR-1019 の Why に1行を足す。
  - 「- 再読み込みしないと新しい在庫が出ないと、開いたままの閲覧者は古い値段を見続ける。入口を増やさずに2分以内を満たすため、すぐ知らせる仕組みではなく、1分ごとの読み直しにした（2026-10-22）。」
- `docs/handoff/gas-viewer-fresh-fast/design.md:590` の行末に追記する。
  - 「【改訂 2026-10-22 PO「1」】再読み込みしなくても、開いている間は1分ごとに自動で新しくなる（docs/handoff/viewer-auto-refresh/design.md）。更新ボタンは付けないまま。」
- `node scripts/generate-adr-index.js` を実行し、`docs/adr/README.md` の差分を一緒にコミットする。

## 4. 実装カード（Sonnet）
1. worktree `~/worktrees/salesanchor/release-viewer-auto-refresh` で `./scripts/dev/executor-preflight.sh || exit 1`。`git fetch origin && git merge origin/main` で最新に揃える。
2. 実物の点検: ViewerApp.tsx :65-80 の load()、InventoryView.tsx :55 の `now` と :1 の注記が、本書 §3 の「変更前」と同じかを見る。違えば停止して Opus へ（NEEDS_DECISION:）。
3. §3-1〜3-4 をそのまま入れる。§2 の対象外は触らない。
4. テスト（vitest、`vi.useFakeTimers()`）。
   - `frontend/src/pages/viewer/useViewerAutoRefresh.test.ts`:
     - T1: enabled=true のとき、60秒進めると refresh が1回、120秒で2回呼ばれる。
     - T2: enabled=false なら呼ばれない。
     - T3: document.hidden=true の間に60秒進めても呼ばれない。visibilitychange（hidden=false）で1回だけ呼ばれる。
     - T4: unmount 後は呼ばれない。
   - `frontend/src/pages/viewer/ViewerApp.test.tsx`（fetchInventory を vi.mock。readToken はトークンありを返す）:
     - T5: 1回目の応答で表が出る。検索欄に文字を入れ、2ページ目へ進む（行は PER_PAGE を超える数を用意する）。60秒進めて2回目の応答（updated_at と行が違う）を返す。そのあと次をすべて確かめる。
       - 検索欄の文字がそのまま
       - ページが2のまま
       - 最終更新の表示が2回目の時刻
       - 2回目にしか無い行が出る（検索に合う行で）
       - 読み込み中の表示（data-testid="viewer-loading"）が一度も出ない
     - T6: 2回目が 503 を返しても表と検索の文字はそのまま。案内画面に替わらない。
     - T7: 2回目が 401 "invalid viewer token" なら、ログイン画面になり、clearToken が呼ばれる。
     - T8（`frontend/src/pages/viewer/InventoryView.test.tsx` に足す）: 24時間の判定。
       - 手順: 時計を固定し、23時間30分前に投稿された行を含む data で描く（24時間以内のみ表示がオン）。その行が出ることを確かめる。
       - 時計を1時間進め、updated_at だけ違う新しい data オブジェクト（行は同じ）で描き直す。
       - 期待: その行が消える。`now` が取り直されている証拠になる。
5. 確認コマンド（生出力は /tmp/CC報告ファイル/viewer-live/impl/ に保存）:
   - `cd frontend && npm run test:unit -- src/pages/viewer`
   - `cd frontend && npx tsc --noEmit -p .`
   - `cd frontend && npx eslint src/pages/viewer`
   - `cd frontend && npm run build`
   - ハードコード日本語の検査（frontend/CLAUDE.md の grep）
6. コミット（PR は Opus が作る）。報告は DONE / BLOCKED: / NEEDS_DECISION:。
- 想定分岐:
  - fetchInventory の名前や引数が違っていた → 停止
  - 既存テストが落ちた → 原因を書いて停止（テストを書き換えて通さない）
  - lint が useMemo(Date.now) を指摘した → 停止
  - T5 でスクロールやページが保てない → 停止して事実を報告

## 5. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K1 開いている間、1分ごとに裏で読み直す。裏のタブでは読まず、表に戻ったら1回読む | vitest T1〜T4 合格 |
| K2 差し替えで検索の文字・ページが変わらず、読み込み中の画面が出ない | vitest T5 合格 |
| K3 一時的な失敗で表が消えない。無効なトークンはログインへ戻る | vitest T6・T7 合格 |
| K4 24時間以内の判定が新しい時刻で行われる | vitest T8 合格 |
| K5 本番で、開いたまま（再読み込みなし）1分ごとに在庫の取得が起き、最終更新の時刻が進む | 本番反映後、閲覧ページを開いて3分置く。ブラウザの通信記録で `GET /api/v1/viewer/inventory` が約60秒おきに出ることと、最終更新の時刻が2回以上進むことを確かめる（Evaluator。閲覧者の試験アカウントが使えなければ PO の目視に回す） |
| K6（KGI） 解析が終わってから2分以内に新しい在庫が表に出る | K5 の通信の間隔（60秒）と、作り置きの更新間隔（`backend/app/celery_app.py:188-192` の60秒）の和で判定する。本番で新しい投稿の解析が終わった時刻と、その行が閲覧ページに出た時刻を1件以上照らし合わせる |
| K7 型・lint・build・既存テストがすべて合格 | §4-5 のコマンド、CI |

## 6. 外部・過去事例の参照と我々への応用
- 過去事例（社内）: `frontend/src/hooks/useExpiryRefresh.ts`（ADR-1016 改訂 2026-10-19）。裏のタブで保留し、表に戻ったら1回だけ読み直す作りを、そのまま写す。
- 過去事例（社内）: 本体アプリでポーリングを「不採用」とした判断（`docs/handoff/realtime-standard/design.md:116`）は、多くの画面と多くの利用者が DB を読む前提だった。閲覧ページの読み直しは Redis の作り置きを返すだけで DB を読まない。だから同じ理由は当てはまらない。
- 外部事例: 不要と判断。新しい技術は使わない（setInterval と visibilitychange は既存のフックと同じ）。

## 7. リスクと対処
- 同じ IP から60人以上が開くと、回数の制限（60回/分）にかかる。その場合も 429 は「失敗しても表を出したまま」（§3-2）なので、画面は消えない。今の閲覧者の数は確かめていない【未確認】。人数が増えたら、閲覧者の取得を認証済みの枠で数える変更を別に設計する。
- 応答の大きさは実測していない【未確認】。行数の上限は5000行（`backend/app/services/tcg_distribution_svc.py:45`）。K5 の確認のとき、通信記録で1回の大きさを記録する。
- 毎分 data が替わるので、表は毎分描き直される。開いている絞り込み Drawer と検索欄は InventoryView の state なので残る。

## 8. 戻し方
- 本 PR を Revert する。backend・DB・nginx は変えないので、画面だけが元に戻る。

## 9. 測り方
- K5・K6 を本番反映後に1回測る。結果はこの設計書の末尾「結果」に追記する。

## 10. 維持の仕組み
- 読み直しの間隔は `VIEWER_REFRESH_MS` の1か所だけに置く。守り手: `frontend/src/pages/viewer/useViewerAutoRefresh.test.ts`。
- 差し替えで検索やページが消えないことは T5 で固定する。守り手: `frontend/src/pages/viewer/ViewerApp.test.tsx`。

## 審査
- （設計審査の判定をここに書く）
