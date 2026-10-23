/**
 * ProductMasterDrawer — PARITY-03 Phase 3 FE
 *
 * GAS ProductMasterDrawer.tsx を移植。
 * google.script.run → api.get / api.post に差し替え。
 *
 * 4モード:
 *   PRODUCT_MASTER_UNREGISTERED → RegistrationSection
 *   PRODUCT_ID_UNRESOLVED       → SearchKeywordSection
 *   EXCLUDED                    → ExcludedSection
 *   解決済み（上記なし）          → ProductAssignSection（商品割り当て変更・確認済み記録）
 *
 * API パスは /tcg/... から書く（api クライアントが /api/v1 を付与する）。
 * mark / english_title は配信機能用列（ADR: BE 側で migration 追加予定）。
 */
import React, { useEffect, useState } from 'react';
import { Trans, useTranslation } from 'react-i18next';
import { Button } from '../../components/Button';
import { Callout } from '../../components/Callout';
import { Checkbox } from '../../components/Checkbox';
import { SelectControl } from '../../components/Select';
import { TextFieldControl } from '../../components/TextField';
import { TextareaControl } from '../../components/Textarea';
import { X } from '../../constants/icons';
import { api } from '../../lib/api';
import {
  checkProductDuplicates,
  createProduct,
  fetchRegistrationForm,
  postProductCorrection,
  type DupCandidate,
  type LookupOption,
  type RegistrationForm,
  type RegistrationValues,
} from './reviewActions';
import {
  blankCodeOf,
  blankConfirmable,
  formatAfterWorkChange,
  formatOptionsFor,
  missingFields,
  requiredFieldsMessage,
  type BlankCode,
} from '../tcg-product-import/productDetailModel';
import type { AnalysisReviewItem } from './ItemComparison';

// ── 型定義 ──────────────────────────────────────────────────────────────────

type SearchCandidate = { product_id: string; japanese_title: string; search_keywords: string };

type TextKey = Exclude<keyof RegistrationValues, 'blank_confirmations'>;

// ── 共通 UI 部品 ─────────────────────────────────────────────────────────────

const toSelectOptions = (options: LookupOption[]) => options.map((o) => ({ value: String(o.id), label: o.name }));

// ── 商品マスタ新規登録フォーム（PRODUCT_MASTER_UNREGISTERED） ─────────────────

