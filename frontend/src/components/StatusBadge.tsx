import type { DownloadStatus } from "../types/download";

const COLORS: Record<DownloadStatus, string> = {
  pending: "bg-yellow-500/20 text-yellow-400",
  processing: "bg-blue-500/20 text-blue-400",
  completed: "bg-green-500/20 text-green-400",
  cancelled: "bg-red-500/20 text-red-400",
};

const LABELS: Record<DownloadStatus, string> = {
  pending: "Pendente",
  processing: "Baixando",
  completed: "Concluído",
  cancelled: "Cancelado",
};

export default function StatusBadge({ status }: { status: DownloadStatus }) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${COLORS[status]}`}>
      {LABELS[status]}
    </span>
  );
}
