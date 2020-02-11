import unittest
import sys
import tempfile
from SimBGP.simbgp import SimBGP

class AddPathsTest(unittest.TestCase):
    """Test for AddPath implementation """
    def setUp(self):
        SimBGP.init()
    def tearDown(self):
        SimBGP.SHOW_RECEIVE_EVENTS=False
        SimBGP.SHOW_FINAL_RIBS=False
        SimBGP.init()
    def testAddPathsBasic(self):
        """Checking propagation of all paths in iBGP and one paths only in eBGP"""
        SimBGP.runConfigFile("../../config/add_paths.cfg")  
        if SimBGP._router_list["1.1"].loc_rib.has_key("2.0/8") : 
            self.assertEqual(len(SimBGP._router_list["1.1"].loc_rib["2.0/8"]),3)
        if SimBGP._router_list["1.2"].loc_rib.has_key("2.0/8") : 
            self.assertEqual(len(SimBGP._router_list["1.2"].loc_rib["2.0/8"]),3)
        if SimBGP._router_list["1.3"].loc_rib.has_key("2.0/8") : 
            self.assertEqual(len(SimBGP._router_list["1.3"].loc_rib["2.0/8"]),4)
        if SimBGP._router_list["1.4"].loc_rib.has_key("2.0/8") : 
            self.assertEqual(len(SimBGP._router_list["1.4"].loc_rib["2.0/8"]),4)
        #These routers have one local path and receives zero or one path from AS1
        #but does not consider the latter because the local one has priority
        if SimBGP._router_list["2.1"].loc_rib.has_key("2.0/8") : 
            self.assertEqual(len(SimBGP._router_list["2.1"].loc_rib["2.0/8"]),1)
        if SimBGP._router_list["2.1"].peers["1.1"].rib_in.has_key("2.0/8") : 
            self.assertEqual(len(SimBGP._router_list["2.1"].peers["1.1"].rib_in["2.0/8"]),1)
        if SimBGP._router_list["3.2"].loc_rib.has_key("2.0/8") : 
            self.assertEqual(len(SimBGP._router_list["3.2"].loc_rib["2.0/8"]),1)
        if SimBGP._router_list["3.2"].peers["1.2"].rib_in.has_key("2.0/8") : 
            self.assertEqual(len(SimBGP._router_list["3.2"].peers["1.2"].rib_in["2.0/8"]),0)
            
    def testAddPathsWithdraw(self):
        """Checking path withdrawal"""
        #SimBGP.SHOW_RECEIVE_EVENTS=True
        #SimBGP.SHOW_FINAL_RIBS=True        
        SimBGP.runConfigFile("../../config/add_paths.cfg")  
        #Activate msg logging
        SimBGP.SHOW_RECEIVE_EVENTS=True        
        #Save stdout
        old_stdout=sys.stdout
        #redirect stdout to tmp file
        tmpfile=tempfile.TemporaryFile()
        sys.stdout=tmpfile
        # -- Remove one of the two pahts (best locpref)
        SimBGP._router_list["2.1"].withdraw_prefix("2.0/8")
        SimBGP.run()
        sys.stdout.flush()
        #Restore stdout
        sys.stdout=old_stdout
        tmpfile.seek(0)
        #Check that all routers have only one path
        for id, router in SimBGP._router_list.iteritems() :
            for p in router.loc_rib["2.0/8"] :
                self.assertNotEqual(p.nexthop, "2.1")
        #Check msg log : Five W must be seen
        # One from 2.1 to 1.1, two from 1.1 to RRs, and two from RRs to 
        # 1.5 (because they are using its path now) 
        # Other messages must be BGP update
        num_withdraws=0
        for line in tmpfile :
            #print line.strip()
            if 'W' in line : 
                num_withdraws+=1
        tmpfile.close()
        self.assertEqual(num_withdraws, 5)
            
        # -- Remove last path, check that adjribins are empty
        
        #Save stdout
        old_stdout=sys.stdout
        #redirect stdout to tmp file
        tmpfile=tempfile.TemporaryFile()
        sys.stdout=tmpfile
        SimBGP._router_list["3.2"].withdraw_prefix("2.0/8")
        SimBGP.run()
        #Restore stdout
        sys.stdout=old_stdout
        tmpfile.seek(0)
        for id, router in SimBGP._router_list.iteritems() : 
           self.assertEqual(len(router.loc_rib["2.0/8"]),0)
            
       
        num_withdraws=0
        for line in tmpfile :
            #print line.strip()
            if 'W' in line : 
                num_withdraws+=1
        tmpfile.close()
        self.assertEqual(num_withdraws, 11)
        
    def testAddPathsBestBin(self) :
        #Discard AddPaths config
        SimBGP.init()
        SimBGP.readConfigFile("../../config/add_paths2.cfg") 
        SimBGP.computeIGP()
        #Test with two paths : One with LP100, one with LP80
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(10.0), ["2.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(10.0), ["3.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP.run()
        #Two paths available : one best, plus one from second bin
        #Check that all routers have two paths with different nexthop
        for id, router in SimBGP._router_list.iteritems() : 
             if id[0:2]=="1." : 
                 self.assertNotEqual(router.loc_rib["1/8"][0].nexthop,router.loc_rib["1/8"][1].nexthop)
        #Add one more path with LP 100 : All routers have both LP100, plus possibly LP80 for the announcers
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(11.0), ["4.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP.run()
        for id, router in SimBGP._router_list.iteritems() : 
            if id[0:2]=="1." : 
                self.assertNotEqual(router.loc_rib["1/8"][0].nexthop,router.loc_rib["1/8"][1].nexthop)
                #print router, router.loc_rib["1/8"][0].nexthop, router.loc_rib["1/8"][1].nexthop
                if id=="1.1" : 
                    self.assertEqual(len(router.loc_rib["1/8"]), 3)
                else : 
                    self.assertEqual(len(router.loc_rib["1/8"]), 2)
        #Add one path with LP80, remove one with LP100 => 2LP80, 1LP100
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(12.0), ["5.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(12.0), ["3.1", "1/8"], SimBGP.EVENT_WITHDRAW_PREFIX))
        SimBGP.run()
        for id, router in SimBGP._router_list.iteritems() : 
            if id[0:2]=="1." : 
                self.assertNotEqual(router.loc_rib["1/8"][0].nexthop,router.loc_rib["1/8"][1].nexthop)
                try : 
                    self.assertEqual(len(router.loc_rib["1/8"]), 3)
                except AssertionError : 
                    print >>sys.stderr, "Router ", id, "is missing a path"
                    raise
    def testAddBestPaths(self) :
        #Discard AddPaths config
        SimBGP.init()
        SimBGP.readConfigFile("../../config/add_paths2.cfg") 
        SimBGP.computeIGP()
        #Test with two paths : One with LP100, one with LP80
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(10.0), ["2.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(10.0), ["3.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP.run()
        #Two paths available : one best, plus one from second bin
        #Check that all routers have two paths with different nexthop
        for id, router in SimBGP._router_list.iteritems() : 
             if id[0:2]=="1." : 
                 self.assertNotEqual(router.loc_rib["1/8"][0].nexthop,router.loc_rib["1/8"][1].nexthop)
        #Add one more path with LP 100 : All routers have both LP100, plus possibly LP80 for the announcers
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(11.0), ["4.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP.run()
        for id, router in SimBGP._router_list.iteritems() : 
            if id[0:2]=="1." : 
                self.assertNotEqual(router.loc_rib["1/8"][0].nexthop,router.loc_rib["1/8"][1].nexthop)
                #print router, router.loc_rib["1/8"][0].nexthop, router.loc_rib["1/8"][1].nexthop
                if id=="1.1" : 
                    self.assertEqual(len(router.loc_rib["1/8"]), 3)
                else : 
                    self.assertEqual(len(router.loc_rib["1/8"]), 2)
        #Add one more path again : 2 LP100 and 2 LP80.  Only 1.1 and 1.5 knows about LP80
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(12.0), ["5.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP.run()
        for id, router in SimBGP._router_list.iteritems() : 
            if id[0:2]=="1." : 
                self.assertNotEqual(router.loc_rib["1/8"][0].nexthop,router.loc_rib["1/8"][1].nexthop)
                if id=="1.1" or id=="1.5": 
                    self.assertEqual(len(router.loc_rib["1/8"]), 3)
                else : 
                    self.assertEqual(len(router.loc_rib["1/8"]), 2)
                    
        
        #Same, but use ASPath prepending instead of local pref       
        SimBGP.init()
        SimBGP.readConfigFile("../../config/add_paths3.cfg") 
        SimBGP.computeIGP()
        #Test with two paths : One with ASPL1, one with ASPL4
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(10.0), ["2.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(10.0), ["3.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP.run()
        #Two paths available : one best, plus one from second bin
        #Check that all routers have only best, except for 1.1
        for id, router in SimBGP._router_list.iteritems() :
            if id[0:2]=="1." :
                if id=="1.1" :
                    self.assertEqual(len(router.loc_rib["1/8"]), 2)
                else :
                    self.assertEqual(len(router.loc_rib["1/8"]), 1)
                
        #Add one more path with ASPathLen 1 : All routers have both ASPL1, plus possibly ASPL4 for the announcers
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(11.0), ["4.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP.run()
        for id, router in SimBGP._router_list.iteritems() : 
            if id[0:2]=="1." : 
                self.assertNotEqual(router.loc_rib["1/8"][0].nexthop,router.loc_rib["1/8"][1].nexthop)
                #print router, router.loc_rib["1/8"][0].nexthop, router.loc_rib["1/8"][1].nexthop
                if id=="1.1" : 
                    self.assertEqual(len(router.loc_rib["1/8"]), 3)
                else : 
                    self.assertEqual(len(router.loc_rib["1/8"]), 2)
        #Add one more path again : 2 ASPL 1 and 2 ASPL 4.  Only 1.1 and 1.5 knows about ASPL4
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(12.0), ["5.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP.run()
        for id, router in SimBGP._router_list.iteritems() : 
            if id[0:2]=="1." : 
                self.assertNotEqual(router.loc_rib["1/8"][0].nexthop,router.loc_rib["1/8"][1].nexthop)
                if id=="1.1" or id=="1.5": 
                    self.assertEqual(len(router.loc_rib["1/8"]), 3)
                else : 
                    self.assertEqual(len(router.loc_rib["1/8"]), 2)
                    
    def testSelectionModes(self) :
        SimBGP.init()
        SimBGP.readConfigFile("../../config/add-paths-mode-test.cfg") 
        SimBGP.computeIGP()   
        SimBGP.run()
        router=SimBGP._router_list["1.1"]
        path1=SimBGP.CPath()
        path2=SimBGP.CPath()
        path3=SimBGP.CPath()
        path4=SimBGP.CPath()
        path5=SimBGP.CPath()
        path1.local_pref=100
        path2.local_pref=100
        path3.local_pref=100
        path4.local_pref=80
        path5.local_pref=80
        path4.src_pid="1.2"
        path1.aspath=["1","2"]
        path2.aspath=["1","3"]
        path3.aspath=["2","1","3"]
        path4.aspath=["1"]
        path5.aspath=["1"]
        path1.igp_cost=10
        path2.igp_cost=20
        path3.igp_cost=30
        path4.igp_cost=40
        path4.igp_cost=50
        path5.igp_cost=60
        router.loc_rib["1.0/8"]=[path1,path2,path3, path4, path5]
        #BGP AddNBests
        router.bgp_mode=SimBGP.BGP_MODE_ADD_N_BESTS
        router.bgp_num_paths=2
        result=router.compute_paths_for_peer("1.2","1.0/8")
        self.assertEqual(len(result),2)
        router.bgp_num_paths=4
        result=router.compute_paths_for_peer("1.2","1.0/8")
        self.assertEqual(len(result),3)
        #BGP AddNPaths
        router.bgp_mode=SimBGP.BGP_MODE_ADD_N_PATHS
        router.bgp_num_paths=2
        result=router.compute_paths_for_peer("1.2","1.0/8")
        self.assertEqual(len(result),2)
        router.bgp_num_paths=4
        result=router.compute_paths_for_peer("1.2","1.0/8")
        self.assertEqual(len(result),4)
        #BGP AddAllPaths
        router.bgp_mode=SimBGP.BGP_MODE_ADD_ALL_PATHS
        path4.src_pid="1.3"
        result=router.compute_paths_for_peer("1.2","1.0/8")
        self.assertEqual(len(result),5)
        #BGP Best Bin
        router.bgp_mode=SimBGP.BGP_MODE_BEST_BIN
        result=router.compute_paths_for_peer("1.2","1.0/8")
        self.assertEqual(len(result),3)
        for path in result : self.assertEqual(path.local_pref,100)
            #Add better path => second bin needed
        path1.local_pref=120
        result=router.compute_paths_for_peer("1.2","1.0/8")
        self.assertEqual(len(result),3)
        for path in result : self.assertTrue(path.local_pref>=100)
        path1.local_pref=100
        #BGP AddAllBest
        router.bgp_mode=SimBGP.BGP_MODE_ADD_BEST_PATHS
        result=router.compute_paths_for_peer("1.2","1.0/8")
        self.assertEqual(len(result),2)
        #BGP AddGroupBest
        router.bgp_mode=SimBGP.BGP_MODE_GROUP_BEST
        result=router.compute_paths_for_peer("1.2","1.0/8")
        self.assertEqual(len(result),2)
        ases=[]
        for path in result : 
            self.assertTrue(path.aspath[0] not in ases)
            ases.append(path.aspath[0])
        #Decisive step 
        router.bgp_mode=SimBGP.BGP_MODE_DECISIVE_STEP
        result=router.compute_paths_for_peer("1.2","1.0/8")
        self.assertEqual(len(result),2)
            #second test : med is decisive step, and 3 first paths have ASPath len of 2
        path3.aspath=["1","2"]
        path1.med=10
        path2.med=20
        path3.med=20   
        result=router.compute_paths_for_peer("1.2","1.0/8")
        self.assertEqual(len(result),3)
    def testAddNPathsLoop(self) : 
        SimBGP.init()
        SimBGP.readConfigFile("../../config/add_n_paths_loop.cfg") 
        SimBGP.computeIGP()
        #Test with two paths
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(10.0), ["2.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(10.0), ["3.1", "1/8"], SimBGP.EVENT_ANNOUNCE_PREFIX))
        SimBGP.run()
        #Loop? 
        self.assertFalse(SimBGP._systime < SimBGP.toSystemTime(2000)) 
            
