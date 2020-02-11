import unittest
import LinkTest
import IGPLinkTest
import IGPNetworkTest
import RouteMapTest
import BestExternalTest
import RouterTest
#import AddPathFuncTest
import PlainBGPTest
import AddPathsTest
import AllBGPTest
import TracerouteTest
import sys


#Defining test suites
suiteLink = unittest.makeSuite(LinkTest.CLinkTest, "test")
suiteIGPLink = unittest.makeSuite(IGPLinkTest.CIGPLinkTest, "test")
suiteIGPNetwork = unittest.makeSuite(IGPNetworkTest.CIGPNetworkTest, "test")
suiteRouteMap= unittest.makeSuite(RouteMapTest.CRouteMapTest, "test")
suiteBestExternal=unittest.makeSuite(BestExternalTest.ExternalBestTest, "test")
suiteRouter=unittest.makeSuite(RouterTest.CRouterTest, "test")
#suiteAddPathsFunc=unittest.makeSuite(AddPathFuncTest.AddPathFuncTest, "test")
suiteAddPaths=unittest.makeSuite(AddPathsTest.AddPathsTest, "test")
suitePlainBGP=unittest.makeSuite(PlainBGPTest.PlainBGPTest, "test")
suiteAllBGP=unittest.makeSuite(AllBGPTest.AllBGPTest, "test")
suiteTraceroute=unittest.makeSuite(TracerouteTest.TracerouteTest, "test")
#Initialising test runner
runner = unittest.TextTestRunner(verbosity=2)
sys.stderr.write("\n")
sys.stderr.write("Testing link functionnalities : \n")
sys.stderr.write("*******************************\n")
runner.run(suiteLink)
sys.stderr.write("===============================================================================\n")  

sys.stderr.write("\n")
sys.stderr.write("Testing IGP link functionnalities : \n")
sys.stderr.write("*******************************\n")
runner.run(suiteIGPLink)
sys.stderr.write("===============================================================================\n")

sys.stderr.write("\n")
sys.stderr.write("Testing IGP Network functionnalities : \n")
sys.stderr.write("*******************************\n")
runner.run(suiteIGPNetwork)
sys.stderr.write("===============================================================================\n")


sys.stderr.write("Testing Route Maps functionnalities : \n")
sys.stderr.write("*************************************\n")
runner.run(suiteRouteMap)
sys.stderr.write("===============================================================================\n")  
        
sys.stderr.write("Testing router functionnalities : \n")
sys.stderr.write("*********************************\n")
runner.run(suiteRouter)
sys.stderr.write("===============================================================================\n")  
        

sys.stderr.write("\n")
sys.stderr.write("Testing normal BGP behaviour in all modes : \n")
sys.stderr.write("********************************************\n")
runner.run(suiteAllBGP)
sys.stderr.write("===============================================================================\n")  


sys.stderr.write("\n")
sys.stderr.write("Testing Plain BGP mode: \n")
sys.stderr.write("************************\n")
runner.run(suitePlainBGP) 
sys.stderr.write("===============================================================================\n")  

sys.stderr.write("Testing Best External mode : \n")
sys.stderr.write("*****************************\n")
runner.run(suiteBestExternal)
sys.stderr.write("===============================================================================\n")  

sys.stderr.write("Testing Add Path mode: \n")
sys.stderr.write("***********************\n")
runner.run(suiteAddPaths)
sys.stderr.write("===============================================================================\n")  

sys.stderr.write("Testing Traceroute: \n")
sys.stderr.write("***********************\n")
runner.run(suiteTraceroute)
sys.stderr.write("===============================================================================\n")  
