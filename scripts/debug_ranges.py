from unittest.mock import Mock
from app.services.ranges_service import RangesService

mock_connector = Mock()
mock_connector.database = 'test_db'
mock_connector.execute_query = Mock()
mock_connector.execute_query.return_value = '''
<lift-ranges>
  <range id="test-range" guid="r1">
    <range-element id="parent" value="parent">
      <label><form lang="en"><text>ParentLabel</text></form></label>
      <abbrev>P1</abbrev>
      <range-element id="child" value="child" />
    </range-element>
  </range>
</lift-ranges>
'''

s = RangesService(mock_connector)
print('First call (resolved=True)')
r = s.get_range('test-range', resolved=True)
import pprint
pprint.pprint(r)
print('\nSecond call (resolved=False)')
orig = s.get_range('test-range', resolved=False)
pprint.pprint(orig)
