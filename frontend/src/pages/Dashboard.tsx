import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import StatusCard from "../components/StatusCard";
import WorkerStatus from "../components/WorkerStatus";
import { getStatus } from "../services/api";
import type { IStatusResponse } from "../types/status";
import type { DownloadStatus } from "../types/download";

const STATUSES: DownloadStatus[] = ["pending", "processing", "completed", "cancelled"];

export default function Dashboard() {
  const [status, setStatus] = useState<IStatusResponse | null>(null);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const data = await getStatus();
        if (active) setStatus(data);
      } catch { /* ignore */ }
    };
    poll();
    const hasProcessing = status?.queue.processing ?? 0;
    const interval = setInterval(poll, hasProcessing > 0 ? 10_000 : 60_000);
    return () => { active = false; clearInterval(interval); };
  }, [status?.queue.processing]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <Link
          to="/downloads/new"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded font-medium transition-colors"
        >
          + Novo Download
        </Link>
      </div>

      {status && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {STATUSES.map((s) => (
              <StatusCard key={s} status={s} count={status.queue[s]} />
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <WorkerStatus worker={status.worker} />
            {status.index.isStale && (
              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                <p className="text-yellow-400 text-sm">
                  ⚠️ Índice desatualizado há mais de 2 minutos
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
