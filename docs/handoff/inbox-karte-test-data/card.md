# 実装カード: 住所から開いたときのカルテの最初のタブ

- 設計: `docs/handoff/inbox-karte-test-data/design.md`（PO 承認「1」2026-11-24）
- ブランチ: `release/inbox-karte-test-data`（このカードと同じ枝。origin/main 起点）
- 触ってよいファイル: `frontend/src/pages/inbox/useInboxState.ts`、新規 `frontend/src/pages/inbox/useInboxState.karteTabFromUrl.test.tsx` の 2 つだけ
- 触らない: CSS・`frontend/src/locales/*.json`・`karteLayout.ts`・`InboxKartePanel.tsx`・backend・migrations・ほかの試験

## 0. 始める前の点検（合わなければ止めて BLOCKED: で返す）

- `frontend/src/pages/inbox/useInboxState.ts:267` が `const [karteTab, setKarteTab] = useState<"contact" | "company" | "deal">("deal");`
- `:656-658` が ADR-1089 のコメントと `setKarteTab(getKarteLayout(conv?.lead_status).tabs[0]);`
- `:380` が `const leadDetail = selectedLeadId === null || leadFailedId === selectedLeadId ? null : leadDetailQuery.data ?? null;`
- `:698-728` が selectedLeadId 変更時の効果（loadLeadDetail を呼ぶ）
- 行がずれていたら中身で探す。中身が違えば止める。

## 1. 変更（この 3 か所だけ）

(1) `:267` の直後に足す:

```ts
  // ADR-1089: 住所の lead_id で開いた会話は selectLead を通らない。カルテが初めて届いたときに 1 回だけ、段階の最初のタブにする
  const urlKarteTabPendingRef = useRef(initialLeadId !== null);
```

(2) `selectLead` の中、`setKarteTab(getKarteLayout(conv?.lead_status).tabs[0]);` の直後に足す:

```ts
    urlKarteTabPendingRef.current = false;
```

(3) `:698-728` の効果（`}, [selectedLeadId, loadMessages, markRead, loadLeadDetail]);` で終わる）の直後に足す:

```ts

  // ADR-1089: 住所から開いた会話の最初のタブ（段階はカルテの中身から読む。一覧に無い古い会話でも決まるように）
  useEffect(() => {
    if (!urlKarteTabPendingRef.current || !leadDetail || leadDetail.id !== initialLeadId) return;
    urlKarteTabPendingRef.current = false;
    setKarteTab(getKarteLayout(leadDetail.status).tabs[0]);
  }, [leadDetail, initialLeadId]);
```

## 2. 試験（新規 `useInboxState.karteTabFromUrl.test.tsx`）

`useInboxState.autoSelectBadge.test.tsx` の vi.mock の作法を写す。`searchParamsStub = new URLSearchParams("lead_id=…")` で住所から開く。`lib/api` の `api.get` は `/leads/<id>` に対してカルテ（id と status）を返すようにする。試験は 4 本:

- existing_customer → `result.current.karteTab` が `"company"`
- follow_up_short → `"company"`
- lead → `"deal"`、negotiating → `"deal"`（1 本にまとめてよい）
- follow_up_short で `"company"` になったあと `act(() => result.current.setKarteTab("contact"))`、カルテを読み直させても（`rerender`）`"contact"` のまま

## 3. 流す確かめ（全部の生の出力をファイルに残す）

- `cd frontend && npx vitest run src/pages/inbox` → 全部緑
- `cd frontend && npx tsc --noEmit -p .` → 0 件
- `cd frontend && npx eslint src/pages/inbox/useInboxState.ts src/pages/inbox/useInboxState.karteTabFromUrl.test.tsx` → 0 件
- `git diff origin/main --name-only` → 上の 2 ファイルと `docs/handoff/inbox-karte-test-data/` だけ

## 4. 想定の分かれ道

- 試験で `leadDetail` が届かない（useApiQuery の写しが空）→ `useInboxState.cache.test.tsx` の作法（queryClient を毎回 clear）を写す。それでも届かなければ止めて BLOCKED: で返す。設計を変えない。
- 既存の試験が赤 → 直さずに止めて BLOCKED: で返す。

## 5. 返すもの

commit（`fix(inbox): open karte on stage first tab when opened from URL (ADR-1089)`）を同じ枝に push。PR は作らない。最後に DONE と commit の番号、§3 の結果。
