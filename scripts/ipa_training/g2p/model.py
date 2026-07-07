# encoding: UTF-8
"""
G2P Model - Transformer-based Grapheme-to-Phoneme model.

Implements an Encoder-Decoder transformer architecture:
- Encoder: BERT-based (multilingual)
- Decoder: Custom transformer decoder
- Output: IPA phoneme sequence with stress markers
"""

import os
from dataclasses import dataclass
from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn import CrossEntropyLoss
from transformers.modeling_outputs import Seq2SeqLMOutput


@dataclass
class ModelConfig:
    """Configuration for the G2P model."""
    # Encoder settings (smaller than BERT - character-level transformer)
    encoder_model_name: str = "custom"  # Use custom encoder, not pretrained BERT
    encoder_hidden_size: int = 256
    encoder_num_layers: int = 4
    encoder_num_heads: int = 4
    encoder_dropout: float = 0.1

    # Decoder settings
    decoder_hidden_size: int = 256
    decoder_num_layers: int = 4
    decoder_num_heads: int = 4
    decoder_dropout: float = 0.1
    decoder_max_length: int = 100

    # Vocab sizes (set by tokenizer)
    grapheme_vocab_size: int = 100
    phoneme_vocab_size: int = 100

    # Token IDs (set by tokenizer)
    pad_token_id: int = 0
    bos_token_id: int = 2
    eos_token_id: int = 3
    unk_token_id: int = 1

    # Generation settings
    num_beams: int = 5
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 0.95


