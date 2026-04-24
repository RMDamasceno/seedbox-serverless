import type { DownloadStatus } from "../types/download";

const ICONS: Record<DownloadStatus, string> = {
  pending: "⏳",
  processing: "⬇️",
  completed: "✅",
  cancelled: "❌",
};

const LABELS: Record<DownloadStatus, string> = {
  pending: "Pendentes",
  processing: "Baixando",
  completed: "Concluídos",
  cancelled: "Cancelados",
};

interface Props {
  status: DownloadStatus;
  count: number;
}

export default function StatusCard({ status, count }: Props) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 flex items-center gap-3">
      <span className="text-2xl">{ICONS[status]}</span>
      <div>
        <p className="text-2xl font-bold">{count}</p>
        <p className="text-sm text-gray-400">{LABELS[status]}</p>
      </div>
    </div>
  );
}
