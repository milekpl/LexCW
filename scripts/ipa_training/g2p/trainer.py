# encoding: UTF-8
"""
G2P Trainer - Training pipeline for the G2P transformer model.

Provides:
- Data loading and batching
- Training loop with validation
- Checkpoint saving/loading
- Metrics computation (PER, accuracy)
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import torch
from torch.optim import AdamW
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
from transformers import get_linear_schedule_with_warmup

try:
    from .model import G2PModel, ModelConfig
    from .tokenizer import G2PTokenizer
    from .preprocessor import G2PPreprocessor
except ImportError:
    from model import G2PModel, ModelConfig
    from tokenizer import G2PTokenizer
    from preprocessor import G2PPreprocessor


# Memory monitoring utilities
def get_gpu_memory_info():
    """Get GPU memory info if CUDA is available.

    Returns:
        Tuple of (allocated_mb, reserved_mb, total_mb) or None if no GPU
    """
    if not torch.cuda.is_available():
        return None

    return (
        torch.cuda.memory_allocated() / 1024 / 1024,  # Allocated
        torch.cuda.memory_reserved() / 1024 / 1024,   # Reserved
        torch.cuda.get_device_properties(0).total_memory / 1024 / 1024  # Total
    )


def check_memory_and_recommend(device: torch.device, estimated_model_mb: float = 4000) -> str:
    """Check available memory and provide recommendations.

    Args:
        device: Target device
        estimated_model_mb: Estimated model memory usage in MB

    Returns:
        Status message with recommendations
    """
    if device.type == 'cpu':
        return "Using CPU - training will be slow but stable"

    mem_info = get_gpu_memory_info()
    if mem_info is None:
        return "CUDA not available, falling back to CPU"

    allocated, reserved, total = mem_info
    available = total - allocated

    # Add some headroom for gradients and optimizer states
    required_headroom = estimated_model_mb * 1.5  # Gradients can use 1.5x model size

    if available > required_headroom + 500:
        return f"GPU Memory OK: {available:.0f}MB available (need ~{required_headroom:.0f}MB headroom)"
    elif available > estimated_model_mb:
        return f"LOW GPU MEMORY: {available:.0f}MB available. Consider reducing batch_size."
    else:
        return f"CRITICAL: Only {available:.0f}MB GPU memory available. Use CPU or reduce batch_size significantly."


def get_safe_batch_size(device: torch.device, base_batch: int = 8) -> int:
    """Determine a safe batch size based on available GPU memory.

    Args:
        device: Target device
        base_batch: Starting batch size to try

    Returns:
        Safe batch size
    """
    if device.type == 'cpu':
        return 4  # Smaller batch for CPU

    if not torch.cuda.is_available():
        return 4

    mem_info = get_gpu_memory_info()
    if mem_info is None:
        return 4

    allocated, reserved, total = mem_info
    available = total - allocated

    # Estimate: model ~4GB + batch data ~500MB per sample + gradients ~1GB
    # For 8GB card with 1GB used by system, we have ~7GB available
    usable = available - 1024  # Reserve 1GB for system stability

    if usable < 2000:
        return 1  # Critical - only 1 sample at a time
    elif usable < 4000:
        return 2
    elif usable < 6000:
        return 4
    else:
        return base_batch


@dataclass
class TrainingConfig:
    """Configuration for training."""
    # Model settings
    grapheme_vocab_size: int = 100
    phoneme_vocab_size: int = 100
    pad_token_id: int = 0
    bos_token_id: int = 2
    eos_token_id: int = 3

    # Training settings
    learning_rate: float = 1e-4
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0
    batch_size: int = 8  # Reduced from 32 to avoid GPU OOM on 8GB cards
    num_epochs: int = 10
    warmup_steps: int = 500

    # Generation settings (for validation)
    num_beams: int = 1  # Greedy decoding for fast validation
    max_generate_length: int = 40  # Shorter for validation

    # Logging
    log_interval: int = 100
    save_interval: int = 1000
    eval_interval: int = 1000

    # Output
    output_dir: str = "./checkpoints"
    resume_from: Optional[str] = None


class G2PDataset(Dataset):
    """
    Dataset for G2P training.

    Stores grapheme-phoneme pairs and provides tokenized batches.
    """

    def __init__(self,
                 pairs: List[Tuple[str, str]],
                 tokenizer: G2PTokenizer,
                 preprocessor: G2PPreprocessor,
                 max_grapheme_length: int = 50,
                 max_phoneme_length: int = 100):
        """
        Initialize dataset.

        Args:
            pairs: List of (grapheme, phoneme) tuples
            tokenizer: G2PTokenizer instance
            preprocessor: G2PPreprocessor instance
            max_grapheme_length: Maximum grapheme sequence length
            max_phoneme_length: Maximum phoneme sequence length
        """
        self.tokenizer = tokenizer
        self.preprocessor = preprocessor
        self.max_grapheme_length = max_grapheme_length
        self.max_phoneme_length = max_phoneme_length

        # Filter and store valid pairs
        self.data = []
        for grapheme, phoneme in pairs:
            # Preprocess
            result = preprocessor.normalize_for_training(grapheme, phoneme)
            if result is None:
                continue
            norm_grapheme, norm_phoneme = result
            self.data.append((norm_grapheme, norm_phoneme))

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        grapheme, phoneme = self.data[idx]

        # Tokenize
        g_ids = self.tokenizer.encode_grapheme(grapheme, add_bos=True, add_eos=True)
        p_ids = self.tokenizer.encode_phoneme(phoneme, add_bos=True, add_eos=True)

        # Truncate
        g_ids = g_ids[:self.max_grapheme_length + 2]  # +2 for BOS/EOS
        p_ids = p_ids[:self.max_phoneme_length + 2]

        return {
            'input_ids': torch.tensor(g_ids, dtype=torch.long),
            'labels': torch.tensor(p_ids, dtype=torch.long),
        }


class G2PDataCollator:
    """
    Data collator for batching.
    """

    def __init__(self, tokenizer: G2PTokenizer, max_length: int = 100):
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __call__(self, batch: List[Dict[str, torch.Tensor]]) -> Dict[str, torch.Tensor]:
        max_len = min(max(item['input_ids'].size(0) for item in batch), self.max_length + 2)

        input_ids = []
        labels = []

        # Get pad_id once (outside loop)
        pad_id = self.tokenizer.PAD_ID if self.tokenizer else 0

        for item in batch:
            ids = item['input_ids'][:max_len]
            lbl = item['labels'][:max_len]

            # Pad
            if ids.size(0) < max_len:
                padding = torch.full((max_len - ids.size(0),), pad_id, dtype=torch.long)
                ids = torch.cat([ids, padding])
            if lbl.size(0) < max_len:
                padding = torch.full((max_len - lbl.size(0),), pad_id, dtype=torch.long)
                lbl = torch.cat([lbl, padding])

            input_ids.append(ids)
            labels.append(lbl)

        return {
            'input_ids': torch.stack(input_ids),
            'labels': torch.stack(labels),
        }


class G2PTrainer:
    """
    Trainer for G2P model.
    """

    def __init__(self,
                 model: G2PModel,
                 tokenizer: G2PTokenizer,
                 config: TrainingConfig,
                 train_dataset: Dataset,
                 val_dataset: Optional[Dataset] = None,
                 device: Optional[torch.device] = None,
                 grapheme_vocab: Optional[Dict[str, int]] = None,
                 phoneme_vocab: Optional[Dict[str, int]] = None):
        """
        Initialize trainer.

        Args:
            model: G2PModel instance
            tokenizer: G2PTokenizer instance
            config: TrainingConfig
            train_dataset: Training dataset
            val_dataset: Optional validation dataset
            device: Device to train on
            grapheme_vocab: Grapheme vocabulary dict (for saving in checkpoints)
            phoneme_vocab: Phoneme vocabulary dict (for saving in checkpoints)
        """
        self.model = model
        self.tokenizer = tokenizer
        self.config = config
        self.train_dataset = train_dataset
        self.val_dataset = val_dataset
        self.grapheme_vocab = grapheme_vocab or {}
        self.phoneme_vocab = phoneme_vocab or {}

        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = device

        self.model.to(self.device)

        # Optimizer
        self.optimizer = AdamW(
            model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay
        )

        # Scheduler
        total_steps = len(train_dataset) * config.num_epochs // config.batch_size
        self.scheduler = get_linear_schedule_with_warmup(
            self.optimizer,
            num_warmup_steps=config.warmup_steps,
            num_training_steps=total_steps
        )

        # Training state
        self.global_step = 0
        self.epoch = 0
        self.best_val_loss = float('inf')
        self.history: List[Dict] = []

        # Create output directory
        os.makedirs(config.output_dir, exist_ok=True)

    def train(self) -> Dict:
        """
        Run full training loop.

        Returns:
            Training history
        """
        train_loader = DataLoader(
            self.train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            collate_fn=G2PDataCollator(self.tokenizer),
            num_workers=0
        )

        for epoch in range(self.epoch, self.config.num_epochs):
            self.epoch = epoch
            train_loss = self._train_epoch(train_loader)

            # Validation
            val_loss = None
            val_per = None
            if self.val_dataset:
                val_loader = DataLoader(
                    self.val_dataset,
                    batch_size=self.config.batch_size,
                    shuffle=False,
                    collate_fn=G2PDataCollator(self.tokenizer),
                    num_workers=0
                )
                val_loss, val_per = self._evaluate(val_loader)

                if val_loss < self.best_val_loss:
                    self.best_val_loss = val_loss
                    self._save_checkpoint('best_model.pt')

            # Save epoch checkpoint
            self._save_checkpoint(f'epoch_{epoch}.pt')

            # Log
            log_entry = {
                'epoch': epoch,
                'train_loss': train_loss,
                'val_loss': val_loss,
                'val_per': val_per,
                'learning_rate': self.scheduler.get_last_lr()[0],
            }
            self.history.append(log_entry)

            val_loss_str = f"{val_loss:.4f}" if val_loss is not None else "N/A"
            val_per_str = f"{val_per:.4f}" if val_per is not None else "N/A"
            print(f"Epoch {epoch}: train_loss={train_loss:.4f}, "
                  f"val_loss={val_loss_str}, "
                  f"val_per={val_per_str}")

        return self.history

    def _train_epoch(self, train_loader: DataLoader) -> float:
        """
        Train for one epoch.

        Args:
            train_loader: Training data loader

        Returns:
            Average training loss
        """
        self.model.train()
        total_loss = 0.0
        batch_count = 0

        # Log initial memory status
        mem_info = get_gpu_memory_info()
        if mem_info:
            allocated, reserved, total = mem_info
            print(f"[Memory] GPU: {allocated:.0f}MB allocated, {reserved:.0f}MB reserved, {total:.0f}MB total")

        progress_bar = tqdm(train_loader, desc=f"Epoch {self.epoch}")
        for batch in progress_bar:
            input_ids = batch['input_ids'].to(self.device)
            labels = batch['labels'].to(self.device)

            # Forward pass
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=(input_ids != self.config.pad_token_id),
                decoder_input_ids=labels[:, :-1].contiguous(),
                labels=labels[:, 1:].contiguous()
            )

            loss = outputs.loss

            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)
            self.optimizer.step()
            self.scheduler.step()
            self.optimizer.zero_grad()

            self.global_step += 1
            total_loss += loss.item()
            batch_count += 1

            # Memory monitoring every 50 steps
            if self.global_step % 50 == 0:
                mem_info = get_gpu_memory_info()
                if mem_info:
                    allocated, reserved, total = mem_info
                    # Warn if memory is getting high
                    usage_pct = (allocated / total) * 100
                    if usage_pct > 80:
                        print(f"[WARNING] High GPU memory: {usage_pct:.1f}% ({allocated:.0f}MB)")

            # Logging
            if self.global_step % self.config.log_interval == 0:
                avg_loss = total_loss / batch_count
                progress_bar.set_postfix({'loss': f'{avg_loss:.4f}'})

            # Checkpoint saving
            if self.global_step % self.config.save_interval == 0:
                self._save_checkpoint(f'step_{self.global_step}.pt')

        return total_loss / batch_count

    def _evaluate(self, val_loader: DataLoader) -> Tuple[float, float]:
        """
        Evaluate on validation set.

        Args:
            val_loader: Validation data loader

        Returns:
            Tuple of (average loss, PER)
        """
        self.model.eval()
        total_loss = 0.0
        total_per = 0.0
        batch_count = 0

        preprocessor = G2PPreprocessor()

        with torch.no_grad():
            for batch in tqdm(val_loader, desc="Evaluating"):
                input_ids = batch['input_ids'].to(self.device)
                labels = batch['labels'].to(self.device)

                # Forward pass
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=(input_ids != self.config.pad_token_id),
                    decoder_input_ids=labels[:, :-1].contiguous(),
                    labels=labels[:, 1:].contiguous()
                )

                loss = outputs.loss
                total_loss += loss.item()

                # Generate and compute PER
                generated = self.model.generate(
                    input_ids=input_ids,
                    attention_mask=(input_ids != self.config.pad_token_id),
                    max_length=self.config.max_generate_length,
                    num_beams=self.config.num_beams
                )

                # Compute PER for each sample
                for i in range(input_ids.size(0)):
                    ref_text = self.tokenizer.decode_phoneme(labels[i].tolist())
                    hyp_text = self.tokenizer.decode_phoneme(generated[i].tolist())
                    per = preprocessor.compute_phoneme_error_rate(ref_text, hyp_text)
                    total_per += per

                batch_count += 1

        avg_loss = total_loss / batch_count
        avg_per = total_per / batch_count

        return avg_loss, avg_per

    def _save_checkpoint(self, filename: str) -> None:
        """
        Save model checkpoint.

        Args:
            filename: Output filename
        """
        checkpoint = {
            'global_step': self.global_step,
            'epoch': self.epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'best_val_loss': self.best_val_loss,
            'history': self.history,
            'config': self.config,
            'grapheme_vocab': self.grapheme_vocab,
            'phoneme_vocab': self.phoneme_vocab,
        }

        path = os.path.join(self.config.output_dir, filename)
        torch.save(checkpoint, path)

    def load_checkpoint(self, checkpoint_path: str) -> None:
        """
        Load from checkpoint.

        Args:
            checkpoint_path: Path to checkpoint
        """
        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)

        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint.get('optimizer_state_dict', {}))
        self.scheduler.load_state_dict(checkpoint.get('scheduler_state_dict', {}))
        self.global_step = checkpoint.get('global_step', 0)
        self.epoch = checkpoint.get('epoch', 0)
        self.best_val_loss = checkpoint.get('best_val_loss', float('inf'))
        self.history = checkpoint.get('history', [])


def compute_per(predictions: List[str],
                references: List[str],
                preprocessor: G2PPreprocessor) -> float:
    """
    Compute average Phoneme Error Rate.

    Args:
        predictions: List of predicted IPA strings
        references: List of reference IPA strings
        preprocessor: G2PPreprocessor instance

    Returns:
        Average PER
    """
    if len(predictions) != len(references):
        raise ValueError("Predictions and references must have same length")

    total_per = 0.0
    for pred, ref in zip(predictions, references):
        per = preprocessor.compute_phoneme_error_rate(ref, pred)
        total_per += per

    return total_per / len(predictions)


def compute_accuracy(predictions: List[str],
                     references: List[str]) -> float:
    """
    Compute exact match accuracy.

    Args:
        predictions: List of predicted strings
        references: List of reference strings

    Returns:
        Exact match accuracy (0.0 to 1.0)
    """
    if len(predictions) != len(references):
        raise ValueError("Predictions and references must have same length")

    matches = sum(1 for p, r in zip(predictions, references) if p == r)
    return matches / len(predictions)


if __name__ == '__main__':
    print("G2P Trainer module loaded.")
    print("Usage: Initialize G2PTrainer with model, tokenizer, and dataset.")
