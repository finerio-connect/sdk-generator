#!/usr/bin/env python3
"""Generador de SDK para Cortex Rules con Pydantic v2.

Este script genera un SDK cliente completo con modelos Pydantic v2 desde
la especificación OpenAPI, incluyendo validación automática de tipos y valores.

Utiliza datamodel-code-generator para generar modelos Pydantic v2 nativos.
"""

from __future__ import annotations

import argparse
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


def _generate_pydantic_models(
        spec_path: Path,
        package_dir: Path,
) -> None:
    """Genera modelos Pydantic v2 desde OpenAPI usando datamodel-code-generator."""
    print(f"Generando modelos Pydantic v2 desde {spec_path.name}...")

    models_file = package_dir / "models.py"

    # Comando para generar modelos Pydantic v2
    command = [
        "datamodel-codegen",
        "--input",
        str(spec_path),
        "--output",
        str(models_file),
        "--input-file-type",
        "openapi",
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--field-constraints",  # Genera constraints (min, max, etc)
        "--use-standard-collections",  # Usa list, dict en vez de List, Dict
        "--use-union-operator",  # Usa | en vez de Union
        "--target-python-version",
        "3.12",
        "--snake-case-field",  # Nombres de campos en snake_case
        "--allow-extra-fields",  # Permite campos adicionales (important!)
        "--use-default-kwarg",  # Usa default= en vez de Field(default=...)
        "--enable-faux-immutability",  # Hace los modelos más seguros
        "--use-annotated",  # Usa Annotated para constraints
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
        print("  * Modelos Pydantic v2 generados")
        if result.stdout:
            print(f"     {result.stdout.strip()}")
    except subprocess.CalledProcessError as exc:
        print(f"  ERROR generando modelos: {exc.stderr}")
        raise RuntimeError(
            f"Falló la generación de modelos con datamodel-code-generator:\n{exc.stderr}"
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


def _create_client_structure(
        output_dir: Path,
        package_name: str,
        package_version: str,
) -> None:
    """Crea la estructura del cliente HTTP con soporte para Pydantic."""
    print(f"Creando estructura del SDK cliente...")

    package_dir = output_dir / package_name
    package_dir.mkdir(parents=True, exist_ok=True)

    # Crear __init__.py principal
    init_content = _render_template("__init__.py.template", version=package_version)
    (package_dir / "__init__.py").write_text(init_content, encoding="utf-8")

    # Crear client.py
    client_content = _render_template("client.py.template")
    (package_dir / "client.py").write_text(client_content, encoding="utf-8")

    # Copiar config.py del template existente
    script_dir = Path(__file__).parent
    config_template = script_dir / "sdk_templates" / "config.py.template"

    if config_template.exists():
        shutil.copy(str(config_template), str(package_dir / "config.py"))
        print("  * Copiado config.py con soporte AWS IAM")
    else:
        # Crear config.py básico
        config_content = '''"""Configuración del SDK desde variables de entorno."""

from __future__ import annotations

import os
from typing import Any

from .client import CortexRulesClient


def get_base_url() -> str:
    """Obtiene la URL base desde variable de entorno.

    Returns:
        URL desde CORTEX_RULE_ENGINE_BASE_URL o default localhost
    """
    return os.getenv("CORTEX_RULE_ENGINE_BASE_URL", "http://localhost:8000")


def create_client(
    base_url: str | None = None,
    timeout: float = 30.0,
    verify_ssl: bool = True,
    **kwargs: Any,
) -> CortexRulesClient:
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
        >>> os.environ["CORTEX_RULE_ENGINE_BASE_URL"] = "https://api.example.com"
        >>> client = create_client()
        >>> # O con URL explícita:
        >>> client = create_client(base_url="https://other-api.example.com")
    """
    url = base_url or get_base_url()
    return CortexRulesClient(
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
    readme_content = _render_template(
        "README.md.template",
        package_name=package_name,
        package_version=package_version,
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
) -> None:
    """Genera un SDK completo con Pydantic v2."""
    # Verificar que datamodel-codegen esté instalado
    if not _check_datamodel_codegen():
        raise RuntimeError(
            "datamodel-code-generator no está instalado.\n"
            "Instálalo con: pip install 'datamodel-code-generator[http]'\n"
            "O agrega al pyproject.toml: datamodel-code-generator>=0.25.0"
        )

    # spec_path_resolved = _ensure_openapi_spec(spec_path, regenerate_spec)

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

    # Crear estructura del cliente primero (crea el package_dir)
    _create_client_structure(output_dir, package_name, package_version)

    # Generar modelos Pydantic v2
    _generate_pydantic_models(spec_path, package_dir)
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
        default=Path("build/sdk/python/cortex_rules_sdk"),
        help="Directorio de salida para el SDK",
    )
    parser.add_argument(
        "--package-name",
        default="cortex_rules_sdk",
        help="Nombre del paquete Python (default: cortex_rules_sdk)",
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
    return parser.parse_args(argv)


def generate(
        spec: Path,
        output_dir: Path,
        version: str,
        overwrite: bool,
) -> None:
    """Punto de entrada principal."""

    base_url = None
    package_name = "cortex_rules_sdk"

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
