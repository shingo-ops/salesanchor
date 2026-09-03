/**
 * ProductMasterDrawer — PARITY-03 Phase 3 FE
 *
 * GAS ProductMasterDrawer.tsx を移植。
 * google.script.run → api.get / api.post に差し替え。
 *
 * 3モード:
 *   PRODUCT_MASTER_UNREGISTERED → RegistrationSection
 *   PRODUCT_ID_UNRESOLVED       → SearchKeywordSection
 *   EXCLUDED                    → ExcludedSection
 *
 * API パスは /tcg/... から書く（api クライアントが /api/v1 を付与する）。
 * mark / english_title は配信機能用列（ADR: BE 側で migration 追加予定）。
 */
import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import type { AnalysisReviewItem } from './ItemComparison';

// ── 型定義 ──────────────────────────────────────────────────────────────────

type LookupOption = { id: string; name: string };

type RegistrationForm = {
  item: { extraction_item_id: string; source_message_id: string; raw_name: string };
  lookups: Record<string, LookupOption[]>;
};

type RegistrationValues = {
  division_id: string;
  work_id: string;
  manufacturer_id: string;
  product_category_id: string;
  mark: string;
  japanese_title: string;
  english_title: string;
  release_date: string;
  search_keywords: string;
  exclude_keywords: string;
};

type DupCandidate = { product_id: string; japanese_title: string };
type SearchCandidate = { product_id: string; japanese_title: string; search_keywords: string };

// ── 共通 UI 部品 ─────────────────────────────────────────────────────────────

function SearchSelect({
  label,
  lookupKey,
  options,
  value,
  onChange,
}: {
  label: string;
  lookupKey: keyof RegistrationValues;
  options: LookupOption[];
  value: string;
  onChange: (key: keyof RegistrationValues, value: string) => void;
}) {
  const selected = options.find((o) => o.id === value);
  const listId = `lookup-${lookupKey}`;
  const [query, setQuery] = useState(selected?.name || '');
  useEffect(() => { if (selected) setQuery(selected.name); }, [selected]);
  return (
    <label className="pmd-field">
      {label}
      <input
        list={listId}
        value={query}
        placeholder="名称で検索・選択"
        onChange={(e) => {
          setQuery(e.target.value);
          const match = options.find((o) => o.name === e.target.value);
          onChange(lookupKey, match?.id || '');
        }}
      />
      <datalist id={listId}>
        {options.map((o) => <option value={o.name} key={o.id} />)}
      </datalist>
    </label>
  );
}

// ── 商品マスタ新規登録フォーム（PRODUCT_MASTER_UNREGISTERED） ─────────────────

