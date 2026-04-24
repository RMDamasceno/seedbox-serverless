import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { createDownload, getUploadUrl, uploadTorrentFile } from "../services/api";

export default function AddDownload() {
  const [tab, setTab] = useState<"magnet" | "torrent">("magnet");
  const [magnetLink, setMagnetLink] = useState("");
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const clientRequestId = crypto.randomUUID();

    try {
      if (tab === "magnet") {
        if (!magnetLink.startsWith("magnet:?")) {
          setError("Magnet link inválido");
          return;
        }
        await createDownload({ clientRequestId, type: "magnet", magnetLink, name: name || undefined });
      } else {
        if (!file) { setError("Selecione um arquivo .torrent"); return; }
        if (file.size > 1_048_576) { setError("Arquivo muito grande (máx 1MB)"); return; }

        const { uploadUrl, torrentS3Key } = await getUploadUrl(file.name, file.size);
        await uploadTorrentFile(uploadUrl, file);
        await createDownload({ clientRequestId, type: "torrent_file", torrentS3Key, name: name || undefined });
      }
      navigate("/downloads");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar download");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-bold mb-6">Novo Download</h1>

      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setTab("magnet")}
          className={`px-4 py-2 rounded text-sm ${tab === "magnet" ? "bg-blue-600" : "bg-gray-800 text-gray-400"}`}
        >
          Magnet Link
        </button>
        <button
          onClick={() => setTab("torrent")}
          className={`px-4 py-2 rounded text-sm ${tab === "torrent" ? "bg-blue-600" : "bg-gray-800 text-gray-400"}`}
        >
          Arquivo .torrent
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {tab === "magnet" ? (
          <textarea
            value={magnetLink}
            onChange={(e) => setMagnetLink(e.target.value)}
            placeholder="magnet:?xt=urn:btih:..."
            rows={3}
            className="w-full px-4 py-2 bg-gray-800 rounded border border-gray-700 focus:border-blue-500 focus:outline-none resize-none"
          />
        ) : (
          <div
            className="border-2 border-dashed border-gray-700 rounded-lg p-8 text-center cursor-pointer hover:border-gray-500"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); setFile(e.dataTransfer.files[0]); }}
            onClick={() => document.getElementById("torrent-input")?.click()}
          >
            <input
              id="torrent-input"
              type="file"
              accept=".torrent"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            {file ? (
              <p className="text-blue-400">{file.name}</p>
            ) : (
              <p className="text-gray-500">Arraste um .torrent ou clique para selecionar</p>
            )}
          </div>
        )}

        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Nome (opcional)"
          maxLength={255}
          className="w-full px-4 py-2 bg-gray-800 rounded border border-gray-700 focus:border-blue-500 focus:outline-none"
        />

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded font-medium transition-colors"
        >
          {loading ? "Enviando..." : "Adicionar Download"}
        </button>
      </form>
    </div>
  );
}
