#!/usr/bin/env python
# encoding: utf-8
"""
IGPNetworkTest.py

Created by Virginie Van den Schrieck on 2009-05-20.
Copyright (c) 2009 . All rights reserved.
"""

import unittest
import networkx as nx
#from SimBGP.simbgp import SimBGP
import SimBGP

class CIGPNetworkTest(unittest.TestCase): 
    def setUp(self):
        SimBGP.init()
    def tearDown(self):
        #Clean all SimBGP data
        SimBGP.init()
    def testGetLink(self):
        myNet=SimBGP.CIGPNetwork()
        myNet.addRouter("1",1)
        myNet.addRouter("2",1)
        myNet.addRouter("3",1)
        myNet.addIGPLink("1","2",1500)
        myNet.addIGPLink("2","3")
        myNet.addIGPLink("1","3")
        myNet.compute()
        self.assertEqual(myNet.getIGPLink("3","1").cost, 500)
        self.assertEqual(myNet.getIGPLink("3","2").cost, 500) 
        self.assertEqual(myNet.getIGPLink("1","2").cost, 1500)   
    def testIGPShortestPath(self):
        myNet=SimBGP.CIGPNetwork()
        myNet.addRouter("1",1)
        myNet.addRouter("2",1)
        myNet.addRouter("3",1)
        myNet.addIGPLink("1","2",1500)
        myNet.addIGPLink("2","3",500)
        myNet.addIGPLink("3","1",500)
        myNet.compute()
        self.assertEqual(myNet.getShortestPathLength("1","2"),
            myNet.getShortestPathLength("2","1"))
        self.assertEqual(myNet.getShortestPathLength("1","2"),
            myNet.getShortestPathLength("2","1"))
        self.assertEqual(myNet.getShortestPathLength("1","2"), 1000)
        self.assertEqual(myNet.getShortestPathLength("1","3"), 500)   
        self.assertEqual(myNet.getShortestPathLength("3","1"), 500)       
        self.assertEqual(myNet.getShortestPathLength("3","2"), 500)
    def testDelayBetweenRouters(self):
        myNet=SimBGP.CIGPNetwork()
        myNet.addRouter("1",1)
        myNet.addRouter("2",1)
        myNet.addRouter("3",1)
        myNet.addIGPLink("1","2",1500)
        myNet.addIGPLink("2","3")
        myNet.addIGPLink("3","1")
        myNet.compute()
        #Link delay must be twice the default delay with a cost of 1 
        # See class IGP Link test
        self.assertEqual(myNet.getPathTransmissionDelay("1","2", 100000000), 
            2*1000000*(5.0/3000.0 + 1.0))
    def testUnreachability(self):
        #Create unconnected network
        myNet=SimBGP.CIGPNetwork()
        myNet.addRouter("1",1)
        myNet.addRouter("2",1)
        myNet.addRouter("4",1)
        myNet.addRouter("5",1)
        myNet.addIGPLink("1","2",1500)
        myNet.addIGPLink("4","5")
        myNet.compute()
        self.assertFalse(myNet.isReachableFrom("1","5"))
        self.assertFalse(myNet.isReachableFrom("5","1"))    
        self.assertEquals(myNet.getShortestPathLength("1","5"), None) 

    def testDomainIsolation(self):
        #Create two connected domains
        myNet=SimBGP.CIGPNetwork()
        myNet.addRouter("1",1)
        myNet.addRouter("2",1)
        myNet.addRouter("3",2)
        myNet.addRouter("4",2)
        myNet.addIGPLink("1","2",1500)
        myNet.addIGPLink("3","4")
        myNet.addIGPLink("2","3")
        myNet.compute()
        self.assertFalse(myNet.isReachableFrom("1","4"))
        self.assertFalse(myNet.isReachableFrom("4","1"))  
        #1 can join 3 because 3 is ASBR
        self.assertTrue(myNet.isReachableFrom("1","3"))
        #3 cannot join 1 because 1 is not ASBR of AS1
        self.assertFalse(myNet.isReachableFrom("3","1"))
        #2 ASBR => must be reachable
        self.assertTrue(myNet.isReachableFrom("2","3"))
        #4 is not ASBR => not joignable from outside
        self.assertFalse(myNet.isReachableFrom("2","4"))
        #2 is an ASBR 
        self.assertTrue(myNet.isReachableFrom("4","2"))
        #Reg link
        self.assertTrue(myNet.isReachableFrom("3","2"))
        self.assertTrue(myNet.isReachableFrom("2","3"))
        #Inside domains
        self.assertTrue(myNet.isReachableFrom("1","2"))
        self.assertTrue(myNet.isReachableFrom("3","4"))
        self.assertTrue(myNet.isReachableFrom("2","1"))
        self.assertTrue(myNet.isReachableFrom("4","3"))
                
        

        
    def testIGPConfig(self):
        #SimBGP.runConfigFile("../../config/igp_config.cfg") 
        SimBGP.runConfigFile("igp_config.cfg")
        self.assertEqual(SimBGP._igp_graph.getIGPLink("3","1").cost, 500)
        self.assertEqual(SimBGP._igp_graph.getIGPLink("3","2").cost, 500) 
        self.assertEqual(SimBGP._igp_graph.getIGPLink("1","2").cost, 1500)
        self.assertEqual(SimBGP._igp_graph.getShortestPathLength("1","2"), 1000)
        self.assertEqual(SimBGP._igp_graph.getShortestPathLength("1","3"), 500)   
        self.assertEqual(SimBGP._igp_graph.getShortestPathLength("3","1"), 500)       
        self.assertEqual(SimBGP._igp_graph.getShortestPathLength("3","2"), 500)
        self.assertEqual(SimBGP._igp_graph.getPathTransmissionDelay("1","2", 100000000), 
            2*1000000*(5.0/3000.0 + 0.5))
            
    def testLinkDown(self):
        #SimBGP.runConfigFile("../../config/igp_config.cfg") 
        SimBGP.runConfigFile("igp_config.cfg")
        SimBGP._event_Scheduler.add(SimBGP.CEvent(SimBGP.toSystemTime(100.0), ["3", "2"], SimBGP.EVENT_LINK_DOWN))
        SimBGP.run()
        self.assertEqual(SimBGP._igp_graph.getShortestPathLength("3","2"), 2000)
