# Outstanding project issues and bugs

1. Reordering functionality: Make sure that buttons on the entry_form.html actually reorder senses within an entry. The approach should be general enough for any other multi-item lists (we might want to reorder pronunciations, notes, examples etc.). In the dictionary, the order is not arbitrary.

2. The source language should not require a definition if there is none. Currently, it does, which makes NO sense for me (validation does not require this!). Also, if there is an empty definition, I should be able to remove it, especially if it is an empty definition / gloss for the source language.

8. Remaining Issues in Validation (failures):

- Note Structure Validation: Missing validation rule implementation (failing unit test)
- IPA Character Validation: Missing validation rule  implementation (failing unit test)
- POS Consistency Rules: Missing validation rule implementation

11. Make validation rules editable per project. Is this in JSON?