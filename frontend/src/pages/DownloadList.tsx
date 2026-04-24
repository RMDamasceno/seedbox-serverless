import { useEffect, useState } from "react";
import DownloadCard from "../components/DownloadCard";
import { listDownloads, cancelDownload, deleteDownload } from "../services/api";
import type { IDownloadSummary, DownloadStatus } from "../types/download";

const TABS: { label: string; value: DownloadStatus | "" }[] = [
  { label: "Todos", value: "" },
  { label: "Pendentes", value: "pending" },
  { label: "Baixando", value: "processing" },
  { label: "Concluídos", value: "completed" },
  { label: "Cancelados", value: "cancelled" },
];

export default function DownloadList() {
  const [items, setItems] = useState<IDownloadSummary[]>([]);
  const [filter, setFilter] = useState<DownloadStatus | "">("");

  const fetchItems = async () => {
    try {
      const data = await listDownloads(filter || undefined);
      setItems(data.items);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    fetchItems();
    const hasProcessing = items.some((i) => i.status === "processing");
    const interval = setInterval(fetchItems, hasProcessing ? 10_000 : 30_000);
    return () => clearInterval(interval);
  }, [filter, items.length]);

  const handleCancel = async (id: string) => {
    await cancelDownload(id);
    fetchItems();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Remover permanentemente?")) return;
    await deleteDownload(id);
    fetchItems();
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Downloads</h1>

      <div className="flex gap-2 mb-6 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilter(tab.value)}
            className={`px-3 py-1.5 rounded text-sm whitespace-nowrap transition-colors ${
              filter === tab.value
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {items.length === 0 ? (
        <p className="text-gray-500 text-center py-12">Nenhum download encontrado</p>
      ) : (
        <div className="grid gap-3">
          {items.map((item) => (
            <DownloadCard
              key={item.id}
              item={item}
              onCancel={handleCancel}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}
