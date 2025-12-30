from abc import ABC, abstractmethod
from sdk_generator.domain.model.sdk_spec import SdkSpec


class OpenApiGeneratorPort(ABC):
    @abstractmethod
    def generate_models(
            self,
            config: SdkSpec,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def check_datamodel_codegen(self) -> bool:
        raise NotImplementedError

