# encoding: UTF-8
"""
G2P Generator - Generate missing pronunciations for dictionary entries.

Provides:
- Batch generation for entries without IPA
- Confidence scoring
- Integration with LLM filtering
"""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

import torch

try:
    from .model import G2PModel, ModelConfig
    from .tokenizer import G2PTokenizer
    from .preprocessor import G2PPreprocessor
except ImportError:
    from model import G2PModel, ModelConfig
    from tokenizer import G2PTokenizer
    from preprocessor import G2PPreprocessor


class ConfidenceLevel(Enum):
    """Confidence levels for generated pronunciations."""
    HIGH = "high"      # PER < 0.1
    MEDIUM = "medium"  # PER < 0.3
    LOW = "low"        # PER < 0.5
    VERY_LOW = "very_low"  # PER >= 0.5


@dataclass
class GenerationResult:
    """Result of pronunciation generation."""
    lexeme: str
    pos: Optional[str]
    generated_ipa: str
    confidence_score: float
    confidence_level: ConfidenceLevel
    is_valid: bool = True
    rejection_reason: Optional[str] = None
    filtered_by_llm: bool = False
    llm_verdict: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'lexeme': self.lexeme,
            'pos': self.pos,
            'generated_ipa': self.generated_ipa,
            'confidence_score': self.confidence_score,
            'confidence_level': self.confidence_level.value,
            'is_valid': self.is_valid,
            'rejection_reason': self.rejection_reason,
            'filtered_by_llm': self.filtered_by_llm,
            'llm_verdict': self.llm_verdict,
        }


