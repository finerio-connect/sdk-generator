# cortex_rules_sdk

SDK Cliente para Cortex Rules con **Pydantic v2** para validación automática.

## Instalación

```bash
pip install cortex_rules_sdk
```

## Uso Básico

```python
import os
from cortex_rules_sdk import create_client
from cortex_rules_sdk.models import EvaluationRequest

# Configurar URL base
os.environ["CORTEX_RULE_ENGINE_BASE_URL"] = "https://api.example.com"

# Crear cliente
client = create_client()

# Crear request (con validación Pydantic automática)
request = EvaluationRequest(
    tenant_id="my-tenant",
    user_id="my-user",
    context={
        "transaction": {
            "amount": 100,
            "type": "income"
        }
    },
    decision="MAIN"
)

# Evaluar (response también validado con Pydantic)
response = client.evaluate_decision(request)
print(response.result)
```

## Ventajas de Pydantic v2

*    **Validación automática** de tipos y valores
*    **Errores descriptivos** si los datos son inválidos
*    **Serialización/deserialización** optimizada
*    **Type hints completos** para IDE
*    **model_dump()** y **model_validate()** built-in

## Soporte AWS IAM

Para autenticación con AWS IAM (Lambda URLs):

```bash
pip install cortex_rules_sdk[aws]
```

```python
from cortex_rules_sdk import create_client
from cortex_rules_sdk.config import AWSSigV4Auth

# Cliente con firma AWS SigV4
client = create_client(
    base_url="https://xxx.lambda-url.us-east-1.on.aws/",
    auth=AWSSigV4Auth(service="lambda", region="us-east-1")
)
```

## Versión

**1** - Generado con datamodel-code-generator + Pydantic v2
