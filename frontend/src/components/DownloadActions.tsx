import type { IDownload } from "../types/download";

interface Props {
  download: IDownload;
  onCancel: () => void;
  onDelete: () => void;
  onRequeue: () => void;
  onDownload: () => void;
}

export default function DownloadActions({ download, onCancel, onDelete, onRequeue, onDownload }: Props) {
  const s = download.status;

  return (
    <div className="flex flex-wrap gap-2">
      {s === "completed" && (
        <button onClick={onDownload} className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-sm transition-colors">
          Baixar Arquivo
        </button>
      )}
      {(s === "pending" || s === "processing") && (
        <button onClick={onCancel} className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm transition-colors">
          Cancelar
        </button>
      )}
      {s === "cancelled" && (
        <button onClick={onRequeue} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm transition-colors">
          Recolocar na Fila
        </button>
      )}
      <button onClick={onDelete} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors">
        Remover
      </button>
    </div>
  );
}
