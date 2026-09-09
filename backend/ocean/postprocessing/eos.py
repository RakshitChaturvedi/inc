import torch

def linear_eos(
        temperature: torch.Tensor,
        salinity: torch.Tensor,
        rho0: float = 1027.0,
        alpha: float = 0.15,
        beta: float = 0.78
) -> torch.Tensor:
    """
    Simplified differential equation of state (eos), computes density from temp and salinity.
    rho = rho0 - alpha*T + beta*S
    """
    return rho0 - (alpha*temperature) + (beta*salinity)