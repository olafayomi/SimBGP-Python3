import unittest
#from SimBGP.simbgp import SimBGP
import SimBGP

class PlainBGPTest(unittest.TestCase):
    """Test for normal BGP behaviour on topology files"""
    def setUp(self):
        pass 
    def tearDown(self):
        SimBGP.init()
        SimBGP.BEST_EXTERNAL=False
        SimBGP.MAX_PATH_NUMBER=1
    def testPrefixAdvertisement(self):
        """Testing simple topology without filters (Check that all routers have at least one path)"""
        #SimBGP.runConfigFile("../../config/plain_bgp_base_topo.cfg")
        SimBGP. runConfigFile("plain_bgp_base_topo.cfg")
        for router in SimBGP._router_list : 
            self.assertEqual(len(SimBGP._router_list[router].loc_rib["2.0/8"]), 1)
    def testPrefixWithdrawal(self):
        """Testing that prefix are unreachable by all routers after prefix withdrawal"""
        #Same as above.  Withdraw prefix after some time, and check that no one has a path
        #SimBGP.runConfigFile("../../config/plain_bgp_base_topo.cfg")
        SimBGP.runConfigFile("plain_bgp_base_topo.cfg")
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP._systime, ["2.1", "2.0/8"], SimBGP.EVENT_WITHDRAW_PREFIX))
        SimBGP.run()
        for router in SimBGP._router_list : 
            self.assertEqual(len(SimBGP._router_list[router].loc_rib["2.0/8"]), 0)
    def testNotBestExternal(self):
        """Check that best external is not activated in normal mode"""
        SimBGP.init()
        #SimBGP.readConfigFile("../../config/best_external.cfg")
        SimBGP.readConfigFile("best_external.cfg")
        SimBGP.BGPModeAllRouters("BGP_NORMAL")
        SimBGP.computeIGP()
        SimBGP.run()
#        print SimBGP._router_list["1.1"].loc_rib["2.0/8"][0]
#        print SimBGP._router_list["1.1"].loc_rib["2.0/8"][1]
        if SimBGP._router_list["1.3"].peers["1.1"].rib_in.has_key("2.0/8") : 
            self.assertEqual(len(SimBGP._router_list["1.3"].peers["1.1"].rib_in["2.0/8"]),0)
            
   
            
