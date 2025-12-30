# Cortex Rules SDK - Guía de Uso

Este SDK proporciona una interfaz Python para interactuar con el API de Cortex Rules Engine.

## Instalación

```bash
pip install ./build/sdk/python
```

## Configuración con Variables de Entorno

El SDK puede configurarse usando variables de entorno, lo que facilita su uso en diferentes entornos (desarrollo, staging, producción).

### Variables de Entorno Disponibles

- `CORTEX_RULE_ENGINE_BASE_URL`: URL base del API (por defecto: `http://localhost:8000`)
- `CORTEX_RULE_ENGINE_TOKEN`: Token de autenticación (opcional, solo para autenticación Bearer token tradicional)
- `CORTEX_RULE_ENGINE_USE_AWS_AUTH`: Set a `"true"` para forzar autenticación AWS IAM (opcional, se auto-detecta para Lambda Function URLs)

## Autenticación AWS IAM (Lambda Function URLs)

Si tu API de Cortex Rules está desplegada como una Lambda Function URL con autenticación `AWS_IAM`, el SDK puede usar automáticamente las credenciales de IAM del contexto de ejecución (Lambda, EC2, ECS, etc.) para firmar las requests.

**Ventajas:**
- ✅ Completamente transparente - no necesitas gestionar tokens
- ✅ Usa IAM roles automáticamente
- ✅ Funciona en cualquier entorno AWS con credenciales configuradas
- ✅ Auto-detecta Lambda Function URLs y aplica autenticación AWS IAM

**Requisitos:**
- El SDK debe tener instalado `boto3`: `pip install boto3`
- Debe haber credenciales de AWS disponibles (IAM role, variables de entorno, archivo de credenciales, etc.)
- La Lambda Function URL debe estar configurada con `AuthType: AWS_IAM`
- El IAM role/user debe tener permisos `lambda:InvokeFunctionUrl` y `lambda:InvokeFunction`

### Ejemplo: Auto-detección de Lambda Function URL

```python
import os
from cortex_rules_sdk import create_client
from cortex_rules_sdk.api.evaluation import evaluate_decision_decisions_evaluate_post
from cortex_rules_sdk.models import EvaluationRequest, EvaluationRequestContext

# Configurar la URL de la Lambda Function
os.environ["CORTEX_RULE_ENGINE_BASE_URL"] = (
    "https://abc123def456.lambda-url.us-east-1.on.aws/"
)

# El SDK auto-detecta que es una Lambda Function URL y usa AWS IAM auth automáticamente
client = create_client()

# Realizar una evaluación (la request se firma automáticamente con credenciales de IAM)
request = EvaluationRequest(
    tenant_id="01K0WPPET0GQH42G64B3Y2FPPJ",
    owner_id="SYSTEM#01K0WPPET0GQH42G64B3Y2FPPJ",
    decision_name="MAIN",
    context=EvaluationRequestContext(
        additional_properties={
            "amount": 1500.0,
            "currency": "MXN",
            "merchant_name": "Amazon"
        }
    )
)

response = evaluate_decision_decisions_evaluate_post.sync(client=client, body=request)
print(f"Resultado: {response.result}")
```

### Ejemplo: Uso en AWS Lambda

Cuando ejecutas este código dentro de una Lambda de AWS, las credenciales se obtienen automáticamente del execution role:

```python
# lambda_function.py
from cortex_rules_sdk import create_client
from cortex_rules_sdk.api.evaluation import evaluate_decision_decisions_evaluate_post
from cortex_rules_sdk.models import EvaluationRequest, EvaluationRequestContext

# Crear cliente una vez fuera del handler (reutilización)
client = create_client()  # Usa automáticamente credenciales del Lambda execution role

def lambda_handler(event, context):
    """Handler de Lambda que evalúa reglas."""
    
    request = EvaluationRequest(
        tenant_id=event["tenant_id"],
        owner_id=event.get("owner_id", "SYSTEM"),
        decision_name=event.get("decision_name", "MAIN"),
        context=EvaluationRequestContext(
            additional_properties=event["context"]
        )
    )
    
    response = evaluate_decision_decisions_evaluate_post.sync(
        client=client,
        body=request
    )
    
    return {
        "statusCode": 200,
        "body": {
            "result": response.result,
            "source_id": response.source_id,
            "performance": response.performance
        }
    }
```

### Permisos IAM Requeridos

Tu IAM role necesita estos permisos para invocar la Lambda Function URL:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunctionUrl",
                "lambda:InvokeFunction"
            ],
            "Resource": "arn:aws:lambda:us-east-1:123456789012:function:cortex-rules-api",
            "Condition": {
                "Bool": {
                    "lambda:InvokedViaFunctionUrl": "true"
                }
            }
        }
    ]
}
```

### Ejemplo 1: Cliente Básico con Variables de Entorno

```python
import os
from cortex_rules_sdk import create_client
from cortex_rules_sdk.api.evaluation import evaluate_decision_decisions_evaluate_post
from cortex_rules_sdk.models import EvaluationRequest, EvaluationRequestContext

# Configurar la URL base
os.environ["CORTEX_RULE_ENGINE_BASE_URL"] = "https://api.example.com"

# Crear cliente (usa automáticamente la variable de entorno)
client = create_client()