class G2PGenerator:
    """
    Generate pronunciations for dictionary entries missing IPA.
    """

    def __init__(self,
                 model: G2PModel,
                 tokenizer: G2PTokenizer,
                 preprocessor: G2PPreprocessor,
                 min_confidence: float = 0.3,
                 device: Optional[torch.device] = None):
        """
        Initialize generator.

        Args:
            model: Trained G2PModel
            tokenizer: G2PTokenizer
            preprocessor: G2PPreprocessor
            min_confidence: Minimum confidence for acceptance
            device: Computation device
        """
        self.model = model
        self.tokenizer = tokenizer
        self.preprocessor = preprocessor
        self.min_confidence = min_confidence

        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = device

        self.model.to(self.device)
        self.model.eval()

    def generate(self,
                 lexeme: str,
                 pos: Optional[str] = None,
                 num_return_sequences: int = 1,
                 temperature: float = 0.8,
                 top_k: int = 50,
                 top_p: float = 0.95) -> List[GenerationResult]:
        """
        Generate pronunciation for a single entry.

        Args:
            lexeme: The headword
            pos: Optional part of speech
            num_return_sequences: Number of hypotheses to generate
            temperature: Sampling temperature
            top_k: Top-k sampling parameter
            top_p: Top-p sampling parameter

        Returns:
            List of GenerationResult objects
        """
        # Tokenize input
        input_text = lexeme
        if pos:
            input_text = f"[{pos}] {lexeme}"

        input_ids = self.tokenizer.encode_grapheme(lexeme, add_bos=False, add_eos=False)
        input_tensor = torch.tensor([input_ids], dtype=torch.long).to(self.device)
        attention_mask = (input_tensor != self.tokenizer.PAD_ID)

        results = []

        with torch.no_grad():
            generated = self.model.generate(
                input_tensor,
                attention_mask,
                max_length=self.tokenizer.max_phoneme_length,
                num_beams=num_return_sequences,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                early_stopping=True
            )

        for gen_seq in generated:
            predicted_ipa = self.tokenizer.decode_phoneme(gen_seq.tolist())

            # Validate
            is_valid, reason = self._validate_generation(predicted_ipa)
            confidence_score = self._compute_confidence(predicted_ipa)
            confidence_level = self._get_confidence_level(confidence_score)

            result = GenerationResult(
                lexeme=lexeme,
                pos=pos,
                generated_ipa=predicted_ipa,
                confidence_score=confidence_score,
                confidence_level=confidence_level,
                is_valid=is_valid,
                rejection_reason=reason if not is_valid else None
            )

            results.append(result)

        return results

    def generate_batch(self,
                       entries: List[Dict[str, str]],
                       num_return_sequences: int = 1,
                       show_progress: bool = True,
                       callback: Optional[Any] = None) -> List[GenerationResult]:
        """
        Generate pronunciations for multiple entries.

        Args:
            entries: List of {'lexeme': str, 'pos': Optional[str]}
            num_return_sequences: Number of hypotheses per entry
            show_progress: Show progress bar
            callback: Optional callback for progress updates

        Returns:
            List of GenerationResult objects
        """
        all_results = []
        iterator = enumerate(entries)

        if show_progress:
            from tqdm import tqdm
            iterator = tqdm(iterator, total=len(entries), desc="Generating")

        for i, entry in iterator:
            results = self.generate(
                entry['lexeme'],
                pos=entry.get('pos'),
                num_return_sequences=num_return_sequences
            )
            all_results.extend(results)

            if callback:
                callback(i, len(entries), results)

        return all_results

    def _validate_generation(self, ipa: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a generated IPA string.

        Args:
            ipa: Generated IPA string

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        if not ipa:
            return False, "Empty IPA"

        if len(ipa) < 2:
            return False, "Too short"

        # Check for stress markers
        has_stress = 'ˈ' in ipa or 'ˌ' in ipa
        if not has_stress:
            # Some words might legitimately not have stress marked
            # Just add a note
            pass

        # Validate using preprocessor
        is_valid, reason = self.preprocessor.validate_ipa(ipa)
        if not is_valid:
            return False, reason

        return True, None

    def _compute_confidence(self, ipa: str) -> float:
        """
        Compute confidence score for a generation.

        Simple heuristic: based on phoneme validity and patterns.

        Args:
            ipa: Generated IPA string

        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 1.0

        # Penalty for missing stress
        if 'ˈ' not in ipa and 'ˌ' not in ipa:
            confidence -= 0.1

        # Bonus for reasonable length
        length = len(ipa)
        if 3 <= length <= 15:
            confidence += 0.1
        elif length > 20:
            confidence -= 0.1

        # Check for unusual character combinations
        # This is a simple heuristic - a real model would use learned patterns

        return max(0.0, min(1.0, confidence))

    def _get_confidence_level(self, score: float) -> ConfidenceLevel:
        """Convert numerical score to confidence level."""
        if score >= 0.9:
            return ConfidenceLevel.HIGH
        elif score >= 0.7:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.5:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def filter_by_confidence(self,
                             results: List[GenerationResult],
                             min_confidence: Optional[float] = None,
                             min_level: Optional[ConfidenceLevel] = None) -> List[GenerationResult]:
        """
        Filter results by confidence.

        Args:
            results: List of GenerationResult objects
            min_confidence: Minimum numerical confidence
            min_level: Minimum confidence level

        Returns:
            Filtered list
        """
        if min_confidence is None:
            min_confidence = self.min_confidence

        filtered = []
        for r in results:
            if not r.is_valid:
                continue

            if r.confidence_score < min_confidence:
                continue

            if min_level is not None:
                level_order = [ConfidenceLevel.VERY_LOW, ConfidenceLevel.LOW,
                              ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]
                if level_order.index(r.confidence_level) < level_order.index(min_level):
                    continue

            filtered.append(r)

        return filtered

    def get_best_generation(self,
                            results: List[GenerationResult]) -> Optional[GenerationResult]:
        """
        Get the best generation from results.

        Args:
            results: List of GenerationResult objects

        Returns:
            Best result or None
        """
        valid = [r for r in results if r.is_valid and not r.filtered_by_llm]
        if not valid:
            return None

        return max(valid, key=lambda r: r.confidence_score)

    def format_for_flex(self,
                        result: GenerationResult,
                        add_review_flag: bool = True) -> str:
        """
        Format generated IPA for adding to FLEx.

        Args:
            result: GenerationResult
            add_review_flag: Add review marker

        Returns:
            Formatted IPA string
        """
        parts = [result.generated_ipa]

        if add_review_flag:
            parts.append(f"[G2P:{result.confidence_level.value}]")

        return ' '.join(parts)

    def export_results(self,
                       results: List[GenerationResult],
                       filepath: str,
                       include_filtered: bool = False) -> None:
        """
        Export generation results to JSON.

        Args:
            results: List of GenerationResult objects
            filepath: Output file path
            include_filtered: Include filtered-out results
        """
        export_data = []

        for r in results:
            if not include_filtered and r.filtered_by_llm:
                continue

            export_data.append(r.to_dict())

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

    def import_entries(self, filepath: str) -> List[Dict[str, str]]:
        """
        Import entries from JSON file for generation.

        Args:
            filepath: Input file path

        Returns:
            List of {'lexeme': str, 'pos': Optional[str]} dicts
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return [{'lexeme': item['lexeme'], 'pos': item.get('pos')}
                for item in data]


def load_generator(model_path: str,
                   config: ModelConfig,
                   tokenizer: G2PTokenizer,
                   min_confidence: float = 0.3) -> G2PGenerator:
    """
    Load a generator from saved model.

    Args:
        model_path: Path to model checkpoint
        config: ModelConfig
        tokenizer: G2PTokenizer
        min_confidence: Minimum confidence threshold

    Returns:
        Configured G2PGenerator
    """
    # Load model
    model = G2PModel(config)
    checkpoint = torch.load(model_path, map_location='cpu')
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    preprocessor = G2PPreprocessor()

    return G2PGenerator(
        model=model,
        tokenizer=tokenizer,
        preprocessor=preprocessor,
        min_confidence=min_confidence
    )


if __name__ == '__main__':
    print("G2P Generator module loaded.")
    print("Usage: Initialize with trained model and call generate() or generate_batch().")
