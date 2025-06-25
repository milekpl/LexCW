try:
    from BaseXClient.BaseXClient import Session as BaseXSession
    print('BaseXSession is available')
except ImportError:
    print('BaseXSession is NOT available')
