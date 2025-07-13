# Outstanding project issues and bugs

1. Make sure that config settings as defined in Project Settings (ConfigManager) are properly saved and used throughout the project.

2. Reordering functionality: Make sure that buttons on the entry_form.html actually reorder senses within an entry. The approach should be general enough for any other multi-item lists (we might want to reorder pronunciations, notes, examples etc.). In the dictionary, the order is not arbitrary.

3. Make it possible to sort entries on any column in the Entries view (not only Lexeme, but also Citation Form, Part of Speech, Definition, Gloss, Last Modified Date etc.). Make the columns configurable (hide/show columns). Remember this in the Project Settings (implicitly.)

4. Fix bug: an entry without any sense, when added a definition to it, won't save, probably because it fails validation because there's no sense. 

5. Fix bug: you cannot delete an entry from the UI (entries.js shows an error) -- at least for entries without any sense. Again, possible validation issue?