function RegistrationSection({ item }: { item: AnalysisReviewItem }) {
  const [form, setForm] = useState<RegistrationForm>();
  const [values, setValues] = useState<RegistrationValues>({
    division_id: '',
    work_id: '',
    manufacturer_id: '',
    product_category_id: '',
    mark: '',
    japanese_title: item.gemini.name || '',
    english_title: '',
    release_date: '',
    search_keywords: '',
    exclude_keywords: '',
  });
  const [candidates, setCandidates] = useState<DupCandidate[]>([]);
  const [status, setStatus] = useState<'loading' | 'ready' | 'checking' | 'saving' | 'saved' | 'error'>('loading');
  const [error, setError] = useState('');
  const [issuedProductId, setIssuedProductId] = useState('');

  const setValue = (key: keyof RegistrationValues, value: string) => {
    setValues((c) => ({ ...c, [key]: value }));
    setCandidates([]);
  };

  useEffect(() => {
    const params = new URLSearchParams({
      extraction_item_id: item.extraction_item_id,
      source_message_id: item.source_message_id,
    });
    api.get<RegistrationForm>(`/tcg/products/registration-form?${params.toString()}`)
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
    values.division_id && values.work_id && values.manufacturer_id &&
    values.product_category_id && values.japanese_title
  );

  const checkDuplicates = () => {
    if (!required) return;
    setStatus('checking');
    setError('');
    api.post<{ candidates: DupCandidate[] }>('/tcg/products/check-duplicates', {
      extraction_item_id: item.extraction_item_id,
      source_message_id: item.source_message_id,
      ...values,
    })
      .then((result) => { setCandidates(result.candidates); setStatus('ready'); })
      .catch((reason: unknown) => { setError(String((reason as Error)?.message || reason)); setStatus('error'); });
  };

  const save = () => {
    if (!required || candidates.length) return;
    setStatus('saving');
    setError('');
    api.post<{ ok: boolean; product_id?: string; code?: string; candidates?: DupCandidate[] }>(
      '/tcg/products',
      {
        extraction_item_id: item.extraction_item_id,
        source_message_id: item.source_message_id,
        ...values,
      }
    )
      .then((result) => {
        if (!result.ok) {
          setCandidates(result.candidates || []);
          setStatus('ready');
          return;
        }
        setIssuedProductId(result.product_id || '');
        setStatus('saved');
      })
      .catch((reason: unknown) => { setError(String((reason as Error)?.message || reason)); setStatus('error'); });
  };

  const optionName = (key: string) =>
    form?.lookups[key]?.find((o) => o.id === values[key as keyof RegistrationValues])?.name || '未選択';

  if (status === 'saved') {
    return (
      <div className="pmd-result">
        <strong>商品マスタへの登録が完了しました（次回解析で反映）</strong>
        <p>商品: {values.japanese_title}</p>
        <small>発行された商品ID: {issuedProductId}</small>
      </div>
    );
  }

  return (
    <>
      <h3>商品マスタ新規登録</h3>
      {status === 'loading' ? (
        <p>登録フォームを読み込み中…</p>
      ) : (
        <>
          <div className="pmd-fields">
            <SearchSelect label="大分類" lookupKey="division_id" options={form?.lookups.division_id || []} value={values.division_id} onChange={setValue} />
            <SearchSelect label="作品" lookupKey="work_id" options={form?.lookups.work_id || []} value={values.work_id} onChange={setValue} />
            <SearchSelect label="メーカー" lookupKey="manufacturer_id" options={form?.lookups.manufacturer_id || []} value={values.manufacturer_id} onChange={setValue} />
            <SearchSelect label="商品カテゴリ" lookupKey="product_category_id" options={form?.lookups.product_category_id || []} value={values.product_category_id} onChange={setValue} />
            <label className="pmd-field">
              マーク
              <input value={values.mark} onChange={(e) => setValue('mark', e.target.value)} />
            </label>
            <label className="pmd-field">
              日本語タイトル
              <input value={values.japanese_title} required onChange={(e) => setValue('japanese_title', e.target.value)} />
            </label>
            <label className="pmd-field">
              英語タイトル
              <input value={values.english_title} onChange={(e) => setValue('english_title', e.target.value)} />
            </label>
            <label className="pmd-field">
              発売日
              <input type="date" value={values.release_date} onChange={(e) => setValue('release_date', e.target.value)} />
            </label>
            <label className="pmd-field">
              検索キーワード
              <textarea value={values.search_keywords} onChange={(e) => setValue('search_keywords', e.target.value)} />
            </label>
            <label className="pmd-field">
              除外キーワード
              <textarea value={values.exclude_keywords} onChange={(e) => setValue('exclude_keywords', e.target.value)} />
            </label>
          </div>
          <section className="pmd-result">
            <h4>登録内容確認</h4>
            <p>大分類: {optionName('division_id')}</p>
            <p>作品: {optionName('work_id')}</p>
            <p>メーカー: {optionName('manufacturer_id')}</p>
            <p>商品カテゴリ: {optionName('product_category_id')}</p>
            <p>マーク: {values.mark || '未入力'}</p>
            <p>日本語タイトル: {values.japanese_title || '未入力'}</p>
            <p>英語タイトル: {values.english_title || '未入力'}</p>
          </section>
          {candidates.length > 0 && (
            <section className="pmd-warning">
              <strong>既存商品の可能性があります（確認してください）</strong>
              {candidates.map((c) => (
                <p key={c.product_id}>{c.product_id}: {c.japanese_title}</p>
              ))}
            </section>
          )}
          {error && <p className="pmd-error">登録エラー: {error}</p>}
          <div className="pmd-actions">
            <button
              type="button"
              disabled={!required || status === 'checking' || status === 'saving'}
              onClick={checkDuplicates}
            >
              {status === 'checking' ? '確認中…' : '重複候補を確認'}
            </button>
            <button
              type="button"
              disabled={!required || candidates.length > 0 || status === 'saving'}
              onClick={save}
            >
              {status === 'saving' ? '登録中…' : '商品マスタに登録'}
            </button>
          </div>
        </>
      )}
    </>
  );
}

// ── 検索ワード追記セクション（PRODUCT_ID_UNRESOLVED） ────────────────────────

function SearchKeywordSection({ item }: { item: AnalysisReviewItem }) {
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
          setAddError('このキーワードはすでに登録済みです。');
        } else {
          setAddStatus('error');
          setAddError('追記に失敗しました。');
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
        <strong>検索キーワードを追記しました（次回解析で反映）</strong>
        <p>商品: {selected?.japanese_title}</p>
        <small>追記したキーワード: {item.gemini.name}</small>
      </div>
    );
  }

  return (
    <>
      <h3>マスタ検索・検索キーワード追記</h3>
      <p>Gemini抽出名「<strong>{item.gemini.name || '未取得'}</strong>」を既存商品の検索キーワードに追記します。</p>
      <div className="pmd-fields">
        <label className="pmd-field">
          商品名で検索
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="商品名を入力"
          />
        </label>
      </div>
      <div className="pmd-actions">
        <button type="button" disabled={!query.trim() || searching} onClick={search}>
          {searching ? '検索中…' : 'マスタを検索'}
        </button>
      </div>
      {candidates.length === 0 && !searching && (
        <p className="pmd-note">検索結果なし</p>
      )}
      {candidates.map((c) => (
        <div
          key={c.product_id}
          className={`pmd-search-candidate${selected?.product_id === c.product_id ? ' pmd-search-candidate--selected' : ''}`}
        >
          <button type="button" onClick={() => setSelected(c === selected ? undefined : c)}>
            <strong>{c.product_id}</strong> {c.japanese_title}
          </button>
          {c.search_keywords && <small>現在の検索KW: {c.search_keywords}</small>}
        </div>
      ))}
      {selected && (
        <>
          <div className="pmd-result">
            <p>選択中: <strong>{selected.japanese_title}</strong></p>
            <p>追記するキーワード: <strong>{item.gemini.name}</strong></p>
          </div>
          {addError && <p className="pmd-error">{addError}</p>}
          <div className="pmd-actions">
            <button type="button" disabled={addStatus === 'saving'} onClick={addKeyword}>
              {addStatus === 'saving' ? '追記中…' : 'キーワードを追記'}
            </button>
          </div>
        </>
      )}
    </>
  );
}

