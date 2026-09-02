/**
 * /super-admin/tcg-analysis-review — 解析レビュー画面
 *
 * PARITY-03 第1段階:
 *   GAS getAnalysisReviewPage → GET /api/v1/tcg/analysis-results
 *   GAS previewAnalysisReviewStatusTabs → GET /api/v1/tcg/analysis-results/status-counts
 *   is_super_admin=false なら 403 メッセージを表示
 *
 * Phase 1 制限:
 *   - 手動修正・メモの保存ボタンは disabled（保存エンドポイント未実装）
 *   - notes/correctionOptions の fetch なし
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { api } from "../../lib/api";
import { AnalysisReviewWorkspace } from "../../features/tcg-analysis-review/AnalysisReviewWorkspace";
import type { AnalysisReviewItem, CorrectionValues } from "../../features/tcg-analysis-review/ItemComparison";
import type { ReviewTabId } from "../../features/tcg-analysis-review/reviewTabs";
import type { SourceLineJump } from "../../features/tcg-analysis-review/SourceRawPane";
import "../../features/tcg-analysis-review/analysis-review.css";

// ---------------------------------------------------------------------------
// API レスポンス型（BE snake_case → FE で正規化）
// ---------------------------------------------------------------------------

interface AnalysisResultsResponse {
  items: AnalysisReviewItem[];
  total: number;
  item_total: number;
  offset: number;
  limit: number;
  providers: string[];
  status_tab_counts: Partial<Record<ReviewTabId, number>>;
}

// ---------------------------------------------------------------------------
// ユーティリティ
// ---------------------------------------------------------------------------

const emptyCorrections = (): CorrectionValues => ({
  corrected_product_name: '',
  corrected_quantity: '',
  corrected_price: '',
  corrected_unit: '',
  corrected_condition: '',
  corrected_memo: '',
});

// ---------------------------------------------------------------------------
// ページコンポーネント
// ---------------------------------------------------------------------------

export default function TcgAnalysisReviewPage() {
  const { isSuperAdmin, loading: superAdminLoading } = useSuperAdmin();

  const [data, setData] = useState<AnalysisResultsResponse | null>(null);
  const [query, setQuery] = useState('');
  const [provider, setProvider] = useState('');
  const [reviewOnly, setReviewOnly] = useState(false);
  const [unresolvedUnitOnly, setUnresolvedUnitOnly] = useState(false);
  const [unregisteredOnly, setUnregisteredOnly] = useState(false);
  const [activeStatusTab, setActiveStatusTab] = useState<ReviewTabId>('ALL');
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState('');
  const [notes] = useState<Record<string, string>>({});
  const [noteState] = useState<Record<string, 'idle' | 'saving' | 'saved' | 'error'>>({});
  const [noteDiagnostics] = useState<Record<string, undefined>>({});
  const [corrections, setCorrections] = useState<Record<string, CorrectionValues>>({});
  const [correctionState] = useState<Record<string, 'idle' | 'saving' | 'saved' | 'error'>>({});
  const [sourceJumps, setSourceJumps] = useState<Record<string, SourceLineJump>>({});
  const jumpSequence = useRef(0);

  const load = useCallback(async () => {
    if (!isSuperAdmin) return;
    setError('');
    try {
      const params = new URLSearchParams();
      if (query) params.set('query', query);
      if (provider) params.set('provider', provider);
      params.set('status_tab', activeStatusTab);
      params.set('offset', String(offset));
      params.set('limit', '10');
      if (reviewOnly) params.set('review_only', 'true');
      if (unregisteredOnly) params.set('unregistered_only', 'true');
      if (unresolvedUnitOnly) params.set('unresolved_unit_only', 'true');
      const res = await api.get<AnalysisResultsResponse>(
        `/tcg/analysis-results?${params.toString()}`
      );
      setData(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    }
  }, [isSuperAdmin, activeStatusTab, offset, provider, query, reviewOnly, unresolvedUnitOnly, unregisteredOnly]);

  useEffect(() => { load(); }, [load]);

  const resetOffset = (setter: (value: any) => void) => (value: any) => {
    setOffset(0);
    setter(value);
  };

  const updateCorrection = (id: string, key: keyof CorrectionValues, value: string) => {
    setCorrections((current) => ({ ...current, [id]: { ...(current[id] || emptyCorrections()), [key]: value } }));
  };

  const jumpToSourceLine = (sourceMessageId: string, line: number) => {
    jumpSequence.current += 1;
    setSourceJumps((jumps) => ({ ...jumps, [sourceMessageId]: { line, requestId: jumpSequence.current } }));
  };

  if (superAdminLoading) {
    return <PageLayout navKey="nav.superAdminTcgAnalysisReview">読み込み中…</PageLayout>;
  }
  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminTcgAnalysisReview">
        <p style={{ color: "var(--color-error)" }}>このページは super_admin 専用です。</p>
      </PageLayout>
    );
  }

  return (
    <PageLayout navKey="nav.superAdminTcgAnalysisReview">
      <AnalysisReviewWorkspace
        activeStatusTab={activeStatusTab}
        correctionOptions={undefined}
        corrections={corrections}
        correctionState={correctionState}
        dataLoaded={Boolean(data)}
        error={error}
        itemTotal={data?.item_total}
        items={data?.items || []}
        limit={data?.limit || 0}
        noteDiagnostics={noteDiagnostics}
        noteState={noteState}
        notes={notes}
        offset={offset}
        onCorrectionChange={updateCorrection}
        onCorrectionSave={() => {}}
        onNextPage={() => setOffset(offset + (data?.limit || 0))}
        onNoteChange={() => {}}
        onNoteSave={() => {}}
        onPreviousPage={() => setOffset(Math.max(0, offset - (data?.limit || 0)))}
        onProviderChange={resetOffset(setProvider)}
        onQueryChange={resetOffset(setQuery)}
        onReviewOnlyChange={resetOffset(setReviewOnly)}
        onSourceLineJump={jumpToSourceLine}
        onStatusTabChange={(id) => { setOffset(0); setActiveStatusTab(id); }}
        onUnregisteredOnlyChange={resetOffset(setUnregisteredOnly)}
        onUnresolvedUnitOnlyChange={resetOffset(setUnresolvedUnitOnly)}
        provider={provider}
        providers={data?.providers || []}
        query={query}
        reviewOnly={reviewOnly}
        sourceJumps={sourceJumps}
        statusTabCounts={data?.status_tab_counts || {}}
        total={data?.total || 0}
        unregisteredOnly={unregisteredOnly}
        unresolvedUnitOnly={unresolvedUnitOnly}
      />
    </PageLayout>
  );
}
