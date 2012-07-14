import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from git import GitTestCase

suite = unittest.TestSuite()
suite.addTest(unittest.makeSuite(GitTestCase))

os.popen(os.path.join(os.path.dirname(__file__), "createrepo.sh"))
os.chdir(os.path.join(os.path.dirname(__file__), "repo"))
unittest.TextTestRunner().run(suite)
os.popen(os.path.join(os.path.dirname(__file__), "destroyrepo.sh"))
