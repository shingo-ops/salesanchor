/**
 * useRecordDrawer — 「行クリック → 右スライド → フルページ」共通フック
 *
 * 開閉状態・編集対象 ID・フォーム状態・handleRowClick・closeDrawer を管理する。
 * 各ページは toForm / emptyForm を渡すだけで Drawer 統合が完了する。
 *
 * 使い方:
 *   const { drawerOpen, editId, editForm, handleRowClick, closeDrawer, setEditForm } =
 *     useRecordDrawer<MyRecord, MyFormState>({ toForm, emptyForm });
 *
 * ページが自分で管理するもの（フックの外）:
 *   - フォーム UI（*FormFields コンポーネント）
 *   - API 呼び出し（GET/PATCH）
 *   - 保存後コールバック（load() など）
 *   - Drawer タイトル・権限キー・フルページ route
 */

import { useState } from "react";

interface UseRecordDrawerOptions<T, F> {
  /** レコード → フォーム状態への変換 */
  toForm: (record: T) => F;
  /** 空フォーム（Drawer クローズ時のリセット用） */
  emptyForm: F;
}

interface UseRecordDrawerReturn<F> {
  drawerOpen: boolean;
  editId: number | null;
  editForm: F;
  setEditForm: React.Dispatch<React.SetStateAction<F>>;
  /** DataTable の onRowClick / 編集ボタンの onClick に渡す */
  handleRowClick: (record: { id: number }) => void;
  /** Drawer の onClose / 保存後のクリアに使う */
  closeDrawer: () => void;
}

export function useRecordDrawer<T extends { id: number }, F>(
  options: UseRecordDrawerOptions<T, F>,
): UseRecordDrawerReturn<F> {
  const { toForm, emptyForm } = options;

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<F>(emptyForm);

  const handleRowClick = (record: { id: number }) => {
    setEditId(record.id);
    setEditForm(toForm(record as T));
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setEditId(null);
    setEditForm(emptyForm);
  };

  return { drawerOpen, editId, editForm, setEditForm, handleRowClick, closeDrawer };
}
