import yaml
from pydantic import BaseModel, Field
from .paths import get_config_path

class ProfileConfig(BaseModel):
    ssids: list[str] = Field(default_factory=list)
    username: str = ""

class AppConfig(BaseModel):
    profiles: dict[str, ProfileConfig] = Field(
        default_factory=lambda: {"iiitk": ProfileConfig(ssids=["IIITKottayam", "IIITKottayam_5G"])}
    )

def load_config() -> AppConfig:
    p = get_config_path()
    if p.exists():
        with p.open("r") as f:
            data = yaml.safe_load(f) or {}
        return AppConfig(**data)
    return AppConfig()

def save_config(config: AppConfig):
    p = get_config_path()
    with p.open("w") as f:
        yaml.safe_dump(config.model_dump(), f)
