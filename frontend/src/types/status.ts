export interface IStatusResponse {
  worker: IWorkerStatus;
  queue: IQueueStatus;
  index: IIndexStatus;
}

export interface IWorkerStatus {
  status: "running" | "stopped" | "starting" | "stopping" | "pending";
  instanceId: string | null;
  instanceType: string | null;
  launchedAt: string | null;
  uptimeSeconds: number;
}

export interface IQueueStatus {
  pending: number;
  processing: number;
  completed: number;
  cancelled: number;
}

export interface IIndexStatus {
  updatedAt: string | null;
  isStale: boolean;
}
