"""SDK Cliente para Cortex Embeddings Sdk con modelos Pydantic v2.

Este SDK utiliza Pydantic v2 para validación automática de datos.
"""

from .client import CortexEmbeddingsSdkClient
from .config import create_client, get_base_url

# Importar todos los modelos para fácil acceso
try:
    from .models import *  # noqa: F403
except ImportError:
    # Si no se generaron los modelos todavía
    pass

__version__ = "1.0.0"
__all__ = ["CortexEmbeddingsSdkClient", "create_client", "get_base_url"]
