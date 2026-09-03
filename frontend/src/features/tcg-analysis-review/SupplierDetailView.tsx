import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../lib/api';
import { ItemComparison, type AnalysisReviewItem } from './ItemComparison';
import { ProductMasterDrawer } from './ProductMasterDrawer';
import { SourceRawPane, type SourceLineJump } from './SourceRawPane';
import './supplier-detail-view.css';

const PAGE_SIZE = 20;
const MASTER_ISSUE_IDS = ['PRODUCT_MASTER_UNREGISTERED', 'PRODUCT_ID_UNRESOLVED', 'EXCLUDED'];

interface SourceApiResponse {
  found: boolean;
  source_message_id: string;
  supplier_id: string;
  supplier_name: string;
  raw_text: string;
}

interface ItemsApiResponse {
  items: AnalysisReviewItem[];
  total: number;
  item_total: number;
  offset: number;
  limit: number;
  providers: string[];
}

export function SupplierDetailView({ supplierId, supplierName, onBack }: { supplierId: string; supplierName: string; onBack: () => void }) {
  const { t } = useTranslation();
  const [rawText, setRawText] = useState('');
  const [sourceMessageId, setSourceMessageId] = useState('');
  const [items, setItems] = useState<AnalysisReviewItem[]>([]);
  const [displayCount, setDisplayCount] = useState(PAGE_SIZE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [jump, setJump] = useState<SourceLineJump | undefined>();
  const [masterDrawerItem, setMasterDrawerItem] = useState<AnalysisReviewItem | undefined>();
  const jumpSequence = useRef(0);
  const sourceLoaded = useRef(false);
  const itemsLoaded = useRef(false);

  useEffect(() => {
    setLoading(true);
    setError('');
    setRawText('');
    setSourceMessageId('');
    setItems([]);
    setDisplayCount(PAGE_SIZE);
    sourceLoaded.current = false;
    itemsLoaded.current = false;
    const checkDone = () => { if (sourceLoaded.current && itemsLoaded.current) setLoading(false); };

    api.get<SourceApiResponse>(`/tcg/suppliers/${supplierId}/source`)
      .then((res) => { if (res.found) { setRawText(res.raw_text); setSourceMessageId(res.source_message_id); } })
      .catch((e: unknown) => { setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { sourceLoaded.current = true; checkDone(); });

    const params = new URLSearchParams({ provider: supplierName, offset: '0', limit: '500', strip_raw_text: 'true' });
    api.get<ItemsApiResponse>(`/tcg/analysis-results?${params.toString()}`)
      .then((res) => { setItems(res.items || []); })
      .catch((e: unknown) => { setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { itemsLoaded.current = true; checkDone(); });
  }, [supplierId, supplierName]);

  const jumpToLine = (line: number) => {
    jumpSequence.current += 1;
    setJump({ line, requestId: jumpSequence.current });
  };

  const visibleItems = items.slice(0, displayCount);
  const remaining = items.length - displayCount;

  return (
    <>
      <div className="supplier-detail-view">
        <div className="supplier-detail-view-header">
          <button type="button" className="supplier-detail-back" onClick={onBack}>{t("superAdmin.supplierQuality.backToList")}</button>
          <h2>{supplierName} <span className="supplier-detail-id">{supplierId}</span></h2>
        </div>
        {loading && <p>{t("common.loading")}</p>}
        {error   && <p style={{ color: 'var(--color-error)' }}>{error}</p>}
        {!loading && !error && (
          <div className="supplier-detail-view-body">
            <SourceRawPane sourceMessageId={sourceMessageId} rawText={rawText} itemCount={items.length} jump={jump} />
            <section className="supplier-detail-items">
              {items.length === 0 && <p>{t("superAdmin.supplierQuality.noItems")}</p>}
              {visibleItems.map((item) => (
                <div key={item.extraction_item_id} className="supplier-detail-item-row">
                  <ItemComparison item={item} readOnly={true} onJumpToSourceLine={jumpToLine} />
                  {(item.review_issues || []).some((id) => MASTER_ISSUE_IDS.includes(id)) && (
                    <div className="supplier-detail-item-actions">
                      <button type="button" className="supplier-detail-correct-btn" onClick={() => setMasterDrawerItem(item)}>{t("superAdmin.supplierQuality.correctPhase3")}</button>
                    </div>
                  )}
                </div>
              ))}
              {remaining > 0 && (
                <div className="supplier-detail-load-more">
                  <button type="button" className="supplier-detail-back" onClick={() => setDisplayCount((c) => c + PAGE_SIZE)}>
                    {t("superAdmin.supplierQuality.loadMore", { remaining })}
                  </button>
                </div>
              )}
            </section>
          </div>
        )}
      </div>
      {masterDrawerItem && <ProductMasterDrawer item={masterDrawerItem} onClose={() => setMasterDrawerItem(undefined)} />}
    </>
  );
}
