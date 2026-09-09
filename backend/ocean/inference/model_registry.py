import json
from pathlib import Path

class ModelRegistry:
    def __init__(self, registry_root: str | Path):
        self.registry_root = Path(registry_root).resolve()
        self.manifest_path = self.registry_root / "manifest.json"
        
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found at {self.manifest_path}")
            
        with open(self.manifest_path, "r") as f:
            self.manifest = json.load(f)

    @property
    def architecture_config(self) -> dict:
        """Returns the architecture params (e.g., in_channels=12, cbam=true)"""
        return self.manifest["architecture"]

    @property
    def ensemble_members(self) -> list[dict]:
        """Returns the list of 5 members and their relative paths"""
        return self.manifest["ensemble"]["members"]

    def get_checkpoint_path(self, relative_path: str) -> Path:
        """Resolves the absolute path to a specific .pt file"""
        checkpoint_path = self.registry_root / relative_path
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Missing checkpoint: {checkpoint_path}")
        return checkpoint_path