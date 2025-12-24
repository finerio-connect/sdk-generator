#!/usr/bin/env python3
"""Generador de SDK para Cortex Rules con Pydantic v2.

Este script genera un SDK cliente completo con modelos Pydantic v2 desde
la especificación OpenAPI, incluyendo validación automática de tipos y valores.

Utiliza datamodel-code-generator para generar modelos Pydantic v2 nativos.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


TEMPLATE_DIR = Path(__file__).parent / "sdk_templates"

def _check_datamodel_codegen() -> bool:
    """Verifica si datamodel-code-generator está instalado."""
    try:
        result = subprocess.run(
            ["datamodel-codegen", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _generate_pydantic_models_and_client(
    spec_path: Path,
    package_dir: Path,
    generate_http_client: bool = True,
) -> None:
    """Genera modelos Pydantic v2 y opcionalmente el cliente HTTP desde OpenAPI."""
    print(f"Generando código desde {spec_path.name}...")

    if generate_http_client:
        # Generar todo (modelos + cliente HTTP) en un solo archivo
        output_file = package_dir / "api.py"
        print("  * Generando modelos y cliente HTTP integrado...")
        
        command = [
            "datamodel-codegen",
            "--input",
            str(spec_path),
            "--output",
            str(output_file),
            "--input-file-type",
            "openapi",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--http-client",
            "httpx",  # Genera cliente con httpx
            "--field-constraints",
            "--use-standard-collections",
            "--use-union-operator",
            "--target-python-version",
            "3.12",
            "--snake-case-field",
            "--allow-extra-fields",
            "--use-default-kwarg",
            "--enable-faux-immutability",
            "--use-annotated",
        ]
    else:
        # Solo generar modelos (modo anterior)
        output_file = package_dir / "models.py"
        print("  * Generando solo modelos Pydantic v2...")
        
        command = [
            "datamodel-codegen",
            "--input",
            str(spec_path),
            "--output",
            str(output_file),
            "--input-file-type",
            "openapi",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--field-constraints",
            "--use-standard-collections",
            "--use-union-operator",
            "--target-python-version",
            "3.12",
            "--snake-case-field",
            "--allow-extra-fields",
            "--use-default-kwarg",
            "--enable-faux-immutability",
            "--use-annotated",
        ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"  * Generado exitosamente: {output_file.name}")
        if result.stdout:
            print(f"     {result.stdout.strip()}")
    except subprocess.CalledProcessError as exc:
        print(f"  ERROR: {exc.stderr}")
        raise RuntimeError(
            f"Falló la generación con datamodel-code-generator:\n{exc.stderr}"
        ) from exc


def _add_dto_aliases(models_file: Path) -> None:
    """Agrega alias sin sufijo DTO para compatibilidad."""
    if not models_file.exists():
        return

    content = models_file.read_text(encoding="utf-8")
    marker = "# Backwards compatibility aliases (DTO -> canonical)"
    if marker in content:
        content = content.split(marker)[0].rstrip()

    dto_classes = sorted(set(re.findall(r"class (\w+DTO)\(BaseModel\):", content)))
    if not dto_classes:
        models_file.write_text(content + "\n", encoding="utf-8")
        return

    alias_lines = [marker]
    alias_lines.extend(f"{name[:-3]} = {name}" for name in dto_classes)
    alias_block = "\n\n" + "\n".join(alias_lines) + "\n"
    models_file.write_text(content.rstrip() + alias_block, encoding="utf-8")


def _render_template(template_name: str, **context: Any) -> str:
    """Carga un template y reemplaza los placeholders."""
    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"No se encontró el template {template_name}")
    template_content = template_path.read_text(encoding="utf-8")
    return template_content.format(**context)


def _extract_schema_name(schema_ref: dict) -> str | None:
    """Extrae el nombre del modelo desde un $ref."""
    if isinstance(schema_ref, dict) and '$ref' in schema_ref:
        # #/components/schemas/ModelName -> ModelName
        return schema_ref['$ref'].split('/')[-1]
    return None


def _clean_method_name(operation_id: str, path: str, http_method: str) -> str:
    """Limpia y estandariza el nombre del método.
    
    Convierte operationId como 'create_embeddings_v1_embeddings_post' 
    a 'create_embeddings'.
    """
    if not operation_id:
        # Generar desde path y método si no hay operationId
        clean_path = path.strip('/').replace('/', '_').replace('{', '').replace('}', '')
        return f"{http_method.lower()}_{clean_path}"
    
    # Remover sufijos comunes del operationId
    name = operation_id.lower()
    
    # Remover sufijo del método HTTP (_get, _post, etc.)
    for method in ['_get', '_post', '_put', '_patch', '_delete']:
        if name.endswith(method):
            name = name[:-len(method)]
            break
    
    # Remover partes redundantes del path (versión, repeticiones)
    # Ej: "create_embeddings_v1_embeddings" -> "create_embeddings"
    parts = name.split('_')
    seen = set()
    cleaned_parts = []
    
    for part in parts:
        # Saltar versiones (v1, v2, etc.)
        if part.startswith('v') and len(part) == 2 and part[1].isdigit():
            continue
        # Evitar repeticiones consecutivas
        if part not in seen or (cleaned_parts and cleaned_parts[-1] != part):
            cleaned_parts.append(part)
            seen.add(part)
    
    return '_'.join(cleaned_parts)


def _generate_client_methods(spec_path: Path) -> tuple[str, set[str]]:
    """Genera métodos del cliente dinámicamente desde el OpenAPI spec con tipado completo.
    
    Returns:
        Tuple de (código de métodos, conjunto de modelos usados)
    """
    with open(spec_path, 'r', encoding='utf-8') as f:
        spec = json.load(f)
    
    methods = []
    used_models = set()
    paths = spec.get('paths', {})
    
    for path, path_item in paths.items():
        for http_method, operation in path_item.items():
            if http_method.lower() not in ['get', 'post', 'put', 'patch', 'delete']:
                continue
            
            operation_id = operation.get('operationId', '')
            summary = operation.get('summary', '')
            description = operation.get('description', summary)
            
            # Limpiar y estandarizar nombre del método
            method_name = _clean_method_name(operation_id, path, http_method)
            
            # Extraer tipo de request body
            request_body = operation.get('requestBody', {})
            request_type = None
            if request_body:
                content = request_body.get('content', {})
                json_content = content.get('application/json', {})
                schema = json_content.get('schema', {})
                request_type = _extract_schema_name(schema)
                if request_type:
                    used_models.add(request_type)
            
            # Extraer tipo de response
            responses = operation.get('responses', {})
            response_type = None
            success_response = responses.get('200') or responses.get('201')
            if success_response:
                content = success_response.get('content', {})
                json_content = content.get('application/json', {})
                schema = json_content.get('schema', {})
                response_type = _extract_schema_name(schema)
                if response_type:
                    used_models.add(response_type)
            
            # Construir parámetros del método
            params = ["self"]
            args_doc = []
            
            if request_type:
                params.append(f"request: '{request_type}'")
                args_doc.append(f"request: Datos del request ({request_type})")
            
            params.append("timeout: float | None = None")
            args_doc.append("timeout: Timeout específico para esta request")
            
            # Tipo de retorno con quotes para forward reference
            return_type = f"'{response_type}'" if response_type else "dict[str, Any]"
            
            # Construir el cuerpo del método
            method_lines = []
            
            # Import local
            if response_type:
                method_lines.append(f"from .models import {response_type}")
                method_lines.append("")
            
            if request_type:
                # Con request body
                method_lines.append("# Serializar request con Pydantic")
                method_lines.append("request_data = request.model_dump(mode=\"json\", exclude_none=True)")
                method_lines.append("")
                method_lines.append(f"response = self._client.{http_method.lower()}(")
                method_lines.append(f'    "{path}",')
                method_lines.append("    json=request_data,")
                method_lines.append("    timeout=timeout,")
                method_lines.append(")")
            else:
                # Sin request body
                method_lines.append(f"response = self._client.{http_method.lower()}(")
                method_lines.append(f'    "{path}",')
                method_lines.append("    timeout=timeout,")
                method_lines.append(")")
            
            method_lines.append("response.raise_for_status()")
            method_lines.append("")
            
            if response_type:
                method_lines.append("# Deserializar y validar con Pydantic")
                method_lines.append(f"return {response_type}.model_validate(response.json())")
            else:
                method_lines.append("return response.json()")
            
            method_body = "\n        ".join(method_lines)
            
            # Generar método completo
            params_str = ",\n        ".join(params)
            args_doc_str = "\n            ".join(args_doc)
            
            method_code = f'''
    def {method_name}(
        {params_str},
    ) -> {return_type}:
        """{description if description else summary}
        
        Args:
            {args_doc_str}
            
        Returns:
            {"Modelo " + response_type + " con la respuesta tipada" if response_type else "Respuesta del API"}
        """
        {method_body}
'''
            methods.append(method_code)
    
    return '\n'.join(methods), used_models


def _create_basic_structure(
    output_dir: Path,
    package_name: str,
    package_version: str,
) -> None:
    """Crea estructura básica cuando se usa el cliente integrado."""
    print(f"Creando estructura básica del SDK...")
    
    package_dir = output_dir / package_name
    package_dir.mkdir(parents=True, exist_ok=True)
    
    # Generar nombres
    client_class = "".join(word.capitalize() for word in package_name.split("_")) + "Client"
    package_title = " ".join(word.capitalize() for word in package_name.split("_"))
    
    # __init__.py simple que exporta desde api.py
    init_content = f'''"""SDK Cliente para {package_title} con modelos Pydantic v2.

