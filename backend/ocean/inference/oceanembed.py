import torch
import torch.nn as nn

from .encoder import Encoder
from .cbam import CBAM
from .bottleneck import Bottleneck
from .decoder import Decoder

class OceanEmbedModel(nn.Module):
    # complete architecture, Physics-informed, dual-head attention u-net
    def __init__(self, in_channels: int = 12, use_cbam: bool = True):
        super().__init__()
        
        attn_block = CBAM if use_cbam else None

        self.encoder = Encoder(in_channels=in_channels, attention_block=attn_block)
        self.bottleneck = Bottleneck(channels=512, attention_block=attn_block)

        self.temp_decoder = Decoder()
        self.salinity_decoder = Decoder()

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        latent, skips = self.encoder(x)
        latent = self.bottleneck(latent)

        temperature = self.temp_decoder(latent, skips)
        salinity = self.salinity_decoder(latent, skips)

        return temperature, salinity
