#!/usr/bin/env python
# encoding: utf-8
"""
IGPLinkTest.py

Created by Virginie Van den Schrieck on 2009-05-20.
Copyright (c) 2009 . All rights reserved.
"""

import unittest
from SimBGP.simbgp import SimBGP

class CIGPLinkTest(unittest.TestCase):
    """Test the class representing an IGP link"""
    def setUp(self):
        pass 
    def tearDown(self):
        pass
    def testLinkDelay(self): 
        link=SimBGP.CIGPLink("1","2", 300000, SimBGP.interpretBandwidth("100M"))
        self.assertEqual(link.link_delay(100000000), 2000000)
        #Test default value
        link=SimBGP.CIGPLink("1","2")
        self.assertEqual(link.link_delay(100000000), 1000000*(5.0/3000.0 + 1.0))