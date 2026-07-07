# encoding: UTF-8
"""
G2P Anomaly Detector - Detect anomalous pronunciations using dual methods.

Two detection methods:
1. Confidence-based: Compare model prediction to stored IPA
2. Autoencoder: Detect unusual phoneme patterns via reconstruction error
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

try:
    from .model import G2PModel, ModelConfig
    from .tokenizer import G2PTokenizer
    from .preprocessor import G2PPreprocessor
except ImportError:
    from model import G2PModel, ModelConfig
    from tokenizer import G2PTokenizer
    from preprocessor import G2PPreprocessor


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""
    lexeme: str
    stored_ipa: str
    predicted_ipa: str
    confidence_score: float
    reconstruction_error: Optional[float] = None
    is_anomaly: bool = False
    anomaly_type: Optional[str] = None  # 'confidence', 'reconstruction', 'both'
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class IPAutoencoder(nn.Module):
    """
    Autoencoder for IPA sequence anomaly detection.

    Encodes IPA sequences to a latent representation and reconstructs them.
    High reconstruction error indicates anomalous sequences.
    """

    def __init__(self,
                 vocab_size: int,
                 embedding_dim: int = 128,
                 hidden_dim: int = 256,
                 latent_dim: int = 128,
                 max_length: int = 100):
        super().__init__()

        self.vocab_size = vocab_size
        self.max_length = max_length
        self.latent_dim = latent_dim

        # Encoder
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.encoder_gru = nn.GRU(embedding_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.encoder_fc = nn.Linear(hidden_dim * 2, latent_dim)

        # Decoder
        self.decoder_fc = nn.Linear(latent_dim, hidden_dim)
        self.decoder_gru = nn.GRU(hidden_dim, embedding_dim, batch_first=True)
        self.output_fc = nn.Linear(embedding_dim, vocab_size)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.

        Args:
            x: Input token IDs (batch, seq_len)

        Returns:
            Tuple of (reconstructed logits, latent representation)
        """
        # Embed
        embedded = self.embedding(x)  # (batch, seq_len, embed_dim)

        # Encode
        _, hidden = self.encoder_gru(embedded)
        # Concatenate bidirectional final hidden states
        hidden = torch.cat([hidden[0], hidden[1]], dim=1)
        latent = self.encoder_fc(hidden)  # (batch, latent_dim)

        # Decode (teacher forcing during training)
        decoded = self.decoder_fc(latent).unsqueeze(1).expand(-1, x.size(1), -1)
        output, _ = self.decoder_gru(decoded)
        logits = self.output_fc(output)  # (batch, seq_len, vocab_size)

        return logits, latent

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Encode to latent representation."""
        with torch.no_grad():
            embedded = self.embedding(x)
            _, hidden = self.encoder_gru(embedded)
            hidden = torch.cat([hidden[0], hidden[1]], dim=1)
            return self.encoder_fc(hidden)

    def decode(self, latent: torch.Tensor, max_length: int) -> torch.Tensor:
        """Decode from latent representation."""
        with torch.no_grad():
            decoded = self.decoder_fc(latent).unsqueeze(1).expand(-1, max_length, -1)
            output, _ = self.decoder_gru(decoded)
            return self.output_fc(output)


class G2PAnomalyDetector:
    """
    Detect anomalous pronunciations using dual methods.

    Method 1: Compare model predictions to stored IPA
    Method 2: Autoencoder reconstruction error
    """

    def __init__(self,
                 model: G2PModel,
                 tokenizer: G2PTokenizer,
                 preprocessor: G2PPreprocessor,
                 confidence_threshold: float = 0.5,
                 reconstruction_threshold: float = 0.3,
                 device: Optional[torch.device] = None):
        """
        Initialize detector.

        Args:
            model: Trained G2PModel
            tokenizer: G2PTokenizer
            preprocessor: G2PPreprocessor
            confidence_threshold: Below this = anomaly (for PER-based confidence)
            reconstruction_threshold: Above this = anomaly (for autoencoder)
            device: Computation device
        """
        self.model = model
        self.tokenizer = tokenizer
        self.preprocessor = preprocessor
        self.confidence_threshold = confidence_threshold
        self.reconstruction_threshold = reconstruction_threshold

        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = device

        self.model.to(self.device)
        self.model.eval()

        # Autoencoder (initialized later)
        self.autoencoder: Optional[IPAutoencoder] = None

    def set_autoencoder(self, autoencoder: IPAutoencoder) -> None:
        """Set the autoencoder model."""
        self.autoencoder = autoencoder
        autoencoder.to(self.device)
        autoencoder.eval()

    def detect(self,
               lexeme: str,
               stored_ipa: str,
               location: Optional[str] = None) -> AnomalyResult:
        """
        Detect if a pronunciation is anomalous.

        Args:
            lexeme: The headword
            stored_ipa: The stored IPA transcription
            location: Optional location (for context)

        Returns:
            AnomalyResult with detection details
        """
        # Tokenize input
        input_ids = self.tokenizer.encode_grapheme(lexeme, add_bos=False, add_eos=False)
        input_tensor = torch.tensor([input_ids], dtype=torch.long).to(self.device)
        attention_mask = (input_tensor != self.tokenizer.PAD_ID)

        # Generate prediction
        with torch.no_grad():
            generated = self.model.generate(
                input_tensor,
                attention_mask,
                max_length=self.tokenizer.max_phoneme_length,
                num_beams=5
            )

        predicted_ipa = self.tokenizer.decode_phoneme(generated[0].tolist())

        # Compute confidence (1 - PER)
        per = self.preprocessor.compute_phoneme_error_rate(stored_ipa, predicted_ipa)
        confidence_score = max(0.0, 1.0 - per)

        # Initialize result
        result = AnomalyResult(
            lexeme=lexeme,
            stored_ipa=stored_ipa,
            predicted_ipa=predicted_ipa,
            confidence_score=confidence_score,
        )

        # Check confidence-based anomaly
        confidence_anomaly = confidence_score < self.confidence_threshold

        # Check reconstruction-based anomaly
        reconstruction_error = None
        reconstruction_anomaly = False
        if self.autoencoder is not None:
            stored_ids = self.tokenizer.encode_phoneme(stored_ipa, add_bos=False, add_eos=False)
            stored_tensor = torch.tensor([stored_ids], dtype=torch.long).to(self.device)

            with torch.no_grad():
                logits, _ = self.autoencoder(stored_tensor)

            # Compute reconstruction loss (excluding padding)
            targets = stored_tensor.clone()
            targets[targets == 0] = -100  # Ignore padding in loss
            recon_loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1), ignore_index=-100)
            reconstruction_error = float(recon_loss.item())
            reconstruction_anomaly = reconstruction_error > self.reconstruction_threshold

        result.reconstruction_error = reconstruction_error

        # Determine overall anomaly status
        if confidence_anomaly and reconstruction_anomaly:
            result.is_anomaly = True
            result.anomaly_type = 'both'
        elif confidence_anomaly:
            result.is_anomaly = True
            result.anomaly_type = 'confidence'
        elif reconstruction_anomaly:
            result.is_anomaly = True
            result.anomaly_type = 'reconstruction'

        # Add details
        result.details = {
            'per': per,
            'confidence_threshold': self.confidence_threshold,
            'reconstruction_threshold': self.reconstruction_threshold,
            'location': location,
        }

        return result

    def detect_batch(self,
                     entries: List[Dict[str, str]],
                     show_progress: bool = True,
                     batch_size: int = 64,
                     num_beams: Optional[int] = None,
                     max_length: Optional[int] = None) -> List[AnomalyResult]:
        """
        Detect anomalies for a batch of entries using batched generation (GPU-friendly).

        Args:
            entries: List of {'lexeme': str, 'ipa': str, 'location': Optional[str]}
            show_progress: Show progress bar
            batch_size: Number of entries per batch
            num_beams: Override model beam size for generation
            max_length: Override max generation length

        Returns:
            List of AnomalyResult objects
        """
        results: List[AnomalyResult] = []
        total = len(entries)
        if num_beams is None:
            num_beams = getattr(self.model.config, 'num_beams', 1)

        from math import ceil
        from tqdm import tqdm

        it = range(0, total, batch_size)
        if show_progress:
            it = tqdm(it, total=ceil(total / batch_size), desc="Detecting anomalies")

        import time

        for start in it:
            batch_start_time = time.perf_counter()

            batch = entries[start:start + batch_size]
            lexemes = [e['lexeme'] for e in batch]
            stored_ipas = [e['ipa'] for e in batch]
            locations = [e.get('location') for e in batch]

            # Tokenize and pad graphemes
            t0 = time.perf_counter()
            g_ids_list = [self.tokenizer.encode_grapheme(l, add_bos=False, add_eos=False) for l in lexemes]
            max_g_len = min(max(len(ids) for ids in g_ids_list), self.tokenizer.max_grapheme_length)
            padded_g = []
            for ids in g_ids_list:
                if len(ids) < max_g_len:
                    ids = ids + [self.tokenizer.PAD_ID] * (max_g_len - len(ids))
                else:
                    ids = ids[:max_g_len]
                padded_g.append(ids)

            input_tensor = torch.tensor(padded_g, dtype=torch.long).to(self.device)
            attention_mask = (input_tensor != self.tokenizer.PAD_ID).to(self.device)
            token_time = time.perf_counter() - t0

            # Generate predictions in batch
            t1 = time.perf_counter()
            gen_max_len = max_length if max_length is not None else self.tokenizer.max_phoneme_length
            with torch.no_grad():
                generated = self.model.generate(
                    input_tensor,
                    attention_mask,
                    max_length=gen_max_len,
                    num_beams=num_beams
                )
            gen_time = time.perf_counter() - t1

            # Decode predictions and compute metrics
            t2 = time.perf_counter()
            predicted_ipas = [self.tokenizer.decode_phoneme(g.tolist()) for g in generated]
            decode_time = time.perf_counter() - t2

            # If autoencoder is present, compute reconstruction errors for stored IPA in batch
            recon_errors = [None] * len(batch)
            reconstruction_anomalies = [False] * len(batch)
            t3 = time.perf_counter()
            if self.autoencoder is not None:
                # Prepare stored sequences
                stored_ids_list = [self.tokenizer.encode_phoneme(s, add_bos=False, add_eos=False) for s in stored_ipas]
                if stored_ids_list:
                    max_p_len = min(max(len(ids) for ids in stored_ids_list), self.tokenizer.max_phoneme_length)
                    padded_p = []
                    for ids in stored_ids_list:
                        if len(ids) < max_p_len:
                            ids = ids + [self.tokenizer.PAD_ID] * (max_p_len - len(ids))
                        else:
                            ids = ids[:max_p_len]
                        padded_p.append(ids)

                    p_tensor = torch.tensor(padded_p, dtype=torch.long).to(self.device)

                    with torch.no_grad():
                        logits, _ = self.autoencoder(p_tensor)

                    # Compute per-sample reconstruction loss
                    for j in range(len(batch)):
                        targets = p_tensor[j].clone()
                        targets[targets == self.tokenizer.PAD_ID] = -100
                        # logits[j]: (seq_len, vocab)
                        loss_j = F.cross_entropy(logits[j].view(-1, logits.size(-1)), targets.view(-1), ignore_index=-100)
                        recon_errors[j] = float(loss_j.item())
                        reconstruction_anomalies[j] = recon_errors[j] > self.reconstruction_threshold
            auto_time = time.perf_counter() - t3

            # Build results
            for j, (lex, stored, predicted, loc) in enumerate(zip(lexemes, stored_ipas, predicted_ipas, locations)):
                per = self.preprocessor.compute_phoneme_error_rate(stored, predicted)
                confidence_score = max(0.0, 1.0 - per)

                result = AnomalyResult(
                    lexeme=lex,
                    stored_ipa=stored,
                    predicted_ipa=predicted,
                    confidence_score=confidence_score,
                )

                # Determine anomalies
                confidence_anomaly = confidence_score < self.confidence_threshold
                recon_err = recon_errors[j] if recon_errors[j] is not None else None
                recon_anom = reconstruction_anomalies[j]

                result.reconstruction_error = recon_err

                if confidence_anomaly and recon_anom:
                    result.is_anomaly = True
                    result.anomaly_type = 'both'
                elif confidence_anomaly:
                    result.is_anomaly = True
                    result.anomaly_type = 'confidence'
                elif recon_anom:
                    result.is_anomaly = True
                    result.anomaly_type = 'reconstruction'

                result.details = {
                    'per': per,
                    'confidence_threshold': self.confidence_threshold,
                    'reconstruction_error': recon_err,
                    'reconstruction_threshold': self.reconstruction_threshold,
                }
                results.append(result)

            batch_time = time.perf_counter() - batch_start_time
            samples = len(batch)
            throughput = samples / batch_time if batch_time > 0 else 0.0

            # Update progress bar with timings if present
            try:
                iterator.set_postfix({
                    'batch_time_s': f"{batch_time:.2f}",
                    'token_s': f"{token_time:.2f}",
                    'gen_s': f"{gen_time:.2f}",
                    'decode_s': f"{decode_time:.2f}",
                    'auto_s': f"{auto_time:.2f}",
                    's/s': f"{throughput:.2f}"
                })
            except Exception:
                # iterator may be a simple range if show_progress=False
                print(f"Batch {start}/{total}: batch_time={batch_time:.2f}s, gen={gen_time:.2f}s, s/s={throughput:.2f}")

        return results

    def get_anomaly_stats(self,
                          results: List[AnomalyResult]) -> Dict[str, Any]:
        """
        Get statistics on anomaly detection results.

        Args:
            results: List of AnomalyResult objects

        Returns:
            Dictionary of statistics
        """
        anomalies = [r for r in results if r.is_anomaly]

        confidence_scores = [r.confidence_score for r in results]
        reconstruction_errors = [r.reconstruction_error for r in results if r.reconstruction_error is not None]

        by_type = {}
        for r in anomalies:
            t = r.anomaly_type or 'unknown'
            by_type[t] = by_type.get(t, 0) + 1

        return {
            'total_checked': len(results),
            'anomalies_found': len(anomalies),
            'anomaly_rate': len(anomalies) / len(results) if results else 0,
            'by_type': by_type,
            'avg_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'avg_reconstruction_error': sum(reconstruction_errors) / len(reconstruction_errors) if reconstruction_errors else 0,
            'confidence_range': (min(confidence_scores), max(confidence_scores)) if confidence_scores else None,
        }

    def train_autoencoder(self,
                          valid_ipa_list: List[str],
                          tokenizer: G2PTokenizer,
                          epochs: int = 50,
                          batch_size: int = 64,
                          lr: float = 1e-3) -> IPAutoencoder:
        """
        Train autoencoder on valid IPA sequences.

        Args:
            valid_ipa_list: List of valid IPA transcriptions
            tokenizer: G2PTokenizer
            epochs: Training epochs
            batch_size: Batch size
            lr: Learning rate

        Returns:
            Trained IPAutoencoder
        """
        # Create autoencoder
        autoencoder = IPAutoencoder(
            vocab_size=tokenizer.phoneme_vocab_size,
            embedding_dim=128,
            hidden_dim=256,
            latent_dim=128,
            max_length=tokenizer.max_phoneme_length
        ).to(self.device)

        # Prepare data
        sequences = []
        for ipa in valid_ipa_list:
            ids = tokenizer.encode_phoneme(ipa, add_bos=False, add_eos=False)
            if len(ids) <= tokenizer.max_phoneme_length:
                sequences.append(ids)

        # Pad sequences
        max_len = min(max(len(s) for s in sequences), tokenizer.max_phoneme_length)
        padded = []
        for ids in sequences:
            if len(ids) < max_len:
                ids = ids + [0] * (max_len - len(ids))
            padded.append(ids[:max_len])

        dataset = torch.tensor(padded, dtype=torch.long)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        # Training
        optimizer = torch.optim.Adam(autoencoder.parameters(), lr=lr)
        criterion = nn.CrossEntropyLoss(ignore_index=0)  # Ignore padding

        autoencoder.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch in dataloader:
                batch = batch.to(self.device)
                logits, _ = autoencoder(batch)

                # Shift for next-token prediction
                targets = batch.clone()
                targets[:, -1] = 0  # Remove last token

                loss = criterion(logits.view(-1, logits.size(-1)), targets.view(-1))

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                total_loss += loss.item()

            if (epoch + 1) % 10 == 0:
                print(f"Autoencoder epoch {epoch + 1}/{epochs}, loss: {total_loss / len(dataloader):.4f}")

        autoencoder.eval()
        self.autoencoder = autoencoder

        return autoencoder

    def set_thresholds(self,
                       confidence: Optional[float] = None,
                       reconstruction: Optional[float] = None) -> None:
        """
        Update detection thresholds.

        Args:
            confidence: New confidence threshold
            reconstruction: New reconstruction threshold
        """
        if confidence is not None:
            self.confidence_threshold = confidence
        if reconstruction is not None:
            self.reconstruction_threshold = reconstruction

    def get_thresholds(self) -> Dict[str, float]:
        """Get current thresholds."""
        return {
            'confidence': self.confidence_threshold,
            'reconstruction': self.reconstruction_threshold,
        }


def create_anomaly_detector(model_path: str,
                            config: ModelConfig,
                            tokenizer: G2PTokenizer,
                            confidence_threshold: float = 0.5,
                            reconstruction_threshold: float = 0.3) -> G2PAnomalyDetector:
    """
    Create an anomaly detector from a saved model.

    Args:
        model_path: Path to model checkpoint
        config: ModelConfig
        tokenizer: G2PTokenizer
        confidence_threshold: Confidence threshold
        reconstruction_threshold: Reconstruction threshold

    Returns:
        Configured G2PAnomalyDetector
    """
    # Load model
    model = G2PModel(config)
    # The checkpoint is produced locally by this training script, so it is
    # trusted; allow unpickling of its embedded config/dataclasses.
    checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    preprocessor = G2PPreprocessor()

    detector = G2PAnomalyDetector(
        model=model,
        tokenizer=tokenizer,
        preprocessor=preprocessor,
        confidence_threshold=confidence_threshold,
        reconstruction_threshold=reconstruction_threshold
    )

    return detector


def create_anomaly_detector_from_bundle(
    pt_path: str,
    json_path: str,
    confidence_threshold: float = 0.5,
    reconstruction_threshold: float = 0.3,
) -> G2PAnomalyDetector:
    """
    Create an anomaly detector from a self-contained sidecar bundle.

    The bundle consists of two files produced by the training script:
      * ``<name>.pt``   -- model weights only (safe to load with
                           ``weights_only=True``; no arbitrary code execution)
      * ``<name>.json`` -- ``{"ipa_writing_system", "model_config",
                           "grapheme_vocab", "phoneme_vocab"}``

    This is the format discovered and loaded by the application's
    ``IPAAnomalyService``.

    Args:
        pt_path: Path to the ``.pt`` weights file.
        json_path: Path to the companion ``.json`` metadata file.
        confidence_threshold: Confidence threshold.
        reconstruction_threshold: Reconstruction threshold.

    Returns:
        Configured G2PAnomalyDetector.
    """
    import json

    with open(json_path, "r", encoding="utf-8") as fh:
        meta = json.load(fh)

    config = ModelConfig(**meta["model_config"])
    tokenizer = G2PTokenizer(
        grapheme_vocab=meta["grapheme_vocab"],
        phoneme_vocab=meta["phoneme_vocab"],
    )

    # Weights-only load: the ``.pt`` contains tensors only, so it cannot
    # execute arbitrary code on load.
    checkpoint = torch.load(pt_path, map_location="cpu", weights_only=True)
    model = G2PModel(config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    preprocessor = G2PPreprocessor()

    detector = G2PAnomalyDetector(
        model=model,
        tokenizer=tokenizer,
        preprocessor=preprocessor,
        confidence_threshold=confidence_threshold,
        reconstruction_threshold=reconstruction_threshold,
    )

    return detector


if __name__ == '__main__':
    print("G2P Anomaly Detector module loaded.")
    print("Usage: Initialize with trained model and optionally train autoencoder.")
