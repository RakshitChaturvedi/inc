import numpy as np
import torch
from pathlib import Path

# Import your inference module components
from ocean.inference.model_loader import load_ensemble
from ocean.inference.ensemble import run_ensemble_inference

def test_inference_pipeline():
    print("1. Generating mock preprocessed tensor...")
    # Expected contract shape: [Batch=1, Channels=12, Lat=101, Lon=241]
    mock_tensor = np.random.randn(1, 12, 101, 241).astype(np.float32)
    print(f"   Mock tensor shape: {mock_tensor.shape}")
    
    print("\n2. Setting up device...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"   Using device: {device}")
    
    print("\n3. Loading ensemble models...")
    # Make sure this points to your actual model-registry directory
    registry_path = Path("model-registry") 
    models = load_ensemble(registry_root=registry_path, device=device)
    
    print("\n4. Running forward pass via ensemble facade...")
    t_members, s_members = run_ensemble_inference(models, mock_tensor, device)
    
    print("\n5. Validating outputs...")
    # Expected output contract shape: [Members=5, Depths=15, Lat=101, Lon=241]
    expected_shape = (5, 15, 101, 241)
    
    if t_members.shape == expected_shape and s_members.shape == expected_shape:
        print("✅ SUCCESS! The inference module works perfectly.")
        print(f"   Temperature output shape: {t_members.shape}")
        print(f"   Salinity output shape: {s_members.shape}")
    else:
        print("❌ FAILED! Output shapes do not match the contract.")
        print(f"   Got T shape: {t_members.shape}")

if __name__ == "__main__":
    test_inference_pipeline()