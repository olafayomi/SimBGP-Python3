import unittest
from SimBGP3.simbgp import SimBGP

class AddPathFuncTest(unittest.TestCase):
    """Test for AddPath implementation """
    def setUp(self):
        SimBGP.init()
        self.router=SimBGP.CRouter(1, "1.0")
        SimBGP._router_list["1.0"]=self.router
        SimBGP._router_list["2.0"]=SimBGP.CRouter(2, "2.0")
        self.myLink1=self.router.getPeerLink("2.0")
        self.router.peers["2.0"]=SimBGP.CPeer("2.0",self.myLink1)
        self.router.peers["2.0"].rib_out["1.0/8"]=[]
        map1=SimBGP.CRouteMap("filter-community-1","deny","1")
        map1.match.append("community-list 1".split()) 
        SimBGP._route_map_list["filter-community-1"]=map1
        self.router.peers["2.0"].route_map_out=["filter-community-1"]
        self.router.loc_rib["1.0/8"]=[]
        self.path1=SimBGP.CPath()
        self.path2=SimBGP.CPath()
        self.path3=SimBGP.CPath()
        self.path4=SimBGP.CPath()
        self.path1.igp_cost=10
        self.path2.igp_cost=20
        self.path2.community=["1"]
        self.path3.med=10
        self.path4.local_pref=90
        self.router.loc_rib["1.0/8"]=[self.path1,self.path2,self.path3, self.path4]
    
    def testReceive_AddPaths(self):
        #TODO: testReceive_AddPaths
        pass
    
    def testIsUrgentWithdrawal_AddPaths(self):
        #testIsUrgentWithdrawal_AddPaths
        pass
    def testPresend2peer_AddPaths(self):
        #TODO : test presend2peer_AddPaths    
        pass
    def testSendto_AddPaths(self):
        #TODO: test sendo_addpaths
        pass
 
    def testDelivery_AddPaths(self) : 
        #TODO: Test delivery_AddPaths
        pass
    
    def testDeltaFromRibout(self):   
        print "First test : Empty ribout"
        newpaths=[self.path1, self.path2, self.path3]
        result=self.router.delta_from_ribout("2.0", "1.0/8", newpaths)
        #TODO: assertion
      
        print "Check with unchanged ribout"
        result=self.router.delta_from_ribout("2.0", "1.0/8", newpaths)
        self.assertFalse(result)
        
        print "Check with same size new paths"
        SimBGP._event_Scheduler=SimBGP.COrderedList()
        newpaths=[self.path4, self.path2, self.path3]
        result=self.router.delta_from_ribout("2.0", "1.0/8", newpaths)
        self.assertTrue(result)
        self.assertEqual(len(SimBGP._event_Scheduler), 1)
        num_entry=0
        for entry in self.router.peers["2.0"].rib_out["1.0/8"] : 
            if entry!=None : 
                num_entry+=1
        self.assertEqual(num_entry, len(newpaths))
        
        print "Check with less paths"
        SimBGP._event_Scheduler=SimBGP.COrderedList()
        newpaths=[self.path2, self.path3]
        result=self.router.delta_from_ribout("2.0", "1.0/8", newpaths)
        self.assertTrue(result)
        self.assertEqual(len(SimBGP._event_Scheduler), 1)
        num_entry=0
        for entry in self.router.peers["2.0"].rib_out["1.0/8"] : 
            if entry!=None : 
                num_entry+=1
        self.assertEqual(num_entry, len(newpaths))
        print "Check with more paths"
        SimBGP._event_Scheduler=SimBGP.COrderedList()
        newpaths=[self.path1, self.path2, self.path3, self.path4]
        result=self.router.delta_from_ribout("2.0", "1.0/8", newpaths)
        self.assertTrue(result)
        self.assertEqual(len(SimBGP._event_Scheduler), 2)
        num_entry=0
        for entry in self.router.peers["2.0"].rib_out["1.0/8"] : 
            if entry!=None : 
                num_entry+=1
        self.assertEqual(num_entry, len(newpaths))
        print "Testing holes"
        SimBGP._event_Scheduler=SimBGP.COrderedList()
        newpaths=[self.path1, self.path3, self.path4]
        result=self.router.delta_from_ribout("2.0", "1.0/8", newpaths)
        SimBGP._event_Scheduler=SimBGP.COrderedList()
        self.path2.index=10
        newpaths=[self.path1, self.path2, self.path3, self.path4]
        result=self.router.delta_from_ribout("2.0", "1.0/8", newpaths)
    
    def testSelectionModeNBests(self):
        
    def testSelectionModeNBests(self):
        pass
    def testSelectionModeNBests(self):
        pass
    def testSelectionModeNBests(self):
        pass
    def testSelectionModeNBests(self):
        pass
    def testSelectionModeNBests(self):
        pass
        
