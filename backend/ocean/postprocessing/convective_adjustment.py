from __future__ import annotations

import torch

from .eos import linear_eos


# ---------------------------------------------------------------------------
# OceanEmbed Convective Adjustment Contract
# ---------------------------------------------------------------------------

MAX_PASSES = 15
DENSITY_INVERSION_TOLERANCE = 1e-6

# Layer thicknesses corresponding to the 15 model depth levels:
#
# depth levels:
# 0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000 m
#
# These are intentionally preserved exactly from the training implementation.
DZ = torch.tensor(
    [
        5,
        5,
        10,
        10,
        20,
        25,
        25,
        25,
        25,
        50,
        100,
        200,
        200,
        300,
        300,
    ],
    dtype=torch.float32,
)


def calculate_inversion_statistics(
    t_profiles,
    s_profiles,
    valid_mask,
    tolerance: float = DENSITY_INVERSION_TOLERANCE,
):
    """
    Calculate static-density inversion statistics.

    Parameters
    ----------
    t_profiles : torch.Tensor or array-like
        Shape [N, 15].

    s_profiles : torch.Tensor or array-like
        Shape [N, 15].

    valid_mask : torch.Tensor or array-like
        Boolean shape [N, 15].
        True means the corresponding depth cell is valid ocean data.

    tolerance : float
        Density inversion tolerance.

    Returns
    -------
    dict
        layer_rate
        column_rate
        aggregate_severity
    """

    t = torch.as_tensor(t_profiles, dtype=torch.float32)
    s = torch.as_tensor(s_profiles, dtype=torch.float32)
    mask = torch.as_tensor(valid_mask, dtype=torch.bool)

    if t.numel() == 0:
        return {
            "layer_rate": 0.0,
            "column_rate": 0.0,
            "aggregate_severity": 0.0,
        }

    if t.ndim != 2 or t.shape[1] != 15:
        raise ValueError(
            f"Expected temperature profiles [N, 15], got {tuple(t.shape)}"
        )

    if s.shape != t.shape:
        raise ValueError(
            f"Temperature/salinity shape mismatch: "
            f"{tuple(t.shape)} vs {tuple(s.shape)}"
        )

    if mask.shape != t.shape:
        raise ValueError(
            f"Valid-mask shape mismatch: "
            f"{tuple(mask.shape)} vs {tuple(t.shape)}"
        )

    density = linear_eos(t, s)

    # Positive delta rho means density increases downward.
    delta_rho = torch.diff(density, dim=1)

    valid_transitions = mask[:, 1:] & mask[:, :-1]

    inversion_mask = (
        (delta_rho < -tolerance)
        & valid_transitions
    )

    total_pairs = valid_transitions.sum().item()
    inversion_count = inversion_mask.sum().item()

    layer_rate = (
        inversion_count / total_pairs * 100.0
        if total_pairs > 0
        else 0.0
    )

    valid_columns_mask = valid_transitions.any(dim=1)

    total_valid_columns = valid_columns_mask.sum().item()

    inverted_columns = (
        inversion_mask.any(dim=1)
        & valid_columns_mask
    )

    column_rate = (
        inverted_columns.sum().item()
        / total_valid_columns
        * 100.0
        if total_valid_columns > 0
        else 0.0
    )

    inversion_magnitudes = torch.abs(
        delta_rho[inversion_mask]
    )

    aggregate_severity = (
        inversion_magnitudes.sum().item() / total_pairs
        if total_pairs > 0
        else 0.0
    )

    return {
        "layer_rate": layer_rate,
        "column_rate": column_rate,
        "aggregate_severity": aggregate_severity,
    }


