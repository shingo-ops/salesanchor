/**
 * TCG 配信先管理 API 型定義・呼び出し
 *
 * API パスは /tcg/distribution/... から書く（api クライアントが /api/v1 を付与する）。
 * 全エンドポイントは require_super_admin 認証。
 */
import { api } from "../../lib/api";

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------

export interface DistributionTarget {
  id: string;
  name: string;
  spreadsheet_id: string;
  sheet_name: string;
  is_active: boolean;
  sa_key_secret_name: string;
  last_distributed_at: string | null;
  last_distributed_count: number | null;
  last_result: string | null;
  created_at: string;
  updated_at: string;
}

export interface DistributionTargetCreate {
  name: string;
  spreadsheet_id: string;
  sheet_name: string;
  is_active: boolean;
  sa_key_secret_name: string;
}

export interface DistributionTargetUpdate {
  name?: string;
  spreadsheet_id?: string;
  sheet_name?: string;
  is_active?: boolean;
  sa_key_secret_name?: string;
}

export interface PreviewExclusion {
  flag_series: number;
  pid_unresolved_only: number;
  unit_unresolved_only: number;
  both_unresolved: number;
  price_unresolved: number;
}

export interface PreviewData {
  output_count: number;
  note: string;
  exclusion: PreviewExclusion;
  flag_gate: {
    include_flag_single: boolean;
    gate_status: string;
    gate_message: string;
    flag_single_count: number | null;
  };
  settings: Record<string, string>;
}

export interface RunResultItem {
  target_id: string;
  target_name: string;
  status: string;
  rows_written: number;
}

export interface RunResultError {
  target_id: string | null;
  target_name?: string;
  error: string;
}

export interface RunResult {
  started_at: string;
  output_count: number;
  results: RunResultItem[];
  errors: RunResultError[];
}

export interface VerifyAccessResult {
  accessible: boolean;
  title?: string;
  error?: string;
}

// ---------------------------------------------------------------------------
// API 呼び出し関数
// ---------------------------------------------------------------------------

export async function listTargets(): Promise<DistributionTarget[]> {
  return api.get<DistributionTarget[]>("/tcg/distribution/targets");
}

export async function createTarget(data: DistributionTargetCreate): Promise<DistributionTarget> {
  return api.post<DistributionTarget>("/tcg/distribution/targets", data);
}

export async function updateTarget(id: string, data: DistributionTargetUpdate): Promise<DistributionTarget> {
  return api.put<DistributionTarget>(`/tcg/distribution/targets/${id}`, data);
}

export async function deleteTarget(id: string): Promise<void> {
  await api.delete(`/tcg/distribution/targets/${id}`);
}

export async function fetchPreview(): Promise<PreviewData> {
  return api.get<PreviewData>("/tcg/distribution/preview");
}

export async function runDistributionAll(): Promise<RunResult> {
  return api.post<RunResult>("/tcg/distribution/run", {});
}

export async function runDistributionTarget(targetId: string): Promise<RunResult> {
  return api.post<RunResult>(`/tcg/distribution/run/${targetId}`, {});
}

export async function verifySpreadsheetAccess(spreadsheetId: string): Promise<VerifyAccessResult> {
  return api.get<VerifyAccessResult>(
    `/tcg/distribution/verify-access?spreadsheet_id=${encodeURIComponent(spreadsheetId)}`
  );
}
