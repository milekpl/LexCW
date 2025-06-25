from BaseXClient.BaseXClient import Session
try:
    s = Session('localhost', 1984, 'admin', 'admin')
    print('BaseX server is running')
    s.close()
except Exception as e:
    print(f'Could not connect to BaseX server: {e}')
