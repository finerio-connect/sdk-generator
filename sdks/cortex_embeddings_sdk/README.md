# cortex_embeddings_sdk

SDK Cliente con **Pydantic v2** para validación automática.

## Instalación

```bash
pip install cortex_embeddings_sdk
```

## Uso Básico

```python
import os
from cortex_embeddings_sdk import create_client

# Configurar URL base
os.environ["CORTEX_EMBEDDINGS_SDK_BASE_URL"] = "https://api.example.com"

# Crear cliente
client = create_client()

# Los modelos están disponibles en .models
# from cortex_embeddings_sdk.models import <ModeloDelAPI>

# Verificar health
health = client.health_check()
print(health)
```

## Ventajas de Pydantic v2

- **Validación automática** de tipos y valores
- **Errores descriptivos** si los datos son inválidos
- **Serialización/deserialización** optimizada
- **Type hints completos** para IDE
- **model_dump()** y **model_validate()** built-in

## Soporte AWS IAM

Para autenticación con AWS IAM (Lambda URLs):

```bash
pip install cortex_embeddings_sdk[aws]
```

```python
from cortex_embeddings_sdk import create_client

# Cliente con firma AWS SigV4 (auto-detecta región desde URL)
client = create_client(
    base_url="https://xxx.lambda-url.us-east-1.on.aws/",
    use_aws_auth=True
)

# O usar variable de entorno para auto-detectar
import os
os.environ["CORTEX_EMBEDDINGS_SDK_BASE_URL"] = "https://xxx.lambda-url.us-east-1.on.aws/"
os.environ["CORTEX_EMBEDDINGS_SDK_BASE_URL_USE_AWS_AUTH"] = "true"
client = create_client()  # Auto-detecta AWS IAM
```

## Variables de Entorno

- `CORTEX_EMBEDDINGS_SDK_BASE_URL`: URL base del API
- `CORTEX_EMBEDDINGS_SDK_BASE_URL_USE_AWS_AUTH`: Usar autenticación AWS IAM (true/false)
- `CORTEX_EMBEDDINGS_SDK_BASE_URL_TOKEN`: Token de autenticación Bearer (si aplica)

## Versión

**1.0.0** - Generado con datamodel-code-generator + Pydantic v2
