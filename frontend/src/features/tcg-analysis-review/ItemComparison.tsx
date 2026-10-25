import React from 'react';
import { useTranslation } from 'react-i18next';
import { SelectControl } from '../../components/Select';
import { Button } from '../../components/Button';
import { StatusBadge } from './components/StatusBadge';
import { productMetadataIssueBadges, reviewIssueBadges, type ReviewIssuePresentation } from './reviewIssues';
import type { ReviewReasonDetail } from './reviewReasonLabel';
import './item-comparison-readonly.css';
import { TextareaControl } from "../../components/Textarea";
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { fixRowOf, fixRowsOf } from './reviewFixRows';

export type ConditionReview = {
  condition_id: string | null;
  review_version: string;
  needs_review: boolean;
  review_reasons: string;
  confirmed: boolean;
  classification: string;
};
/** 人が直した値（直した項目だけ入る）。backend の manual_values */
export type ManualValues = Partial<Record<"quantity" | "price" | "unit" | "note" | "status", string>>;
export type AnalysisReviewItem = { extraction_item_id: string; source_message_id: string; provider: string; raw_text: string; gemini: Record<string, string>; system: Record<string, string>; review_issues?: string[]; condition_review?: ConditionReview | null; review_reason_details?: ReviewReasonDetail[]; is_v102?: boolean; manual_values?: ManualValues; thought_summaries?: string[] | null };
export type CorrectionValues = { corrected_product_name: string; corrected_quantity: string; corrected_price: string; corrected_unit: string; corrected_condition: string; corrected_memo: string };
export type CorrectionOptions = { units: string[]; conditions: string[] };

const fieldOrder: Array<[string, string]> = [['name', 'tcgAnalysisReview.fieldLabels.productName'], ['quantity', 'tcgAnalysisReview.fieldLabels.quantity'], ['price', 'tcgAnalysisReview.fieldLabels.price'], ['unit', 'tcgAnalysisReview.fieldLabels.unit'], ['state', 'tcgAnalysisReview.fieldLabels.condition'], ['memo', 'tcgAnalysisReview.fieldLabels.memo']];
const correctionFields: Array<[keyof CorrectionValues, string, 'text' | 'number' | 'select-unit' | 'select-condition' | 'textarea']> = [['corrected_product_name', 'tcgAnalysisReview.fieldLabels.productName', 'text'], ['corrected_quantity', 'tcgAnalysisReview.fieldLabels.quantity', 'number'], ['corrected_price', 'tcgAnalysisReview.fieldLabels.price', 'number'], ['corrected_unit', 'tcgAnalysisReview.fieldLabels.unit', 'select-unit'], ['corrected_condition', 'tcgAnalysisReview.fieldLabels.condition', 'select-condition'], ['corrected_memo', 'tcgAnalysisReview.fieldLabels.memo', 'textarea']];
const rawValue = (value: string | undefined) => value || '';
const emptyCorrections = (): CorrectionValues => ({ corrected_product_name: '', corrected_quantity: '', corrected_price: '', corrected_unit: '', corrected_condition: '', corrected_memo: '' });

