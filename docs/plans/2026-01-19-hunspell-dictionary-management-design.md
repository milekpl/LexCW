# Hunspell Dictionary Management Design

**Date:** 2026-01-19
**Status:** Approved

## Overview

Implement Hunspell dictionary management with project-scoped custom dictionaries and user-personalized word lists. The system auto-detects which dictionary to use based on field language codes.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Dictionary Sources                            │
│                                                                  │
│   ┌─────────────────┐    ┌─────────────────┐                   │
│   │  Project Dicts  │    │   User Dicts    │                   │
│   │                 │    │                 │                   │
│   │ - Standard      │    │ - Custom words  │                   │
│   │   language      │    │ - Uploaded      │                   │
│   │   dictionaries  │    │   dictionaries  │                   │
│   │ - IPA dict      │    │                 │                   │
│   └────────┬────────┘    └────────┬────────┘                   │
│            │                      │                             │
│            └──────────┬───────────┘                             │
│                       ▼                                         │
│            ┌──────────────────────┐                            │
│            │  Merged Dictionary   │                            │
│            │  (hunspell object)   │                            │
└─────────────────────────────────────────────────────────────────┘
```

## Data Models

### ProjectDictionary

```python
class ProjectDictionary(db.Model):
    __tablename__ = 'project_dictionaries'

    id = db.Column(db.String(36), primary_key=True)  # UUID
    project_id = db.Column(Integer, ForeignKey('project_settings.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    lang_code = db.Column(db.String(20), nullable=False)  # en_US, seh-fonipa, etc.
    description = db.Column(db.Text, nullable=True)
    dic_file = db.Column(db.String(255), nullable=False)
    aff_file = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    uploaded_by = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer, nullable=True)
```

### UserDictionary

```python
class UserDictionary(db.Model):
    __tablename__ = 'user_dictionaries'

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(Integer, ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    lang_code = db.Column(db.String(20), nullable=False)
    dic_file = db.Column(db.String(255), nullable=False)
    aff_file = db.Column(db.String(255), nullable=False)
    custom_words = db.Column(JSON, nullable=True)  # List of custom words
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## Storage Structure

```
uploads/
├── dictionaries/
│   └── {project_id}/
│       └── {dictionary_id}/
│           ├── en_US.dic
│           ├── en_US.aff
│           └── metadata.json
└── dictionaries/
    └── user/
        └── {user_id}/
            ├── custom_words.json
            └── {dictionary_id}/
                ├── custom.dic
                └── custom.aff
```

## Field-to-Dictionary Auto-Detection

| Field Path | Language Source | Dictionary |
|------------|-----------------|------------|
| `lexical_unit` | Project source language | Matching project dictionary |
| `pronunciations` | `seh-fonipa` (fixed) | IPA dictionary |
| `definitions` | Field keys (en, fr, etc.) | Matching project dictionary |
| `glosses` | Field keys | Matching project dictionary |
| `examples` | Inherit from parent | Same as definition |
| `notes` | Field keys | Matching project dictionary |
| (fallback) | Project default | Default dictionary |

## API Endpoints

### Project Dictionary Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects/<id>/dictionaries` | GET | List project dictionaries |
| `/api/projects/<id>/dictionaries/upload` | POST | Upload .dic + .aff files |
| `/api/projects/<id>/dictionaries/<dict_id>` | DELETE | Remove dictionary |
| `/api/projects/<id>/dictionaries/<dict_id>/default` | PUT | Set as default |

### User Dictionary Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/user/dictionaries` | GET | List user's dictionaries |
| `/api/user/dictionaries/custom-words` | POST | Add custom words |
| `/api/user/dictionaries/<dict_id>` | DELETE | Remove dictionary |

### Validation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/validation/spell-check` | POST | Validate with auto-detection |

## Implementation Order

1. Create database models
2. Create dictionary storage directories
3. Implement DictionaryLoader service
4. Implement FieldLanguageDetector
5. Update LayeredHunspellValidator
6. Add API endpoints
7. Add file upload validation
8. Add UI for dictionary management

## Configuration Integration

Added to `project_settings.settings_json`:

```json
{
  "spell_check": {
    "dictionaries": ["dict_id1", "dict_id2"],
    "ipa_dictionary_id": "dict_id_ipa",
    "default_dictionary_id": "dict_id_default"
  }
}
```

## Validation Lookup Order

1. Project dictionaries (by language code match)
2. User dictionaries (by language code match)
3. Project default dictionary (fallback)
