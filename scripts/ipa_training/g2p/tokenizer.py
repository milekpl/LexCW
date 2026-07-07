# encoding: UTF-8
"""
G2P Tokenizer - Character-level tokenization for G2P training.

Provides character-level vocabulary and tokenization for:
- Grapheme (headword) sequences
- Phoneme (IPA) sequences
- Special tokens for sequence start/end/padding
"""

import json
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

import torch


class G2PTokenizer:
    """
    Character-level tokenizer for G2P.

    Maintains separate vocabularies for:
    - Grapheme tokens (letters, diacritics)
    - Phoneme tokens (IPA characters)

    Special tokens:
    - <PAD>: Padding token
    - <UNK>: Unknown character
    - <BOS>: Beginning of sequence
    - <EOS>: End of sequence
    """

    # Special token constants
    PAD_TOKEN = '<PAD>'
    UNK_TOKEN = '<UNK>'
    BOS_TOKEN = '<BOS>'
    EOS_TOKEN = '<EOS>'

    # Default special token IDs
    PAD_ID = 0
    UNK_ID = 1
    BOS_ID = 2
    EOS_ID = 3

    def __init__(self,
                 grapheme_vocab: Optional[Dict[str, int]] = None,
                 phoneme_vocab: Optional[Dict[str, int]] = None,
                 max_grapheme_length: int = 50,
                 max_phoneme_length: int = 100):
        """
        Initialize the tokenizer.

        Args:
            grapheme_vocab: Optional pre-defined grapheme vocabulary
            phoneme_vocab: Optional pre-defined phoneme vocabulary
            max_grapheme_length: Maximum grapheme sequence length
            max_phoneme_length: Maximum phoneme sequence length
        """
        self.max_grapheme_length = max_grapheme_length
        self.max_phoneme_length = max_phoneme_length

        # Initialize vocabularies
        if grapheme_vocab:
            self.grapheme_vocab = grapheme_vocab
        else:
            self.grapheme_vocab = self._build_default_grapheme_vocab()

        if phoneme_vocab:
            self.phoneme_vocab = phoneme_vocab
        else:
            self.phoneme_vocab = self._build_default_phoneme_vocab()

        # Build reverse vocabularies
        self.grapheme_ids_to_tokens = {v: k for k, v in self.grapheme_vocab.items()}
        self.phoneme_ids_to_tokens = {v: k for k, v in self.phoneme_vocab.items()}

        # Vocabulary sizes (including special tokens)
        self.grapheme_vocab_size = len(self.grapheme_vocab)
        self.phoneme_vocab_size = len(self.phoneme_vocab)

    def _build_default_grapheme_vocab(self) -> Dict[str, int]:
        """Build default grapheme vocabulary from English/Polish characters."""
        vocab = OrderedDict()

        # Add special tokens first
        vocab[self.PAD_TOKEN] = self.PAD_ID
        vocab[self.UNK_TOKEN] = self.UNK_ID
        vocab[self.BOS_TOKEN] = self.BOS_ID
        vocab[self.EOS_TOKEN] = self.EOS_ID

        # English lowercase letters
        for c in 'abcdefghijklmnopqrstuvwxyz':
            vocab[c] = len(vocab)

        # English uppercase letters
        for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            vocab[c] = len(vocab)

        # Polish diacritics
        polish_chars = 'ąćęłńóśźżĄĆĘŁŃÓŚŨŻ'  # Note: some may not render but are valid
        for c in polish_chars:
            vocab[c] = len(vocab)

        # Common grapheme patterns (hyphen, apostrophe for compounds/contractions)
        vocab['-'] = len(vocab)
        vocab["'"] = len(vocab)
        vocab[' '] = len(vocab)

        return vocab

    def _build_default_phoneme_vocab(self) -> Dict[str, int]:
        """Build default phoneme vocabulary from IPA characters."""
        vocab = OrderedDict()

        # Add special tokens first
        vocab[self.PAD_TOKEN] = self.PAD_ID
        vocab[self.UNK_TOKEN] = self.UNK_ID
        vocab[self.BOS_TOKEN] = self.BOS_ID
        vocab[self.EOS_TOKEN] = self.EOS_ID

        # IPA vowels (monophthongs)
        vowels = 'aeiouəæɛɪʊɔʌɜɐɑːɪ̈ʉɯɤoøɵ'  # Including long vowels and schwa
        for c in vowels:
            vocab[c] = len(vocab)

        # IPA consonants
        consonants = (
            'pbtdkgfvsʃʒɲɳŋm nlrʔʘǃǂɕʑɣɦʁʀwʍhj'
            'çɟɥɬɮʎʏzðθvɸβʦʧ'
        )
        for c in consonants:
            if c not in vocab:
                vocab[c] = len(vocab)

        # Stress markers
        vocab['ˈ'] = len(vocab)  # Primary stress
        vocab['ˌ'] = len(vocab)  # Secondary stress

        # Syllable delimiter
        vocab['.'] = len(vocab)

        return vocab

    def encode_grapheme(self, grapheme: str,
                        add_bos: bool = True,
                        add_eos: bool = True) -> List[int]:
        """
        Encode a grapheme string to token IDs.

        Args:
            grapheme: Input string
            add_bos: Whether to add beginning-of-sequence token
            add_eos: Whether to add end-of-sequence token

        Returns:
            List of token IDs
        """
        tokens = []

        if add_bos:
            tokens.append(self.BOS_ID)

        for char in grapheme[:self.max_grapheme_length]:
            if char in self.grapheme_vocab:
                tokens.append(self.grapheme_vocab[char])
            else:
                tokens.append(self.UNK_ID)

        if add_eos:
            tokens.append(self.EOS_ID)

        return tokens

    def decode_grapheme(self, token_ids: List[int]) -> str:
        """
        Decode token IDs back to grapheme string.

        Args:
            token_ids: List of token IDs

        Returns:
            Decoded string
        """
        chars = []
        for tid in token_ids:
            if tid == self.EOS_ID:
                break
            if tid in (self.PAD_ID, self.BOS_ID):
                continue
            if tid in self.grapheme_ids_to_tokens:
                chars.append(self.grapheme_ids_to_tokens[tid])
        return ''.join(chars)

    def encode_phoneme(self, phoneme: str,
                       add_bos: bool = True,
                       add_eos: bool = True) -> List[int]:
        """
        Encode a phoneme (IPA) string to token IDs.

        Args:
            phoneme: IPA string
            add_bos: Whether to add beginning-of-sequence token
            add_eos: Whether to add end-of-sequence token

        Returns:
            List of token IDs
        """
        tokens = []

        if add_bos:
            tokens.append(self.BOS_ID)

        # Simple character-by-character encoding (no stress marker combining)
        for char in phoneme[:self.max_phoneme_length]:
            if char in self.phoneme_vocab:
                tokens.append(self.phoneme_vocab[char])
            else:
                tokens.append(self.UNK_ID)

        if add_eos:
            tokens.append(self.EOS_ID)

        return tokens

    def decode_phoneme(self, token_ids: List[int]) -> str:
        """
        Decode token IDs back to phoneme string.

        Args:
            token_ids: List of token IDs

        Returns:
            Decoded IPA string
        """
        chars = []
        for tid in token_ids:
            if tid == self.EOS_ID:
                break
            if tid in (self.PAD_ID, self.BOS_ID):
                continue
            if tid in self.phoneme_ids_to_tokens:
                chars.append(self.phoneme_ids_to_tokens[tid])
        return ''.join(chars)

    def encode_pair(self, grapheme: str, phoneme: str,
                    add_bos: bool = True,
                    add_eos: bool = True) -> Tuple[List[int], List[int]]:
        """
        Encode a grapheme-phoneme pair.

        Args:
            grapheme: Headword string
            phoneme: IPA string
            add_bos: Whether to add BOS token
            add_eos: Whether to add EOS token

        Returns:
            Tuple of (grapheme_ids, phoneme_ids)
        """
        grapheme_ids = self.encode_grapheme(grapheme, add_bos=add_bos, add_eos=add_eos)
        phoneme_ids = self.encode_phoneme(phoneme, add_bos=add_bos, add_eos=add_eos)
        return grapheme_ids, phoneme_ids

    def encode_batch(self, pairs: List[Tuple[str, str]],
                     padding: bool = True) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Encode a batch of grapheme-phoneme pairs.

        Args:
            pairs: List of (grapheme, phoneme) tuples
            padding: Whether to pad sequences

        Returns:
            Tuple of (grapheme_ids, phoneme_ids, attention_mask) tensors
        """
        grapheme_ids_list = []
        phoneme_ids_list = []
        attention_mask = []

        max_grapheme_len = max(len(g) for g, _ in pairs) if pairs else 0
        max_phoneme_len = max(len(p) for _, p in pairs) if pairs else 0

        # Apply max length constraints
        max_grapheme_len = min(max_grapheme_len, self.max_grapheme_length)
        max_phoneme_len = min(max_phoneme_len, self.max_phoneme_length)

        for grapheme, phoneme in pairs:
            g_ids = self.encode_grapheme(grapheme, add_bos=False, add_eos=False)
            p_ids = self.encode_phoneme(phoneme, add_bos=False, add_eos=False)

            # Truncate
            g_ids = g_ids[:max_grapheme_len]
            p_ids = p_ids[:max_phoneme_len]

            grapheme_ids_list.append(g_ids)
            phoneme_ids_list.append(p_ids)
            attention_mask.append([1] * len(g_ids))

        if padding:
            # Pad sequences
            g_ids = self._pad_sequences(grapheme_ids_list, max_grapheme_len, self.PAD_ID)
            p_ids = self._pad_sequences(phoneme_ids_list, max_phoneme_len, self.PAD_ID)
            mask = self._pad_sequences(attention_mask, max_grapheme_len, 0)
        else:
            g_ids = torch.tensor(grapheme_ids_list, dtype=torch.long)
            p_ids = torch.tensor(phoneme_ids_list, dtype=torch.long)
            mask = torch.tensor(attention_mask, dtype=torch.long)

        return g_ids, p_ids, mask

    def _pad_sequences(self, sequences: List[List[int]],
                       max_len: int, pad_value: int) -> torch.Tensor:
        """Pad a list of sequences."""
        result = []
        for seq in sequences:
            if len(seq) < max_len:
                seq = seq + [pad_value] * (max_len - len(seq))
            else:
                seq = seq[:max_len]
            result.append(seq)
        return torch.tensor(result, dtype=torch.long)

    def save_vocab(self, grapheme_path: str, phoneme_path: str) -> None:
        """
        Save vocabularies to JSON files.

        Args:
            grapheme_path: Path for grapheme vocabulary
            phoneme_path: Path for phoneme vocabulary
        """
        with open(grapheme_path, 'w', encoding='utf-8') as f:
            json.dump(self.grapheme_vocab, f, ensure_ascii=False, indent=2)

        with open(phoneme_path, 'w', encoding='utf-8') as f:
            json.dump(self.phoneme_vocab, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_vocab(cls, grapheme_path: str, phoneme_path: str) -> 'G2PTokenizer':
        """
        Load vocabularies from JSON files.

        Args:
            grapheme_path: Path to grapheme vocabulary
            phoneme_path: Path to phoneme vocabulary

        Returns:
            G2PTokenizer instance
        """
        with open(grapheme_path, 'r', encoding='utf-8') as f:
            grapheme_vocab = json.load(f)

        with open(phoneme_path, 'r', encoding='utf-8') as f:
            phoneme_vocab = json.load(f)

        return cls(grapheme_vocab=grapheme_vocab, phoneme_vocab=phoneme_vocab)

    def get_stats(self) -> Dict:
        """Get tokenizer statistics."""
        return {
            'grapheme_vocab_size': self.grapheme_vocab_size,
            'phoneme_vocab_size': self.phoneme_vocab_size,
            'max_grapheme_length': self.max_grapheme_length,
            'max_phoneme_length': self.max_phoneme_length,
            'special_tokens': {
                'pad': self.PAD_TOKEN,
                'unk': self.UNK_TOKEN,
                'bos': self.BOS_TOKEN,
                'eos': self.EOS_TOKEN,
            }
        }


def build_vocab_from_data(pairs: List[Tuple[str, str]],
                          min_freq: int = 1) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    Build vocabularies from training data.

    Args:
        pairs: List of (grapheme, phoneme) tuples
        min_freq: Minimum frequency for inclusion

    Returns:
        Tuple of (grapheme_vocab, phoneme_vocab)
    """
    from collections import Counter

    # Count characters
    grapheme_counts = Counter()
    phoneme_counts = Counter()

    for grapheme, phoneme in pairs:
        for char in grapheme:
            grapheme_counts[char] += 1
        for char in phoneme:
            phoneme_counts[char] += 1

    # Build vocabularies
    grapheme_vocab = {
        G2PTokenizer.PAD_TOKEN: G2PTokenizer.PAD_ID,
        G2PTokenizer.UNK_TOKEN: G2PTokenizer.UNK_ID,
        G2PTokenizer.BOS_TOKEN: G2PTokenizer.BOS_ID,
        G2PTokenizer.EOS_TOKEN: G2PTokenizer.EOS_ID,
    }

    phoneme_vocab = {
        G2PTokenizer.PAD_TOKEN: G2PTokenizer.PAD_ID,
        G2PTokenizer.UNK_TOKEN: G2PTokenizer.UNK_ID,
        G2PTokenizer.BOS_TOKEN: G2PTokenizer.BOS_ID,
        G2PTokenizer.EOS_TOKEN: G2PTokenizer.EOS_ID,
    }

    for char, freq in grapheme_counts.items():
        if freq >= min_freq:
            grapheme_vocab[char] = len(grapheme_vocab)

    for char, freq in phoneme_counts.items():
        if freq >= min_freq:
            phoneme_vocab[char] = len(phoneme_vocab)

    return grapheme_vocab, phoneme_vocab


if __name__ == '__main__':
    # Basic testing
    tokenizer = G2PTokenizer()

    test_pairs = [
        ('apple', 'ˈæpəl'),
        ('banana', 'bəˈnænə'),
        ('cat', 'kæt'),
        ('prehistory', 'priːˈhɪstərɪ'),
    ]

    print("Tokenizer Stats:")
    print(tokenizer.get_stats())
    print()

    for grapheme, phoneme in test_pairs:
        g_ids = tokenizer.encode_grapheme(grapheme)
        p_ids = tokenizer.encode_phoneme(phoneme)

        g_decoded = tokenizer.decode_grapheme(g_ids)
        p_decoded = tokenizer.decode_phoneme(p_ids)

        print(f"Grapheme: {grapheme}")
        print(f"  IDs: {g_ids}")
        print(f"  Decoded: {g_decoded}")
        print(f"Phoneme: {phoneme}")
        print(f"  IDs: {p_ids}")
        print(f"  Decoded: {p_decoded}")
        print()
