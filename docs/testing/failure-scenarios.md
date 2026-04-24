# Cenários de Falha Controlada

10 cenários obrigatórios conforme seção 16 do documento técnico v1.5.

| # | Cenário | Arquivo de Teste | Status |
|---|---------|-----------------|--------|
| 1 | Disco cheio → pausa/retoma | test_failure_scenarios.py::TestScenario1DiskFull | ✅ |
| 2 | Interrupção EC2 (SIGTERM) → pending | test_failure_scenarios.py::TestScenario2EC2Interruption | ✅ |
| 3 | Falha PUT S3 → retry temporário | test_failure_scenarios.py::TestScenario3S3PutFailure | ✅ |
| 4 | Magnet inválido → cancelled definitivo | test_failure_scenarios.py::TestScenario4InvalidMagnet | ✅ |
| 5 | Race enqueue + shutdown → stopping | test_failure_scenarios.py::TestScenario5RaceEnqueueShutdown | ✅ |
| 6 | Duplo clique (idempotência) | test_failure_scenarios.py::TestScenario6Idempotency | ✅ |
| 7 | index.json stale > 2min | test_failure_scenarios.py::TestScenario7IndexStale | ✅ |
| 8 | Cancelamento durante sync | test_failure_scenarios.py::TestScenario8CancelDuringSync | ✅ |
| 9 | Acesso direto S3 bloqueado | test_failure_scenarios.py::TestScenario9CloudflareOnly | ✅ |
| 10 | Pre-signed URL → só completed | test_failure_scenarios.py::TestScenario10ExpiredUrl | ✅ |
