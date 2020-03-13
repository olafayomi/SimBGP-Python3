import unittest
from SimBGP.simbgp import SimBGP

class CLinkTest(unittest.TestCase):
	"""Basic unit tests for CLink Class"""
	def setUp(self):   
		SimBGP.init()
		SimBGP._router_list["A"]=SimBGP.CRouter(1,"A")
		SimBGP._router_list["B"]=SimBGP.CRouter(1,"B")
		SimBGP._router_list["C"]=SimBGP.CRouter(2,"C")
		self.link1=SimBGP.CLink("A","B")
		self.link2=SimBGP.CLink("B","C")
		
	def testStr(self):
		"""Testing textual link representation"""
		self.assertEqual(str(self.link1), "A-B")
		
	def testGetPeer(self):
		"""Testing other link end getter"""
		self.assertEqual(self.link1.getPeer("A"),"B")
		self.assertEqual(self.link1.getPeer("B"),"A")
		self.assertRaises(SimBGP.BadLinkEndException, self.link1.getPeer, "C")
		
	def testIBGP_EBGP(self):
		"""Testing obtention of BGP link type (iBGP vs eBGP)"""
		self.assertEqual(self.link1.ibgp_ebgp(), SimBGP.IBGP_SESSION)
		self.assertEqual(self.link2.ibgp_ebgp(), SimBGP.EBGP_SESSION)
		
