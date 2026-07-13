# encoding: UTF-8
"""
G2P package - Grapheme-to-Phoneme model for IPA pronunciation prediction.

Self-contained adaptation of the Wielki dictionary G2P modules, used by the
published LexCW training script (``scripts/ipa_training``). Provides a small
CPU-trainable encoder-decoder transformer, character-level tokenizer, IPA
preprocessor, trainer, generator, and a dual-method pronunciation anomaly
detector.

Requires ``torch`` (and ``transformers`` for training).
"""

from __future__ import annotations

from .model import G2PModel, ModelConfig
from .tokenizer import G2PTokenizer, build_vocab_from_data
from .preprocessor import G2PPreprocessor
from .trainer import (
    G2PTrainer,
    TrainingConfig,
    G2PDataset,
    G2PDataCollator,
)
from .generator import G2PGenerator, load_generator
from .anomaly_detector import (
    G2PAnomalyDetector,
    IPAutoencoder,
    AnomalyResult,
    create_anomaly_detector,
    create_anomaly_detector_from_bundle,
)

__all__ = [
    "G2PModel",
    "ModelConfig",
    "G2PTokenizer",
    "build_vocab_from_data",
    "G2PPreprocessor",
    "G2PTrainer",
    "TrainingConfig",
    "G2PDataset",
    "G2PDataCollator",
    "G2PGenerator",
    "load_generator",
    "G2PAnomalyDetector",
    "IPAutoencoder",
    "AnomalyResult",
    "create_anomaly_detector",
]
