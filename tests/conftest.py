"""Configuração raiz de testes — ajusta sys.path para imports."""

import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Criar alias para 'backend.lambda' → 'backend.lambda_' pois 'lambda' é keyword
# Solução: usar importlib para mapear os módulos
import importlib
import types

# Importar backend como pacote
backend_path = ROOT / "backend"
if not (backend_path / "__init__.py").exists():
    (backend_path / "__init__.py").write_text("")

lambda_path = backend_path / "lambda"
if not (lambda_path / "__init__.py").exists():
    (lambda_path / "__init__.py").write_text("")

# Registrar 'backend.lambda_' como alias para 'backend.lambda'
import backend
if not hasattr(backend, "lambda_"):
    lambda_mod = importlib.import_module("backend.lambda")
    backend.lambda_ = lambda_mod
    sys.modules["backend.lambda_"] = lambda_mod

    # Sub-módulos
    for sub in ["api", "authorizer", "worker-trigger"]:
        sub_safe = sub.replace("-", "_")
        try:
            mod = importlib.import_module(f"backend.lambda.{sub}")
            sys.modules[f"backend.lambda_.{sub_safe}"] = mod
        except ImportError:
            pass
