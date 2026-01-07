import json
import re
import subprocess
from pathlib import Path

from sdk_generator.domain.ports.open_api_generator_port import OpenApiGeneratorPort
from sdk_generator.domain.model.sdk_spec import SdkSpec
from sdk_generator.infraestructure.utils.open_api_generator_utils import OpenApiGeneratorUtilsPort
from sdk_generator.infraestructure.template_management_impl import TemplateManagementImpl


class OpenApiGeneratorImpl(OpenApiGeneratorPort, OpenApiGeneratorUtilsPort):

    def __init__(self):
        self.template_management = TemplateManagementImpl()

    def check_datamodel_codegen(self) -> bool:
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

    def generate_models(self, config: SdkSpec) -> None:
        package_dir = config.output_dir / config.package_name
        package_dir.mkdir(parents=True, exist_ok=True)
        if config.use_integrated_client:
            # Usar cliente integrado de datamodel-code-generator
            print("Modo: Cliente HTTP integrado de datamodel-code-generator")
            self._generate_pydantic_models_and_client(config.spec_path, package_dir, generate_http_client=True)

            # Crear estructura básica sin client.py personalizado
            self._create_basic_structure(config.output_dir, config.package_name, config.version)
        else:
            # Usar cliente personalizado del template
            print("Modo: Cliente HTTP personalizado con templates")
            self._create_client_structure(config.output_dir, config.package_name, config.version, config.spec_path)

            # Generar solo modelos
            self._generate_pydantic_models_and_client(config.spec_path, package_dir, generate_http_client=False)
            self._add_dto_aliases(package_dir / "models.py")

    def _generate_pydantic_models_and_client(
            self,
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

    def _create_basic_structure(
            self,
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
            self,
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
        init_content = self.template_management.render_template(
            "__init__.py.template",
            version=package_version,
            package_name=package_name,
            package_title=package_title,
            client_class=client_class,
        )
        (package_dir / "__init__.py").write_text(init_content, encoding="utf-8")

        # Generar métodos dinámicos desde OpenAPI spec
        dynamic_methods, used_models = self._generate_client_methods(spec_path)

        # Crear imports de modelos para TYPE_CHECKING
        model_imports = ", ".join(sorted(used_models)) if used_models else ""

        # Crear client.py
        client_content = self.template_management.render_template(
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
        readme_content = self.template_management.render_template(
            "README.md.template",
            package_name=package_name,
            package_version=package_version,
            env_var=env_var,
        )
        (output_dir / "README.md").write_text(readme_content, encoding="utf-8")
        print("  * Creado README.md")

    def _generate_client_methods(self, spec_path: Path) -> tuple[str, set[str]]:
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
                method_name = self.clean_method_name(operation_id, path, http_method)

                # Extraer tipo de request body
                request_body = operation.get('requestBody', {})
                request_type = None
                if request_body:
                    content = request_body.get('content', {})
                    json_content = content.get('application/json', {})
                    schema = json_content.get('schema', {})
                    request_type = self.extract_schema_name(schema)
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
                    response_type = self.extract_schema_name(schema)
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

    def _add_dto_aliases(self, models_file: Path) -> None:
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
