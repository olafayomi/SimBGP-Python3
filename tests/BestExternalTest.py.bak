import unittest, sys
#from SimBGP.simbgp import SimBGP
import SimBGP

class ExternalBestTest(unittest.TestCase):
    """Test for Best External advertisement option"""
    def setUp(self):
        #Configuring topology
        #SimBGP.runConfigFile("../../config/best_external.cfg")
        SimBGP.runConfigFile("best_external.cfg")
    def tearDown(self):
        SimBGP.init()
        
    def testBestExternalConfig(self):
        """Check if best external is configured"""
        for router in SimBGP._router_list.values() : 
            try : 
                self.assertTrue(router.bgp_mode==SimBGP.BGP_MODE_BEST_EXTERNAL)
            except AssertionError : 
                print >>sys.stderr, "Router ", router.id, "is not best external :", router.bgp_mode
    
    def testBestExternalBasic(self):
        """Load example topology and check if Route Reflector receives the best external path from R1.1"""
        if SimBGP._router_list["0.0.1.3"].peers["0.0.1.1"].rib_in.has_key("2.0/8") : 
            self.assertEqual(len(SimBGP._router_list["0.0.1.3"].peers["0.0.1.1"].rib_in["2.0/8"]),1)
        #Rerun same topology but without best external
        
            #print "\n"
            #SimBGP._router_list["1.3"].showAllRib()
        #TODO: Test with two best external - Check if the best is send. 
        
    
    #def testBestExternalMRAI(self):
     #   pass
        
    #TODO: with both MRAI config (peer or prefix-based) 
