import { api, ApiError } from "./api";

export interface StaffProfilePayload {
  surname_jp?: string;
  given_name_jp?: string;
  surname_kana?: string;
  given_name_kana?: string;
  surname_en?: string;
  given_name_en?: string;
  phone?: string | null;
}

export async function patchMyProfile(payload: StaffProfilePayload): Promise<void> {
  await api.patch("/staff/me/profile", payload);
}

export interface StaffAvatarResponse {
  avatar_url: string | null;
}

/** 本人の担当者アイコンを登録・変更する（ADR-159）。サーバー側で形式・サイズを検証する */
export async function uploadMyAvatar(file: File): Promise<StaffAvatarResponse> {
  const body = new FormData();
  body.append("image", file);
  return api.postForm<StaffAvatarResponse>("/staff/me/avatar", body);
}

/** 本人の担当者アイコンを削除する */
export async function deleteMyAvatar(): Promise<void> {
  await api.delete("/staff/me/avatar");
}

/** 英語名（名・姓）がどちらも入力済みか。空白のみは未入力扱い（ADR-159） */
export function hasEnglishNames(form: { surname_en?: string | null; given_name_en?: string | null }): boolean {
  return Boolean(form.surname_en?.trim()) && Boolean(form.given_name_en?.trim());
}

export type AvatarErrorKind = "invalidImage" | "saveFailed";

/** API エラーのコードを、画面に出す文言の種類へ変換する */
export function avatarErrorKind(err: unknown): AvatarErrorKind {
  const detail = err instanceof ApiError ? err.responseDetail : null;
  const code = detail && typeof detail === "object" ? (detail as { code?: unknown }).code : null;
  return code === "AVATAR_INVALID_TYPE" || code === "AVATAR_TOO_LARGE" ? "invalidImage" : "saveFailed";
}