const GEMINI_NOT_COPIED_KEYS = ['name', 'unit', 'state', 'memo'];
/** Gemini 列の表示値。判定はここ1か所（比較表と編集側の両方が使う）。v102 は商品名・単位・状態・メモを書き写さないので「—」 */
export function geminiCell(item: AnalysisReviewItem, keyName: string, t: Translate): string {
  if (item.is_v102 && GEMINI_NOT_COPIED_KEYS.includes(keyName)) return t('tcgAnalysisReview.notApplicable');
  return rawValue(item.gemini[keyName]) || t('tcgAnalysisReview.unresolved');
}
function SystemValue({ value, source }: { value: string; source: string }) { return <><span>{value}</span><small>{source}</small></>; }
type Translate = (key: string) => string;
export type SystemCellResult = { value: string; source: string | null };
/** システム列の値と採用元。判定はここ1か所（FinalSystemValue と比較表の両方が使う）。source が null のときは補足なし */
export function systemCell(item: AnalysisReviewItem, keyName: string, t: Translate): SystemCellResult {
  const system = item.system;
  const unresolved = t('tcgAnalysisReview.unresolved');
  if ((keyName === 'quantity' || keyName === 'price') && system[keyName]) return { value: system[keyName], source: t('tcgAnalysisReview.systemConfirmed') };
  if (keyName === 'name') return { value: system.product_title || unresolved, source: system.product_title ? t('tcgAnalysisReview.systemConfirmed') : unresolved };
  if (keyName === 'quantity' || keyName === 'price') return { value: item.gemini[keyName] || unresolved, source: item.gemini[keyName] ? t('tcgAnalysisReview.geminiExtracted') : unresolved };
  if (keyName === 'unit') return { value: system.unit || unresolved, source: system.unit && system.unit_resolved === 'YES' ? t('tcgAnalysisReview.systemConfirmed') : unresolved };
  if (keyName === 'state') return { value: system.condition || unresolved, source: system.condition ? t('tcgAnalysisReview.systemConfirmed') : unresolved };
  return system.note ? { value: system.note, source: t('tcgAnalysisReview.systemConfirmed') } : { value: t('tcgAnalysisReview.none'), source: null };
}
function FinalSystemValue({ item, keyName }: { item: AnalysisReviewItem; keyName: string }) { const { t } = useTranslation(); const cell = systemCell(item, keyName, t); return cell.source === null ? <span>{cell.value}</span> : <SystemValue value={cell.value} source={cell.source} />; }
function ManualInput({ values, field, options, onChange }: { values: CorrectionValues; field: typeof correctionFields[number]; options?: CorrectionOptions; onChange: (key: keyof CorrectionValues, value: string) => void }) { const { t } = useTranslation(); const [key, labelKey, kind] = field; if (kind === 'textarea') return <TextareaControl value={values[key]} maxLength={2000} aria-label={t('tcgAnalysisReview.manualCorrection', { field: t(labelKey) })} onChange={(event) => onChange(key, event.target.value)} />; if (kind === 'select-unit' || kind === 'select-condition') { const choices = kind === 'select-unit' ? options?.units : options?.conditions; return <SelectControl value={values[key]} disabled={!options} aria-label={t('tcgAnalysisReview.manualCorrection', { field: t(labelKey) })} onChange={(event) => onChange(key, event.target.value)}><option value="">{t('tcgAnalysisReview.noCorrection')}</option>{choices?.map((value) => <option key={value} value={value}>{value}</option>)}</SelectControl>; } return <input type={kind} min={kind === 'number' ? '0' : undefined} step={kind === 'number' ? 'any' : undefined} value={values[key]} maxLength={kind === 'text' ? 500 : undefined} aria-label={t('tcgAnalysisReview.manualCorrection', { field: t(labelKey) })} onChange={(event) => onChange(key, event.target.value)} />; }
function ComparisonMetadataRow({ label, value, badges = [] }: { label: string; value: React.ReactNode; badges?: ReviewIssuePresentation[] }) { return <div className="comparison-metadata-row"><b>{label}</b><span className="comparison-metadata-value">{value}{badges.map((badge) => <StatusBadge key={badge.id} label={badge.label} tone={badge.tone} />)}</span></div>; }
function sourceLine(span: string) { const match = span.match(/L?0*(\d+)/i); return match ? Number(match[1]) : undefined; }

export type ComparisonRow = { key: string; label: string; gemini: string; system: string; source: string; line?: number };
/** 比較表の10行（純データ）。値が「その側に存在しない」ときは「—」、「存在するが未決」は「未解決」 */
export function buildComparisonRows(item: AnalysisReviewItem, t: Translate): ComparisonRow[] {
  const na = t('tcgAnalysisReview.notApplicable');
  const unresolved = t('tcgAnalysisReview.unresolved');
  const lineSpan = item.gemini.span || '';
  const fieldRows: ComparisonRow[] = fieldOrder.map(([key, labelKey]) => {
    const cell = systemCell(item, key, t);
    return { key, label: t(labelKey), gemini: geminiCell(item, key, t), system: cell.value, source: cell.source ?? na };
  });
  const extraRows: ComparisonRow[] = [
    { key: 'sourcePosition', label: t('tcgAnalysisReview.sourcePosition'), gemini: rawValue(lineSpan) || unresolved, system: na, source: na, line: sourceLine(lineSpan) },
    { key: 'work', label: t('superAdmin.supplierQuality.workName'), gemini: na, system: item.system.work_name || t('common.unresolved'), source: na },
    { key: 'productId', label: t('tcgAnalysisReview.productId'), gemini: na, system: item.system.product_id || t('common.unresolved'), source: na },
    { key: 'saleStatus', label: t('tcgAnalysisReview.saleStatus'), gemini: na, system: item.system.status || t('common.unresolved'), source: na },
  ];
  return [...fieldRows, ...extraRows];
}
/** 値の2列用。幅に追従し、はみ出しは省略（title で全文） */
function ComparisonCell({ text, node }: { text: string; node?: React.ReactNode }) { return <span className="item-comparison__cell" title={text}>{node ?? text}</span>; }
/** ラベル列・採用元列用。省略せず、列が文字の幅まで広がる */
function FixedCell({ text, node }: { text: string; node?: React.ReactNode }) { return <span className="item-comparison__fixed" title={text}>{node ?? text}</span>; }

