import torch
import torch.nn as nn

class EncoderStage(nn.Module):
    # single downsampling stage of u-net encoder.
    # contract: conv -> bn -> elu -> conv -> bn -> elu -> cbam -> skip -> maxpool
    def __init__(
            self,
            in_channels: int,
            out_channels: int,
            attention_block=None
    ):
        super().__init__()

        # double conv block
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ELU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ELU(inplace=True)
        )

        # inject cbam dynamically, or default to identity
        if attention_block is not None:
            self.attention = attention_block(out_channels)
        else:
            self.attention = nn.Identity()

        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        # 1. feature extraction
        features = self.double_conv(x)
        # 2. attention mechanism
        skip = self.attention(features)
        # 3. downsample 
        downsampled = self.pool(skip)

        return skip, downsampled

class Encoder(nn.Module):
    # full 4-stage encoder
    # channel progression: 12-64-128-256-512

    def __init__(self, in_channels: int = 12, attention_block=None):
        super().__init__()

        self.stage1 = EncoderStage(in_channels, 64, attention_block)
        self.stage2 = EncoderStage(64, 128, attention_block)
        self.stage3 = EncoderStage(128, 256, attention_block)
        self.stage4 = EncoderStage(256, 512, attention_block)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, tuple]:
        skip1, x = self.stage1(x)
        skip2, x = self.stage2(x)
        skip3, x = self.stage3(x)
        skip4, x = self.stage4(x)

        latent = x
        skips = (skip1, skip2, skip3, skip4)

        return latent, skips