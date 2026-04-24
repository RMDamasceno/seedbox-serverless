import { useEffect, useState } from "react";
import WorkerStatus from "../components/WorkerStatus";
import { getStatus } from "../services/api";
import type { IStatusResponse } from "../types/status";

export default function InfraStatus() {
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
    const interval = setInterval(poll, 30_000);
    return () => { active = false; clearInterval(interval); };
  }, []);

  if (!status) return <p className="text-gray-500">Carregando...</p>;

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Infraestrutura</h1>

      <div className="space-y-4">
        <section className="bg-gray-800 rounded-lg p-4">
          <h2 className="font-medium mb-3">Worker EC2</h2>
          <WorkerStatus worker={status.worker} />
          {status.worker.instanceId && (
            <p className="text-sm text-gray-400 mt-2">ID: {status.worker.instanceId}</p>
          )}
        </section>

        <section className="bg-gray-800 rounded-lg p-4">
          <h2 className="font-medium mb-3">Fila</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
            <Stat label="Pendentes" value={status.queue.pending} />
            <Stat label="Baixando" value={status.queue.processing} />
            <Stat label="Concluídos" value={status.queue.completed} />
            <Stat label="Cancelados" value={status.queue.cancelled} />
          </div>
        </section>

        <section className="bg-gray-800 rounded-lg p-4">
          <h2 className="font-medium mb-3">Índice</h2>
          <p className="text-sm text-gray-400">
            Atualizado: {status.index.updatedAt
              ? new Date(status.index.updatedAt).toLocaleString("pt-BR")
              : "Nunca"}
          </p>
          {status.index.isStale && (
            <p className="text-yellow-400 text-sm mt-1">⚠️ Desatualizado há mais de 2 minutos</p>
          )}
        </section>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}
