# 未決5 の根拠（担当者編集画面の押せない統合ボタン）

origin/main aec493c7f で取得（2026-11-12・Opus）。cee9633b9 から対象パスの差分なし（git diff --stat が空）。コードの写しのみ・顧客情報なし。

```text
=== ContactEditPage head/180-235
     1	/**
     2	 * ContactEditPage — 担当者フルページ編集（/contacts/:id/edit）
     3	 *
     4	 * Drawer 内「フルページで開く↗」から遷移するフルページ版。
     5	 * 全項目編集＋重複確認待ち（pending_dedup_review）の解消フローを含む。
     6	 * 保存後は /contacts 一覧へ戻る。
     7	 */
     8	
     9	import { useState, type FormEvent } from "react";
    10	import { useNavigate, useParams } from "react-router-dom";
    11	import { useTranslation } from "react-i18next";
    12	import { PageLayout } from "../../components/PageLayout";
    13	import { Button } from "../../components/Button";
    14	import { Select } from "../../components/Select";
    15	import { api } from "../../lib/api";
    16	import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
    17	import { useSeededForm } from "../../lib/query/useSeededForm";
    18	import { TextareaControl } from "../../components/Textarea";
    19	import { TextFieldControl } from "../../components/TextField";
    20	import { Checkbox } from "../../components/Checkbox";
    21	import { LoadingBlock } from "../../components/loading";
    22	
    23	interface CompanyMini {
    24	  id: number;
    25	  company_code: string;
    26	  name: string;
    27	}
    28	
    29	interface Contact {
    30	  id: number;
    31	  company_id: number;
    32	  contact_code: string;
    33	  surname: string | null;
    34	  given_name: string | null;
    35	  display_name: string | null;
    36	  job_title: string | null;
    37	  department: string | null;
    38	  is_primary_contact: boolean;
    39	  primary_email: string | null;
    40	  primary_phone: string | null;
    41	  status: string;
    42	  notes: string | null;
    43	}
    44	
    45	type FormState = {
   180	          </div>
   181	          <Select
   182	            label={t("common.status")}
   183	            value={form.status}
   184	            onChange={(e) => setForm({ ...form, status: e.target.value })}
   185	            options={[
   186	              { value: "active", label: t("customers.status_active") },
   187	              { value: "inactive", label: t("customers.status_inactive") },
   188	              { value: "archived", label: t("customers.status_archived") },
   189	              { value: "pending_dedup_review", label: t("contacts.statusPendingDedupOption") },
   190	            ]}
   191	          />
   192	          <div className="form-group"><label>{t("common.notes")}</label>
   193	            <TextareaControl value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
   194	          </div>
   195	
   196	          {form.status === "pending_dedup_review" && (
   197	            <div className="dedup-resolve-section">
   198	              <h3>{t("contacts.dedupResolveTitle")}</h3>
   199	              <p>{t("contacts.dedupResolveDesc")}</p>
   200	              <div className="dedup-resolve-actions">
   201	                <Button variant="primary" size="md" type="button" onClick={handleResolveAsDistinct} disabled={dedupSubmitting}>
   202	                  {t("contacts.confirmAsDistinctFull")}
   203	                </Button>
   204	                <button type="button" disabled style={{ opacity: "var(--opacity-disabled)", cursor: "not-allowed" }}>
   205	                  {t("contacts.mergeAsDuplicate")}
   206	                </button>
   207	              </div>
   208	            </div>
   209	          )}
   210	
   211	          <div className="form-actions">
   212	            <Button type="button" variant="secondary" size="md" onClick={() => navigate("/contacts")}>{t("common.cancel")}</Button>
   213	            <Button type="submit" variant="primary" size="md">{t("common.update")}</Button>
   214	          </div>
   215	        </form>
   216	      )}
   217	    </PageLayout>
   218	  );
   219	}
=== MergeContactModal 1-80
     1	/**
     2	 * 担当者統合モーダル（ADR-098 SA-04 J3）。
     3	 *
     4	 * 役割:
     5	 *   ソース担当者（loser = 消える側）を同一会社内の master 担当者へ吸収させる UI。
     6	 *   MergeLeadModal と同じ 2 段階 UI を踏襲。
     7	 *
     8	 *   loser に紐づく contact_contact_channels が全て master に付け替えられ、
     9	 *   loser の担当者レコードは削除される。
    10	 *
    11	 * 安全策:
    12	 *   1. loser が deals/orders/quotes/invoices を持つ場合は backend が 400 を返す。
    13	 *   2. 確定前に「取り消せません」の警告ダイアログ
    14	 *   3. 任意の reason 入力欄（audit_logs に記録）
    15	 */
    16	
    17	import { useEffect, useMemo, useState, FormEvent } from "react";
    18	import { useTranslation } from "react-i18next";
    19	import { api } from "../lib/api";
    20	import { Modal } from "./Modal";
    21	import { Button } from "./Button";
    22	import { RadioControl } from "./RadioControl";
    23	import { TextField } from "./TextField";
    24	import { Textarea } from "./Textarea";
    25	import { getStatusPresentation } from "../utils/statusPresentation";
    26	import { LoadingBlock } from "./loading";
    27	
    28	interface ContactOption {
    29	  id: number;
    30	  contact_code: string;
    31	  display_name: string | null;
    32	  surname: string | null;
    33	  given_name: string | null;
    34	  status: string;
    35	}
    36	
    37	interface Props {
    38	  open: boolean;
    39	  companyId: number;
    40	  /** マージ元（loser = 吸収されて削除される側）の担当者 */
    41	  source: { id: number; contact_code: string; display_name: string | null; surname: string | null; given_name: string | null };
    42	  /** 成功後コールバック。master の id を渡す */
    43	  onMerged: (masterId: number) => void;
    44	  onCancel: () => void;
    45	}
    46	
    47	const PER_PAGE_CAP = 100;
    48	const SEARCH_DEBOUNCE_MS = 250;
    49	
    50	function contactDisplayName(c: ContactOption | Props["source"]): string {
    51	  return (
    52	    c.display_name ||
    53	    [c.surname, c.given_name].filter(Boolean).join(" ") ||
    54	    `#${"id" in c ? c.id : "?"}`
    55	  );
    56	}
    57	
    58	export default function MergeContactModal({ open, companyId, source, onMerged, onCancel }: Props) {
    59	  const { t } = useTranslation();
    60	  const [candidates, setCandidates] = useState<ContactOption[]>([]);
    61	  const [search, setSearch] = useState("");
    62	  const [selectedId, setSelectedId] = useState<number | null>(null);
    63	  const [selectedSnapshot, setSelectedSnapshot] = useState<ContactOption | null>(null);
    64	  const [reason, setReason] = useState("");
    65	  const [stage, setStage] = useState<"select" | "confirm">("select");
    66	  const [loading, setLoading] = useState(false);
    67	  const [submitting, setSubmitting] = useState(false);
    68	  const [error, setError] = useState<string | null>(null);
    69	  const [resultsCapped, setResultsCapped] = useState(false);
    70	
    71	  useEffect(() => {
    72	    if (!open) return;
    73	    setSelectedId(null);
    74	    setSelectedSnapshot(null);
    75	    setReason("");
    76	    setStage("select");
    77	    setError(null);
    78	  }, [open]);
    79	
    80	  useEffect(() => {
=== CompanyContactsTab
     6	 *        担当者統合モーダル（MergeContactModal）を組み込み。
    11	import { getStatusPresentation } from "../../utils/statusPresentation";
    12	import { STATUS_ICONS } from "../../constants/icons";
    20	import MergeContactModal from "../../components/MergeContactModal";
    56	  const [mergeModalOpen, setMergeModalOpen] = useState(false);
    57	  const [mergeSourceContact, setMergeSourceContact] = useState<Contact | null>(null);
    59	  const [mergeDuplicateContactId, setMergeDuplicateContactId] = useState<number | null>(null);
    67	  const openMergeModal = (contact: Contact) => {
    68	    setMergeSourceContact(contact);
    69	    setMergeDuplicateContactId(null);
    70	    setMergeModalOpen(true);
    73	  const handleRequestMerge = (duplicateContactId: number) => {
    77	    setMergeSourceContact(channelFormContact);
    78	    setMergeDuplicateContactId(duplicateContactId);
    79	    setMergeModalOpen(true);
    82	  const handleMerged = () => {
    83	    setMergeModalOpen(false);
    84	    setMergeSourceContact(null);
   112	              <th>{t("common.status")}</th>
   121	                <td>{c.is_primary_contact ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> : ""}</td>
   124	                <td><span className={`status-badge status-${c.status}`}>{t(getStatusPresentation("contact", c.status).labelKey ?? c.status)}</span></td>
   134	                      <Button size="sm" variant="secondary" onClick={() => openMergeModal(c)}>
   136	                        {t("contacts.mergeAsDuplicate").replace("（担当者単位は未実装）", "")}
   196	              label={t("common.status")}
   197	              value={contactForm.status}
   198	              onChange={(e) => setContactForm({ ...contactForm, status: e.target.value })}
   200	                { value: "active", label: t("customers.status_active") },
   201	                { value: "inactive", label: t("customers.status_inactive") },
   202	                { value: "archived", label: t("customers.status_archived") },
   236	          onRequestMerge={handleRequestMerge}
   241	      {mergeSourceContact && (
   242	        <MergeContactModal
   243	          open={mergeModalOpen}
   246	            id: mergeSourceContact.id,
   247	            contact_code: mergeSourceContact.contact_code,
   248	            display_name: mergeSourceContact.display_name,
   249	            surname: mergeSourceContact.surname,
   250	            given_name: mergeSourceContact.given_name,
   252	          onMerged={handleMerged}
   254	            setMergeModalOpen(false);
   255	            setMergeSourceContact(null);
   125	                <td>
   126	                  <Button size="sm" variant="secondary" onClick={() => openChannelForm(c)}>
   127	                    {t("contactChannel.addTitle")}
   128	                  </Button>
   129	                  {canEdit && (
   130	                    <>
   131	                      <Button size="sm" variant="secondary" onClick={() => openContactEdit(c)}>
   132	                        {t("common.edit")}
   133	                      </Button>
   134	                      <Button size="sm" variant="secondary" onClick={() => openMergeModal(c)}>
   135	                        {/* eslint-disable-next-line local/no-japanese-literal */}
   136	                        {t("contacts.mergeAsDuplicate").replace("（担当者単位は未実装）", "")}
   137	                      </Button>
   138	                      <Button size="sm" variant="danger" onClick={() => setContactDeleteTarget(c)}>
   139	                        {t("common.delete")}
   140	                      </Button>
   141	                    </>
   142	                  )}
   143	                </td>
   144	              </tr>
   145	            ))}
   238	      )}
   239	
   240	      {/* 担当者統合モーダル */}
   241	      {mergeSourceContact && (
   242	        <MergeContactModal
   243	          open={mergeModalOpen}
   244	          companyId={company.id}
   245	          source={{
   246	            id: mergeSourceContact.id,
   247	            contact_code: mergeSourceContact.contact_code,
   248	            display_name: mergeSourceContact.display_name,
   249	            surname: mergeSourceContact.surname,
   250	            given_name: mergeSourceContact.given_name,
   251	          }}
   252	          onMerged={handleMerged}
   253	          onCancel={() => {
   254	            setMergeModalOpen(false);
   255	            setMergeSourceContact(null);
   256	          }}
=== ContactChannelForm head
     1	/**
     2	 * 担当者チャンネル追加・編集フォーム（ADR-098 SA-04 J2/G1）。
     3	 *
     4	 * 役割:
     5	 *   contact_contact_channels にチャンネルを追加または編集する。
     6	 *   - ID 単位で保存（URL 入力欄なし・G1 SSOT 維持）
     7	 *   - 保存前に重複チェック（同一 channel + purpose が別担当者に存在 → 警告 + 2択）
     8	 *     ① 統合する    → MergeContactModal へ遷移
     9	 *     ② 別人として保存（監査ログ記録） → 保存 + audit log エントリ追記
    10	 *   - Discord のみ guild_id 入力欄を追加で表示
    11	 */
    12	
    13	import { useEffect, useState, FormEvent } from "react";
    14	import { useTranslation } from "react-i18next";
    15	import { api } from "../lib/api";
    16	import { Modal } from "./Modal";
    17	import { Button } from "./Button";
    18	import { TextField } from "./TextField";
    19	import { Select } from "./Select";
    20	import { Checkbox } from "./Checkbox";
   700	    master_id: int,
   701	    body: ContactMergeRequest,
   702	    db: AsyncSession = Depends(get_db),
   703	    tenant_id: int = Depends(get_current_tenant),
   704	    current_user: User = Depends(get_current_user),
   705	):
   706	    """担当者の重複統合（ADR-098 SA-04 J3）。
   707	
   708	    loser の deals / orders / quotes / invoices の contact_id を master へ付け替え、
   709	    contact_contact_channels も master へ再ポイントし、loser を削除する。
   710	
   711	    guard（v1）:
   712	        loser に deals / orders / quotes / invoices が紐づいている場合は 400 ブロック。
   713	
   714	    処理順序（同一トランザクション・FOR UPDATE ロック）:
   715	      1. master / loser を FOR UPDATE ロック（昇順 ID・デッドロック防止）
   716	      2. guard: loser が deals / orders / quotes / invoices を持つ → 400
   717	      3. FK 付け替え: deals / orders / quotes / invoices の contact_id → master
   718	      4. contact_contact_channels を master へ再ポイント（重複行は先削除して吸収）
   719	      5. loser 削除
   720	      6. 監査ログ 2 件
   721	    """
   722	    loser_id = body.loser_id
   723	
   724	    if master_id == loser_id:
   725	        raise HTTPException(
   726	            status_code=status.HTTP_400_BAD_REQUEST,
   727	            detail="master_id と loser_id が同じです。自己マージはできません。",
   728	        )
   729	
   730	    ct_t = tenant_table_ref(db, tenant_id, "contacts")
   731	    ccc_t = tenant_table_ref(db, tenant_id, "contact_contact_channels")
   732	    dl_t = tenant_table_ref(db, tenant_id, "deals")
   733	    ord_t = tenant_table_ref(db, tenant_id, "orders")
   734	    qt_t = tenant_table_ref(db, tenant_id, "quotes")
   735	    inv_t = tenant_table_ref(db, tenant_id, "invoices")
   736	
   737	    # 1) master / loser を昇順 FOR UPDATE ロック（デッドロック防止）
   738	    low_id, high_id = min(master_id, loser_id), max(master_id, loser_id)
   739	    locked_res = await db.execute(
   740	        text(f"""
   741	            SELECT {_CONTACT_COLUMNS}
   742	            FROM {ct_t}
   743	            WHERE id IN (:id1, :id2)
   744	            ORDER BY id
   745	            FOR UPDATE
   746	        """),
   747	        {"id1": low_id, "id2": high_id},
   748	    )
   749	    locked_rows = locked_res.mappings().all()
   750	    rows_by_id = {r["id"]: r for r in locked_rows}
   751	    master_row = rows_by_id.get(master_id)
   752	    loser_row = rows_by_id.get(loser_id)
   753	
   754	    if not master_row:
   755	        raise HTTPException(
   756	            status_code=status.HTTP_404_NOT_FOUND,
   757	            detail=f"master 担当者 (id={master_id}) が見つかりません",
   758	        )
   759	    if not loser_row:
   760	        raise HTTPException(
   761	            status_code=status.HTTP_404_NOT_FOUND,
   762	            detail=f"loser 担当者 (id={loser_id}) が見つかりません",
   763	        )
   764	
   765	    # 2) guard: loser が関連レコードを持つ場合は 400
   766	    related_counts: dict[str, int] = {}
   767	    for tbl, label in (
   768	        (dl_t, "deals"),
   769	        (ord_t, "orders"),
   770	        (qt_t, "quotes"),
   771	        (inv_t, "invoices"),
   772	    ):
   773	        cnt_res = await db.execute(
   774	            text(f"SELECT COUNT(*) FROM {tbl} WHERE contact_id = :loser"),
   775	            {"loser": loser_id},
   776	        )
   777	        cnt = cnt_res.scalar() or 0
   778	        if cnt:
   779	            related_counts[label] = cnt
   780	
   781	    if related_counts:
   782	        detail_parts = ", ".join(f"{label}: {cnt}件" for label, cnt in related_counts.items())
   783	        raise HTTPException(
   784	            status_code=status.HTTP_400_BAD_REQUEST,
   785	            detail=(
   786	                f"loser 担当者 (id={loser_id}) には関連レコードがあるため loser にできません。"
   787	                f"（{detail_parts}）先に担当者を変更してください。"
   788	            ),
   789	        )
   790	
   791	    # 3) FK 付け替え: deals / orders / quotes / invoices
   792	    reassigned_deals = (await db.execute(
   793	        text(f"UPDATE {dl_t} SET contact_id = :master WHERE contact_id = :loser"),
   794	        {"master": master_id, "loser": loser_id},
   795	    )).rowcount or 0
   796	
   797	    reassigned_orders = (await db.execute(
   798	        text(f"UPDATE {ord_t} SET contact_id = :master WHERE contact_id = :loser"),
   799	        {"master": master_id, "loser": loser_id},
   800	    )).rowcount or 0
    80	  useEffect(() => {
    81	    if (!open) return;
    82	    const q = search.trim();
    83	    let cancelled = false;
    84	    const handle = window.setTimeout(() => {
    85	      setLoading(true);
    86	      const path = q
    87	        ? `/companies/${companyId}/contacts?per_page=${PER_PAGE_CAP}&search=${encodeURIComponent(q)}`
    88	        : `/companies/${companyId}/contacts?per_page=${PER_PAGE_CAP}`;
    89	      api
    90	        .get<ContactOption[]>(path)
    91	        .then((rows) => {
    92	          if (cancelled) return;
    93	          const filtered = rows.filter((r) => r.id !== source.id);
    94	          setCandidates(filtered);
    95	          setResultsCapped(rows.length >= PER_PAGE_CAP);
    96	        })
    97	        .catch((e: unknown) => {
    98	          if (cancelled) return;
    99	          setError(e instanceof Error ? e.message : t("common.fetchError"));
   100	        })
   101	        .finally(() => {
   102	          if (!cancelled) setLoading(false);
   103	        });
   104	    }, q ? SEARCH_DEBOUNCE_MS : 0);
   105	    return () => {
   106	      cancelled = true;
   107	      window.clearTimeout(handle);
   108	    };
   109	    // eslint-disable-next-line react-hooks/exhaustive-deps
   110	  }, [open, companyId, source.id, search]);
   111	
   112	  const selected = useMemo(() => {
   113	    const fromList = candidates.find((c) => c.id === selectedId) || null;
   114	    if (fromList) return fromList;
   115	    if (selectedSnapshot && selectedSnapshot.id === selectedId) return selectedSnapshot;
   116	    return null;
   117	  }, [candidates, selectedId, selectedSnapshot]);
   118	
   119	  const sourceCode = source.contact_code ?? `#${source.id}`;
   120	  const sourceName = contactDisplayName(source);
   121	
   122	  const handleConfirmSubmit = async (e: FormEvent) => {
   123	    e.preventDefault();
   124	    if (!selected) return;
   125	    setSubmitting(true);
   126	    setError(null);
   127	    try {
   128	      await api.post(`/contacts/${selected.id}/merge`, {
   129	        loser_id: source.id,
   130	        reason: reason.trim() || null,
   131	      });
   132	      onMerged(selected.id);
   133	    } catch (e: unknown) {
   134	      const msg = e instanceof Error ? e.message : "";
   135	      // eslint-disable-next-line local/no-japanese-literal
   136	      if (msg.includes("関連レコード") || msg.includes("related")) {
   137	        setError(t("mergeContact.relatedError"));
   138	      } else {
   139	        setError(msg || t("common.operationError"));
   140	      }
   141	    } finally {
   142	      setSubmitting(false);
   143	    }
   144	  };
   145	
   146	  return (
   147	    <Modal open={open} onClose={onCancel} title={t("mergeContact.title")} size="md">
   148	      <div className="modal-content-wide">
   149	        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-base)", marginTop: "var(--space-1)" }}>
   150	          {t("mergeContact.sourceDesc", { name: sourceName, code: sourceCode })}
   151	        </p>
   152	
   153	        {error && <div className="error-banner">{error}</div>}
   154	
   155	        {stage === "select" && (
   156	          <>
   157	            <TextField
   158	              label={t("mergeContact.selectMaster")}
   159	              type="text"
   160	              placeholder={t("mergeContact.searchPlaceholder")}
   161	              value={search}
   162	              onChange={(e) => setSearch(e.target.value)}
   163	            />
   164	
   165	            {resultsCapped && (
   166	              <div
   167	                style={{
   168	                  background: "var(--warning-bg)",
   169	                  border: "1px solid var(--warning-text)",
   170	                  padding: "var(--space-2)",
   171	                  borderRadius: "var(--radius-sm)",
   172	                  marginTop: "var(--space-2)",
   173	                  fontSize: "var(--font-sm)",
   174	                  color: "var(--warning-text)",
   175	                }}
   176	              >
   177	                {t("mergeContact.resultsCapped", { count: PER_PAGE_CAP })}
   178	              </div>
   179	            )}
   180	
   181	            <div
   182	              style={{
   183	                maxHeight: "var(--dropdown-list-h)",
   184	                overflowY: "auto",
   185	                border: "1px solid var(--border-light)",
   186	                borderRadius: "var(--radius-sm)",
   187	                marginTop: "var(--space-2)",
   188	              }}
   189	            >
   190	              {loading ? (
   191	                <LoadingBlock />
   192	              ) : candidates.length === 0 ? (
   193	                <p style={{ padding: "var(--space-4)", textAlign: "center", color: "var(--text-muted)" }}>
   194	                  {t("mergeContact.noResults")}
   195	                </p>
   196	              ) : (
   197	                <table className="data-table" style={{ marginBottom: 0 }}>
   198	                  <thead>
   199	                    <tr>
   200	                      <th style={{ width: "var(--col-width-checkbox)" }}></th>
```
