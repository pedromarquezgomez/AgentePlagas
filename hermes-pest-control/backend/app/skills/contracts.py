from typing import Literal

from pydantic import BaseModel, Field


SkillRiskLevel = Literal["low", "medium", "high"]


class ProductSkill(BaseModel):
    name: str
    description: str
    allowed_outputs: list[str] = Field(default_factory=list)
    forbidden_effects: list[str] = Field(default_factory=list)
    risk_level: SkillRiskLevel = "low"
    requires_backend_service: bool = True
    instructions: str

    def as_prompt_section(self) -> str:
        allowed = ", ".join(self.allowed_outputs) or "none"
        forbidden = ", ".join(self.forbidden_effects) or "none"
        return "\n".join(
            [
                f"## {self.name}",
                self.description,
                f"Allowed outputs: {allowed}.",
                f"Forbidden effects: {forbidden}.",
                f"Risk level: {self.risk_level}.",
                f"Requires backend service: {self.requires_backend_service}.",
                self.instructions,
            ]
        )

    @classmethod
    def from_markdown_file(cls, file_path: str) -> "ProductSkill":
        import yaml
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if content.strip().startswith("---"):
            # Quitar espacios vacíos iniciales y dividir por '---'
            parts = content.strip().split("---", 2)
            if len(parts) >= 3:
                metadata_yaml = parts[1]
                instructions = parts[2].strip()
                metadata = yaml.safe_load(metadata_yaml) or {}
                return cls(
                    name=metadata.get("name", ""),
                    description=metadata.get("description", ""),
                    allowed_outputs=metadata.get("allowed_outputs", []),
                    forbidden_effects=metadata.get("forbidden_effects", []),
                    risk_level=metadata.get("risk_level", "low"),
                    requires_backend_service=metadata.get("requires_backend_service", True),
                    instructions=instructions,
                )
        raise ValueError(f"Falta el formato frontmatter YAML en el archivo: {file_path}")