class PositionalEncoding(nn.Module):
    """
    Positional encoding for the decoder.

    Uses learned positional embeddings with maximum length support.
    """

    def __init__(self, d_model: int, max_len: int = 500, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        # Learnable positional embeddings
        self.position_embedding = nn.Embedding(max_len, d_model)

        # Initialize
        nn.init.uniform_(self.position_embedding.weight, -0.02, 0.02)

    def forward(self, x: torch.Tensor, positions: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Add positional embeddings to input.

        Args:
            x: Input tensor of shape (batch, seq_len, d_model)
            positions: Optional positions tensor, if None uses range(seq_len)

        Returns:
            Output with positional encoding added
        """
        seq_len = x.size(1)

        if positions is None:
            positions = torch.arange(seq_len, device=x.device, dtype=torch.long)

        position_embeds = self.position_embedding(positions)
        x = x + position_embeds

        return self.dropout(x)


class TransformerDecoderLayer(nn.Module):
    """
    Custom transformer decoder layer.

    Includes masked self-attention and cross-attention with encoder outputs.
    """

    def __init__(self, d_model: int, num_heads: int, dim_feedforward: int = 2048,
                 dropout: float = 0.1):
        super().__init__()

        # Self-attention (masked)
        self.self_attn = nn.MultiheadAttention(d_model, num_heads, dropout=dropout, batch_first=True)
        self.self_attn_layer_norm = nn.LayerNorm(d_model)

        # Cross-attention
        self.cross_attn = nn.MultiheadAttention(d_model, num_heads, dropout=dropout, batch_first=True)
        self.cross_attn_layer_norm = nn.LayerNorm(d_model)

        # Feed-forward
        self.linear1 = nn.Linear(d_model, dim_feedforward)
        self.dropout = nn.Dropout(dropout)
        self.linear2 = nn.Linear(dim_feedforward, d_model)
        self.ffn_layer_norm = nn.LayerNorm(d_model)

    def forward(self,
                tgt: torch.Tensor,
                memory: torch.Tensor,
                tgt_mask: Optional[torch.Tensor] = None,
                memory_mask: Optional[torch.Tensor] = None,
                tgt_key_padding_mask: Optional[torch.Tensor] = None,
                memory_key_padding_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass.

        Args:
            tgt: Target sequence (decoder input)
            memory: Encoder output
            tgt_mask: Target attention mask
            memory_mask: Memory attention mask
            tgt_key_padding_mask: Target padding mask
            memory_key_padding_mask: Memory padding mask

        Returns:
            Decoder output
        """
        # Self-attention with causal masking
        tgt2, _ = self.self_attn(tgt, tgt, tgt, attn_mask=tgt_mask,
                                  key_padding_mask=tgt_key_padding_mask)
        tgt = self.self_attn_layer_norm(tgt + tgt2)

        # Cross-attention
        tgt2, attn_weights = self.cross_attn(tgt, memory, memory,
                                              attn_mask=memory_mask,
                                              key_padding_mask=memory_key_padding_mask)
        tgt = self.cross_attn_layer_norm(tgt + tgt2)

        # Feed-forward
        tgt2 = self.linear2(self.dropout(F.relu(self.linear1(tgt))))
        tgt = self.ffn_layer_norm(tgt + tgt2)

        return tgt


class G2PModel(nn.Module):
    """
    Grapheme-to-Phoneme Transformer model.

    Encoder: BERT (multilingual)
    Decoder: Custom transformer decoder

    Args:
        config: ModelConfig object
    """

    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config

        # Token embeddings
        self.grapheme_embedding = nn.Embedding(config.grapheme_vocab_size,
                                                config.encoder_hidden_size,
                                                padding_idx=config.pad_token_id)
        self.phoneme_embedding = nn.Embedding(config.phoneme_vocab_size,
                                               config.decoder_hidden_size,
                                               padding_idx=config.pad_token_id)

        # Encoder - character-level transformer (simpler than BERT for this task)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.encoder_hidden_size,
            nhead=config.encoder_num_heads,
            dim_feedforward=config.encoder_hidden_size * 4,
            dropout=config.encoder_dropout,
            batch_first=True
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=config.encoder_num_layers)
        
        # Positional encoding for encoder
        self.encoder_positional_encoding = PositionalEncoding(
            d_model=config.encoder_hidden_size,
            max_len=512,
            dropout=config.encoder_dropout
        )

        # Positional encoding for decoder
        self.positional_encoding = PositionalEncoding(
            d_model=config.decoder_hidden_size,
            max_len=config.decoder_max_length,
            dropout=config.decoder_dropout
        )

        # Decoder layers - create separate layer instances
        self.decoder_layers = nn.ModuleList([
            TransformerDecoderLayer(
                d_model=config.decoder_hidden_size,
                num_heads=config.decoder_num_heads,
                dim_feedforward=config.decoder_hidden_size * 4,
                dropout=config.decoder_dropout
            )
            for _ in range(config.decoder_num_layers)
        ])

        # Output projection
        self.output_projection = nn.Linear(config.decoder_hidden_size, config.phoneme_vocab_size)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize weights using Xavier initialization."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def generate_square_subsequent_mask(self, sz: int) -> torch.Tensor:
        """
        Generate causal mask for decoder self-attention.

        Args:
            sz: Sequence length

        Returns:
            Mask tensor of shape (sz, sz)
        """
        mask = torch.triu(torch.ones(sz, sz, device=self.device), diagonal=1).bool()
        return mask

    def forward(self,
                input_ids: torch.Tensor,
                attention_mask: torch.Tensor,
                decoder_input_ids: torch.Tensor,
                decoder_attention_mask: Optional[torch.Tensor] = None,
                labels: Optional[torch.Tensor] = None) -> Seq2SeqLMOutput:
        """
        Forward pass.

        Args:
            input_ids: Grapheme input token IDs (batch, seq_len)
            attention_mask: Input attention mask (batch, seq_len)
            decoder_input_ids: Phoneme input token IDs (batch, seq_len)
            decoder_attention_mask: Decoder attention mask
            labels: Target labels for loss computation

        Returns:
            Seq2SeqLMOutput with loss and logits
        """
        # Encode graphemes with character-level transformer
        encoder_input_embeds = self.grapheme_embedding(input_ids)
        
        # Add positional encoding for encoder
        batch_size = input_ids.size(0)
        enc_seq_len = input_ids.size(1)
        enc_positions = torch.arange(enc_seq_len, device=input_ids.device).unsqueeze(0).expand(batch_size, -1)
        encoder_input_embeds = self.encoder_positional_encoding(encoder_input_embeds, enc_positions)
        
        # Create encoder padding mask (True = ignore)
        encoder_padding_mask = attention_mask.eq(0)
        
        # Encode
        encoder_hidden_states = self.encoder(
            encoder_input_embeds,
            src_key_padding_mask=encoder_padding_mask
        )  # (batch, seq_len, d_model)

        # Prepare decoder input
        decoder_input_embeds = self.phoneme_embedding(decoder_input_ids)

        # Add positional encoding
        batch_size = decoder_input_ids.size(0)
        seq_len = decoder_input_ids.size(1)
        positions = torch.arange(seq_len, device=decoder_input_ids.device).unsqueeze(0).expand(batch_size, -1)
        decoder_input_embeds = self.positional_encoding(decoder_input_embeds, positions)

        # Generate causal mask
        tgt_mask = self.generate_square_subsequent_mask(seq_len)

        # Handle padding mask for decoder
        if decoder_attention_mask is None:
            decoder_padding_mask = (decoder_input_ids == self.config.pad_token_id)
        else:
            decoder_padding_mask = decoder_attention_mask.eq(0)

        # Pass through decoder layers
        decoder_output = decoder_input_embeds
        for layer in self.decoder_layers:
            decoder_output = layer(
                decoder_output,
                encoder_hidden_states,
                tgt_mask=tgt_mask,
                memory_key_padding_mask=attention_mask.eq(0),
                tgt_key_padding_mask=decoder_padding_mask
            )

        # Project to vocabulary
        logits = self.output_projection(decoder_output)  # (batch, seq_len, vocab_size)

        loss = None
        if labels is not None:
            # Shift labels for next-token prediction
            shifted_labels = labels[:, 1:].contiguous()
            logits = logits[:, :-1].contiguous()

            loss_fct = CrossEntropyLoss(ignore_index=self.config.pad_token_id)
            loss = loss_fct(logits.view(-1, logits.size(-1)), shifted_labels.view(-1))

        return Seq2SeqLMOutput(
            loss=loss,
            logits=logits,
            past_key_values=None,
            decoder_hidden_states=None,
            decoder_attentions=None,
            cross_attentions=None,
            encoder_last_hidden_state=encoder_hidden_states,
        )

    def generate(self,
                 input_ids: torch.Tensor,
                 attention_mask: torch.Tensor,
                 max_length: int = 100,
                 num_beams: int = 5,
                 temperature: float = 1.0,
                 top_k: int = 50,
                 top_p: float = 0.95,
                 early_stopping: bool = True) -> torch.Tensor:
        """
        Generate phoneme sequence from grapheme input.

        Args:
            input_ids: Grapheme input token IDs (batch, seq_len)
            attention_mask: Input attention mask (batch, seq_len)
            max_length: Maximum output length
            num_beams: Number of beams for beam search
            temperature: Sampling temperature
            top_k: Top-k sampling parameter
            top_p: Top-p sampling parameter
            early_stopping: Stop when all beams finish

        Returns:
            Generated token IDs (batch, seq_len)
        """
        batch_size = input_ids.size(0)
        device = input_ids.device

        # Encode graphemes with character-level transformer
        encoder_input_embeds = self.grapheme_embedding(input_ids)
        enc_seq_len = input_ids.size(1)
        enc_positions = torch.arange(enc_seq_len, device=device).unsqueeze(0).expand(batch_size, -1)
        encoder_input_embeds = self.encoder_positional_encoding(encoder_input_embeds, enc_positions)
        
        encoder_padding_mask = attention_mask.eq(0)
        memory = self.encoder(encoder_input_embeds, src_key_padding_mask=encoder_padding_mask)  # (batch, input_seq_len, hidden)

        # Expand encoder outputs for beam search
        # Shape: (batch * num_beams, input_seq_len, hidden)
        memory = memory.unsqueeze(1).repeat(1, num_beams, 1, 1).view(batch_size * num_beams, -1, memory.size(-1))
        attention_mask = attention_mask.unsqueeze(1).repeat(1, num_beams, 1).view(batch_size * num_beams, -1)

        # Initialize decoder input with BOS token for each beam
        # Shape: (batch * num_beams, 1)
        decoder_input = torch.full(
            (batch_size * num_beams, 1),
            self.config.bos_token_id,
            dtype=torch.long,
            device=device
        )

        # Initialize beam scores
        # Shape: (batch, num_beams)
        beam_scores = torch.zeros(batch_size, num_beams, device=device)
        beam_scores[:, 1:] = -1e9  # Only first beam is active initially

        # Track finished beams
        done = torch.zeros(batch_size, num_beams, dtype=torch.bool, device=device)

        for step in range(max_length):
            # Get current sequence length
            seq_len = decoder_input.size(1)
            
            # Embed and add positional encoding
            decoder_input_embeds = self.phoneme_embedding(decoder_input)
            positions = torch.arange(seq_len, device=device).unsqueeze(0).expand(batch_size * num_beams, -1)
            decoder_input_embeds = self.positional_encoding(decoder_input_embeds, positions)

            # Generate causal mask
            tgt_mask = self.generate_square_subsequent_mask(seq_len)

            # Pass through decoder layers
            decoder_output = decoder_input_embeds
            for layer in self.decoder_layers:
                decoder_output = layer(
                    decoder_output,
                    memory,
                    tgt_mask=tgt_mask,
                    memory_key_padding_mask=attention_mask.eq(0)
                )

            # Get logits for last position: (batch * num_beams, vocab)
            logits = self.output_projection(decoder_output[:, -1, :])
            
            # Reshape to (batch, num_beams, vocab)
            logits = logits.view(batch_size, num_beams, -1)

            # Apply temperature
            if temperature != 1.0:
                logits = logits / temperature

            # Apply top-k/top-p filtering
            if top_k > 0 or top_p < 1.0:
                logits = top_k_top_p_filtering(logits, top_k=top_k, top_p=top_p)

            # Convert to log probabilities
            log_probs = F.log_softmax(logits, dim=-1)  # (batch, num_beams, vocab)

            # Add current beam scores: (batch, num_beams, vocab)
            scores = beam_scores.unsqueeze(-1) + log_probs

            # Flatten to select top beams across all vocab: (batch, num_beams * vocab)
            scores_flat = scores.view(batch_size, -1)
            
            # Select top num_beams candidates
            next_scores, next_indices = scores_flat.topk(num_beams, dim=1, largest=True, sorted=True)
            
            # Convert flat indices back to (beam_idx, token_id)
            next_beam_indices = next_indices // self.config.phoneme_vocab_size  # Which beam
            next_tokens = next_indices % self.config.phoneme_vocab_size  # Which token

            # Gather sequences from selected beams
            # decoder_input: (batch * num_beams, seq_len) -> (batch, num_beams, seq_len)
            decoder_input_reshaped = decoder_input.view(batch_size, num_beams, -1)
            
            # Gather: (batch, num_beams, seq_len)
            selected_sequences = torch.gather(
                decoder_input_reshaped,
                1,
                next_beam_indices.unsqueeze(-1).expand(-1, -1, decoder_input_reshaped.size(-1))
            )
            
            # Append new tokens: (batch, num_beams, seq_len + 1)
            decoder_input = torch.cat([selected_sequences, next_tokens.unsqueeze(-1)], dim=-1)
            
            # Flatten back: (batch * num_beams, seq_len + 1)
            decoder_input = decoder_input.view(batch_size * num_beams, -1)

            # Update beam scores
            beam_scores = next_scores

            # Check for EOS tokens
            eos_mask = (next_tokens == self.config.eos_token_id)
            done = done | eos_mask

            # Early stopping if all beams are done
            if early_stopping and done.all():
                break

        # Select best sequence from each batch
        # decoder_input: (batch * num_beams, final_seq_len) -> (batch, num_beams, final_seq_len)
        decoder_input = decoder_input.view(batch_size, num_beams, -1)
        
        # Get best beam indices: (batch,)
        best_beam_indices = beam_scores.argmax(dim=1)
        
        # Select best sequences: (batch, final_seq_len)
        output = decoder_input[torch.arange(batch_size), best_beam_indices]

        # Remove BOS token from the beginning: (batch, final_seq_len - 1)
        if output.size(1) > 0 and (output[:, 0] == self.config.bos_token_id).all():
            output = output[:, 1:]

        return output

    @property
    def device(self) -> torch.device:
        """Get model device."""
        return next(self.parameters()).device


def top_k_top_p_filtering(logits: torch.Tensor,
                          top_k: int = 0,
                          top_p: float = 1.0,
                          filter_value: float = -float('Inf')) -> torch.Tensor:
    """
    Filter logits using top-k and/or top-p sampling.

    Args:
        logits: Logits tensor of shape (batch, vocab) or (batch, beams, vocab)
        top_k: Keep top k tokens with highest probability
        top_p: Keep tokens with cumulative probability >= top_p
        filter_value: Value to use for filtered tokens

    Returns:
        Filtered logits
    """
    original_shape = logits.shape
    if logits.dim() == 3:
        # Flatten batch and beams for processing
        batch_size, num_beams, vocab_size = logits.shape
        logits = logits.view(-1, vocab_size)
    
    if top_k > 0:
        # Top-k filtering
        topk_values, topk_indices = torch.topk(logits, min(top_k, logits.size(-1)))
        filter_mask = logits < topk_values[:, -1].unsqueeze(-1)
        logits[filter_mask] = filter_value

    if top_p < 1.0:
        # Top-p filtering
        sorted_logits, sorted_indices = torch.sort(logits, descending=True, dim=-1)
        cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)

        # Remove tokens with cumulative probability > top_p
        filter_mask = cumulative_probs > top_p
        # Keep at least one token
        filter_mask[:, 1:] = filter_mask[:, :-1].clone()
        filter_mask[:, 0] = False

        indices_to_remove = filter_mask.scatter(1, sorted_indices, filter_mask)
        logits[indices_to_remove] = filter_value

    # Restore original shape if needed
    if len(original_shape) == 3:
        logits = logits.view(original_shape)
    
    return logits


