import { Link } from "react-router-dom";
import ProgressBar from "./ProgressBar";
import StatusBadge from "./StatusBadge";
import { formatBytes } from "../services/format";
import type { IDownloadSummary } from "../types/download";

interface Props {
  item: IDownloadSummary;
  onCancel?: (id: string) => void;
  onDelete?: (id: string) => void;
}

export default function DownloadCard({ item, onCancel, onDelete }: Props) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-start justify-between mb-2">
        <Link to={`/downloads/${item.id}`} className="font-medium hover:text-blue-400 truncate flex-1">
          {item.name || item.id.slice(0, 8)}
        </Link>
        <StatusBadge status={item.status} />
      </div>

      {item.status === "processing" && (
        <div className="mb-2">
          <ProgressBar percent={item.progressPercent} />
          <p className="text-xs text-gray-400 mt-1">{item.progressPercent.toFixed(1)}%</p>
        </div>
      )}

      <div className="flex items-center justify-between text-sm text-gray-400">
        <span>{formatBytes(item.sizeBytes)}</span>
        <div className="flex gap-2">
          {(item.status === "pending" || item.status === "processing") && onCancel && (
            <button onClick={() => onCancel(item.id)} className="text-red-400 hover:text-red-300">
              Cancelar
            </button>
          )}
          {onDelete && (
            <button onClick={() => onDelete(item.id)} className="text-gray-500 hover:text-gray-300">
              Remover
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
