import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import DownloadActions from "../components/DownloadActions";
import ProgressBar from "../components/ProgressBar";
import StatusBadge from "../components/StatusBadge";
import {
  getDownload, cancelDownload, deleteDownload,
  requeueDownload, getDownloadUrl, updateDownload,
} from "../services/api";
import { formatBytes, formatSpeed, formatEta } from "../services/format";
import type { IDownload } from "../types/download";

export default function DownloadDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dl, setDl] = useState<IDownload | null>(null);
  const [editing, setEditing] = useState(false);
  const [nameInput, setNameInput] = useState("");

  const fetchData = async () => {
    if (!id) return;
    try {
      const { download } = await getDownload(id);
      setDl(download);
    } catch { navigate("/downloads"); }
  };

  useEffect(() => {
    fetchData();
    if (dl?.status === "processing") {
      const interval = setInterval(fetchData, 10_000);
      return () => clearInterval(interval);
    }
  }, [id, dl?.status]);

  if (!dl) return <p className="text-gray-500">Carregando...</p>;

  const handleCancel = async () => { await cancelDownload(dl.id); fetchData(); };
  const handleDelete = async () => {
    if (!confirm("Remover permanentemente?")) return;
    await deleteDownload(dl.id);
    navigate("/downloads");
  };
  const handleRequeue = async () => { await requeueDownload(dl.id); fetchData(); };
  const handleDownload = async () => {
    const data = await getDownloadUrl(dl.id);
    window.open(data.url, "_blank");
  };
  const handleSaveName = async () => {
    await updateDownload(dl.id, nameInput);
    setEditing(false);
    fetchData();
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        {editing ? (
          <div className="flex gap-2 flex-1">
            <input
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              className="flex-1 px-3 py-1 bg-gray-800 rounded border border-gray-700 focus:border-blue-500 focus:outline-none"
              autoFocus
            />
            <button onClick={handleSaveName} className="px-3 py-1 bg-blue-600 rounded text-sm">Salvar</button>
            <button onClick={() => setEditing(false)} className="px-3 py-1 bg-gray-700 rounded text-sm">Cancelar</button>
          </div>
        ) : (
          <h1
            className="text-2xl font-bold flex-1 cursor-pointer hover:text-blue-400"
            onClick={() => { setNameInput(dl.name); setEditing(true); }}
            title="Clique para editar"
          >
            {dl.name || dl.id.slice(0, 8)}
          </h1>
        )}
        <StatusBadge status={dl.status} />
      </div>

      {dl.status === "processing" && (
        <div className="mb-6">
          <ProgressBar percent={dl.progressPercent} />
          <div className="flex justify-between text-sm text-gray-400 mt-2">
            <span>{dl.progressPercent.toFixed(1)}%</span>
            <span>↓ {formatSpeed(dl.downloadSpeedBps)} ↑ {formatSpeed(dl.uploadSpeedBps)}</span>
            <span>ETA: {formatEta(dl.eta)}</span>
          </div>
        </div>
      )}

      <div className="bg-gray-800 rounded-lg p-4 mb-6 grid grid-cols-2 gap-3 text-sm">
        <Detail label="Tamanho" value={formatBytes(dl.sizeBytes)} />
        <Detail label="Baixado" value={formatBytes(dl.sizeBytesDownloaded)} />
        <Detail label="Tipo" value={dl.type === "magnet" ? "Magnet Link" : "Arquivo .torrent"} />
        <Detail label="Versão" value={String(dl.version)} />
        <Detail label="Criado em" value={new Date(dl.createdAt).toLocaleString("pt-BR")} />
        {dl.completedAt && <Detail label="Concluído em" value={new Date(dl.completedAt).toLocaleString("pt-BR")} />}
        {dl.errorMessage && (
          <div className="col-span-2 text-red-400 bg-red-500/10 rounded p-2">
            Erro: {dl.errorMessage}
          </div>
        )}
      </div>

      <DownloadActions
        download={dl}
        onCancel={handleCancel}
        onDelete={handleDelete}
        onRequeue={handleRequeue}
        onDownload={handleDownload}
      />
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-gray-500">{label}</p>
      <p className="text-gray-200">{value}</p>
    </div>
  );
}
