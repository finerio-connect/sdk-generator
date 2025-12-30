from abc import ABC, abstractmethod


class OpenApiGeneratorUtilsPort(ABC):

    @staticmethod
    def extract_schema_name(schema_ref: dict) -> str | None:
        """Extrae el nombre del modelo desde un $ref."""
        if isinstance(schema_ref, dict) and '$ref' in schema_ref:
            # #/components/schemas/ModelName -> ModelName
            return schema_ref['$ref'].split('/')[-1]
        return None

    @staticmethod
    def clean_method_name(operation_id: str, path: str, http_method: str) -> str:
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
