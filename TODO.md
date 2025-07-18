# Outstanding project issues and bugs

1. Reordering functionality: Make sure that buttons on the entry_form.html actually reorder senses within an entry. The approach should be general enough for any other multi-item lists (we might want to reorder pronunciations, notes, examples etc.). In the dictionary, the order is not arbitrary.

2. Make it possible to sort entries on any column in the Entries view (not only Lexeme, but also Citation Form, Part of Speech, Definition, Gloss, Last Modified Date etc.). Make the columns configurable (hide/show columns). Remember this in the Project Settings (implicitly.)

3. Fix bug: an entry without any sense, when added a definition to it, won't save, probably because it fails validation because there's no sense. 

4. Fix bug: you cannot delete an entry from the UI (entries.js shows an error) -- at least for entries without any sense. Again, possible validation issue?

5. When the entry is deleted (sometimes it is successful even if there is a message it was not), the entry list still displays the old entry (the redis cache is not updated or cleared; perhaps cache update is a better idea than clearing the whole thing?).

6. There are TWO boxes for etymology in the entry form. One is for Etymology, one is for Etymological Notes. They both have the same name="etymology" which causes problems with saving data.

7. Etymology types are empty in the entry form. Should they be populated by default? Or should we add them manually? Are there LIFT ranges for them?

8. Remaining Issues in Validation (failures):

- Note Structure Validation: Missing validation rule implementation (failing unit test)
- IPA Character Validation: Missing validation rule  implementation (failing unit test)
- POS Consistency Rules: Missing validation rule implementation

9. Etymology ranges bugs on opening the entry form:

```
GET http://localhost:5000/api/ranges/etymology-types 500 (INTERNAL SERVER ERROR)
loadRanges @ etymology-forms.js:47
await in loadRanges
init @ etymology-forms.js:30
EtymologyFormsManager @ etymology-forms.js:21
(anonymous) @ edit:902Understand this error
etymology-forms.js:55 Failed to load etymology types from range 'etymology-types', using defaults
```

10. We lost the date time field on the entries list "Last Modified" (again!!!). That's a clear regression. We should have an integration test on this. The git history must have something related to the solution. Why did this break? Weirdly, it displays fine for newly created entries. Perhaps uses some other field now? 

