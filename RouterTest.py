import unittest
#from SimBGP.simbgp import SimBGP
import SimBGP

class CRouterTest(unittest.TestCase):
    """Test for BGP Router Functionnalities"""
    def setUp(self):
        SimBGP.init()
        #Configuring simple triangle topology
        self.myRouter1=SimBGP.CRouter(1,"1.0.0.0")
        self.myRouter2=SimBGP.CRouter(2,"2.0.0.0")
        self.myRouter3=SimBGP.CRouter(2,"2.0.0.1")
        SimBGP._router_list["1.0.0.0"]=self.myRouter1
        SimBGP._router_list["2.0.0.0"]=self.myRouter2
        SimBGP._router_list["2.0.0.1"]=self.myRouter3
        self.myLink1=self.myRouter1.getPeerLink("2.0.0.0")
        self.myLink2=self.myRouter2.getPeerLink("1.0.0.0")
        self.myLink3=self.myRouter3.getPeerLink("2.0.0.0")
        self.myLink4=self.myRouter3.getPeerLink("1.0.0.0")
        self.myRouter1.peers["2.0.0.0"]=SimBGP.CPeer("2.0.0.0",self.myLink1)
        self.myRouter1.peers["2.0.0.1"]=SimBGP.CPeer("2.0.0.1", self.myLink4)
        self.myRouter2.peers["1.0.0.0"]=SimBGP.CPeer("1.0.0.0", self.myLink2)
        self.myRouter2.peers["2.0.0.1"]=SimBGP.CPeer("2.0.0.1", self.myLink3)
        self.myRouter3.peers["1.0.0.0"]=SimBGP.CPeer("1.0.0.0", self.myLink4)
        self.myRouter3.peers["2.0.0.0"]=SimBGP.CPeer("2.0.0.0", self.myLink3)
    def testToString(self):
        """Testing textual representation of a router"""
        self.assertEqual(str(self.myRouter1), "1.0.0.0(1)")
        self.assertEqual(str(self.myRouter2), "2.0.0.0(2)")

    def testGetPeerLink(self):
        """Check if the link between two peer exists and is identical for both routers"""
        self.myLink1=self.myRouter1.getPeerLink("2.0.0.0")
        self.myLink2=self.myRouter2.getPeerLink("1.0.0.0")
        self.assertEqual(self.myLink1, self.myLink2)
        self.assertEqual(self.myLink1.ibgp_ebgp(), SimBGP.EBGP_SESSION)
        
        #self.assertEqual(self.myRouter1.getPeerLink())
    #def testMRAIExpires(self):
    #    pass
    def testImportFilter(self):
        """Testing path importation"""
        #Loop detection from AS Path
        self.myPath=SimBGP.CPath()
        self.myPath.aspath=[1,2]
        self.assertFalse(self.myRouter1.importFilter("2.0.0.0", "1.0/8", self.myPath))
        self.myPath.aspath=[3,2]
        self.assertTrue(self.myRouter1.importFilter("2.0.0.0", "1.0/8", self.myPath))
        #Route Map filtering
   # def testImportActions(self):
   #      Check that all actions are applied in the right order
   #     pass
   # def testExportFilter(self):
   #      Check that all filters are applied in the right order
   #     pass
   # def testExportActions(self):
   #      Check that all actions are applied in the right order
   #     pass
   # def testPathSelection(self):
   #     pass
   # def testPeerDown(self):
   #     pass
   # def testPeerUp(self):
   #     pass
   # def testUpdate(self):
   #     pass 
   # def testIsWithdrawal(self):   
   #     pass
   # def testDelivery(self):
   #     pass
   # def testProcessDelay(self):
   #     pass
   # def testGetIdleTime(self):
   #     pass
