from pathlib import Path
from typing import Any

from sdk_generator.domain.ports.template_management_port import TemplateManagementPort


class TemplateManagementImpl(TemplateManagementPort):

    def __init__(self):
        self.TEMPLATE_DIR = Path(__file__).parent / "sdk_templates"

    def render_template(self, template_name: str, **context: Any) -> str:
        """Carga un template y reemplaza los placeholders."""
        template_path = self.TEMPLATE_DIR / template_name
        print(template_path)
        if not template_path.exists():
            raise FileNotFoundError(f"No se encontró el template {template_name}")
        template_content = template_path.read_text(encoding="utf-8")
        return template_content.format(**context)