// ── 除外対象表示セクション（EXCLUDED） ─────────────────────────────────────

function ExcludedSection({ item }: { item: AnalysisReviewItem }) {
  return (
    <div className="pmd-warning">
      <h3>除外対象</h3>
      <p>この商品は商品マスタの除外キーワードに一致したため、解析から除外されています。</p>
      <p>Gemini抽出名: <strong>{item.gemini.name || '未取得'}</strong></p>
      <p>除外キーワードの確認・変更は 商品マスタV2 シートの Exclude Keywords 列から直接行ってください。</p>
      <small>（編集機能は今後のリリースで追加予定）</small>
    </div>
  );
}

// ── バッジに応じてセクションを切り替え ─────────────────────────────────────

function MasterMaintenanceSection({ item }: { item: AnalysisReviewItem }) {
  const issues = item.review_issues || [];
  if (issues.includes('PRODUCT_MASTER_UNREGISTERED')) return <RegistrationSection item={item} />;
  if (issues.includes('PRODUCT_ID_UNRESOLVED')) return <SearchKeywordSection item={item} />;
  if (issues.includes('EXCLUDED')) return <ExcludedSection item={item} />;
  return null;
}

// ── ドロワー本体 ──────────────────────────────────────────────────────────────

export function ProductMasterDrawer({ item, onClose }: { item: AnalysisReviewItem; onClose: () => void }) {
  return (
    <>
      <div className="pmd-backdrop" onClick={onClose} />
      <aside className="pmd-drawer" aria-label="商品マスタメンテナンス">
        <div className="pmd-head">
          <h2>{item.gemini.name || '商品マスタ修正'}</h2>
          <button type="button" onClick={onClose} aria-label="閉じる">×</button>
        </div>
        <div className="pmd-body">
          <MasterMaintenanceSection item={item} />
        </div>
      </aside>
    </>
  );
}
