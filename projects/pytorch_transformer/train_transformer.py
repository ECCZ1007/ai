import torch
import torch.nn as nn

class SelfAttention(nn.Module):
    """Self Attention Module.
    """
    def __init__(self, embed_size: int, heads: int) -> None:
        """Initialize the Self Attention Module.
        
        Args:
            embed_size (int): The embedding size of the input.
            heads (int): The amount of heads to split the input into.
        
        Returns:
            None
        """
        super(SelfAttention, self).__init__()
        self.embed_size = embed_size
        self.heads = heads
        self.head_dim = embed_size // heads

        assert self.head_dim * self.heads == embed_size, "Embed size needs to be divisible by heads"

        self.values = nn.Linear(self.head_dim, self.head_dim, bias=False)
        self.keys = nn.Linear(self.head_dim, self.head_dim, bias=False)
        self.queries = nn.Linear(self.head_dim, self.head_dim, bias=False)
        self.fc_out = nn.Linear(heads*self.head_dim, embed_size)

    def forward(self, values: torch.Tensor, keys: torch.Tensor, query: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Forward pass of the Self Attention Module.
        
        Args:
            values (torch.Tensor): The values to be used in the attention.
            keys (torch.Tensor): The keys to be used in the attention.
            query (torch.Tensor): The query to be used in the attention.
            mask (torch.Tensor): The mask to be used in the attention.

        Returns:
            out (torch.Tensor): The output of the forward pass.
        """
        N = query.shape[0]
        value_len, key_len, query_len = values.shape[1], keys.shape[1], query.shape[1]

        values = values.reshape(N, value_len, self.heads, self.head_dim)
        keys = keys.reshape(N, key_len, self.heads, self.head_dim)
        queries = query.reshape(N, query_len, self.heads, self.head_dim)

        attention_filter = torch.einsum("nqhd,nkhd->nhqk", [queries, keys])

        if mask is not None:
            attention_filter = attention_filter.masked_fill(mask ==0, float("-1e20"))

        attention_filter = torch.softmax(attention_filter / (self.embed_size ** (1/2)), dim=3)

        out = torch.einsum("nhql,nlhd->nqhd", [attention_filter, values]).reshape(N, query_len, self.heads*self.head_dim)

        out = self.fc_out(out)
        return out

class TransformerBlock(nn.Module):
    def __init__(self, embed_size: int, heads: int, dropout: float, forward_expansion: int) -> None:
        """Initialize the Transformer Block.
        
        Args:
            embed_size (int): The embedding size of the input.
            heads (int): The amount of heads to split the input into.
            dropout (float): The dropout rate.
            forward_expansion (int): The expansion factor of the feed forward layer.

        Returns:
            None
        """
        super(TransformerBlock, self).__init__()
        self.attention = SelfAttention(embed_size, heads)
        self.norm1 = nn.LayerNorm(embed_size)
        self.norm2 = nn.LayerNorm(embed_size)

        self.feed_forward = nn.Sequential(
            nn.Linear(embed_size, forward_expansion*embed_size),
            nn.ReLU(),
            nn.Linear(forward_expansion*embed_size, embed_size)
        )
        self.dropout = nn.Dropout(dropout)

    def forward(self, value, key, query, mask) -> torch.Tensor:
        """Forward pass of the Transformer Block.
        
        Args:
            value (torch.Tensor): The values to be used in the attention.
            key (torch.Tensor): The keys to be used in the attention.
            query (torch.Tensor): The query to be used in the attention.
            mask (torch.Tensor): The mask to be used in the attention.

        Returns:
            out (torch.Tensor): The output of the forward pass.
        """
        attention = self.attention(value, key, query, mask)

        x = self.dropout(self.norm1(attention + query))
        forward = self.feed_forward(x)
        out = self.dropout(self.norm2(forward + x))
        return out