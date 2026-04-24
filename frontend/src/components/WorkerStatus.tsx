import type { IWorkerStatus } from "../types/status";

const STATUS_COLORS: Record<string, string> = {
  running: "bg-green-500",
  stopped: "bg-gray-500",
  starting: "bg-yellow-500",
  stopping: "bg-orange-500",
  pending: "bg-yellow-500",
};

export default function WorkerStatus({ worker }: { worker: IWorkerStatus }) {
  const color = STATUS_COLORS[worker.status] || "bg-gray-500";
  const uptime = worker.uptimeSeconds > 0 ? formatUptime(worker.uptimeSeconds) : null;

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className={`w-3 h-3 rounded-full ${color} animate-pulse`} />
        <span className="font-medium capitalize">{worker.status}</span>
      </div>
      {worker.instanceType && (
        <p className="text-sm text-gray-400">{worker.instanceType}</p>
      )}
      {uptime && <p className="text-sm text-gray-400">Uptime: {uptime}</p>}
    </div>
  );
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}