def apply_convective_adjustment(
    t_profiles,
    s_profiles,
    valid_mask,
    *,
    max_passes: int = MAX_PASSES,
    tolerance: float = DENSITY_INVERSION_TOLERANCE,
):
    """
    Apply OceanEmbed's training-time pairwise convective adjustment.

    This is the same algorithm used during Phase 16 evaluation.

    Parameters
    ----------
    t_profiles : torch.Tensor or array-like
        Temperature profiles, shape [N, 15].

    s_profiles : torch.Tensor or array-like
        Salinity profiles, shape [N, 15].

    valid_mask : torch.Tensor or array-like
        Boolean ocean-validity mask, shape [N, 15].

    max_passes : int
        Maximum number of iterative adjustment passes.

    tolerance : float
        Density inversion tolerance.

    Returns
    -------
    tuple
        (
            adjusted_temperature,
            adjusted_salinity,
            passes_run,
            fraction_touched_percent,
        )

    Notes
    -----
    The operation is depth-weighted using DZ and conserves the
    pairwise weighted mean of temperature and salinity.

    Only adjacent valid inverted pairs are mixed.
    """

    t_adj = torch.as_tensor(
        t_profiles,
        dtype=torch.float32,
    ).clone()

    s_adj = torch.as_tensor(
        s_profiles,
        dtype=torch.float32,
    ).clone()

    mask = torch.as_tensor(
        valid_mask,
        dtype=torch.bool,
    )

    if t_adj.ndim != 2 or t_adj.shape[1] != 15:
        raise ValueError(
            f"Expected temperature profiles [N, 15], "
            f"got {tuple(t_adj.shape)}"
        )

    if s_adj.shape != t_adj.shape:
        raise ValueError(
            f"Temperature/salinity shape mismatch: "
            f"{tuple(t_adj.shape)} vs {tuple(s_adj.shape)}"
        )

    if mask.shape != t_adj.shape:
        raise ValueError(
            f"Valid-mask shape mismatch: "
            f"{tuple(mask.shape)} vs {tuple(t_adj.shape)}"
        )

    if max_passes <= 0:
        raise ValueError("max_passes must be > 0")

    # Track every depth cell that has been mathematically modified.
    touched = torch.zeros_like(
        mask,
        dtype=torch.bool,
    )

    dz = DZ.to(
        device=t_adj.device,
        dtype=t_adj.dtype,
    )

    passes_run = 0

    for _ in range(max_passes):

        density = linear_eos(
            t_adj,
            s_adj,
        )

        delta_rho = (
            density[:, 1:]
            - density[:, :-1]
        )

        inversion_mask = (
            (delta_rho < -tolerance)
            & mask[:, 1:]
            & mask[:, :-1]
        )

        # Entire batch is stable.
        if not inversion_mask.any():
            break

        passes_run += 1

        # ---------------------------------------------------------------
        # Pairwise mixing.
        #
        # We preserve the exact parity ordering from training:
        #
        # parity 0 -> pairs (0,1), (2,3), ...
        # parity 1 -> pairs (1,2), (3,4), ...
        #
        # This avoids simultaneously mixing overlapping pairs.
        # ---------------------------------------------------------------

        for parity in (0, 1):

            for z in range(parity, 14, 2):

                rho_z = linear_eos(
                    t_adj[:, z],
                    s_adj[:, z],
                )

                rho_z1 = linear_eos(
                    t_adj[:, z + 1],
                    s_adj[:, z + 1],
                )

                is_inverted = (
                    (rho_z > rho_z1 + tolerance)
                    & mask[:, z]
                    & mask[:, z + 1]
                )

                if not is_inverted.any():
                    continue

                w1 = dz[z]
                w2 = dz[z + 1]
                w_total = w1 + w2

                # Depth-weighted pairwise mixing.
                t_mix = (
                    t_adj[:, z] * w1
                    + t_adj[:, z + 1] * w2
                ) / w_total

                s_mix = (
                    s_adj[:, z] * w1
                    + s_adj[:, z + 1] * w2
                ) / w_total

                t_adj[:, z] = torch.where(
                    is_inverted,
                    t_mix,
                    t_adj[:, z],
                )

                t_adj[:, z + 1] = torch.where(
                    is_inverted,
                    t_mix,
                    t_adj[:, z + 1],
                )

                s_adj[:, z] = torch.where(
                    is_inverted,
                    s_mix,
                    s_adj[:, z],
                )

                s_adj[:, z + 1] = torch.where(
                    is_inverted,
                    s_mix,
                    s_adj[:, z + 1],
                )

                # Record which cells were actually overwritten.
                touched[:, z] |= is_inverted
                touched[:, z + 1] |= is_inverted

    total_valid = mask.sum().item()

    total_touched = (
        touched & mask
    ).sum().item()

    fraction_touched_percent = (
        total_touched / total_valid * 100.0
        if total_valid > 0
        else 0.0
    )

    return (
        t_adj,
        s_adj,
        passes_run,
        fraction_touched_percent,
    )