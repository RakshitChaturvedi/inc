import torch
import torch.nn as nn

class ChannelAttention(nn.Module):
    # cbam channel attention module
    
    def __init__(self, in_channels: int, reduction_ratio: int =16):
        super().__init__()

        hidden_channels = max(1, in_channels//reduction_ratio)

        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)

        # shared mlp, 1x1 to avoid flattening
        self.mlp = nn.Sequential(
            nn.Conv2d(in_channels, hidden_channels, kernel_size=1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden_channels, in_channels, kernel_size=1, bias=False)
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # 1. pool
        avg_out = self.avg_pool(x)
        max_out = self.max_pool(x)

        # 2. pass through shared mlp
        avg_attn = self.mlp(avg_out)
        max_attn = self.mlp(max_out)

        # 3. combine and activate
        channel_weights = self.sigmoid(avg_attn+max_attn)
        return x*channel_weights

class SpatialAttention(nn.Module):
    # cbam spatial attention module.

    def __init__(self, kernel_size: int = 7):
        super().__init__()

        assert kernel_size in (3,7), "Kernel size must be 3 or 7"
        padding=3 if kernel_size == 7 else 1

        self.conv = nn.Conv2d(2,1,kernel_size=kernel_size, padding=padding, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out = torch.max(x, dim=1, keepdim=True)[0]

        spatial_concat = torch.cat([avg_out, max_out], dim=1)
        spatial_weights = self.sigmoid(self.conv(spatial_concat))

        return x*spatial_weights

class CBAM(nn.Module):
    # complete convolutional block attention module.
    # applied channel attention sequentially followed by spatial attention
    
    def __init__(self, in_channels: int, reduction_ratio: int = 16, spatial_kernel_size: int = 7):
        super().__init__()
        self.channel_attention = ChannelAttention(in_channels, reduction_ratio)
        self.spatial_attention = SpatialAttention(spatial_kernel_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x_refined = self.channel_attention(x)
        x_refined = self.spatial_attention(x_refined)
        return x_refined