/** 要確認スライド用の「修正」列。行を押す操作は onRowSelect だけ（値の変更は別の「直す」欄でしかできない） */
export type FixColumn = { selectedRowKey: string | null; onRowSelect: (rowKey: string) => void; fixableRowKeys: string[] };

function ReadOnlyComparison({ item, onJumpToSourceLine, heading, fixColumn }: { item: AnalysisReviewItem; onJumpToSourceLine: (line: number) => void; heading?: string; fixColumn?: FixColumn }) {
  const { t } = useTranslation();
  const issueBadges = reviewIssueBadges(item.review_issues || []), productIssueBadges = productMetadataIssueBadges(item.review_issues || []);
  const rows = buildComparisonRows(item, t);
  const fixRows = fixRowsOf(item, t);
  const columns: DataTableColumn<ComparisonRow>[] = [
    { key: 'label', header: t('tcgAnalysisReview.compareColumns.field'), width: 'calc(var(--comparison-label-col-w) + 2 * var(--comp-table-cell-px))', renderCell: (r) => <FixedCell text={r.label} /> },
    { key: 'gemini', header: t('tcgAnalysisReview.geminiExtraction'), renderCell: (r) => <ComparisonCell text={r.gemini} node={r.key === 'sourcePosition' && r.line ? <button className="line-jump" type="button" onClick={() => onJumpToSourceLine(r.line as number)}>{r.gemini}</button> : undefined} /> },
    { key: 'system', header: t('tcgAnalysisReview.systemFinalResult'), renderCell: (r) => <ComparisonCell text={r.system} node={r.key === 'productId' && productIssueBadges.length > 0 ? <>{r.system}{productIssueBadges.map((badge) => <StatusBadge key={badge.id} label={badge.label} tone={badge.tone} />)}</> : undefined} /> },
    fixColumn
      ? { key: 'fix', header: t('tcgAnalysisReview.compareColumns.fix'), renderCell: (r) => { const fix = fixRowOf(fixRows, r.key); const text = fix.value ?? (fix.scope ? t('reviewItem.fixColumn.tapToFix') : t('tcgAnalysisReview.notApplicable')); return <ComparisonCell text={text} node={fix.value === null && fix.scope ? <span className="item-comparison__tap">{text}</span> : undefined} />; } }
      : { key: 'source', header: t('tcgAnalysisReview.compareColumns.source'), width: 'calc(var(--comparison-source-col-w) + 2 * var(--comp-table-cell-px))', renderCell: (r) => <FixedCell text={r.source} node={<span className="item-comparison__source">{r.source}</span>} /> },
  ];
  return <article className="item-comparison item-comparison--readonly">
    {heading !== undefined
      ? <div className="review-item-pane-head"><h3>{heading}</h3>{issueBadges.map((badge) => <StatusBadge key={badge.id} label={badge.label} tone={badge.tone} />)}</div>
      : issueBadges.length > 0 && <div className="item-comparison__badges">{issueBadges.map((badge) => <StatusBadge key={badge.id} label={badge.label} tone={badge.tone} />)}</div>}
    <DataTable columns={columns} data={rows} rowKey={(r) => r.key} density="compact" className="item-comparison__table"
      {...(fixColumn ? {
        onRowClick: (r: ComparisonRow) => { if (fixColumn.fixableRowKeys.includes(r.key)) fixColumn.onRowSelect(r.key); },
        selectedKeys: fixColumn.selectedRowKey ? new Set([fixColumn.selectedRowKey]) : undefined,
        rowClassName: (r: ComparisonRow) => (fixColumn.fixableRowKeys.includes(r.key) ? '' : 'item-comparison__row--static'),
      } : {})} />
  </article>;
}

