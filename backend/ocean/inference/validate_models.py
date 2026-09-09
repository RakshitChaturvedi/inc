from __future__ import annotations

import json
from pathlib import Path

import torch

from .oceanembed import OceanEmbedModel


ROOT = Path(__file__).resolve().parents[2]

REGISTRY = ROOT / "model-registry" / "oceanembed-v1.0.0"


def main() -> None:
    print("=" * 70)
    print("OceanEmbed — Model Registry Validation")
    print("=" * 70)

    manifest_path = REGISTRY / "manifest.json"

    with manifest_path.open() as f:
        manifest = json.load(f)

    members = manifest["ensemble"]["members"]

    if len(members) != 5:
        raise RuntimeError(
            f"Expected 5 ensemble members, found {len(members)}"
        )

    print(f"\nEnsemble size: {len(members)}")

    for member in members:
        member_id = member["member"]
        path = REGISTRY / member["path"]

        print(f"\nMember {member_id}")
        print(f"  fold : {member['fold']}")
        print(f"  seed : {member['seed']}")
        print(f"  path : {path}")

        if not path.exists():
            raise RuntimeError(f"Checkpoint missing: {path}")

        # Instantiate exactly the same architecture used during training.
        model = OceanEmbedModel(
            in_channels=12,
            use_cbam=True
        )

        checkpoint = torch.load(
            path,
            map_location="cpu",
            weights_only=False,
        )

        if not isinstance(checkpoint, dict):
            raise RuntimeError(
                f"Member {member_id}: checkpoint is not a dictionary"
            )

        if "model_state_dict" not in checkpoint:
            raise RuntimeError(
                f"Member {member_id}: missing 'model_state_dict'"
            )

        state_dict = checkpoint["model_state_dict"]

        expected = model.state_dict()

        missing = [
            key for key in expected
            if key not in state_dict
        ]

        unexpected = [
            key for key in state_dict
            if key not in expected
        ]

        if missing:
            raise RuntimeError(
                f"Member {member_id}: missing keys:\n{missing}"
            )

        if unexpected:
            raise RuntimeError(
                f"Member {member_id}: unexpected keys:\n{unexpected}"
            )

        model.load_state_dict(
            state_dict,
            strict=True,
        )

        model.eval()

        print(f"  parameters : {len(state_dict)}")
        print("  state dict : PASS")

    print("\n" + "=" * 70)
    print("ALL FIVE MODELS VALID")
    print("=" * 70)


if __name__ == "__main__":
    main()