"""Cliente HTTP para Cortex Embeddings Sdk API."""

from __future__ import annotations

import httpx
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import BulkEmbeddingRequest, BulkEmbeddingResponse, EmbeddingRequest, EmbeddingResponse, HealthResponse


class CortexEmbeddingsSdkClient:
    """Cliente para interactuar con Cortex Embeddings Sdk API.
    
    Este cliente usa httpx y modelos Pydantic v2 para validación automática.
    
    Args:
        base_url: URL base del API
        timeout: Timeout en segundos para las requests
        auth: Objeto de autenticación httpx (opcional)
        headers: Headers adicionales para todas las requests
    
    Examples:
        >>> from cortex_embeddings_sdk import create_client
        >>> client = create_client("https://api.example.com")
        >>> # Use los métodos generados automáticamente
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        auth: httpx.Auth | None = None,
        headers: dict[str, str] | None = None,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
        **httpx_kwargs: Any,
    ):
        """Inicializa el cliente."""
        self.base_url = base_url.rstrip("/")
        
        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            default_headers.update(headers)

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            auth=auth,
            headers=default_headers,
            verify=verify_ssl,
            follow_redirects=follow_redirects,
            **httpx_kwargs,
        )

    def __enter__(self) -> "CortexEmbeddingsSdkClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Cierra el cliente HTTP."""
        self._client.close()


    def health(
        self,
        timeout: float | None = None,
    ) -> 'HealthResponse':
        """Health
        
        Args:
            timeout: Timeout específico para esta request
            
        Returns:
            Modelo HealthResponse con la respuesta tipada
        """
        from .models import HealthResponse
        
        response = self._client.get(
            "/health",
            timeout=timeout,
        )
        response.raise_for_status()
        
        # Deserializar y validar con Pydantic
        return HealthResponse.model_validate(response.json())


    def create_embeddings(
        self,
        request: 'EmbeddingRequest',
        timeout: float | None = None,
    ) -> 'EmbeddingResponse':
        """Create Embeddings
        
        Args:
            request: Datos del request (EmbeddingRequest)
            timeout: Timeout específico para esta request
            
        Returns:
            Modelo EmbeddingResponse con la respuesta tipada
        """
        from .models import EmbeddingResponse
        
        # Serializar request con Pydantic
        request_data = request.model_dump(mode="json", exclude_none=True)
        
        response = self._client.post(
            "/v1/embeddings",
            json=request_data,
            timeout=timeout,
        )
        response.raise_for_status()
        
        # Deserializar y validar con Pydantic
        return EmbeddingResponse.model_validate(response.json())


    def create_bulk_embeddings_bulk(
        self,
        request: 'BulkEmbeddingRequest',
        timeout: float | None = None,
    ) -> 'BulkEmbeddingResponse':
        """Genera embeddings en bulk para múltiples items con ID y descripción.

Garantiza que el orden de los embeddings corresponde al orden de los items
de entrada, permitiendo una asociación explícita mediante IDs.
        
        Args:
            request: Datos del request (BulkEmbeddingRequest)
            timeout: Timeout específico para esta request
            
        Returns:
            Modelo BulkEmbeddingResponse con la respuesta tipada
        """
        from .models import BulkEmbeddingResponse
        
        # Serializar request con Pydantic
        request_data = request.model_dump(mode="json", exclude_none=True)
        
        response = self._client.post(
            "/v1/embeddings/bulk",
            json=request_data,
            timeout=timeout,
        )
        response.raise_for_status()
        
        # Deserializar y validar con Pydantic
        return BulkEmbeddingResponse.model_validate(response.json())
