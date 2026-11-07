/**
 * ロール・権限管理ページ（Discord式カスタムロール / GAS UI互換 split-view版）。
 *
 * レイアウト:
 *   - 左サイドバー: 役割一覧（クリックで選択）+ 「新規ロール」ボタン
 *   - 右メインペイン: 選択中ロールの権限編集
 *     - カテゴリ単位でグループ化（アイコン + カテゴリ名 + メニュー表示トグル）
 *     - 各カテゴリ内に個別権限のチェックボックス
 *     - 未保存時は下部に警告バナー + 上部のキャンセル/保存ボタン有効化
 *
 * 変更履歴:
 *   2026-04-16: 初版（GAS UI互換に刷新、モーダル式→split-view式）
 */

import { LoadingBlock } from "../../components/loading";
import { useMemo, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiCache, useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
import { Modal } from "../../components/Modal";
import ConfirmModal from "../../components/ConfirmModal";
import { Select } from "../../components/Select";
import { RadioControl } from "../../components/RadioControl";
import { Button } from "../../components/Button";
import { usePermissions } from "../../hooks/usePermissions";
import { SlashOutline, STATUS_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { TextareaControl } from "../../components/Textarea";
import { TextFieldControl } from "../../components/TextField";
import { Badge } from "../../components/Badge";
import { SegmentedToggle, type SegmentedOption } from "../../components/SegmentedToggle";
import { ROLE_ROWS, rowMenuLabelKey } from "../../constants/menuPermissions";
import {
  applyState, buildRows, canSetEdit, canSetView, rowState,
  type PermRow, type RowState,
} from "./rolePermissionRows";
import "./RolesPage.css";

interface Role {
  id: number;
  name: string;
  color: string | null;
  priority: number;
  is_system: boolean;
  description: string | null;
  created_at: string;
  updated_at: string;
}

interface Permission {
  id: number;
  key: string;
  resource: string;
  action: string;
  description: string;
  category: string;
}

// 「メニュー以外の許可」の区分の並び（小さい順・無い区分は後ろ）
/* eslint-disable local/no-japanese-literal -- DB 定義のカテゴリキー（backend permission prefix と一致・変更不可） */
const CATEGORY_ORDER: Record<string, number> = {
  "レポート": 1,
  "顧客": 2,
  "リード": 3,
  "案件": 4,
  "注文": 5,
  "チーム": 6,
  "ロール": 7,
  "システム": 99,
};
/* eslint-enable local/no-japanese-literal */

type SectionId = PermRow["section"];
const SECTION_ORDER: SectionId[] = ["sidebar", "team", "data", "business", "other"];
const SECTION_TITLE_KEY: Record<SectionId, string> = {
  sidebar: "roles.sectionSidebar",
  team: "managementCenter.sectionTeam",
  data: "managementCenter.sectionData",
  business: "managementCenter.sectionBusiness",
  other: "roles.sectionOther",
};

// ロール表示色の選択肢（12色、視覚的に明確に区別できるよう Tailwind 500系で統一）
// 正方形スウォッチで表示、ラジオボタン選択
const COLOR_PALETTE = [
  "#ef4444", // 赤
  "#f97316", // オレンジ
  "#eab308", // 黄
  "#84cc16", // ライム
  "#22c55e", // 緑
  "#14b8a6", // ティール
  "#06b6d4", // シアン
  "#3b82f6", // 青
  "#6366f1", // インディゴ
  "#a855f7", // 紫
  "#ec4899", // ピンク
  "#64748b", // スレート
];

// 優先順位は旧GAS版に合わせて第1-第4順位の4段階。priority数値とのマッピング。
const PRIORITY_VALUES = [1000, 900, 500, 300];

const emptyRoleForm = { name: "", color: COLOR_PALETTE[0], priority: 500, description: "" };

const NO_ROLES: Role[] = [];
const NO_PERMISSIONS: Permission[] = [];
const EMPTY_IDS: Set<number> = new Set();
const toIds = (perms: Permission[]): Set<number> => new Set(perms.map((p) => p.id));

export default function RolesPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();

  // データ
  const rolesQ = useApiQuery<Role[]>("/roles");
  const permsQ = useApiQuery<Permission[]>("/permissions");
  const roles = rolesQ.data ?? NO_ROLES;
  const permissions = permsQ.data ?? NO_PERMISSIONS;
  const [error, setError] = useState("");

  // 選択中ロール
  const [pickedRoleId, setPickedRoleId] = useState<number | null>(null);
  // 選んだロールが一覧に無い（まだ選んでいない・消した）時は先頭のロール
  const selectedRoleId = roles.some((r) => r.id === pickedRoleId) ? pickedRoleId : (roles[0]?.id ?? null);
  // そのロールの権限（元の状態は写し・編集中はフォーム。写しが無い間は全部外して押せない）
  const rolePermsQ = useApiQuery<Permission[]>(`/roles/${selectedRoleId}/permissions`, { enabled: selectedRoleId !== null });
  const originalPermIds = useMemo(() => (rolePermsQ.data ? toIds(rolePermsQ.data) : EMPTY_IDS), [rolePermsQ.data]);
  const { form: editedPermIds, setForm: setEditedPermIds, ready: permsReady } = useSeededForm(
    `roles/${selectedRoleId}/permissions`, rolePermsQ.data, toIds, EMPTY_IDS,
  );
  const readError = rolesQ.error ?? permsQ.error ?? rolePermsQ.error;
  const shownError = error || (readError ? (readError instanceof Error ? readError.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
  const cache = useApiCache();
  const [savingPerms, setSavingPerms] = useState(false);

  // ロールCRUD用モーダル
  const [showRoleForm, setShowRoleForm] = useState(false);
  const [editingRoleId, setEditingRoleId] = useState<number | null>(null);
  const [roleForm, setRoleForm] = useState(emptyRoleForm);
  const [deleteTarget, setDeleteTarget] = useState<Role | null>(null);

  // メニューごとの行（正本 constants/menuPermissions.ts）+ 残りの許可は区分ごとの行
  const rows = useMemo(() => buildRows(permissions, ROLE_ROWS, CATEGORY_ORDER), [permissions]);
  const permByKey = useMemo(() => new Map(permissions.map((p) => [p.key, p])), [permissions]);
  const [openRowIds, setOpenRowIds] = useState<Set<string>>(() => new Set());

  const selectedRole = roles.find((r) => r.id === selectedRoleId) ?? null;
  const isSystemRole = selectedRole?.is_system ?? false;
  const dirty = useMemo(() => {
    if (originalPermIds.size !== editedPermIds.size) return true;
    for (const id of editedPermIds) if (!originalPermIds.has(id)) return true;
    return false;
  }, [originalPermIds, editedPermIds]);

  const priorityOptions = PRIORITY_VALUES.map((v) => ({
    value: String(v),
    label: t(`roles.priority_${v}`),
  }));
  if (!PRIORITY_VALUES.includes(roleForm.priority)) {
    priorityOptions.push({
      value: String(roleForm.priority),
      label: t("roles.customPriority", { priority: roleForm.priority }),
    });
  }

  const canEditPerms = hasPermission("roles.update") && !isSystemRole;
  const canTogglePerms = canEditPerms && permsReady;

  // 持っている許可の鍵（編集中）。行の計算は鍵で行い、保存する一覧は id のまま（menu.* もそのまま残る）
  const heldKeys = useMemo(() => {
    const s = new Set<string>();
    for (const p of permissions) if (editedPermIds.has(p.id)) s.add(p.key);
    return s;
  }, [permissions, editedPermIds]);

  // 行の3択を押したとき: その行の許可だけを変える
  const setRowState = (row: PermRow, state: RowState) => {
    if (!canTogglePerms) return;
    const nextKeys = applyState(heldKeys, row.keys, state);
    const next = new Set(editedPermIds);
    for (const k of row.keys) {
      const p = permByKey.get(k);
      if (!p) continue;
      if (nextKeys.has(k)) next.add(p.id);
      else next.delete(p.id);
    }
    setEditedPermIds(next);
  };

  // 許可1つずつの切替
  const setKeyAllowed = (key: string, allowed: boolean) => {
    if (!canTogglePerms) return;
    const p = permByKey.get(key);
    if (!p) return;
    const next = new Set(editedPermIds);
    if (allowed) next.add(p.id);
    else next.delete(p.id);
    setEditedPermIds(next);
  };

  const toggleRowOpen = (rowId: string) => {
    setOpenRowIds((prev) => {
      const next = new Set(prev);
      if (next.has(rowId)) next.delete(rowId);
      else next.add(rowId);
      return next;
    });
  };

  const rowName = (row: PermRow): string =>
    row.menus ? row.menus.map((m) => t(rowMenuLabelKey(m))).join("・") : (row.category ?? "");

  const stateOptions = (row: PermRow): SegmentedOption<"off" | "view" | "edit">[] => [
    { value: "off", icon: STATUS_ICONS.error, label: t("roles.stateOff"), tone: "danger" },
    { value: "view", icon: SlashOutline, label: t("roles.stateView"), tone: "neutral", disabled: !canSetView(row.keys) },
    { value: "edit", icon: STATUS_ICONS.check, label: t("roles.stateEdit"), tone: "success", disabled: !canSetEdit(row.keys) },
  ];

  const keyOptions: SegmentedOption<"deny" | "allow">[] = [
    { value: "deny", icon: STATUS_ICONS.error, label: t("roles.permDeny"), tone: "danger" },
    { value: "allow", icon: STATUS_ICONS.check, label: t("roles.permAllow"), tone: "success" },
  ];

  // 保存
  const savePermissions = async () => {
    if (selectedRoleId == null) return;
    setSavingPerms(true);
    try {
      await api.put(`/roles/${selectedRoleId}/permissions`, {
        permission_ids: Array.from(editedPermIds),
      });
      await invalidate(["roles", String(selectedRoleId), "permissions"]);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setSavingPerms(false);
    }
  };

  // 編集キャンセル（元に戻す）
  const cancelEdits = () => setEditedPermIds(new Set(originalPermIds));

  // ロール選択切替（未保存なら確認）
  const selectRole = (id: number) => {
    if (dirty && !window.confirm(t("roles.unsavedChanges") + t("roles.discardAndSwitch"))) return;
    setPickedRoleId(id);
  };

  // ロール作成/編集
  const openCreateRole = () => {
    setEditingRoleId(null);
    setRoleForm(emptyRoleForm);
    setShowRoleForm(true);
  };
  const openEditRole = (r: Role) => {
    setEditingRoleId(r.id);
    setRoleForm({
      name: r.name,
      color: r.color || "#6c757d",
      priority: r.priority,
      description: r.description || "",
    });
    setShowRoleForm(true);
  };
  const submitRoleForm = async (e: FormEvent) => {
    e.preventDefault();
    const payload = {
      name: roleForm.name,
      color: roleForm.color,
      priority: Number(roleForm.priority),
      description: roleForm.description || null,
    };
    try {
      if (editingRoleId) {
        await api.patch(`/roles/${editingRoleId}`, payload);
      } else {
        await api.post("/roles", payload);
      }
      await cache.fetch("/roles", () => api.get<Role[]>("/roles"));
      setShowRoleForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };
  const performDelete = async () => {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    setDeleteTarget(null);
    try {
      await api.delete(`/roles/${id}`);
      await cache.fetch("/roles", () => api.get<Role[]>("/roles"));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  if (rolesQ.isPending || permsQ.isPending) return <div className="page"><LoadingBlock /></div>;

  return (
    <div className="page roles-page">
      {shownError && <div className="error-message">{shownError}</div>}

      <div className="roles-layout">
        {/* === 左サイドバー: 役割一覧 === */}
        <aside className="roles-sidebar">
          <div className="roles-sidebar-header">
            <h3>{t("roles.title")}</h3>
            {hasPermission("roles.create") && (
              <Button variant="primary" size="sm" onClick={openCreateRole}>+ {t("common.new")}</Button>
            )}
          </div>
          <ul className="roles-list">
            {roles.map((r) => {
              // priorityに応じた階層インデント。カード全体（カラーバー含む）を右にずらす
              // 1000→0, 700→1, 400→2, 100→3, 0→4
              const level =
                r.priority >= 1000 ? 0 :
                r.priority >= 700 ? 1 :
                r.priority >= 400 ? 2 :
                r.priority >= 100 ? 3 : 4;
              return (
                <li key={r.id} style={{ marginLeft: `${level * 16}px` }}>
                  <button
                    className={`role-item ${r.id === selectedRoleId ? "active" : ""}`}
                    style={{ borderLeft: `4px solid ${r.color || "var(--border-color)"}` }}
                    onClick={() => selectRole(r.id)}
                  >
                    <span className="role-item-name">{r.name}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        {/* === 右メインペイン: 権限編集 === */}
        <main className="roles-main">
          {selectedRole ? (
            <>
              <div className="roles-main-header">
                <div>
                  {/* eslint-disable-next-line no-restricted-syntax */}
                  <h2>
                    <span
                      className="badge"
                      style={{ background: selectedRole.color || "var(--bg-hover)", color: "var(--on-accent)", marginRight: "var(--space-2)" }}
                    >
                      {selectedRole.name}
                    </span>
                    <span style={{ fontWeight: "var(--font-weight-normal)", color: "var(--text-secondary)" }}>{t("roles.permissionSuffix")}</span>
                  </h2>
                  {selectedRole.description && (
                    <p className="role-description">{selectedRole.description}</p>
                  )}
                  {isSystemRole && (
                    <p className="role-note">※ {t("roles.systemRole")}{t("roles.systemRoleNote", { reason: hasPermission("roles.update") ? t("roles.cannotEdit") : t("roles.noPermission") })}</p>
                  )}
                </div>
                <div className="roles-main-actions">
                  {canEditPerms && !selectedRole.is_system && (
                    <>
                      <Button variant="secondary" size="sm" onClick={() => openEditRole(selectedRole)}>{t("common.edit")}</Button>
                      {hasPermission("roles.delete") && (
                        <Button variant="danger" size="sm" onClick={() => setDeleteTarget(selectedRole)}>{t("common.delete")}</Button>
                      )}
                    </>
                  )}
                  <Button variant="secondary" size="md" disabled={!dirty || savingPerms} onClick={cancelEdits}>
                    {t("roles.cancelChanges")}
                  </Button>
                  <Button loading={savingPerms} variant="primary" size="md" disabled={!dirty || savingPerms || !canEditPerms} onClick={savePermissions}>
                    {t("roles.saveChanges")}
                  </Button>
                </div>
              </div>

              <p className="role-perm-legend">{t("roles.legend")}</p>
              <div className="role-perm-sections">
                {SECTION_ORDER.map((section) => {
                  const sectionRows = rows.filter((r) => r.section === section);
                  if (sectionRows.length === 0) return null;
                  return (
                    <section key={section} className="role-perm-section">
                      <header className="role-perm-section-header">{t(SECTION_TITLE_KEY[section])}</header>
                      {sectionRows.map((row) => {
                        const name = rowName(row);
                        const state = rowState(row.keys, heldKeys);
                        const isOpen = openRowIds.has(row.id);
                        const hasDetail = !row.fixed && row.keys.length >= 2;
                        const menuCount = row.menus?.length ?? 0;
                        return (
                          <div key={row.id} className="role-perm-row">
                            <div className="role-perm-row-main">
                              <div className="role-perm-row-text">
                                <span className="role-perm-row-name">{name}</span>
                                {menuCount >= 2 && (
                                  <span className="role-perm-row-note">{t("roles.menusTogether", { count: menuCount })}</span>
                                )}
                                {row.noteKey && <span className="role-perm-row-note">{t(row.noteKey)}</span>}
                              </div>
                              <div className="role-perm-row-controls">
                                {hasDetail && (
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    aria-expanded={isOpen}
                                    onClick={() => toggleRowOpen(row.id)}
                                  >
                                    {state === "mixed"
                                      ? <Badge variant="warning" size="sm">{t("roles.individual")}</Badge>
                                      : t("roles.individual")}
                                  </Button>
                                )}
                                {row.fixed ? (
                                  <span className="role-perm-row-fixed">
                                    {t(row.fixed === "always" ? "roles.fixedAlways" : "roles.fixedOwner")}
                                  </span>
                                ) : (
                                  <SegmentedToggle
                                    options={stateOptions(row)}
                                    value={state === "mixed" ? null : state}
                                    onChange={(v) => setRowState(row, v)}
                                    aria-label={name}
                                    disabled={!canTogglePerms}
                                  />
                                )}
                              </div>
                            </div>
                            {hasDetail && isOpen && (
                              <div className="role-perm-detail">
                                {row.keys.map((k) => {
                                  const p = permByKey.get(k);
                                  if (!p) return null;
                                  return (
                                    <div key={k} className="role-perm-detail-row">
                                      <span className="role-perm-detail-name">{p.description}</span>
                                      <SegmentedToggle
                                        options={keyOptions}
                                        value={heldKeys.has(k) ? "allow" : "deny"}
                                        onChange={(v) => setKeyAllowed(k, v === "allow")}
                                        aria-label={p.description}
                                        disabled={!canTogglePerms}
                                      />
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </section>
                  );
                })}
              </div>

              {dirty && (
                <div className="unsaved-banner">
                  <STATUS_ICONS.warning size={ICON.sm} aria-hidden="true" />
                  {" "}{t("roles.unsavedChanges")}{t("roles.unsavedClickHint", { btn: t("roles.saveChanges") })}
                </div>
              )}
            </>
          ) : (
            <div className="empty">{t("roles.selectRoleHint")}</div>
          )}
        </main>
      </div>

      {/* === ロール作成/編集モーダル === */}
      <Modal
        open={showRoleForm}
        onClose={() => setShowRoleForm(false)}
        title={editingRoleId ? t("roles.editRole") : t("roles.newRole")}
        size="md"
      >
        <form onSubmit={submitRoleForm}>
              <div className="form-group"><label>{t("roles.roleName")} *</label>
                <TextFieldControl required value={roleForm.name} onChange={(e) => setRoleForm({ ...roleForm, name: e.target.value })} />
              </div>
              <div className="form-group"><label>{t("roles.color")}</label>
                <div className="color-picker" role="radiogroup" aria-label={t("roles.color")}>
                  {/* 既存ロールの色がパレットに無い場合は「現在の色」として表示 */}
                  {roleForm.color && !COLOR_PALETTE.includes(roleForm.color.toLowerCase()) && !COLOR_PALETTE.includes(roleForm.color) && (
                    <label
                      className="color-swatch selected color-swatch-legacy"
                      style={{ background: roleForm.color }}
                      title={t("roles.currentColorTitle", { color: roleForm.color })}
                      data-current-label={t("roles.currentColorBadge")}
                    >
                      <RadioControl
                        name="role-color"
                        value={roleForm.color}
                        checked
                        readOnly
                      />
                    </label>
                  )}
                  {COLOR_PALETTE.map((c) => (
                    <label
                      key={c}
                      className={`color-swatch ${roleForm.color === c ? "selected" : ""}`}
                      style={{ background: c }}
                      title={c}
                    >
                      <RadioControl
                        name="role-color"
                        value={c}
                        checked={roleForm.color === c}
                        onChange={(e) => setRoleForm({ ...roleForm, color: e.target.value })}
                      />
                    </label>
                  ))}
                </div>
              </div>
              <Select
                label={t("roles.priority")}
                value={roleForm.priority}
                onChange={(e) => setRoleForm({ ...roleForm, priority: Number(e.target.value) })}
                options={priorityOptions}
              />
              <div className="form-group"><label>{t("common.description")}</label>
                <TextareaControl value={roleForm.description} onChange={(e) => setRoleForm({ ...roleForm, description: e.target.value })} />
              </div>
              <div className="form-actions">
                <Button type="button" variant="secondary" size="md" onClick={() => setShowRoleForm(false)}>{t("common.cancel")}</Button>
                <Button type="submit" variant="primary" size="md">{editingRoleId ? t("common.update") : t("common.create")}</Button>
              </div>
        </form>
      </Modal>

      {/* === 削除確認 === */}
      <ConfirmModal
        open={!!deleteTarget}
        title={t("roles.deleteRole")}
        message={<><strong>{deleteTarget?.name}</strong>{t("common.deleteConfirmSuffix")}<br />{t("roles.deleteConfirmNote")}</>}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={performDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
