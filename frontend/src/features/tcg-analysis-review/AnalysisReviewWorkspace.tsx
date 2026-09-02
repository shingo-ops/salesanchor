import React, { type ComponentProps, useEffect, useMemo, useState } from 'react';
import { ItemComparison, type AnalysisReviewItem, type CorrectionOptions, type CorrectionValues } from './ItemComparison';
import { SourceRawPane, type SourceLineJump } from './SourceRawPane';
import { StatusTabBar } from './components/StatusTabBar';
import { REVIEW_TABS, type ReviewTabId } from './reviewTabs';
import { ReviewListPanel } from './ReviewListPanel';

type SourceGroup = {
  source_message_id: string;
  provider: string;
  raw_text: string;
  items: AnalysisReviewItem[];
};

type SaveState = 'idle' | 'saving' | 'saved' | 'error';

type Props = {
  activeStatusTab: ReviewTabId;
  correctionOptions?: CorrectionOptions;
  corrections: Record<string, CorrectionValues>;
  correctionState: Record<string, SaveState>;
  dataLoaded: boolean;
  error: string;
  itemTotal?: number;
  items: AnalysisReviewItem[];
  limit: number;
  noteDiagnostics: Record<string, ComponentProps<typeof ItemComparison>['noteDiagnostic']>;
  noteState: Record<string, SaveState>;
  notes: Record<string, string>;
  offset: number;
  onCorrectionChange: (id: string, key: keyof CorrectionValues, value: string) => void;
  onCorrectionSave: (item: AnalysisReviewItem) => void;
  onNextPage: () => void;
  onNoteChange: (id: string, value: string) => void;
  onNoteSave: (item: AnalysisReviewItem) => void;
  onPreviousPage: () => void;
  onProviderChange: (value: string) => void;
  onQueryChange: (value: string) => void;
  onReviewOnlyChange: (value: boolean) => void;
  onSourceLineJump: (sourceMessageId: string, line: number) => void;
  onStatusTabChange: (id: ReviewTabId) => void;
  onUnregisteredOnlyChange: (value: boolean) => void;
  onUnresolvedUnitOnlyChange: (value: boolean) => void;
  provider: string;
  providers: string[];
  query: string;
  reviewOnly: boolean;
  sourceJumps: Record<string, SourceLineJump>;
  statusTabCounts: Partial<Record<ReviewTabId, number>>;
  total: number;
  unregisteredOnly: boolean;
  unresolvedUnitOnly: boolean;
};

const emptyCorrections = (): CorrectionValues => ({ corrected_product_name: '', corrected_quantity: '', corrected_price: '', corrected_unit: '', corrected_condition: '', corrected_memo: '' });

function groupItemsBySource(items: AnalysisReviewItem[]): SourceGroup[] {
  const bySource = new Map<string, SourceGroup>();
  items.forEach((item) => {
    let group = bySource.get(item.source_message_id);
    if (!group) {
      group = { source_message_id: item.source_message_id, provider: item.provider, raw_text: item.raw_text, items: [] };
      bySource.set(item.source_message_id, group);
    }
    group.items.push(item);
  });
  return [...bySource.values()];
}

export function AnalysisReviewWorkspace(props: Props) {
  const groups = useMemo(() => groupItemsBySource(props.items), [props.items]);
  const [selectedExtractionItemId, setSelectedExtractionItemId] = useState<string>();
  const selectedGroup = useMemo(() => groups.find((group) => group.items.some((item) => item.extraction_item_id === selectedExtractionItemId)), [groups, selectedExtractionItemId]);
  const selectedItem = selectedGroup?.items.find((item) => item.extraction_item_id === selectedExtractionItemId);
  useEffect(() => { if (selectedExtractionItemId && !selectedItem) setSelectedExtractionItemId(undefined); }, [selectedExtractionItemId, selectedItem]);
  return <main className="tcg-analysis-review"><h1>在庫解析 比較ビュー</h1><StatusTabBar tabs={REVIEW_TABS} activeTab={props.activeStatusTab} counts={props.statusTabCounts} onChange={props.onStatusTabChange} /><section className="tools" aria-label="絞り込み"><input value={props.query} onChange={(event) => props.onQueryChange(event.target.value)} placeholder="提供者・商品名・商品IDを検索" aria-label="提供者・商品名・商品IDを検索" /><select value={props.provider} onChange={(event) => props.onProviderChange(event.target.value)} aria-label="提供者"><option value="">すべての提供者</option>{props.providers.map((name) => <option key={name}>{name}</option>)}</select><label><input type="checkbox" checked={props.reviewOnly} onChange={(event) => props.onReviewOnlyChange(event.target.checked)} />要確認のみ</label><label><input type="checkbox" checked={props.unregisteredOnly} onChange={(event) => props.onUnregisteredOnlyChange(event.target.checked)} />マスタ未登録のみ</label><label><input type="checkbox" checked={props.unresolvedUnitOnly} onChange={(event) => props.onUnresolvedUnitOnlyChange(event.target.checked)} />単位未解決のみ</label></section>{props.error && <p className="error">読み込みエラー: {props.error}</p>}{!props.dataLoaded ? <p>読み込み中…</p> : <><ReviewListPanel items={props.items} notes={props.notes} onSelect={setSelectedExtractionItemId} /><div className="scroll">{selectedItem && selectedGroup && <section className="comparison-sheet" aria-label="選択した解析比較"><header className="sheet-header"><b>No.</b><b>原文</b><b>Gemini抽出結果</b><b>システム最終結果</b><b>手動修正</b></header><section className="source-group"><aside className="source-number"><span className="provider">{selectedGroup.provider || '未記載'}</span></aside><SourceRawPane sourceMessageId={selectedGroup.source_message_id} rawText={selectedGroup.raw_text} itemCount={selectedGroup.items.length} jump={props.sourceJumps[selectedGroup.source_message_id]} /><div className="group-items"><ItemComparison key={selectedItem.extraction_item_id} item={selectedItem} values={props.corrections[selectedItem.extraction_item_id] || emptyCorrections()} options={props.correctionOptions} correctionState={props.correctionState[selectedItem.extraction_item_id]} note={props.notes[selectedItem.extraction_item_id] || ''} noteState={props.noteState[selectedItem.extraction_item_id]} noteDiagnostic={props.noteDiagnostics[selectedItem.extraction_item_id]} onCorrectionChange={(key, value) => props.onCorrectionChange(selectedItem.extraction_item_id, key, value)} onCorrectionSave={() => props.onCorrectionSave(selectedItem)} onNoteChange={(value) => props.onNoteChange(selectedItem.extraction_item_id, value)} onNoteSave={() => props.onNoteSave(selectedItem)} onJumpToSourceLine={(line) => props.onSourceLineJump(selectedGroup.source_message_id, line)} /></div></section></section>}</div>{props.items.length === 0 && <p className="empty">条件に一致する解析結果はありません。</p>}<nav className="paging" aria-label="ページ送り"><button disabled={!props.offset} onClick={props.onPreviousPage}>前へ</button><span>原文 {props.offset + 1}–{Math.min(props.offset + props.limit, props.total)} / {props.total}（商品 {props.itemTotal ?? props.items.length}件）</span><button disabled={props.offset + props.limit >= props.total} onClick={props.onNextPage}>次へ</button></nav></>}</main>;
}
