import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools', 'skills'))

class TestICAMemoryMCP(unittest.TestCase):
    def test_fts_search(self):
        import ica_memory_mcp
        self.assertTrue(hasattr(ica_memory_mcp, 'search_graph_fts'))

    def test_faiss_search(self):
        import ica_memory_mcp
        self.assertTrue(hasattr(ica_memory_mcp, 'search_graph_semantic'))

if __name__ == "__main__":
    unittest.main()
