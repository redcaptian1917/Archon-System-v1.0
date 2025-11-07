
import unittest
from unittest.mock import patch, MagicMock

# It's good practice to add the path to the modules to be tested.
import sys
sys.path.insert(0, './archon_repo/agents/core')

# Now we can import the modules.
import auth
import fapc_tools

class TestAuth(unittest.TestCase):

    @patch('auth.db_manager.db_connect')
    def test_get_privilege_by_id_admin(self, mock_db_connect):
        """ Test that get_privilege_by_id returns 'admin' for an admin user. """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Simulate the database returning an 'admin' privilege.
        mock_cursor.fetchone.return_value = ('admin',)

        privilege = auth.get_privilege_by_id(1)

        self.assertEqual(privilege, 'admin')

    @patch('auth.db_manager.db_connect')
    def test_get_privilege_by_id_user(self, mock_db_connect):
        """ Test that get_privilege_by_id returns 'user' for a regular user. """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Simulate the database returning a 'user' privilege.
        mock_cursor.fetchone.return_value = ('user',)

        privilege = auth.get_privilege_by_id(2)

        self.assertEqual(privilege, 'user')

    @patch('fapc_tools.auth.get_privilege_by_id')
    @patch('fapc_tools.db_manager.db_connect')
    def test_auth_management_tool_admin_access(self, mock_db_connect, mock_get_privilege):
        """ Test that an admin can use the auth_management_tool. """
        mock_get_privilege.return_value = 'admin'

        # Mock the database calls within the tool itself to prevent errors.
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # We expect a success message if the admin runs the tool.
        result = fapc_tools.auth_management_tool('lock', 'testuser', 1)

        self.assertIn('Success', result)

    @patch('fapc_tools.auth.get_privilege_by_id')
    def test_auth_management_tool_non_admin_access(self, mock_get_privilege):
        """ Test that a non-admin is blocked from using the auth_management_tool. """
        mock_get_privilege.return_value = 'user'

        result = fapc_tools.auth_management_tool('lock', 'testuser', 2)

        self.assertEqual(result, 'Error: This tool can only be run by an admin.')

if __name__ == '__main__':
    unittest.main()
