import torch
import torch.nn as nn
import torch.nn.functional as F

class DecoderStage(nn.Module):
    # single upsampling and concatenation stage
    # upsample -> dynamic pad -> concat -> double conv -> output

    def __init__(self, in_channels: int, skip_channels: int, out_channels: int):
        super().__init__()

        # 1. upsampling (bilinear, no learned params)
        self.upsample = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False)

        # 2. double conv, accepts concatenated depth: in + skip
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels + skip_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ELU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ELU(inplace=True)
        )

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        # 1. upsample
        x=self.upsample(x)

        # 2. dynamic spatial padding, calc how much padding is needed to match skip connection
        diff_y = skip.shape[2] - x.shape[2]
        diff_x = skip.shape[3] - x.shape[3]

        # (left, right, top, bottom)
        # split padding symmetrically 
        x = F.pad(x, [
            diff_x//2, diff_x-diff_x//2,
            diff_y//2, diff_y-diff_y//2
        ])

        # 3. concat along channel dimension
        x = torch.cat([x, skip], dim=1)
        return self.double_conv(x)

class Decoder(nn.Module):
    # full 4 stage decoder. Terminates in 1x1 convolution yielding 15 depth layers

    def __init__(self):
        super().__init__()

        self.stage1 = DecoderStage(512, 512, 512)
        self.stage2 = DecoderStage(512, 256, 256)
        self.stage3 = DecoderStage(256, 128, 128)
        self.stage4 = DecoderStage(128, 64, 64)

        self.final_conv = nn.Conv2d(64, 15, kernel_size=1)

    def forward(self, x: torch.Tensor, skips: tuple) -> torch.Tensor:
        skip1, skip2, skip3, skip4 = skips

        # consume in reverse order
        x = self.stage1(x, skip4)
        x = self.stage2(x, skip3)
        x = self.stage3(x, skip2)
        x = self.stage4(x, skip1)

        return self.final_conv(x)