export function ItemComparison({ item, values = emptyCorrections(), options, correctionState, note = '', noteState, noteDiagnostic, onCorrectionChange = () => {}, onCorrectionSave = () => {}, onNoteChange = () => {}, onNoteSave = () => {}, onJumpToSourceLine, readOnly = false, heading, fixColumn }: { item: AnalysisReviewItem; values?: CorrectionValues; options?: CorrectionOptions; correctionState?: 'idle' | 'saving' | 'saved' | 'error'; note?: string; noteState?: 'idle' | 'saving' | 'saved' | 'error'; noteDiagnostic?: { error_code: string; stage: string; extraction_item_id: string; source_message_id: string; build_sha: string; request_id: string }; onCorrectionChange?: (key: keyof CorrectionValues, value: string) => void; onCorrectionSave?: () => void; onNoteChange?: (value: string) => void; onNoteSave?: () => void; onJumpToSourceLine: (line: number) => void; readOnly?: boolean; heading?: string; fixColumn?: FixColumn }) {
  const { t } = useTranslation();
  if (readOnly) return <ReadOnlyComparison item={item} onJumpToSourceLine={onJumpToSourceLine} heading={heading} fixColumn={fixColumn} />;
  const corrected = Object.values(values).some(Boolean), issueBadges = reviewIssueBadges(item.review_issues || []), productIssueBadges = productMetadataIssueBadges(item.review_issues || []), lineSpan = item.gemini.span || '', line = sourceLine(lineSpan);
  return <article className={readOnly ? 'item-comparison item-comparison--readonly' : 'item-comparison'}><div className="item-head-grid"><h3>{t('tcgAnalysisReview.geminiExtraction')}</h3><div><h3>{t('tcgAnalysisReview.systemFinalResult')}</h3><span className="inline-badges">{issueBadges.map((badge) => <StatusBadge key={badge.id} label={badge.label} tone={badge.tone} />)}</span></div>{!readOnly && <div><h3>{t('tcgAnalysisReview.manualCorrection')}</h3><span className={`badge ${corrected ? 'badge-warning' : 'badge-neutral'}`}>{corrected ? t('tcgAnalysisReview.hasCorrected') : t('tcgAnalysisReview.uncorrected')}</span></div>}</div><div className="aligned-fields">{fieldOrder.map(([key, labelKey], index) => <React.Fragment key={key}><div className="comparison-field"><b>{t(labelKey)}</b><span>{geminiCell(item, key, t)}</span></div><div className="comparison-field system-field"><b>{t(labelKey)}</b><FinalSystemValue item={item} keyName={key} /></div>{!readOnly && <div className="comparison-field manual-field"><b>{t(labelKey)}</b><ManualInput values={values} field={correctionFields[index]} options={options} onChange={onCorrectionChange} /></div>}</React.Fragment>)}</div><div className="item-extra-grid"><div className="comparison-extra"><ComparisonMetadataRow label={t('tcgAnalysisReview.sourcePosition')} value={line ? <button className="line-jump" type="button" onClick={() => onJumpToSourceLine(line)}>{lineSpan}</button> : (rawValue(lineSpan) || t('tcgAnalysisReview.unresolved'))} /></div><div className="system-extra"><ComparisonMetadataRow label={t("superAdmin.supplierQuality.workName")} value={item.system.work_name || t("common.unresolved")} /><ComparisonMetadataRow label={t('tcgAnalysisReview.productId')} value={item.system.product_id || t("common.unresolved")} badges={productIssueBadges} /><ComparisonMetadataRow label={t('tcgAnalysisReview.saleStatus')} value={item.system.status || t("common.unresolved")} /></div>{!readOnly && <div className="manual-actions"><label htmlFor={`note-${item.extraction_item_id}`}>{t('tcgAnalysisReview.yourMemo')}</label><TextareaControl id={`note-${item.extraction_item_id}`} value={note} maxLength={2000} onChange={(event) => onNoteChange(event.target.value)} /><div><Button type="button" variant="secondary" size="sm" loading={correctionState === 'saving'} disabled={true} onClick={onCorrectionSave}>{t('tcgAnalysisReview.saveCorrected')}</Button><Button type="button" variant="secondary" size="sm" loading={noteState === 'saving'} disabled={true} onClick={onNoteSave}>{t('tcgAnalysisReview.saveMemo')}</Button></div>{correctionState === 'saved' && <span className="note-saved">{t('tcgAnalysisReview.correctionSaved')}</span>}{correctionState === 'error' && <span className="note-error">{t('tcgAnalysisReview.correctionSaveError')}</span>}{noteState === 'saved' && <span className="note-saved">{t('tcgAnalysisReview.memoSaved')}</span>}{noteState === 'error' && <span className="note-error">{t('tcgAnalysisReview.memoSaveError')}{noteDiagnostic && <><br /><small>{t('tcgAnalysisReview.error')}: {noteDiagnostic.error_code}<br />{t('tcgAnalysisReview.process')}: {noteDiagnostic.stage}<br />{t('tcgAnalysisReview.targetId')}: {noteDiagnostic.extraction_item_id || t('tcgAnalysisReview.unresolved')}<br />{t('tcgAnalysisReview.requestId')}: {noteDiagnostic.request_id}</small></>}</span>}</div>}</div></article>;
}
