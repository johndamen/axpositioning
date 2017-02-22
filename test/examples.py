import unittest
import subprocess
import sys
import os


class TestExamples(unittest.TestCase):

    def run_example_file(self, name, root):
        cmd = [sys.executable, '-m', 'examples.' + name]
        try:
            p = subprocess.Popen(cmd, cwd=root,
                                 stdout=subprocess.DEVNULL)
            p.wait(timeout=5)
        except subprocess.CalledProcessError:
            raise AssertionError('{} not valid'.format(name))

    def test_example_files_errors(self):
        root = os.path.abspath(os.path.join(os.path.split(__file__)[0], '..'))
        for ex in os.listdir(os.path.join(root, 'examples')):
            if not ex.startswith('example'):
                continue
            self.run_example_file(os.path.splitext(ex)[0], root)
