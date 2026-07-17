"""
Shared fixtures for coverage module unit tests.
"""
import pytest
from app.services.coverage_check.models import (
    LexicalSenseFormat, Metadata, Entry, Sense, Example, UsageNote,
    GapAnalysis, GapSummary, MissingHeadword, MissingSense,
)


@pytest.fixture
def minimal_clsf():
    """A minimal CLSF with one entry for testing."""
    return LexicalSenseFormat(
        metadata=Metadata(
            name="test-dictionary",
            version="1.0",
            language="en",
        ),
        entries=[
            Entry(
                headword="hello",
                part_of_speech="interjection",
                language="en",
                senses=[
                    Sense(
                        id="s1",
                        definition="Used as a greeting",
                        translations=["halo", "cześć"],
                    )
                ],
            )
        ],
    )


@pytest.fixture
def bilingual_clsf():
    """CLSF with entries in two languages for gap analysis testing."""
    return LexicalSenseFormat(
        metadata=Metadata(
            name="test-bilingual",
            version="1.0",
            language="en",
        ),
        entries=[
            Entry(
                headword="cat",
                part_of_speech="noun",
                language="en",
                senses=[
                    Sense(id="s1", definition="A small feline", translations=["кот"]),
                    Sense(id="s2", definition="A person", translations=[]),
                ],
            ),
            Entry(
                headword="dog",
                part_of_speech="noun",
                language="en",
                senses=[
                    Sense(id="s3", definition="A canine", translations=["собака"]),
                ],
            ),
        ],
    )


@pytest.fixture
def wn_baseline_clsf():
    """Simulated WordNet baseline for gap analysis."""
    return LexicalSenseFormat(
        metadata=Metadata(
            name="wordnet-baseline",
            version="3.1",
            language="en",
        ),
        entries=[
            Entry(
                headword="cat",
                part_of_speech="noun",
                language="en",
                senses=[
                    Sense(id="wn:s1", definition="feline mammal", translations=["кот"]),
                    Sense(id="wn:s2", definition="guy", translations=[]),
                    Sense(id="wn:s3", definition="game equipment", translations=[]),
                ],
            ),
            Entry(
                headword="dog",
                part_of_speech="noun",
                language="en",
                senses=[
                    Sense(id="wn:s4", definition="canine", translations=["собака"]),
                    Sense(id="wn:s5", definition="unattractive person", translations=[]),
                ],
            ),
            Entry(
                headword="car",
                part_of_speech="noun",
                language="en",
                senses=[
                    Sense(id="wn:s6", definition="automobile", translations=["автомобиль"]),
                ],
            ),
        ],
    )
