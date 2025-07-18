# Outstanding project issues and bugs

1. Reordering functionality: Make sure that buttons on the entry_form.html actually reorder senses within an entry. The approach should be general enough for any other multi-item lists (we might want to reorder pronunciations, notes, examples etc.). In the dictionary, the order is not arbitrary.

2. When sorting on Last Modified, we get "–" at the top, but we cannot revert to the real contents (it gets replaced by the default null value being still at the top even if the direction is reversed).

3. Fix bug: an entry without any sense, when added a definition to it, won't save, probably because it fails validation because there's no sense. 

4. When the entry is deleted (sometimes it is successful even if there is a message it was not), the entry list still displays the old entry (the redis cache is not updated or cleared; perhaps cache update is a better idea than clearing the whole thing?).

5. The language selector does not work properly. It only shows one language, even if there are two in the project settings. It should show all languages available in the project settings.

6. There are TWO boxes for etymology in the entry form. One is for Etymology, one is for Etymological Notes. They both have the same name="etymology" which causes problems with saving data.

8. Remaining Issues in Validation (failures):

- Note Structure Validation: Missing validation rule implementation (failing unit test)
- IPA Character Validation: Missing validation rule  implementation (failing unit test)
- POS Consistency Rules: Missing validation rule implementation

10. The validation rule R1.2.1 is wrong: "Invalid entry ID format. Use only letters, numbers, underscores, and hyphens (R1.2.1)". We should admit spaces as well!

11. Make validation rules editable per project. Is this in JSON?