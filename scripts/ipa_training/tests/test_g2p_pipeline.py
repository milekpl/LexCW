"""Unit tests for the G2P pipeline (training smoke + anomaly detection)."""

from __future__ import annotations

from pathlib import Path

from g2p import (
    G2PModel,
    ModelConfig,
    G2PTokenizer,
    build_vocab_from_data,
    G2PPreprocessor,
    G2PTrainer,
    TrainingConfig,
    G2PDataset,
    G2PAnomalyDetector,
)


# NOTE: IPA uses canonical script-g (U+0261), and avoids combining tie-bars /
# palatalization marks, which the G2P preprocessor's IPA validator rejects.
SAMPLE_PAIRS = [
    ("cat", "kæt"),
    ("dog", "dɔɡ"),
    ("bird", "bɜːd"),
    ("water", "wɔtə"),
    ("house", "haʊs"),
    ("tree", "triː"),
    ("sun", "sʌn"),
    ("moon", "mun"),
    ("book", "bʊk"),
    ("fish", "fɪʃ"),
    ("church", "tʃɜːtʃ"),
    ("judge", "dʒʌdʒ"),
]


def _build_trained_model(tmp_path: Path):
    grapheme_vocab, phoneme_vocab = build_vocab_from_data(SAMPLE_PAIRS)
    tokenizer = G2PTokenizer(grapheme_vocab=grapheme_vocab, phoneme_vocab=phoneme_vocab)
    config = ModelConfig(
        grapheme_vocab_size=len(grapheme_vocab),
        phoneme_vocab_size=len(phoneme_vocab),
        pad_token_id=tokenizer.PAD_ID,
        bos_token_id=tokenizer.BOS_ID,
        eos_token_id=tokenizer.EOS_ID,
    )
    model = G2PModel(config)
    preprocessor = G2PPreprocessor()
    train_dataset = G2PDataset(SAMPLE_PAIRS[:-1], tokenizer, preprocessor)
    val_dataset = G2PDataset(SAMPLE_PAIRS[-1:], tokenizer, preprocessor)
    train_config = TrainingConfig(
        batch_size=4,
        num_epochs=1,
        learning_rate=1e-3,
        output_dir=str(tmp_path / "ckpt"),
        eval_interval=1000,
        save_interval=1000,
    )
    trainer = G2PTrainer(
        model=model,
        tokenizer=tokenizer,
        config=train_config,
        train_dataset=train_dataset,
        val_dataset=val_dataset,
    )
    trainer.train()
    return model, tokenizer, config, trainer


def test_tokenizer_roundtrip():
    grapheme_vocab, phoneme_vocab = build_vocab_from_data(SAMPLE_PAIRS)
    tokenizer = G2PTokenizer(
        grapheme_vocab=grapheme_vocab, phoneme_vocab=phoneme_vocab
    )
    g_ids = tokenizer.encode_grapheme("kot")
    p_ids = tokenizer.encode_phoneme("kɔt")
    assert tokenizer.decode_grapheme(g_ids) == "kot"
    assert tokenizer.decode_phoneme(p_ids) == "kɔt"
    assert isinstance(tokenizer.grapheme_vocab_size, int)


def test_train_runs_and_produces_finite_loss(tmp_path: Path):
    _, _, _, trainer = _build_trained_model(tmp_path)
    assert isinstance(trainer.best_val_loss, float)
    assert trainer.best_val_loss == trainer.best_val_loss  # not NaN
    assert (tmp_path / "ckpt" / "best_model.pt").exists()


def test_anomaly_detector_runs(tmp_path: Path):
    model, tokenizer, config, _ = _build_trained_model(tmp_path)
    model.eval()
    detector = G2PAnomalyDetector(
        model=model,
        tokenizer=tokenizer,
        preprocessor=G2PPreprocessor(),
        confidence_threshold=0.5,
    )
    result = detector.detect("kot", "kɔt")
    assert result.lexeme == "kot"
    assert isinstance(result.predicted_ipa, str)
    assert 0.0 <= result.confidence_score <= 1.0
    assert result.stored_ipa == "kɔt"


def test_anomaly_detector_flags_wrong_ipa(tmp_path: Path):
    model, tokenizer, config, _ = _build_trained_model(tmp_path)
    model.eval()
    detector = G2PAnomalyDetector(
        model=model,
        tokenizer=tokenizer,
        preprocessor=G2PPreprocessor(),
        confidence_threshold=0.5,
    )
    correct = detector.detect("kot", "kɔt")
    wrong = detector.detect("kot", "zzzqqq")
    # A clearly invalid IPA should score no higher than the plausible one.
    assert wrong.confidence_score <= correct.confidence_score
