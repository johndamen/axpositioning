import unittest
from . import axpositioning
from . import examples


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromModule(axpositioning))
    suite.addTest(unittest.TestLoader().loadTestsFromModule(examples))
    unittest.TextTestRunner(verbosity=1).run(suite)
