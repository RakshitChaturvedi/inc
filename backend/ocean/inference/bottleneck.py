import torch
import torch.nn as nn

class Bottleneck(nn.Module):
    # compressed latent representation bridging encoder and decoder
    # contract: [B, 512, 6, 15] -> [B, 512, 6, 15]

    def __init__(self, channels: int = 512, attention_block=None):
        super().__init__()

        self.double_conv = nn.Sequential(
            nn.Conv2d(channels, channels, kernel_size=3, padding=1, stride=1),
            nn.BatchNorm2d(channels),
            nn.ELU(inplace=True),
            nn.Conv2d(channels, channels, kernel_size=3, padding=1, stride=1),
            nn.BatchNorm2d(channels),
            nn.ELU(inplace=True)
        )

        if attention_block is not None:
            self.attention = attention_block(channels)
        else:
            self.attention = nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.double_conv(x)
        latent_out = self.attention(features)
        return latent_out
    