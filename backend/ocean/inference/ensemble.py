import torch
import numpy as np
from .oceanembed import OceanEmbedModel

def run_ensemble_inference(
    models: list[OceanEmbedModel], 
    input_array: np.ndarray, 
    device: torch.device
) -> tuple[np.ndarray, np.ndarray]:
    """
    Runs the preprocessed input through all 5 models.
    Returns stacked numpy arrays of shape [5, 15, 101, 241] for both T and S.
    """
    print("\n[B5] Running 5-Model Ensemble Inference...")
    
    # Convert the [1, 12, 101, 241] numpy array back to a PyTorch tensor
    x = torch.from_numpy(input_array).to(device)
    
    t_predictions = []
    s_predictions = []
    
    with torch.no_grad():
        for i, model in enumerate(models):
            # Forward pass
            t_pred, s_pred = model(x)
            
            # Remove batch dim and move to CPU numpy: [15, 101, 241]
            t_predictions.append(t_pred.squeeze(0).cpu().numpy())
            s_predictions.append(s_pred.squeeze(0).cpu().numpy())
            
    # Stack into [5, 15, 101, 241] arrays
    t_members = np.stack(t_predictions, axis=0)
    s_members = np.stack(s_predictions, axis=0)
    
    print(f"     -> Inference complete. T shape: {t_members.shape}, S shape: {s_members.shape}")
    
    return t_members, s_members