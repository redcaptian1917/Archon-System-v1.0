
import unittest
import sys
sys.path.insert(0, '.')

from archon_repo.agents.tools.core_tools import delegate_to_crew

class TestCoreTools(unittest.TestCase):

    def test_delegate_to_crew(self):
        """ Test that delegate_to_crew returns the correct placeholder message. """
        result = delegate_to_crew("test task", "test_crew", 1)
        self.assertEqual(result, "Note: Delegation request received and will be processed by the CEO's internal logic.")

if __name__ == '__main__':
    unittest.main()
