"""
AI Service for the Lexicographic Curation Workbench.

Provides AI-powered proofreading and drafting of dictionary entries using
OpenAI-compatible chat completion APIs (OpenAI, GitHub Models, etc.).

Design:
- BYOK (Bring Your Own Key) — API key passed per request or stored per project
- Entry data serialized to human-readable YAML with meaningful markers
- Customizable prompt templates stored as JSON
- Supports interactive (single entry) and batch (multiple entries) modes
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml

logger = logging.getLogger(__name__)

# Default OpenAI-compatible endpoint
DEFAULT_API_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o"

# Available models (OpenAI + GitHub Models)
AVAILABLE_MODELS = [
    {"id": "gpt-4o", "name": "GPT-4o", "provider": "OpenAI"},
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "OpenAI"},
    {"id": "gpt-4.1-nano", "name": "GPT-4.1 Nano", "provider": "OpenAI"},
    {"id": "o3-mini", "name": "o3-mini", "provider": "OpenAI / GitHub"},
    {"id": "o4-mini", "name": "o4-mini", "provider": "OpenAI / GitHub"},
]


class AIServiceError(Exception):
    """Base exception for AI service errors."""
    pass


class AIConfigurationError(AIServiceError):
    """Configuration error (missing API key, invalid model, etc.)."""
    pass


class AIAPIError(AIServiceError):
    """Error from the AI API (rate limit, auth, server error)."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class AIService:
    """Core AI service for proofreading and drafting dictionary entries."""

    def __init__(self, prompt_templates_path: Optional[Path] = None):
        """Initialize the AI service.

        Args:
            prompt_templates_path: Path to prompt templates JSON file.
                Defaults to instance/prompt_templates.json.
        """
        self._prompt_templates_path = prompt_templates_path
        self._prompt_templates: Dict[str, Dict[str, Any]] = {}
        self._load_prompt_templates()

    # ========================================================================
    # Prompt Template Management
    # ========================================================================

    def _default_templates_path(self) -> Path:
        """Return the default path for prompt templates."""
        if self._prompt_templates_path:
            return self._prompt_templates_path
        # Use the config directory in the project root
        return Path(__file__).parent.parent.parent / "config" / "prompt_templates.json"

    def _load_prompt_templates(self) -> None:
        """Load prompt templates from disk."""
        path = self._default_templates_path()
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._prompt_templates = {t["id"]: t for t in data.get("templates", [])}
                logger.info(f"Loaded {len(self._prompt_templates)} prompt templates from {path}")
            else:
                logger.info("No prompt templates file found, using built-in defaults")
                self._prompt_templates = self._builtin_templates()
                self._save_prompt_templates()
        except Exception as e:
            logger.warning(f"Failed to load prompt templates: {e}, using built-in defaults")
            self._prompt_templates = self._builtin_templates()

    def _save_prompt_templates(self) -> None:
        """Save prompt templates to disk."""
        path = self._default_templates_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {"templates": list(self._prompt_templates.values())},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.error(f"Failed to save prompt templates: {e}")

    @staticmethod
    def _builtin_templates() -> Dict[str, Dict[str, Any]]:
        """Return built-in default prompt templates (kept in sync with config/prompt_templates.json)."""
        return {
            "proofreading-default": {
                "id": "proofreading-default",
                "name": "Default Proofreading",
                "type": "proofread",
                "description": "Standard proofreading for a bilingual PL-EN dictionary",
                "system_prompt": (
                    "You are an expert lexicographic editor reviewing a bilingual Polish-English "
                    "dictionary entry in LIFT format.\n\n"
                    "IMPORTANT — do NOT flag these as issues:\n"
                    '- "seh-fonipa" is the CORRECT writing system code for IPA transcriptions.\n'
                    "- Grammatical info at the entry level is INHERITED by senses — do not flag missing POS on senses.\n"
                    "- Examples are OPTIONAL / facultative.\n"
                    "- English definitions are OPTIONAL. Polish definitions are the primary requirement and ARE required.\n\n"
                    "DO flag: missing Polish definitions, spelling errors, wrong translations, "
                    "missing lexical unit in PL or EN, wrong/missing entry-level POS."
                ),
                "user_prompt_template": (
                    "Proofread this bilingual Polish-English dictionary entry:\n\n"
                    "```yaml\n{entry_yaml}\n```\n\n"
                    "Return JSON with issues (field, severity, message, suggestion, optional "
                    "corrected_text) and a summary.\n"
                    "Remember: seh-fonipa is correct for IPA, examples are optional, "
                    "Polish definitions are required, English definitions are optional."
                ),
            },
            "drafting-default": {
                "id": "drafting-default",
                "name": "Default Entry Drafting",
                "type": "draft",
                "description": "Standard entry drafting for a bilingual PL-EN dictionary",
                "system_prompt": (
                    "You are an expert lexicographer creating entries for a bilingual Polish-English "
                    "dictionary in LIFT format. Include: lexical_unit in PL and EN, grammatical_info "
                    "at entry level, senses with Polish definitions (required) and optional English "
                    "definitions, optional examples, and pronunciation in IPA using 'seh-fonipa'."
                ),
                "user_prompt_template": (
                    "Draft a dictionary entry for:\n\n"
                    "**Word/Phrase:** {description}\n"
                    "**Source language:** {source_lang}\n"
                    "**Target language(s):** {target_langs}\n\n"
                    "Return JSON: {\"entry_yaml\": \"...\", \"notes\": \"...\"}"
                ),
            },
        }

    def get_prompt_templates(self, template_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available prompt templates, optionally filtered by type.

        Args:
            template_type: Filter by type ('proofread' or 'draft'), or None for all.

        Returns:
            List of prompt template dicts.
        """
        templates = list(self._prompt_templates.values())
        if template_type:
            templates = [t for t in templates if t.get("type") == template_type]
        return templates

    def get_prompt_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific prompt template by ID."""
        return self._prompt_templates.get(template_id)

    def save_prompt_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a prompt template.

        Args:
            template_data: Template dict with id, name, type, system_prompt, user_prompt_template.

        Returns:
            The saved template dict.
        """
        required = ["id", "name", "type", "system_prompt", "user_prompt_template"]
        for field in required:
            if field not in template_data:
                raise ValueError(f"Missing required field: {field}")

        if template_data["type"] not in ("proofread", "draft"):
            raise ValueError("Template type must be 'proofread' or 'draft'")

        self._prompt_templates[template_data["id"]] = template_data
        self._save_prompt_templates()
        return template_data

    def delete_prompt_template(self, template_id: str) -> bool:
        """Delete a prompt template. Built-in defaults cannot be deleted.

        Returns:
            True if deleted, False if not found or is built-in.
        """
        builtins = self._builtin_templates()
        if template_id in builtins:
            logger.warning(f"Cannot delete built-in template: {template_id}")
            return False
        if template_id in self._prompt_templates:
            del self._prompt_templates[template_id]
            self._save_prompt_templates()
            return True
        return False

    @staticmethod
    def get_available_models() -> List[Dict[str, str]]:
        """Return list of available AI models."""
        return AVAILABLE_MODELS

    # ========================================================================
    # Entry → YAML Serialization
    # ========================================================================

    @staticmethod
    def entry_to_yaml(entry_data: Dict[str, Any]) -> str:
        """Serialize entry data to human-readable YAML with meaningful markers.

        The output is designed to be easy for an LLM to read and understand.

        Args:
            entry_data: Entry dict (as returned by Entry.to_dict() or form data).

        Returns:
            YAML string with section markers.
        """
        lines = []

        # Header with ID and citation form
        entry_id = entry_data.get("id", "unknown")
        lexical_unit = entry_data.get("lexical_unit", {})
        headword = ""
        if isinstance(lexical_unit, dict):
            headword = lexical_unit.get("en", list(lexical_unit.values())[0] if lexical_unit else "")
        elif isinstance(lexical_unit, str):
            headword = lexical_unit

        lines.append(f"# ====== ENTRY: {headword} (id: {entry_id}) ======")
        lines.append("")

        # Lexical unit
        lines.append("# --- Lexical Unit (headword in all languages) ---")
        lines.append("lexical_unit:")
        if isinstance(lexical_unit, dict):
            for lang, text in sorted(lexical_unit.items()):
                lines.append(f"  {lang}: {AIService._yaml_str(text)}")
        lines.append("")

        # Pronunciation
        pronunciations = entry_data.get("pronunciations", {}) or entry_data.get("pronunciation", {})
        if pronunciations:
            lines.append("# --- Pronunciation (IPA) ---")
            if isinstance(pronunciations, dict):
                lines.append("pronunciation:")
                for ws, ipa in pronunciations.items():
                    if ipa:
                        lines.append(f"  {ws}: {AIService._yaml_str(str(ipa))}")
            elif isinstance(pronunciations, list):
                lines.append("pronunciation:")
                for p in pronunciations:
                    if isinstance(p, dict):
                        ws = p.get("type", p.get("writing_system", "?"))
                        val = p.get("value", p.get("ipa", ""))
                        lines.append(f"  {ws}: {AIService._yaml_str(str(val))}")
            lines.append("")

        # Grammatical info (entry-level)
        grammatical_info = entry_data.get("grammatical_info", "")
        if grammatical_info:
            lines.append(f"# --- Part of Speech ---")
            lines.append(f"grammatical_info: {AIService._yaml_str(str(grammatical_info))}")
            lines.append("")

        # Senses
        senses = entry_data.get("senses", [])
        if senses:
            lines.append("# --- Senses ---")
            lines.append("senses:")
            for i, sense in enumerate(senses):
                if isinstance(sense, dict):
                    lines.append(f"  - # Sense {i + 1}")
                    sense_pos = sense.get("grammatical_info", "")
                    if sense_pos:
                        lines.append(f"    grammatical_info: {AIService._yaml_str(str(sense_pos))}")

                    # Definition(s)
                    definitions = sense.get("definitions") or sense.get("definition")
                    if definitions:
                        lines.append("    definition:")
                        if isinstance(definitions, dict):
                            for lang, text in definitions.items():
                                if isinstance(text, str):
                                    lines.append(f"      {lang}: {AIService._yaml_str(text)}")
                                elif isinstance(text, dict):
                                    txt = text.get("text", str(text))
                                    lines.append(f"      {lang}: {AIService._yaml_str(str(txt))}")
                        elif isinstance(definitions, str):
                            lines.append(f"      en: {AIService._yaml_str(definitions)}")

                    # Gloss(es)
                    glosses = sense.get("glosses") or sense.get("gloss")
                    if glosses:
                        lines.append("    gloss:")
                        if isinstance(glosses, dict):
                            for lang, text in glosses.items():
                                lines.append(f"      {lang}: {AIService._yaml_str(str(text))}")

                    # Examples
                    examples = sense.get("examples", [])
                    if examples:
                        lines.append("    examples:")
                        for ex in examples:
                            if isinstance(ex, dict):
                                form = ex.get("form", ex.get("form_text", ""))
                                translation = ex.get("translation", ex.get("translations", ""))
                                if isinstance(form, dict):
                                    form_text = form.get("en", list(form.values())[0] if form else "")
                                else:
                                    form_text = str(form) if form else ""
                                if isinstance(translation, dict):
                                    trans_text = translation.get("pl", translation.get("en", list(translation.values())[0] if translation else ""))
                                else:
                                    trans_text = str(translation) if translation else ""
                                lines.append(f"      - form: {{en: {AIService._yaml_str(form_text)}}}")
                                if trans_text:
                                    lines.append(f"        translation: {{pl: {AIService._yaml_str(trans_text)}}}")
            lines.append("")

        # Etymology
        etymologies = entry_data.get("etymologies", [])
        if etymologies:
            lines.append("# --- Etymology ---")
            lines.append("etymology:")
            for etym in etymologies:
                if isinstance(etym, dict):
                    etype = etym.get("type", "")
                    esource = etym.get("source", "")
                    eform = etym.get("form", {})
                    egloss = etym.get("gloss", {})
                    lines.append(f"  - type: {AIService._yaml_str(str(etype))}")
                    if esource:
                        lines.append(f"    source: {AIService._yaml_str(str(esource))}")
                    if eform and isinstance(eform, dict):
                        lines.append("    form:")
                        for lang, text in eform.items():
                            lines.append(f"      {lang}: {AIService._yaml_str(str(text))}")
                    if egloss and isinstance(egloss, dict):
                        lines.append("    gloss:")
                        for lang, text in egloss.items():
                            lines.append(f"      {lang}: {AIService._yaml_str(str(text))}")
            lines.append("")

        # Relations
        relations = entry_data.get("relations", [])
        if relations:
            lines.append("# --- Relations to Other Entries ---")
            lines.append("relations:")
            for rel in relations:
                if isinstance(rel, dict):
                    rtype = rel.get("type", "")
                    rref = rel.get("ref", "")
                    lines.append(f"  - type: {AIService._yaml_str(str(rtype))}")
                    lines.append(f"    ref: {AIService._yaml_str(str(rref))}")
            lines.append("")

        # Variants
        variants = entry_data.get("variants", [])
        if variants:
            lines.append("# --- Variant Forms ---")
            lines.append("variants:")
            for v in variants:
                if isinstance(v, dict):
                    vform = v.get("form", {})
                    if isinstance(vform, dict):
                        for lang, text in vform.items():
                            lines.append(f"  - form: {{{lang}: {AIService._yaml_str(str(text))}}}")
            lines.append("")

        # Notes
        notes = entry_data.get("notes", {})
        if notes and isinstance(notes, dict):
            lines.append("# --- Notes ---")
            lines.append("notes:")
            for note_type, note_content in notes.items():
                if isinstance(note_content, dict):
                    lines.append(f"  {note_type}:")
                    for lang, text in note_content.items():
                        lines.append(f"    {lang}: {AIService._yaml_str(str(text))}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _yaml_str(text: str) -> str:
        """Format a string value for YAML output, quoting if necessary."""
        if not text:
            return "''"
        # Quote if contains special YAML characters
        if any(c in text for c in ('"', "'", ":", "#", "{", "}", "[", "]", ",", "&", "*", "?", "|", "-", "<", ">", "=", "!", "%", "@", "`")):
            # Use single quotes and escape internal single quotes
            escaped = text.replace("'", "''")
            return f"'{escaped}'"
        # Quote if it could be interpreted as a non-string type
        if text.lower() in ("true", "false", "yes", "no", "null", "none"):
            return f"'{text}'"
        return text

    # ========================================================================
    # OpenAI-compatible Chat Client
    # ========================================================================

    @staticmethod
    def _call_llm(
        system_prompt: str,
        user_prompt: str,
        api_key: str,
        model: str = DEFAULT_MODEL,
        api_base: str = DEFAULT_API_BASE,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 60,
    ) -> str:
        """Call an OpenAI-compatible chat completion API.

        Args:
            system_prompt: System message (instructions).
            user_prompt: User message (the task).
            api_key: API key for authentication.
            model: Model ID to use.
            api_base: Base URL for the API (default: OpenAI).
            temperature: Sampling temperature (0-2).
            max_tokens: Maximum response tokens.
            timeout: Request timeout in seconds.

        Returns:
            The model's response text content.

        Raises:
            AIConfigurationError: If API key is missing.
            AIAPIError: If the API returns an error.
        """
        if not api_key:
            raise AIConfigurationError(
                "No API key provided. Set an OpenAI API key in project settings "
                "or pass it with the request."
            )

        url = f"{api_base.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(
                f"LLM call successful: model={model}, tokens_used={data.get('usage', {}).get('total_tokens', '?')}"
            )
            return content
        except requests.exceptions.Timeout:
            raise AIAPIError(f"AI API request timed out after {timeout}s")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            body = ""
            try:
                body = e.response.json().get("error", {}).get("message", str(e))
            except Exception:
                body = str(e)
            raise AIAPIError(f"AI API error (HTTP {status}): {body}")
        except requests.exceptions.ConnectionError as e:
            raise AIAPIError(f"Could not connect to AI API: {e}")
        except KeyError:
            raise AIAPIError(f"Unexpected API response format: {data}")

    # ========================================================================
    # Proofreading
    # ========================================================================

    def proofread_entry(
        self,
        entry_data: Dict[str, Any],
        api_key: str,
        model: str = DEFAULT_MODEL,
        prompt_template_id: str = "proofreading-default",
        api_base: str = DEFAULT_API_BASE,
    ) -> Dict[str, Any]:
        """Proofread a dictionary entry using AI.

        Args:
            entry_data: Entry dict (from Entry.to_dict() or form data).
            api_key: OpenAI API key.
            model: Model ID.
            prompt_template_id: ID of the prompt template to use.
            api_base: API base URL.

        Returns:
            Dict with 'suggestions' list and 'entry_yaml' (the YAML sent).

        Raises:
            AIConfigurationError: If prompt template not found.
            AIAPIError: If the API call fails.
        """
        template = self.get_prompt_template(prompt_template_id)
        if not template:
            raise AIConfigurationError(f"Prompt template not found: {prompt_template_id}")

        entry_yaml = self.entry_to_yaml(entry_data)
        user_prompt = template["user_prompt_template"].replace("{entry_yaml}", entry_yaml)

        response_text = self._call_llm(
            system_prompt=template["system_prompt"],
            user_prompt=user_prompt,
            api_key=api_key,
            model=model,
            api_base=api_base,
            temperature=0.2,  # Low temperature for proofreading
        )

        # Parse JSON from response (handle markdown fences if present)
        response_text = self._extract_json(response_text)

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse AI response as JSON, returning raw: {response_text[:200]}")
            result = {"suggestions": [], "raw_response": response_text}

        result["entry_yaml"] = entry_yaml
        return result

    # ========================================================================
    # Drafting
    # ========================================================================

    def draft_entry(
        self,
        description: str,
        api_key: str,
        source_lang: str = "en",
        target_langs: str = "en",
        model: str = DEFAULT_MODEL,
        prompt_template_id: str = "drafting-default",
        api_base: str = DEFAULT_API_BASE,
    ) -> Dict[str, Any]:
        """Draft a new dictionary entry from a description.

        Args:
            description: Text description of the word to draft an entry for.
            api_key: OpenAI API key.
            source_lang: Source language code (e.g. 'en').
            target_langs: Comma-separated target language codes (e.g. 'pl,en').
            model: Model ID.
            prompt_template_id: ID of the prompt template to use.
            api_base: API base URL.

        Returns:
            Dict with 'entry_yaml' (drafted entry as YAML string),
            'entry_data' (parsed entry dict), and 'notes' (editorial notes).

        Raises:
            AIConfigurationError: If prompt template not found.
            AIAPIError: If the API call fails.
        """
        template = self.get_prompt_template(prompt_template_id)
        if not template:
            raise AIConfigurationError(f"Prompt template not found: {prompt_template_id}")

        user_prompt = template["user_prompt_template"]
        user_prompt = user_prompt.replace("{description}", description)
        user_prompt = user_prompt.replace("{source_lang}", source_lang)
        user_prompt = user_prompt.replace("{target_langs}", target_langs)

        response_text = self._call_llm(
            system_prompt=template["system_prompt"],
            user_prompt=user_prompt,
            api_key=api_key,
            model=model,
            api_base=api_base,
            temperature=0.4,  # Slightly higher temperature for creative drafting
        )

        # Parse JSON from response
        response_text = self._extract_json(response_text)

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse AI draft response as JSON, returning raw: {response_text[:200]}")
            result = {"entry_yaml": response_text, "notes": []}

        # Try to parse the drafted entry YAML into a dict
        entry_data = None
        if "entry_yaml" in result and result["entry_yaml"]:
            try:
                entry_data = yaml.safe_load(result["entry_yaml"])
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse drafted entry YAML: {e}")
                result["parse_error"] = str(e)

        result["entry_data"] = entry_data
        return result

    # ========================================================================
    # Batch Operations
    # ========================================================================

    def batch_proofread(
        self,
        entries: List[Dict[str, Any]],
        api_key: str,
        model: str = DEFAULT_MODEL,
        prompt_template_id: str = "proofreading-default",
        api_base: str = DEFAULT_API_BASE,
    ) -> List[Dict[str, Any]]:
        """Proofread multiple entries in batch.

        Args:
            entries: List of entry dicts.
            api_key: OpenAI API key.
            model: Model ID.
            prompt_template_id: Prompt template ID.
            api_base: API base URL.

        Returns:
            List of result dicts (same structure as proofread_entry), one per entry.
        """
        results = []
        for i, entry_data in enumerate(entries):
            try:
                result = self.proofread_entry(
                    entry_data=entry_data,
                    api_key=api_key,
                    model=model,
                    prompt_template_id=prompt_template_id,
                    api_base=api_base,
                )
                result["entry_index"] = i
                entry_id = entry_data.get("id", str(i))
                result["entry_id"] = entry_id
                results.append(result)
            except AIServiceError as e:
                logger.error(f"Batch proofread failed for entry {i}: {e}")
                results.append({
                    "entry_index": i,
                    "entry_id": entry_data.get("id", str(i)),
                    "error": str(e),
                    "suggestions": [],
                })
        return results

    # ========================================================================
    # Helpers
    # ========================================================================

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from a response that may have markdown fences."""
        text = text.strip()
        # Remove ```json ... ``` fences
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```)
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text

    @staticmethod
    def validate_api_key(api_key: str, api_base: str = DEFAULT_API_BASE) -> bool:
        """Validate an API key by making a lightweight call to list models.

        Args:
            api_key: The API key to validate.
            api_base: API base URL.

        Returns:
            True if the key is valid, False otherwise.
        """
        try:
            url = f"{api_base.rstrip('/')}/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
