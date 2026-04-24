export type DownloadStatus = "pending" | "processing" | "completed" | "cancelled";
export type DownloadType = "magnet" | "torrent_file";

export interface IDownload {
  id: string;
  clientRequestId: string;
  name: string;
  status: DownloadStatus;
  type: DownloadType;
  magnetLink: string | null;
  torrentS3Key: string | null;
  transmissionId: number | null;
  sizeBytes: number | null;
  sizeBytesDownloaded: number;
  progressPercent: number;
  downloadSpeedBps: number;
  uploadSpeedBps: number;
  eta: number | null;
  errorMessage: string | null;
  retryCount: number;
  retryAfter: string | null;
  workerId: string | null;
  version: number;
  createdAt: string;
  updatedAt: string;
  startedAt: string | null;
  completedAt: string | null;
  cancelledAt: string | null;
  s3Key: string | null;
  s3SizeBytes: number | null;
}

export interface IDownloadListResponse {
  items: IDownloadSummary[];
  total: number;
  page: number;
}

export interface IDownloadSummary {
  id: string;
  name: string;
  status: DownloadStatus;
  progressPercent: number;
  sizeBytes: number | null;
  updatedAt: string;
}

export interface ICreateDownloadRequest {
  clientRequestId: string;
  type: DownloadType;
  magnetLink?: string;
  torrentS3Key?: string;
  name?: string;
}

export interface IDownloadUrlResponse {
  url: string;
  filename: string;
  sizeBytes: number;
  expiresAt: string;
  estimatedTransferCostUSD: number;
}

export interface IUploadUrlResponse {
  uploadUrl: string;
  torrentS3Key: string;
}
