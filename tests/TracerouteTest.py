import unittest
import sys
#from SimBGP.simbgp import SimBGP
import SimBGP3 as SimBGP

class TracerouteTest(unittest.TestCase):
    """Test for normal BGP behaviour on topology files, for all BGP mode"""
    def setUp(self):
        #SimBGP.SHOW_DEBUG=True
        #SimBGP.runConfigFile("../../config/traceroute.cfg")
        SimBGP.runConfigFile("traceroute.cfg")
    def tearDown(self):
        SimBGP.init()
    def testBaseTopo(self):
        """Check that all router can reach the destination"""
        self.assertTrue(SimBGP.checkForwarding("1", "1.0/8"))
        self.assertTrue(SimBGP.checkForwarding("2", "1.0/8"))
        self.assertTrue(SimBGP.checkForwarding("3", "1.0/8"))
        self.assertTrue(SimBGP.checkForwarding("4", "1.0/8"))
        self.assertTrue(SimBGP.checkForwarding("5", "1.0/8"))
        
    def testOneFailure(self) :
        """Check that node 1 can still reach destination with alternate path"""
        SimBGP.eventLinkDown("1","2")
        SimBGP.run()
        self.assertTrue(SimBGP.checkForwarding("1", "1.0/8"))
        self.assertTrue(SimBGP.checkForwarding("2", "1.0/8"))
        self.assertTrue(SimBGP.checkForwarding("3", "1.0/8"))
        self.assertTrue(SimBGP.checkForwarding("4", "1.0/8"))
        self.assertTrue(SimBGP.checkForwarding("5", "1.0/8"))

    def testGraphUnconnected(self) :
        """Check that traceroute detects that no path is available"""
        SimBGP.eventLinkDown("1","2")
        SimBGP.eventLinkDown("4","5")
        SimBGP.run()
        self.assertFalse(SimBGP.checkForwarding("1", "1.0/8"))
        self.assertTrue(SimBGP.checkForwarding("2", "1.0/8"))
        self.assertTrue(SimBGP.checkForwarding("3", "1.0/8"))
        self.assertFalse(SimBGP.checkForwarding("4", "1.0/8"))
        self.assertTrue(SimBGP.checkForwarding("5", "1.0/8"))        
