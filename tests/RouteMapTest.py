import unittest
from SimBGP.simbgp import SimBGP

class CRouteMapTest(unittest.TestCase):
    """Test for Route Map filters"""
     
    def setUp(self):
        pass
            
    def testMatchCommunities(self):
        """Testing filtering based on communities"""
        self.routemap1=SimBGP.CRouteMap("RM1", "permit", 10)
        self.routemap1.match.append("community-list 1:2:3 exact".split())
        self.routemap2=SimBGP.CRouteMap("RM2", "permit", 10)
        self.routemap2.match.append("community-list 1 exact".split())
        self.routemap3=SimBGP.CRouteMap("RM3", "permit", 10)
        self.routemap3.match.append("community-list 1".split())
        self.routemap4=SimBGP.CRouteMap("RM4", "permit", 10)
        self.routemap4.match.append("community-list 4".split())
        path=SimBGP.CPath()
        path.community.append("1")
        path.community.append("3")
        path.community.append("2")
        path.community.sort()
        #Exact community list - Match
        self.assertTrue(self.routemap1.isMatch(2.0/8, path))
        #Exact community list - Don't match
        self.assertFalse(self.routemap2.isMatch(2.0/8, path))
        #Contains community - Match
        self.assertTrue(self.routemap3.isMatch(2.0/8, path))
        #Contains community - Doesn't match
        self.assertFalse(self.routemap4.isMatch(2.0/8, path))
        
    def testMatchASPath(self):
        """Testing filtering based on ASPath"""
        #Testing for regular expressions matching
        self.routemap1=SimBGP.CRouteMap("RM1", "permit", 10)
        self.routemap1.match.append("as-path ^0".split())
        path=SimBGP.CPath()
        path.aspath=[0, 1]
        self.assertTrue(self.routemap1.isMatch(2.0/8, path))
        #Testing for regular expressions not matching
        self.routemap1=SimBGP.CRouteMap("RM1", "permit", 10)
        self.routemap1.match.append("as-path ^1".split())
        path=SimBGP.CPath()
        path.aspath=[0, 1]
        self.assertFalse(self.routemap1.isMatch(2.0/8, path))
        
    def testMatchPrefix(self):
        """Testing filtering based on prefix match"""
        #Testing prefix match
        self.routemap1=SimBGP.CRouteMap("RM1", "permit", 10)
        self.routemap1.match.append("ip address 2.0/8".split())
        self.assertTrue(self.routemap1.isMatch("2.0/8", None))
        #Testing prefix not matching
        self.routemap1=SimBGP.CRouteMap("RM1", "permit", 10)
        self.routemap1.match.append("ip address 3.0/8".split())
        self.assertFalse(self.routemap1.isMatch("2.0/8", None))
        #Caution : Does not cover more specific!!! 
        
    def testMatchMetric(self):
        """Testing filtering based on MED match"""
        path=SimBGP.CPath()
        path.med=10
        self.routemap1=SimBGP.CRouteMap("RM1", "permit", 10)
        self.routemap1.match.append("metric 10".split())
        self.assertTrue(self.routemap1.isMatch("2.0/8", path))
        self.routemap1=SimBGP.CRouteMap("RM1", "permit", 10)
        self.routemap1.match.append("metric 5".split()) 
        self.assertFalse(self.routemap1.isMatch("2.0/8", path))
        
    def testActionLocPref(self):
        """Testing locpref tagging"""
        path=SimBGP.CPath()
        self.routemap1=SimBGP.CRouteMap("RM1", "permit", 10)
        self.routemap1.action.append("local-preference 80".split())
        self.routemap1.performAction(path)
        self.assertEqual(path.local_pref, 80)
        
    def testActionCommunity(self):
        """Testing community tagging"""
        path=SimBGP.CPath()
        path.community=['1','2','3']
        self.routemap1=SimBGP.CRouteMap("RM1", "permit", 10)
        self.routemap1.action.append("community none".split())
        self.routemap1.performAction(path)
        self.assertEqual(path.community, [])
        path.community=['1','2','3']
        self.routemap1=SimBGP.CRouteMap("RM1", "permit", 10)
        self.routemap1.action.append("community 1:4:2".split())
        self.routemap1.performAction(path)
        self.assertEqual(path.community, ['1','2','4'])
        self.routemap1=SimBGP.CRouteMap("RM1", "permit", 10)
        self.routemap1.action.append("community 5:2 additive".split())
        self.routemap1.performAction(path)
        self.assertEqual(path.community, ['1','2','2','4','5'])
      
    def testActionMetric(self):
        """Testing MED tagging"""
        path=SimBGP.CPath()
        self.routemap1=SimBGP.CRouteMap("RM1", "permit", 10)
        self.routemap1.action.append("metric 45".split())
        self.routemap1.performAction(path)
        self.assertEqual(path.med, 45)
        
    def testActionASPathPrepend(self):
        """Testing ASPath Prepending"""
        path=SimBGP.CPath()
        self.routemap1=SimBGP.CRouteMap("RM1", "permit", 10)
        self.routemap1.action.append("as-path prepend 10 10 10".split())
        self.routemap1.performAction(path)
        self.assertEqual(len(path.aspath), 3)