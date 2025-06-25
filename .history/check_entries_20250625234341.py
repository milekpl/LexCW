from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector

connector = BaseXConnector(
    host='localhost',
    port=1984,
    username='admin',
    password='admin',
    database='dictionary'
)

service = DictionaryService(connector)
entries, count = service.list_entries(limit=5)
print(f'Total entries: {count}')
print('First 5 entries:')
for entry in entries:
    print(f'- {entry.id}: {entry.lexical_unit}')