Este SDK utiliza Pydantic v2 para validación automática de datos.
Generado automáticamente con datamodel-code-generator[http].
"""

# Los modelos y cliente están en api.py (generado automáticamente)
from .api import *  # noqa: F403

__version__ = "{package_version}"
'''
    (package_dir / "__init__.py").write_text(init_content, encoding="utf-8")
    
    # pyproject.toml
    pyproject_content = f'''[project]
name = "{package_name}"
version = "{package_version}"
description = "SDK Cliente con Pydantic v2 (generado con datamodel-code-generator)"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
aws = [
    "boto3>=1.35.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
'''
    (output_dir / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
    print("  * Creado pyproject.toml")
    
    # README básico
    readme_content = f'''# {package_name}

SDK generado automáticamente con **datamodel-code-generator[http]** y **Pydantic v2**.

## Instalación

```bash
pip install {package_name}
```

## Uso

```python
from {package_name} import *

# Los modelos y cliente HTTP están disponibles automáticamente
```

## Versión

**{package_version}**
'''
    (output_dir / "README.md").write_text(readme_content, encoding="utf-8")
    print("  * Creado README.md")


def _create_client_structure(
    output_dir: Path,
    package_name: str,
    package_version: str,
    spec_path: Path,
) -> None:
    """Crea la estructura del cliente HTTP con soporte para Pydantic."""
    print(f"Creando estructura del SDK cliente...")

    package_dir = output_dir / package_name
    package_dir.mkdir(parents=True, exist_ok=True)

    # Generar nombre de clase del cliente desde el nombre del paquete
    # Ej: cortex_embeddings -> CortexEmbeddingsClient
    client_class = "".join(word.capitalize() for word in package_name.split("_")) + "Client"
    
    # Título legible del paquete
    package_title = " ".join(word.capitalize() for word in package_name.split("_"))

    # Crear __init__.py principal
    init_content = _render_template(
        "__init__.py.template",
        version=package_version,
        package_name=package_name,
        package_title=package_title,
        client_class=client_class,
    )
    (package_dir / "__init__.py").write_text(init_content, encoding="utf-8")

    # Generar métodos dinámicos desde OpenAPI spec
    dynamic_methods, used_models = _generate_client_methods(spec_path)


    print(dynamic_methods)
    
    # Crear imports de modelos para TYPE_CHECKING
    model_imports = ", ".join(sorted(used_models)) if used_models else ""
    
    # Crear client.py
    client_content = _render_template(
        "client.py.template",
        package_name=package_name,
        package_title=package_title,
        client_class=client_class,
    )
    
    # Agregar imports de modelos en TYPE_CHECKING
    if model_imports:
        client_content = client_content.replace(
            "if TYPE_CHECKING:\n    # Los tipos de modelos se importan dinámicamente en cada método\n    pass",
            f"if TYPE_CHECKING:\n    from .models import {model_imports}"
        )
    
    # Insertar métodos dinámicos antes del final de la clase
    # Reemplazar el comentario placeholder con los métodos generados
    client_content = client_content.replace(
        "    # Métodos específicos del API se pueden agregar aquí\n    # o extender este cliente según necesidades",
        dynamic_methods.rstrip()
    )
    
    (package_dir / "client.py").write_text(client_content, encoding="utf-8")

    # Copiar config.py del template existente
    script_dir = Path(__file__).parent
    config_template = script_dir / "sdk_templates" / "config.py.template"
    
    # Generar nombre de clase y variable de entorno
    client_class = "".join(word.capitalize() for word in package_name.split("_")) + "Client"
    env_var = package_name.upper() + "_BASE_URL"
    print(client_class)
    if config_template.exists():
        # Leer template y renderizar con parámetros
        config_template_content = config_template.read_text(encoding="utf-8")
        config_content = config_template_content.format(
            client_class=client_class,
            env_var=env_var,
        )
        (package_dir / "config.py").write_text(config_content, encoding="utf-8")
        print("  * Generado config.py desde template")
    else:
        # Crear config.py básico
        config_content = f'''"""Configuración del SDK desde variables de entorno."""

from __future__ import annotations

import os
from typing import Any

from .client import {client_class}


def get_base_url() -> str:
    """Obtiene la URL base desde variable de entorno.
    
    Returns:
        URL desde {env_var} o default localhost
    """
    return os.getenv("{env_var}", "http://localhost:8000")


def create_client(
    base_url: str | None = None,
    timeout: float = 30.0,
    verify_ssl: bool = True,
    **kwargs: Any,
) -> {client_class}:
    """Crea un cliente usando configuración de entorno.
    
    Args:
        base_url: URL base (opcional, usa env var si no se provee)
        timeout: Timeout en segundos
        verify_ssl: Si verificar certificados SSL
        **kwargs: Argumentos adicionales para httpx.Client
    
    Returns:
        Cliente configurado y listo para usar
    
    Examples:
        >>> import os
        >>> os.environ["{env_var}"] = "https://api.example.com"
        >>> client = create_client()
        >>> # O con URL explícita:
        >>> client = create_client(base_url="https://other-api.example.com")
    """
    url = base_url or get_base_url()
    return {client_class}(
        base_url=url,
        timeout=timeout,
        verify_ssl=verify_ssl,
        **kwargs,
    )
'''
        (package_dir / "config.py").write_text(config_content, encoding="utf-8")
        print("  * Creado config.py básico")

    # Crear pyproject.toml para el paquete
    pyproject_content = f'''[project]
name = "{package_name}"
version = "{package_version}"
description = "SDK Cliente para Cortex Rules con Pydantic v2"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0",
    "httpx>=0.27.0",
    "httpx-aws-auth>=4.1.1",
]

[project.optional-dependencies]
aws = [
    "boto3>=1.35.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
'''

    (output_dir / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
    print("  * Creado pyproject.toml")

    # Crear README
    env_var = package_name.upper() + "_BASE_URL"
    readme_content = _render_template(
        "README.md.template",
        package_name=package_name,
        package_version=package_version,
        env_var=env_var,
    )
    (output_dir / "README.md").write_text(readme_content, encoding="utf-8")
    print("  * Creado README.md")


def generate_sdk_pydantic(
    spec_path: Path,
    output_dir: Path,
    package_name: str,
    package_version: str,
    overwrite: bool,
    regenerate_spec: bool = False,
    base_url: str | None = None,
    use_integrated_client: bool = False,
) -> None:
    """Genera un SDK completo con Pydantic v2.
    
    Args:
        use_integrated_client: Si True, usa el cliente HTTP generado por datamodel-code-generator.
                              Si False, usa el cliente personalizado del template.
    """
    # Verificar que datamodel-codegen esté instalado
    if not _check_datamodel_codegen():
        raise RuntimeError(
            "datamodel-code-generator no está instalado.\n"
            "Instálalo con: pip install 'datamodel-code-generator[http]'\n"
            "O agrega al pyproject.toml: datamodel-code-generator>=0.25.0"
        )

    spec_path_resolved = spec_path

    if output_dir.exists():
        if overwrite:
            shutil.rmtree(output_dir)
            print(f"Eliminado directorio existente: {output_dir}")
        else:
            raise FileExistsError(
                f"El directorio de salida {output_dir} ya existe. "
                "Usa --overwrite para reemplazarlo."
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    package_dir = output_dir / package_name
    package_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerando SDK Pydantic en: {output_dir}")

    if use_integrated_client:
        # Usar cliente integrado de datamodel-code-generator
        print("Modo: Cliente HTTP integrado de datamodel-code-generator")
        _generate_pydantic_models_and_client(spec_path_resolved, package_dir, generate_http_client=True)
        
        # Crear estructura básica sin client.py personalizado
        _create_basic_structure(output_dir, package_name, package_version)
    else:
        # Usar cliente personalizado del template
        print("Modo: Cliente HTTP personalizado con templates")
        _create_client_structure(output_dir, package_name, package_version, spec_path_resolved)
        
        # Generar solo modelos
        _generate_pydantic_models_and_client(spec_path_resolved, package_dir, generate_http_client=False)
        _add_dto_aliases(package_dir / "models.py")

    print(f"\nSDK Pydantic v2 generado exitosamente!")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Genera SDK Python para Cortex Rules con Pydantic v2 desde OpenAPI."
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=Path("build/openapi.json"),
        help="Ruta al archivo OpenAPI (default: build/openapi.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/sdk/python/cortex_embeddings_sdk"),
        help="Directorio de salida para el SDK",
    )
    parser.add_argument(
        "--package-name",
        default="cortex_embeddings_sdk",
        help="Nombre del paquete Python (default: cortex_embeddings_sdk)",
    )
    parser.add_argument(
        "--package-version",
        default="0.1.0",
        help="Versión del paquete (default: 0.1.0)",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("CORTEX_RULE_ENGINE_BASE_URL"),
        help="URL base del API (default: variable de entorno)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescribe el directorio de salida si existe",
    )
    parser.add_argument(
        "--skip-openapi",
        action="store_true",
        help="Omite la regeneración de la especificación OpenAPI",
    )
    parser.add_argument(
        "--use-integrated-client",
        action="store_true",
        help="Usa el cliente HTTP generado por datamodel-code-generator (experimental)",
    )
    return parser.parse_args(argv)


def generate(
    spec: Path,
    output_dir: Path,
    version: str,
    overwrite: bool,
) -> None:
    """Punto de entrada principal."""

    base_url = None
    package_name = "cortex_embeddings_sdk"

    print(output_dir.resolve())

    try:
        generate_sdk_pydantic(
            spec_path=spec,
            output_dir=output_dir,
            package_name=package_name,
            package_version=version,
            overwrite=overwrite,
        )
        print(f"\nSDK generado en: {output_dir.resolve()}")
        if base_url:
            print(f"URL base configurada: {base_url}")
        print("Usando Pydantic v2 para validación automática")

        install_path = output_dir.resolve()
        print("\nInstalación editable:")
        print(f"   pip install -e \"{install_path}\"")
        print("\nImportar en tus scripts:")
        print(f"   from {package_name} import create_client")

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
