import unittest
import sqlite3
from pathlib import Path
from models.analyzer import SlangAnalyzer
from data.data_loader import DataLoader

class TestIntegration(unittest.TestCase):
    """Integration tests for full pipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = SlangAnalyzer()
        self.loader = DataLoader("test.db")
    
    def test_end_to_end_scraping(self):
        """Test complete scraping to analysis pipeline."""
        # Test data
        word = "rizz"
        
        # Scrape
        data = self.analyzer.get_slang_data(word)
        
        # Assert
        self.assertIsNotNone(data)
        self.assertEqual(data['word'], word)
    
    def test_invalid_word_handling(self):
        """Test handling of invalid words."""
        invalid_words = ["", "   ", "!@#$%", "a" * 100]
        
        for word in invalid_words:
            data = self.analyzer.get_slang_data(word)
            self.assertEqual(data, {})
    
    def test_database_connection(self):
        """Test database connection handling."""
        results = self.loader.query_database(
            "SELECT * FROM mentions WHERE word = ?",
            ("test_word",)
        )
        self.assertIsInstance(results, list)

if __name__ == '__main__':
    unittest.main()