# Realizar una evaluación
request = EvaluationRequest(
    tenant_id="01K0WPPET0GQH42G64B3Y2FPPJ",
    owner_id="SYSTEM#01K0WPPET0GQH42G64B3Y2FPPJ",
    decision_name="MAIN",
    context=EvaluationRequestContext(
        additional_properties={
            "amount": 1500.0,
            "currency": "MXN",
            "merchant_name": "Amazon"
        }
    )
)

response = evaluate_decision_decisions_evaluate_post.sync(client=client, body=request)
print(f"Resultado: {response.result}")
print(f"Source ID: {response.source_id}")
```

### Ejemplo 2: Cliente Autenticado

```python
import os
from cortex_rules_sdk import create_authenticated_client
from cortex_rules_sdk.api.evaluation import evaluate_decision_decisions_evaluate_post
from cortex_rules_sdk.models import EvaluationRequest, EvaluationRequestContext

# Configurar variables de entorno
os.environ["CORTEX_RULE_ENGINE_BASE_URL"] = "https://api.example.com"
os.environ["CORTEX_RULE_ENGINE_TOKEN"] = "my-secret-token"

# Crear cliente autenticado (usa automáticamente las variables de entorno)
client = create_authenticated_client()

# O proporcionar el token explícitamente
client = create_authenticated_client(token="my-secret-token")

# Realizar operaciones autenticadas...
```

### Ejemplo 3: Configuración Manual (sin variables de entorno)

```python
from cortex_rules_sdk import Client
from cortex_rules_sdk.api.evaluation import evaluate_decision_decisions_evaluate_post

# Crear cliente con configuración explícita
client = Client(base_url="https://api.example.com")

# Usar el cliente normalmente...
```

### Ejemplo 4: Configuración Avanzada

```python
from cortex_rules_sdk import create_client
import httpx

# Crear cliente con configuración avanzada
client = create_client(
    base_url="https://api.example.com",  # Sobrescribe la variable de entorno
    timeout=30.0,
    verify_ssl=True,
    headers={"X-Custom-Header": "value"}
)
```

## API Disponibles

### Evaluación de Decisiones

```python
from cortex_rules_sdk.api.evaluation import evaluate_decision_decisions_evaluate_post
from cortex_rules_sdk.models import EvaluationRequest, EvaluationRequestContext

request = EvaluationRequest(
    tenant_id="01K0WPPET0GQH42G64B3Y2FPPJ",
    owner_id="SYSTEM#01K0WPPET0GQH42G64B3Y2FPPJ",
    decision_name="MAIN",
    context=EvaluationRequestContext(
        additional_properties={"key": "value"}
    )
)

response = evaluate_decision_decisions_evaluate_post.sync(client=client, body=request)
```

### Gestión de Reglas

```python
from cortex_rules_sdk.api.rules import (
    get_rules_decisions_rules_get,
    upsert_rules_decisions_rules_put,
    delete_rules_decisions_rules_delete
)
from cortex_rules_sdk.models import RulesUpsertRequest

# Obtener reglas
response = get_rules_decisions_rules_get.sync(
    client=client,
    tenant_id="01K0WPPET0GQH42G64B3Y2FPPJ",
    owner_id="SYSTEM#01K0WPPET0GQH42G64B3Y2FPPJ",
    decision_name="MAIN"
)

# Crear/actualizar reglas
request = RulesUpsertRequest(...)  # Configurar según necesidad
upsert_rules_decisions_rules_put.sync(client=client, body=request)
```

### Gestión de JDM (JSON Decision Model)

```python
from cortex_rules_sdk.api.jdm_decisions import (
    get_jdm_decisions_jdm_get,
    upsert_jdm_decisions_jdm_put,
    delete_jdm_decisions_jdm_delete
)

# Obtener JDM
response = get_jdm_decisions_jdm_get.sync(
    client=client,
    tenant_id="01K0WPPET0GQH42G64B3Y2FPPJ",
    owner_id="SYSTEM#01K0WPPET0GQH42G64B3Y2FPPJ",
    decision_name="MAIN"
)
```

## Cliente Asíncrono

Todas las operaciones también están disponibles en versión asíncrona:

```python
import asyncio
from cortex_rules_sdk import create_client
from cortex_rules_sdk.api.evaluation import evaluate_decision_decisions_evaluate_post

async def evaluate():
    client = create_client()
    
    async with client:
        response = await evaluate_decision_decisions_evaluate_post.asyncio(
            client=client,
            body=request
        )
        return response

# Ejecutar
result = asyncio.run(evaluate())
```

## Mejores Prácticas

1. **Usar variables de entorno en producción**: Facilita la configuración sin cambiar código.
2. **Reutilizar instancias del cliente**: Evita crear múltiples clientes innecesariamente.
3. **Usar context managers**: Para gestión automática de recursos con clientes asíncronos.
4. **Manejar errores apropiadamente**: Capturar excepciones de `httpx` y del SDK.

```python
from cortex_rules_sdk import create_client
from cortex_rules_sdk.errors import UnexpectedStatus
import httpx

client = create_client()

try:
    response = evaluate_decision_decisions_evaluate_post.sync(client=client, body=request)
except UnexpectedStatus as e:
    print(f"Error inesperado del servidor: {e.status_code}")
except httpx.TimeoutException:
    print("Timeout al conectar con el servidor")
except httpx.ConnectError:
    print("No se pudo conectar al servidor")
```

