import type { ILoginResponse } from "../types/auth";
import type {
  ICreateDownloadRequest,
  IDownload,
  IDownloadListResponse,
  IDownloadUrlResponse,
  IUploadUrlResponse,
  DownloadStatus,
} from "../types/download";
import type { IStatusResponse } from "../types/status";

const API_URL = import.meta.env.VITE_API_URL || "";
const TOKEN_KEY = "seedbox_token";

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (res.status === 204) return undefined as T;

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${res.status}`);
  }

  return res.json();
}

// Auth
export async function login(password: string): Promise<ILoginResponse> {
  const data = await request<ILoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
  setToken(data.token);
  return data;
}

// Downloads
export async function listDownloads(
  status?: DownloadStatus,
  page = 1,
  limit = 50
): Promise<IDownloadListResponse> {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (status) params.set("status", status);
  return request(`/downloads?${params}`);
}

export async function getDownload(id: string): Promise<{ download: IDownload }> {
  return request(`/downloads/${id}`);
}

export async function createDownload(
  req: ICreateDownloadRequest
): Promise<{ download: IDownload }> {
  return request("/downloads", { method: "POST", body: JSON.stringify(req) });
}

export async function updateDownload(
  id: string,
  name: string
): Promise<{ download: IDownload }> {
  return request(`/downloads/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export async function deleteDownload(id: string): Promise<void> {
  return request(`/downloads/${id}`, { method: "DELETE" });
}

export async function cancelDownload(
  id: string
): Promise<{ download: IDownload }> {
  return request(`/downloads/${id}/cancel`, { method: "POST" });
}

export async function requeueDownload(
  id: string
): Promise<{ download: IDownload }> {
  return request(`/downloads/${id}/requeue`, { method: "POST" });
}

export async function getDownloadUrl(
  id: string,
  expiresIn = 3600
): Promise<IDownloadUrlResponse> {
  return request(`/downloads/${id}/download-url`, {
    method: "POST",
    body: JSON.stringify({ expiresIn }),
  });
}

export async function getUploadUrl(
  filename: string,
  sizeBytes: number
): Promise<IUploadUrlResponse> {
  return request("/downloads/upload-url", {
    method: "POST",
    body: JSON.stringify({ filename, sizeBytes }),
  });
}

export async function uploadTorrentFile(
  uploadUrl: string,
  file: File
): Promise<void> {
  const res = await fetch(uploadUrl, {
    method: "PUT",
    body: file,
    headers: { "Content-Type": "application/x-bittorrent" },
  });
  if (!res.ok) throw new Error("Upload failed");
}

// Status
export async function getStatus(): Promise<IStatusResponse> {
  return request("/status");
}