function RegistrationSection({ item }: { item: AnalysisReviewItem }) {
  const { t } = useTranslation();
  const [form, setForm] = useState<RegistrationForm>();
  const [values, setValues] = useState<RegistrationValues>({
    product_kind_id: '',
    work_id: '',
    manufacturer_id: '',
    product_category_id: '',
    mark: '',
    japanese_title: item.gemini.name || '',
    english_title: '',
    release_date: '',
    search_keywords: '',
    exclude_keywords: '',
    product_format_id: '',
    blank_confirmations: [],
  });
  const [candidates, setCandidates] = useState<DupCandidate[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const [status, setStatus] = useState<'loading' | 'ready' | 'checking' | 'saving' | 'saved' | 'error'>('loading');
  const [error, setError] = useState('');
  const [issuedProductId, setIssuedProductId] = useState('');

  const formats = form?.lookups.product_format_id ?? [];
  const setValue = (key: TextKey, value: string) => {
    setValues((c) => {
      const next = { ...c, [key]: value };
      // ADR-1020: 値を入れたら、その項目の「調べたが存在しない」を外す。作品を変えたら紐づかない細分類を空に戻す
      const code = blankCodeOf(key);
      if (code && value.trim()) next.blank_confirmations = c.blank_confirmations.filter((x) => x !== code);
      if (key === 'work_id') next.product_format_id = formatAfterWorkChange(formats, value, c.product_format_id);
      return next;
    });
    setCandidates([]);
    setConfirmed(false);
  };

  const toggleBlank = (code: BlankCode, checked: boolean) => {
    setValues((c) => ({
      ...c,
      blank_confirmations: checked
        ? [...c.blank_confirmations.filter((x) => x !== code), code]
        : c.blank_confirmations.filter((x) => x !== code),
    }));
    setCandidates([]);
    setConfirmed(false);
  };

  useEffect(() => {
    fetchRegistrationForm(item)
      .then((result) => {
        setForm(result);
        setValues((c) => ({ ...c, japanese_title: result.item.raw_name || c.japanese_title }));
        setStatus('ready');
      })
      .catch((reason: unknown) => {
        setError(String((reason as Error)?.message || reason));
        setStatus('error');
      });
  }, [item]);

  const required = Boolean(
    values.product_kind_id && values.work_id && values.manufacturer_id &&
    values.product_category_id && values.japanese_title
  );

  const checkDuplicates = () => {
    if (!required) return;
    setStatus('checking');
    setError('');
    checkProductDuplicates(item, values)
      .then((result) => { setCandidates(result.candidates); setStatus('ready'); })
      .catch((reason: unknown) => { setError(String((reason as Error)?.message || reason)); setStatus('error'); });
  };

  const save = () => {
    if (!required || (candidates.length && !confirmed)) return;
    setStatus('saving');
    setError('');
    createProduct(item, values, confirmed)
      .then((result) => {
        if (!result.ok) {
          setCandidates(result.candidates || []);
          setConfirmed(false);
          setStatus('ready');
          return;
        }
        setIssuedProductId(result.product_id || '');
        setStatus('saved');
      })
      .catch((reason: unknown) => { setError(requiredFieldsMessage(reason, t) ?? String((reason as Error)?.message || reason)); setStatus('error'); });
  };

  const optionName = (key: 'product_kind_id' | 'work_id' | 'manufacturer_id' | 'product_category_id' | 'product_format_id') => {
    const list: LookupOption[] = form?.lookups[key] ?? [];
    return list.find((o) => o.id === values[key])?.name || t('tcgAnalysisReview.productMasterDrawer.unselected');
  };
  const missingNow = missingFields(values);
  const blankLabels: Record<BlankCode, string> = {
    name_en: 'fieldEnglishTitle', mark: 'fieldMark', release_date: 'fieldReleaseDate', exclude_keywords: 'fieldExcludeKeywords',
  };

  if (status === 'saved') {
    return (
      <div className="pmd-result">
        <strong>{t('tcgAnalysisReview.productMasterDrawer.registeredTitle')}</strong>
        <p>{t('tcgAnalysisReview.productMasterDrawer.product')}: {values.japanese_title}</p>
        <small>{t('tcgAnalysisReview.productMasterDrawer.issuedProductId')}: {issuedProductId}</small>
      </div>
    );
  }

  return (
    <>
      <h3>{t('tcgAnalysisReview.productMasterDrawer.registerHeading')}</h3>
      {status === 'loading' ? (
        <p>{t('tcgAnalysisReview.productMasterDrawer.formLoading')}</p>
      ) : (
        <>
          <div className="pmd-fields">
            <label className="pmd-field">
              {t('tcgAnalysisReview.productMasterDrawer.fieldKind')}
              <SelectControl
                size="sm"
                fullWidth
                placeholder={t('tcgAnalysisReview.productMasterDrawer.selectPlaceholder')}
                options={toSelectOptions(form?.lookups.product_kind_id || [])}
                value={values.product_kind_id}
                onChange={(e) => setValue('product_kind_id', e.target.value)}
              />
            </label>
            <label className="pmd-field">
              {t('tcgAnalysisReview.productMasterDrawer.fieldWork')}
              <SelectControl
                size="sm"
                fullWidth
                placeholder={t('tcgAnalysisReview.productMasterDrawer.selectPlaceholder')}
                options={toSelectOptions(form?.lookups.work_id || [])}
                value={values.work_id}
                onChange={(e) => setValue('work_id', e.target.value)}
              />
            </label>
            <label className="pmd-field">
              {t('tcgAnalysisReview.productMasterDrawer.fieldManufacturer')}
              <SelectControl
                size="sm"
                fullWidth
                placeholder={t('tcgAnalysisReview.productMasterDrawer.selectPlaceholder')}
                options={toSelectOptions(form?.lookups.manufacturer_id || [])}
                value={values.manufacturer_id}
                onChange={(e) => setValue('manufacturer_id', e.target.value)}
              />
            </label>
            <label className="pmd-field">
              {t('tcgAnalysisReview.productMasterDrawer.fieldCategory')}
              <SelectControl
                size="sm"
                fullWidth
                placeholder={t('tcgAnalysisReview.productMasterDrawer.selectPlaceholder')}
                options={toSelectOptions(form?.lookups.product_category_id || [])}
                value={values.product_category_id}
                onChange={(e) => setValue('product_category_id', e.target.value)}
              />
            </label>
            <label className="pmd-field">
              {t('tcgAnalysisReview.productMasterDrawer.fieldFormat')}
              <SelectControl
                size="sm"
                fullWidth
                placeholder={t('tcgAnalysisReview.productMasterDrawer.selectPlaceholder')}
                options={toSelectOptions(formatOptionsFor(formats, values.work_id))}
                value={values.product_format_id}
                onChange={(e) => setValue('product_format_id', e.target.value)}
                disabled={!values.work_id}
              />
            </label>
            <label className="pmd-field">
              {t('tcgAnalysisReview.productMasterDrawer.fieldMark')}
              <TextFieldControl size="sm" value={values.mark} onChange={(e) => setValue('mark', e.target.value)} />
            </label>
            <label className="pmd-field">
              {t('tcgAnalysisReview.productMasterDrawer.fieldJapaneseTitle')}
              <TextFieldControl size="sm" value={values.japanese_title} required onChange={(e) => setValue('japanese_title', e.target.value)} />
            </label>
            <label className="pmd-field">
              {t('tcgAnalysisReview.productMasterDrawer.fieldEnglishTitle')}
              <TextFieldControl size="sm" value={values.english_title} onChange={(e) => setValue('english_title', e.target.value)} />
            </label>
            <label className="pmd-field">
              {t('tcgAnalysisReview.productMasterDrawer.fieldReleaseDate')}
              <TextFieldControl size="sm" type="date" value={values.release_date} onChange={(e) => setValue('release_date', e.target.value)} />
            </label>
            <label className="pmd-field">
              {t('tcgAnalysisReview.productMasterDrawer.fieldSearchKeywords')}
              <TextareaControl size="sm" value={values.search_keywords} onChange={(e) => setValue('search_keywords', e.target.value)} />
            </label>
            <label className="pmd-field">
              {t('tcgAnalysisReview.productMasterDrawer.fieldExcludeKeywords')}
              <TextareaControl size="sm" value={values.exclude_keywords} onChange={(e) => setValue('exclude_keywords', e.target.value)} />
            </label>
            {blankConfirmable.map(([code, field]) => (
              <Checkbox
                key={code}
                size="sm"
                label={t('productDetail.notFound', { field: t(`tcgAnalysisReview.productMasterDrawer.${blankLabels[code]}`) })}
                checked={values.blank_confirmations.includes(code)}
                disabled={Boolean(values[field].trim())}
                onChange={(e) => toggleBlank(code, e.target.checked)}
              />
            ))}
          </div>
          <section className="pmd-result">
            <h4>{t('tcgAnalysisReview.productMasterDrawer.confirmHeading')}</h4>
            <p>{t('tcgAnalysisReview.productMasterDrawer.fieldKind')}: {optionName('product_kind_id')}</p>
            <p>{t('tcgAnalysisReview.productMasterDrawer.fieldWork')}: {optionName('work_id')}</p>
            <p>{t('tcgAnalysisReview.productMasterDrawer.fieldManufacturer')}: {optionName('manufacturer_id')}</p>
            <p>{t('tcgAnalysisReview.productMasterDrawer.fieldCategory')}: {optionName('product_category_id')}</p>
            <p>{t('tcgAnalysisReview.productMasterDrawer.fieldFormat')}: {optionName('product_format_id')}</p>
            <p>{t('tcgAnalysisReview.productMasterDrawer.fieldMark')}: {values.mark || t('tcgAnalysisReview.productMasterDrawer.emptyValue')}</p>
            <p>{t('tcgAnalysisReview.productMasterDrawer.fieldJapaneseTitle')}: {values.japanese_title || t('tcgAnalysisReview.productMasterDrawer.emptyValue')}</p>
            <p>{t('tcgAnalysisReview.productMasterDrawer.fieldEnglishTitle')}: {values.english_title || t('tcgAnalysisReview.productMasterDrawer.emptyValue')}</p>
          </section>
          {missingNow.length > 0 && (
            <Callout
              variant="info"
              title={t('reviewItem.wizard.register.missingFields', {
                fields: missingNow.map((field) => t(`productDetail.${field}`)).join(t('reviewItem.wizard.register.listSeparator')),
              })}
            />
          )}
          {candidates.length > 0 && (
            <section className="pmd-warning">
              <strong>{t('tcgAnalysisReview.productMasterDrawer.duplicateWarning')}</strong>
              {candidates.map((c) => (
                <p key={c.product_id}>{c.product_id}: {c.japanese_title}</p>
              ))}
              <Checkbox
                label={t('tcgAnalysisReview.productMasterDrawer.duplicateConfirmed')}
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />
            </section>
          )}
          {error && <p className="pmd-error">{t('tcgAnalysisReview.productMasterDrawer.registerError')}: {error}</p>}
          <div className="pmd-actions">
            <Button
              type="button"
              variant="secondary"
              size="md"
              disabled={!required || status === 'checking' || status === 'saving'}
              onClick={checkDuplicates}
            >
              {status === 'checking' ? t('tcgAnalysisReview.productMasterDrawer.checking') : t('tcgAnalysisReview.productMasterDrawer.checkDuplicates')}
            </Button>
            <Button
              type="button"
              variant="primary"
              size="md"
              disabled={!required || (candidates.length > 0 && !confirmed) || status === 'saving'}
              onClick={save}
            >
              {status === 'saving' ? t('tcgAnalysisReview.productMasterDrawer.saving') : t('tcgAnalysisReview.productMasterDrawer.register')}
            </Button>
          </div>
        </>
      )}
    </>
  );
}

// ── 検索ワード追記セクション（PRODUCT_ID_UNRESOLVED） ────────────────────────

function SearchKeywordSection({ item }: { item: AnalysisReviewItem }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState(item.gemini.name || '');
  const [candidates, setCandidates] = useState<SearchCandidate[]>([]);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState<SearchCandidate>();
  const [addStatus, setAddStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [addError, setAddError] = useState('');

  const search = () => {
    if (!query.trim()) return;
    setSearching(true);
    setCandidates([]);
    setSelected(undefined);
    const params = new URLSearchParams({ query });
    api.get<{ candidates: SearchCandidate[] }>(`/tcg/products/search?${params.toString()}`)
      .then((result) => { setCandidates(result.candidates); setSearching(false); })
      .catch(() => { setSearching(false); });
  };

  const addKeyword = () => {
    if (!selected || !item.gemini.name) return;
    setAddStatus('saving');
    setAddError('');
    api.post<{ ok: boolean; code?: string }>(
      `/tcg/products/${encodeURIComponent(selected.product_id)}/search-keywords`,
      { new_keyword: item.gemini.name }
    )
      .then((result) => {
        if (result.ok) {
          setAddStatus('saved');
        } else if (result.code === 'KEYWORD_ALREADY_EXISTS') {
          setAddStatus('idle');
          setAddError(t('tcgAnalysisReview.productMasterDrawer.keywordExists'));
        } else {
          setAddStatus('error');
          setAddError(t('tcgAnalysisReview.productMasterDrawer.keywordAddFailed'));
        }
      })
      .catch((reason: unknown) => {
        setAddStatus('error');
        setAddError(String((reason as Error)?.message || reason));
      });
  };

  if (addStatus === 'saved') {
    return (
      <div className="pmd-result">
        <strong>{t('tcgAnalysisReview.productMasterDrawer.keywordAddedTitle')}</strong>
        <p>{t('tcgAnalysisReview.productMasterDrawer.product')}: {selected?.japanese_title}</p>
        <small>{t('tcgAnalysisReview.productMasterDrawer.addedKeyword')}: {item.gemini.name}</small>
      </div>
    );
  }

  return (
    <>
      <h3>{t('tcgAnalysisReview.productMasterDrawer.keywordHeading')}</h3>
      <p>
        <Trans
          i18nKey={'tcgAnalysisReview.productMasterDrawer.keywordIntro'}
          values={{ name: item.gemini.name || t('tcgAnalysisReview.productMasterDrawer.notAvailable') }}
          components={{ strong: <strong /> }}
          tOptions={{ interpolation: { escapeValue: true } }}
          shouldUnescape
        />
      </p>
      <div className="pmd-fields">
        <label className="pmd-field">
          {t('tcgAnalysisReview.productMasterDrawer.searchByName')}
          <TextFieldControl
            size="sm"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('superAdmin.supplierQuality.productAssign.searchPlaceholder')}
          />
        </label>
      </div>
      <div className="pmd-actions">
        <Button type="button" variant="secondary" size="md" disabled={!query.trim() || searching} onClick={search}>
          {searching ? t('superAdmin.supplierQuality.productAssign.searching') : t('tcgAnalysisReview.productMasterDrawer.searchMaster')}
        </Button>
      </div>
      {candidates.length === 0 && !searching && (
        <p className="pmd-note">{t('superAdmin.supplierQuality.productAssign.noResults')}</p>
      )}
      {candidates.map((c) => (
        <div
          key={c.product_id}
          className={`pmd-search-candidate${selected?.product_id === c.product_id ? ' pmd-search-candidate--selected' : ''}`}
        >
          <Button type="button" variant="ghost" size="md" layoutClassName="pmd-candidate-btn" onClick={() => setSelected(c === selected ? undefined : c)}>
            <span><strong>{c.product_id}</strong> {c.japanese_title}</span>
          </Button>
          {c.search_keywords && <small>{t('tcgAnalysisReview.productMasterDrawer.currentKeywords')}: {c.search_keywords}</small>}
        </div>
      ))}
      {selected && (
        <>
          <div className="pmd-result">
            <p>{t('tcgAnalysisReview.productMasterDrawer.selected')}: <strong>{selected.japanese_title}</strong></p>
            <p>{t('tcgAnalysisReview.productMasterDrawer.keywordToAdd')}: <strong>{item.gemini.name}</strong></p>
          </div>
          {addError && <p className="pmd-error">{addError}</p>}
          <div className="pmd-actions">
            <Button type="button" variant="primary" size="md" disabled={addStatus === 'saving'} onClick={addKeyword}>
              {addStatus === 'saving' ? t('tcgAnalysisReview.productMasterDrawer.adding') : t('tcgAnalysisReview.productMasterDrawer.addKeyword')}
            </Button>
          </div>
        </>
      )}
    </>
  );
}

// ── 除外対象表示セクション（EXCLUDED） ─────────────────────────────────────

function ExcludedSection({ item }: { item: AnalysisReviewItem }) {
  const { t } = useTranslation();
  return (
    <div className="pmd-warning">
      <h3>{t('reviewIssues.excluded')}</h3>
      <p>{t('tcgAnalysisReview.productMasterDrawer.excludedBody')}</p>
      <p>{t('tcgAnalysisReview.productMasterDrawer.geminiName')}: <strong>{item.gemini.name || t('tcgAnalysisReview.productMasterDrawer.notAvailable')}</strong></p>
      <p>{t('tcgAnalysisReview.productMasterDrawer.excludedHowTo')}</p>
      <small>{t('tcgAnalysisReview.productMasterDrawer.editLater')}</small>
    </div>
  );
}

// ── 商品割り当て変更セクション（解決済み行） ──────────────────────────────────

type AssignCandidate = { product_id: string; product_uuid: string; japanese_title: string; search_keywords: string };

function ProductAssignSection({ item, onSaved }: { item: AnalysisReviewItem; onSaved?: () => void }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [candidates, setCandidates] = useState<AssignCandidate[]>([]);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState<AssignCandidate>();
  const [status, setStatus] = useState<'idle' | 'changing' | 'changed' | 'confirming' | 'confirmed' | 'error'>('idle');
  const [error, setError] = useState('');

  const search = () => {
    if (!query.trim()) return;
    setSearching(true);
    setCandidates([]);
    setSelected(undefined);
    const params = new URLSearchParams({ query });
    api.get<{ candidates: AssignCandidate[] }>(`/tcg/products/search?${params.toString()}`)
      .then((result) => { setCandidates(result.candidates); setSearching(false); })
      .catch(() => { setSearching(false); });
  };

  const postCorrection = (humanValue: string) => postProductCorrection(item, humanValue);

  const changeProduct = () => {
    if (!selected) return;
    setStatus('changing');
    setError('');
    postCorrection(selected.product_uuid)
      .then(() => { setStatus('changed'); onSaved?.(); })
      .catch((reason: unknown) => { setStatus('error'); setError(String((reason as Error)?.message || reason)); });
  };

  const markConfirmed = () => {
    const currentUuid = item.system.product_uuid || '';
    if (!currentUuid) return;
    setStatus('confirming');
    setError('');
    postCorrection(currentUuid)
      .then(() => { setStatus('confirmed'); onSaved?.(); })
      .catch((reason: unknown) => { setStatus('error'); setError(String((reason as Error)?.message || reason)); });
  };

  const currentCode = item.system.product_id || '';
  const currentTitle = item.system.product_title || '';
  const busy = status === 'changing' || status === 'confirming';

  if (status === 'changed' || status === 'confirmed') {
    const msg = status === 'changed'
      ? t('superAdmin.supplierQuality.productAssign.changed')
      : t('superAdmin.supplierQuality.productAssign.confirmed');
    return <div className="pmd-result"><strong>{msg}</strong></div>;
  }

  return (
    <>
      <h3>{t('superAdmin.supplierQuality.productAssign.title')}</h3>
      <div className="pmd-result">
        <p><b>{t('superAdmin.supplierQuality.productAssign.currentProduct')}</b></p>
        <p>{currentCode ? `${currentCode}  ${currentTitle}` : t('superAdmin.supplierQuality.productAssign.noProduct')}</p>
      </div>
      <div className="pmd-fields">
        <label className="pmd-field">
          {t('superAdmin.supplierQuality.productAssign.searchPlaceholder')}
          <TextFieldControl
            size="sm"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') search(); }}
            placeholder={t('superAdmin.supplierQuality.productAssign.searchPlaceholder')}
          />
        </label>
      </div>
      <div className="pmd-actions">
        <Button type="button" variant="secondary" size="md" disabled={!query.trim() || searching} onClick={search}>
          {searching ? t('superAdmin.supplierQuality.productAssign.searching') : t('superAdmin.supplierQuality.productAssign.searchBtn')}
        </Button>
      </div>
      {candidates.length === 0 && !searching && query && (
        <p className="pmd-note">{t('superAdmin.supplierQuality.productAssign.noResults')}</p>
      )}
      {candidates.map((c) => (
        <div
          key={c.product_uuid}
          className={`pmd-search-candidate${selected?.product_uuid === c.product_uuid ? ' pmd-search-candidate--selected' : ''}`}
        >
          <Button type="button" variant="ghost" size="md" layoutClassName="pmd-candidate-btn" onClick={() => setSelected(c === selected ? undefined : c)}>
            <span><strong>{c.product_id}</strong>  {c.japanese_title}</span>
          </Button>
          {c.search_keywords && <small>{c.search_keywords}</small>}
        </div>
      ))}
      {error && <p className="pmd-error">{error}</p>}
      <div className="pmd-actions">
        <Button type="button" variant="primary" size="md" disabled={!selected || busy} onClick={changeProduct}>
          {status === 'changing' ? t('superAdmin.supplierQuality.productAssign.changing') : t('superAdmin.supplierQuality.productAssign.changeBtn')}
        </Button>
        <Button type="button" variant="secondary" size="md" disabled={!item.system.product_uuid || busy} onClick={markConfirmed}>
          {status === 'confirming' ? t('superAdmin.supplierQuality.productAssign.confirming') : t('superAdmin.supplierQuality.productAssign.confirmBtn')}
        </Button>
      </div>
    </>
  );
}

// ── バッジに応じてセクションを切り替え ─────────────────────────────────────

function MasterMaintenanceSection({ item, onSaved }: { item: AnalysisReviewItem; onSaved?: () => void }) {
  const issues = item.review_issues || [];
  if (issues.includes('PRODUCT_MASTER_UNREGISTERED')) return <RegistrationSection item={item} />;
  if (issues.includes('PRODUCT_ID_UNRESOLVED')) return <SearchKeywordSection item={item} />;
  if (issues.includes('EXCLUDED')) return <ExcludedSection item={item} />;
  return <ProductAssignSection item={item} onSaved={onSaved} />;
}

// ── ドロワー本体 ──────────────────────────────────────────────────────────────

export function ProductMasterDrawer({ item, onClose, onSaved }: { item: AnalysisReviewItem; onClose: () => void; onSaved?: () => void }) {
  const { t } = useTranslation();
  return (
    <>
      <div className="pmd-backdrop" onClick={onClose} />
      <aside className="pmd-drawer" aria-label={t('tcgAnalysisReview.productMasterDrawer.drawerAriaLabel')}>
        <div className="pmd-head">
          <h2>{item.gemini.name || t('tcgAnalysisReview.productMasterDrawer.drawerTitleFallback')}</h2>
          <Button type="button" variant="ghost" size="md" iconOnly aria-label={t('common.close')} onClick={onClose}>
            <X size={20} aria-hidden="true" />
          </Button>
        </div>
        <div className="pmd-body">
          <MasterMaintenanceSection item={item} onSaved={onSaved} />
        </div>
      </aside>
    </>
  );
}