def load_model(checkpoint_path: str,
               config: ModelConfig,
               device: Optional[torch.device] = None) -> G2PModel:
    """
    Load a trained model from checkpoint.

    Args:
        checkpoint_path: Path to model checkpoint
        config: Model configuration
        device: Device to load model on

    Returns:
        Loaded G2PModel
    """
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)

    # Create model
    model = G2PModel(config)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(device)
    model.eval()

    return model


def save_model(model: G2PModel,
               checkpoint_path: str,
               optimizer_state_dict: Optional[Dict] = None,
               epoch: int = 0,
               loss: float = 0.0) -> None:
    """
    Save model checkpoint.

    Args:
        model: G2PModel to save
        checkpoint_path: Output path
        optimizer_state_dict: Optional optimizer state
        epoch: Current epoch
        loss: Current loss
    """
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'config': model.config,
        'epoch': epoch,
        'loss': loss,
    }

    if optimizer_state_dict:
        checkpoint['optimizer_state_dict'] = optimizer_state_dict

    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
    torch.save(checkpoint, checkpoint_path)


if __name__ == '__main__':
    # Basic model instantiation test
    config = ModelConfig(
        grapheme_vocab_size=100,
        phoneme_vocab_size=100,
        pad_token_id=0,
        bos_token_id=2,
        eos_token_id=3,
    )

    model = G2PModel(config)
    print(f"Model created with {sum(p.numel() for p in model.parameters()):,} parameters")

    # Test forward pass
    batch_size = 2
    grapheme_ids = torch.randint(0, 100, (batch_size, 20))
    grapheme_mask = torch.ones(batch_size, 20, dtype=torch.long)
    decoder_ids = torch.randint(0, 100, (batch_size, 30))
    decoder_mask = torch.ones(batch_size, 30, dtype=torch.long)
    labels = torch.randint(0, 100, (batch_size, 30))

    output = model(
        input_ids=grapheme_ids,
        attention_mask=grapheme_mask,
        decoder_input_ids=decoder_ids,
        decoder_attention_mask=decoder_mask,
        labels=labels
    )

    print(f"Loss: {output.loss.item():.4f}")
    print(f"Logits shape: {output.logits.shape}")
