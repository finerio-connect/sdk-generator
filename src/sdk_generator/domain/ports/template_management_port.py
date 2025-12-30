from abc import ABC, abstractmethod
from typing import Any


class TemplateManagementPort(ABC):

    @abstractmethod
    def render_template(self, template_name: str, **context: Any) -> str:
        raise NotImplementedError
