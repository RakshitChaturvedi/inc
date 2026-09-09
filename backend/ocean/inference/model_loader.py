import torch
from pathlib import Path
from .oceanembed import OceanEmbedModel # Must be accessible to the backend
from .model_registry import ModelRegistry

def load_ensemble(registry_root: str | Path, device: torch.device) -> list[OceanEmbedModel]:
    """
    Loads all 5 production ensemble members into memory and sets them to eval mode.
    """
    print("\n[B2] Initializing Model Registry...")
    registry = ModelRegistry(registry_root)
    
    config = registry.architecture_config
    in_channels = config["input_channels"]
    use_cbam = config["cbam"]
    
    print(f"     -> Architecture: OceanEmbed (channels={in_channels}, CBAM={use_cbam})")
    print("     -> Loading 5 ensemble members...")
    
    models = []
    for member in registry.ensemble_members:
        # 1. Instantiate the empty architecture
        model = OceanEmbedModel(
            in_channels=in_channels, 
            use_cbam=use_cbam
        ).to(device)
        
        # 2. Load the state dict
        ckpt_path = registry.get_checkpoint_path(member["path"])
        checkpoint = torch.load(ckpt_path, map_location=device, weights_only=True)
        model.load_state_dict(checkpoint["model_state_dict"])
        
        # 3. Lock it for inference
        model.eval()
        models.append(model)
        print(f"        Loaded Seed {member['seed']} (Fold {member['fold']})")
        
    print("     -> Ensemble load complete. 5/5 valid.")
    return models