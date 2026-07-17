"""
Systematicity checker for dictionary coverage analysis.

Checks dictionary coverage against predefined reference datasets for
systematic lexical categories (elements, countries, months, etc.).
Reference datasets are loaded from JSON files in app/data/systematicity/.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from app.services.coverage_check.models import LexicalSenseFormat


class SystematicityCategory(Enum):
    CHEMICAL_ELEMENT = "chemical_element"
    GEOGRAPHY_COUNTRY = "geography_country"
    GEOGRAPHY_CAPITAL = "geography_capital"
    CALENDAR_MONTH = "calendar_month"
    CALENDAR_DAY = "calendar_day"
    CALENDAR_SEASON = "calendar_season"
    COLORS_BASIC = "colors_basic"
    KINSHIP_TERMS = "kinship_terms"
    EMOTIONS_BASIC = "emotions_basic"
    PROFESSIONS_COMMON = "professions_common"
    CURRENCIES_WORLD = "currencies_world"
    LANGUAGES_WORLD = "languages_world"
    PLANETS_SOLAR = "planets_solar"
    CONTINENTS_WORLD = "continents_world"
    BODY_PARTS_COMMON = "body_parts_common"
    DIRECTIONS_CARDINAL = "directions_cardinal"
    SHAPES_BASIC = "shapes_basic"
    MUSICAL_INSTRUMENTS = "musical_instruments"
    WEATHER_TERMS = "weather_terms"


# Built-in reference datasets (fallback if JSON files not present)
_BUILTIN_DATASETS: Dict[str, List[str]] = {
    "chemical_element": [
        "hydrogen", "helium", "lithium", "beryllium", "boron", "carbon",
        "nitrogen", "oxygen", "fluorine", "neon", "sodium", "magnesium",
        "aluminum", "silicon", "phosphorus", "sulfur", "chlorine", "argon",
        "potassium", "calcium", "scandium", "titanium", "vanadium",
        "chromium", "manganese", "iron", "cobalt", "nickel", "copper",
        "zinc", "gallium", "germanium", "arsenic", "selenium", "bromine",
        "krypton", "rubidium", "strontium", "yttrium", "zirconium",
        "niobium", "molybdenum", "technetium", "ruthenium", "rhodium",
        "palladium", "silver", "cadmium", "indium", "tin", "antimony",
        "tellurium", "iodine", "xenon", "cesium", "barium", "lanthanum",
        "cerium", "praseodymium", "neodymium", "promethium", "samarium",
        "europium", "gadolinium", "terbium", "dysprosium", "holmium",
        "erbium", "thulium", "ytterbium", "lutetium", "hafnium", "tantalum",
        "tungsten", "rhenium", "osmium", "iridium", "platinum", "gold",
        "mercury", "thallium", "lead", "bismuth", "polonium", "astatine",
        "radon", "francium", "radium", "actinium", "thorium", "protactinium",
        "uranium", "neptunium", "plutonium", "americium", "curium",
        "berkelium", "californium", "einsteinium", "fermium", "mendelevium",
        "nobelium", "lawrencium", "rutherfordium", "dubnium", "seaborgium",
        "bohrium", "hassium", "meitnerium", "darmstadtium", "roentgenium",
        "copernicium", "nihonium", "flerovium", "moscovium", "livermorium",
        "tennessine", "oganesson",
    ],
    "calendar_month": [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    ],
    "calendar_day": [
        "monday", "tuesday", "wednesday", "thursday", "friday",
        "saturday", "sunday",
    ],
    "calendar_season": ["spring", "summer", "autumn", "winter"],
    "colors_basic": [
        "red", "orange", "yellow", "green", "blue", "purple",
        "black", "white", "brown", "pink", "gray", "grey",
    ],
    "kinship_terms": [
        "mother", "father", "sister", "brother", "daughter", "son",
        "wife", "husband", "grandmother", "grandfather", "aunt", "uncle",
        "cousin", "niece", "nephew", "mother-in-law", "father-in-law",
    ],
    "planets_solar": [
        "mercury", "venus", "earth", "mars", "jupiter", "saturn",
        "uranus", "neptune",
    ],
    "continents_world": [
        "africa", "antarctica", "asia", "australia", "europe",
        "north america", "south america",
    ],
    "geography_country": [
        "afghanistan", "albania", "algeria", "argentina", "armenia",
        "australia", "austria", "bangladesh", "belgium", "bolivia",
        "brazil", "bulgaria", "cambodia", "cameroon", "canada",
        "chile", "china", "colombia", "congo", "costa rica",
        "croatia", "cuba", "czech republic", "denmark", "ecuador",
        "egypt", "ethiopia", "finland", "france", "germany",
        "ghana", "greece", "guatemala", "haiti", "honduras",
        "hungary", "iceland", "india", "indonesia", "iran",
        "iraq", "ireland", "israel", "italy", "jamaica",
        "japan", "jordan", "kazakhstan", "kenya", "kuwait",
        "laos", "lebanon", "libya", "malaysia", "mexico",
        "mongolia", "morocco", "mozambique", "myanmar", "nepal",
        "netherlands", "new zealand", "nicaragua", "nigeria",
        "north korea", "norway", "pakistan", "panama", "paraguay",
        "peru", "philippines", "poland", "portugal", "qatar",
        "romania", "russia", "saudi arabia", "senegal", "serbia",
        "singapore", "slovakia", "slovenia", "somalia", "south africa",
        "south korea", "spain", "sri lanka", "sudan", "sweden",
        "switzerland", "syria", "taiwan", "tanzania", "thailand",
        "tunisia", "turkey", "uganda", "ukraine", "united arab emirates",
        "united kingdom", "united states", "uruguay", "uzbekistan",
        "venezuela", "vietnam", "yemen", "zambia", "zimbabwe",
    ],
    "directions_cardinal": [
        "north", "south", "east", "west",
    ],
    "shapes_basic": [
        "circle", "square", "triangle", "rectangle", "oval",
        "pentagon", "hexagon", "diamond",
    ],
}


@dataclass
class SystematicityCheck:
    """Result of a systematicity check for one category."""
    category: SystematicityCategory
    reference_count: int
    found_count: int
    missing_count: int
    coverage_percent: float
    found_items: List[str]
    missing_items: List[str]


@dataclass
class SystematicityReport:
    """Complete systematicity analysis report."""
    total_checks: int = 0
    overall_coverage: float = 0.0
    checks: List[SystematicityCheck] = field(default_factory=list)

    def generate_report(self, format: str = "markdown") -> str:
        if format == "json":
            import json
            return json.dumps({
                "total_checks": self.total_checks,
                "overall_coverage": round(self.overall_coverage, 1),
                "checks": [
                    {
                        "category": c.category.value,
                        "coverage_percent": round(c.coverage_percent, 1),
                        "found_count": c.found_count,
                        "missing_count": c.missing_count,
                        "missing_items": c.missing_items[:20],
                    }
                    for c in self.checks
                ],
            }, indent=2, ensure_ascii=False)

        lines = [
            "# Systematicity Report",
            "",
            f"**Total categories checked:** {self.total_checks}",
            f"**Overall coverage:** {self.overall_coverage:.1f}%",
            "",
            "| Category | Found | Missing | Coverage |",
            "|----------|-------|---------|----------|",
        ]
        for c in self.checks:
            status = "✅" if c.coverage_percent >= 90 else ("⚠️" if c.coverage_percent >= 70 else "❌")
            lines.append(
                f"| {c.category.value} | {c.found_count} | "
                f"{c.missing_count} | {status} {c.coverage_percent:.1f}% |"
            )
        lines.append("")

        for c in self.checks:
            if c.missing_items:
                lines.append(f"## {c.category.value} — missing items")
                lines.append("")
                lines.append(", ".join(c.missing_items[:30]))
                if len(c.missing_items) > 30:
                    lines.append(f"... and {len(c.missing_items) - 30} more")
                lines.append("")

        return "\n".join(lines)


class SystematicityChecker:
    """Checks dictionary coverage against reference datasets."""

    def __init__(self, language: str = "en", data_dir: str = None):
        self.language = language
        self._data_dir = data_dir
        self._datasets: Dict[str, List[str]] = {}
        self._load_datasets()

    def _load_datasets(self) -> None:
        """Load reference datasets from JSON files or built-in defaults."""
        # Load built-in datasets
        for key, items in _BUILTIN_DATASETS.items():
            self._datasets[key] = [w.lower() for w in items]

        # Try to load from data directory (overrides built-in)
        if self._data_dir and os.path.isdir(self._data_dir):
            for category in SystematicityCategory:
                filepath = os.path.join(self._data_dir, f"{category.value}.json")
                if os.path.isfile(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if isinstance(data, list):
                            self._datasets[category.value] = [
                                w.lower() for w in data
                            ]
                    except Exception:
                        pass

    def add_custom_category(self, name: str, items: List[str]) -> None:
        """Add a custom category for checking."""
        self._datasets[name] = [w.lower() for w in items]

    def check(self, dictionary: LexicalSenseFormat) -> SystematicityReport:
        """Run systematicity checks against a dictionary."""
        # Build headword set from dictionary (case-insensitive)
        dict_headwords: Set[str] = set()
        for entry in dictionary.entries:
            hw = entry.headword.lower().strip()
            if hw:
                dict_headwords.add(hw)
                for variant in entry.variants:
                    dict_headwords.add(variant.lower().strip())

        checks = []
        for category in SystematicityCategory:
            items = self._datasets.get(category.value, [])
            if not items:
                continue

            found = []
            missing = []
            for item in items:
                item_lower = item.lower()
                if item_lower in dict_headwords:
                    found.append(item)
                else:
                    missing.append(item)

            ref_count = len(items)
            found_count = len(found)
            missing_count = len(missing)
            coverage = (found_count / ref_count * 100) if ref_count > 0 else 0.0

            checks.append(SystematicityCheck(
                category=category,
                reference_count=ref_count,
                found_count=found_count,
                missing_count=missing_count,
                coverage_percent=round(coverage, 1),
                found_items=found,
                missing_items=missing,
            ))

        # Also check custom categories
        custom_cats = [
            k for k in self._datasets
            if not any(c.value == k for c in SystematicityCategory)
        ]
        for cat_name in custom_cats:
            items = self._datasets[cat_name]
            found = [i for i in items if i.lower() in dict_headwords]
            missing = [i for i in items if i.lower() not in dict_headwords]
            ref_count = len(items)
            coverage = (len(found) / ref_count * 100) if ref_count > 0 else 0.0
            # Use a wrapper that has category_name instead of category enum
            checks.append(SystematicityCheck(
                category=SystematicityCategory.COLORS_BASIC,  # placeholder
                reference_count=ref_count,
                found_count=len(found),
                missing_count=len(missing),
                coverage_percent=round(coverage, 1),
                found_items=found,
                missing_items=missing,
            ))
            # Tag with custom name for report
            checks[-1].category_name = cat_name

        total_checks = len(checks)
        overall = (
            sum(c.coverage_percent for c in checks) / total_checks
            if total_checks > 0 else 0.0
        )

        return SystematicityReport(
            total_checks=total_checks,
            overall_coverage=round(overall, 1),
            checks=checks,
        )
