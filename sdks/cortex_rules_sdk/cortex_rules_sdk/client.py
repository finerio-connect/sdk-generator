"""Cliente HTTP para Cortex Rules API."""

from __future__ import annotations

import httpx
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import EvaluationRequest, EvaluationResponse


class CortexRulesClient:
    """Cliente para interactuar con Cortex Rules API.
    
    Este cliente usa httpx y modelos Pydantic v2 para validación automática.
    
    Args:
        base_url: URL base del API
        timeout: Timeout en segundos para las requests
        auth: Objeto de autenticación httpx (opcional)
        headers: Headers adicionales para todas las requests
    
    Examples:
        >>> client = CortexRulesClient("https://api.example.com")
        >>> request = EvaluationRequest(
        ...     tenant_id="tenant-123",
        ...     user_id="user-456",
        ...     context={"transaction": {"amount": 100}}
        ... )
        >>> response = client.evaluate_decision(request)
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

    def __enter__(self) -> CortexRulesClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Cierra el cliente HTTP."""
        self._client.close()

    def evaluate_decision(
        self,
        request: "EvaluationRequest",
        timeout: float | None = None,
    ) -> "EvaluationResponse":
        """Evalúa una decisión con el contexto proporcionado.
        
        Args:
            request: Request con tenant_id, user_id, context y decision
            timeout: Timeout específico para esta request (opcional)
        
        Returns:
            EvaluationResponse con el resultado de la evaluación
        
        Raises:
            httpx.HTTPStatusError: Si la respuesta tiene un código de error
            ValidationError: Si el request o response no pasan validación Pydantic
        
        Examples:
            >>> request = EvaluationRequest(
            ...     tenant_id="tenant-123",
            ...     user_id="user-456",
            ...     context={"data": "value"},
            ...     decision="MAIN"
            ... )
            >>> response = client.evaluate_decision(request)
            >>> print(response.result)
        """
        from .models import EvaluationResponse
        
        # Serializa con Pydantic (incluye validación automática)
        request_data = request.model_dump(mode="json", exclude_none=True)
        
        # Hace la request HTTP
        http_response = self._client.post(
            "/decisions/evaluate",
            json=request_data,
            timeout=timeout,
        )
        http_response.raise_for_status()
        
        # Deserializa y valida con Pydantic
        return EvaluationResponse.model_validate(http_response.json())

    def health_check(self) -> dict[str, Any]:
        """Verifica el estado del servicio.
        
        Returns:
            Dict con información de salud del servicio
        """
        response = self._client.get("/health")
        response.raise_for_status()
        return response.json()
