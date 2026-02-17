import sys
import os
import unittest

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.analyzer import SlangAnalyzer

class TestCringeLogic(unittest.TestCase):
    def setUp(self):
        self.analyzer = SlangAnalyzer(db_path=':memory:') # No DB needed for logic check

    def test_niche_growing_faster(self):
        """Case: Niche growing faster than Mainstream. Should NOT be cringe."""
        m_growth = 0.05
        n_growth = 0.10
        # Alert if M > 3 * N
        # 0.05 > 0.30 -> False
        self.assertFalse(self.analyzer.check_cringe_alert(m_growth, n_growth))

    def test_mainstream_growing_moderately(self):
        """Case: Mainstream growing faster, but not 200% more than Niche."""
        m_growth = 0.25
        n_growth = 0.10
        # 0.25 > 0.30 -> False
        self.assertFalse(self.analyzer.check_cringe_alert(m_growth, n_growth))

    def test_mainstream_exploding(self):
        """Case: Mainstream growing > 200% more than Niche (i.e. > 3x)."""
        m_growth = 0.50
        n_growth = 0.10
        # 0.50 > 0.30 -> True
        self.assertTrue(self.analyzer.check_cringe_alert(m_growth, n_growth))

    def test_niche_dying(self):
        """Case: Niche is flat/dying (0 or negative). Mainstream significant."""
        m_growth = 0.15
        n_growth = 0.0
        # Logic: if n <= 0, alert if m > 0.1
        self.assertTrue(self.analyzer.check_cringe_alert(m_growth, n_growth))

    def test_both_dying(self):
        """Case: Both dying."""
        m_growth = -0.1
        n_growth = -0.1
        self.assertFalse(self.analyzer.check_cringe_alert(m_growth, n_growth))

if __name__ == '__main__':
    unittest.main()
