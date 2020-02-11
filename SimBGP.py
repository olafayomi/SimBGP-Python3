#!/usr/bin/env python


# * Copyright (c) 2008, Jian Qui
# * All rights reserved.
# * Redistribution and use in source and binary forms, with or without
# * modification, are permitted provided that the following conditions are met:
# *
# *     * Redistributions of source code must retain the above copyright
# *       notice, this list of conditions and the following disclaimer.
# *     * Redistributions in binary form must reproduce the above copyright
# *       notice, this list of conditions and the following disclaimer in the
# *       documentation and/or other materials provided with the distribution.
# *     * Neither the name of the University of California, Berkeley nor the
# *       names of its contributors may be used to endorse or promote products
# *       derived from this software without specific prior written permission.
# *
# * THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND ANY
# * EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# * DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY
# * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# @Author : Jian Qiu (Original SimBGP)
# @Author : Virginie Van den Schrieck (virginie.vandenschrieck@uclouvain.be)
#           (AddPaths support, IGP layer improved BUT : not compatible anymore
#            with BRAP,Ghost Flushing, Ghost Buster and EPIC)
# @Author : Dimeji Fayomi (olafayomi@wand.net.nz)
#           (Ensure the cost of links provided in config file is passed as a 
#            weight attribute when creating links/edges and then used in shortest 
#            path calculation as opposed to using the default which is one. 
#            Port code to Python 3 and fix bugs introduced as a result.)
# @Last modified : Feb.11, 2020 



import sys;
import string;
import re;
import time;
import random;
import subprocess
import inspect
import networkx as nx
## Installed by dimeji 2020/02/08
from beeprint import pp


MRAI_PEER_BASED = 0;
MRAI_PREFIX_BASED = 1;
GLOBAL_MRAI=False
GLOBAL_IBGP_MRAI=15
GLOBAL_EBGP_MRAI=30

MRAI_JITTER = True;

bgp_always_compare_med = False;
#TODO: Manage configuration of cost-based-delay
cost_based_delay=True;
ssld = True;
wrate = False;


always_mrai = False;
default_local_preference = 100;

default_weight = 1000;
default_backup_weight_internal = 0;
default_backup_weight_internal_client = 10;
default_backup_weight_external = 20;


backup_communities=False;
BGP_MODE_NORMAL=1
BGP_MODE_ADD_N_PATHS=2
BGP_MODE_ADD_N_BESTS=3
BGP_MODE_BEST_EXTERNAL=4
BGP_MODE_ADD_ALL_PATHS=5
BGP_MODE_BEST_BIN=6
BGP_MODE_ADD_BEST_PATHS=7
BGP_MODE_GROUP_BEST=8
BGP_MODE_DECISIVE_STEP=9

RANDOMIZED_KEY = "";

SHOW_UPDATE_RIBS = False;
SHOW_RIB_UPDATE = False
CHECK_FORWARDING=False

SHOW_1PATH_RIB_UPDATE=False
SHOW_RECEIVE_EVENTS = False;
SHOW_LINK_EVENTS=False;
SHOW_SEND_EVENTS = False;
SHOW_FINAL_RIBS = False;
SHOW_DEBUG = False
SHOW_NH=False
DEBUG_ADDPATHS = False;
CHECK_LOOP = False;
SHOW_FINAL_RIBOUTS_COUNT=False
KEEP_VIRTUAL_LOC_PREF=False


_link_delay_table = {};
default_link_delay_func = ["uniform", 0.01, 0.1];
default_process_delay_func = ["uniform", 0.001, 0.01];



###################################
EVENT_TERMINATE = 0;
EVENT_MRAI_EXPIRE_SENDTO = 1;
EVENT_UPDATE = 2;
EVENT_RECEIVE = 3;
EVENT_LINK_DOWN = 4;
EVENT_LINK_UP   = 5;
EVENT_ANNOUNCE_PREFIX = 6;
EVENT_WITHDRAW_PREFIX = 7;
EVENT_PEER_DOWN = 8;
EVENT_PEER_UP   = 9;
EVENT_TRACEROUTE = 10
EVENT_INJECT_MRT = 11

IBGP_SESSION = 0;
EBGP_SESSION = 1;
LOCAL=2

LINK_DOWN = -1
LINK_UP   = 0
PEER_DOWN=-1
PEER_UP=0
PEER_UNREACH=-1
PEER_REACH=0
_seq_seed = 0;
_systime = 0; # in microsecond
_event_Scheduler = None
num_ebgp_msgs=0


############################################################################################################################
#                                     Miscellaneous utility function
############################################################################################################################

#
# Print time in second with six digit precision
#
def formatTime(tm):
    #print >>sys.stderr,  tm, str(int(tm/1000.0)*1.0/1000.0)
    return str(int(tm/1000.0)*1.0/1000.0)


#
# Return formatted system time
#
def getSystemTimeStr():
    global _systime;
    return formatTime(_systime);

#
# Return 1 if x is strictly positive, -1 if it is negative, 0  if it is nul
#
def sgn(x):
    if x < 0:
        return -1;
    elif x == 0:
        return 0;
    else:
        return 1;


#
# Return delay in function of 
#
def interpretDelayfunc(obj, rand_seed, delayfunc):
    global RANDOMIZED_KEY;
    if delayfunc[0] == "deterministic":
        return delayfunc[1];
    else:
        if rand_seed is None:
            seed = str(obj) + RANDOMIZED_KEY;
            rand_seed = random.Random(seed);
        if delayfunc[0] == "normal": # normal mu sigma
            return rand_seed.gauss(delayfunc[1], delayfunc[2]);
        elif delayfunc[0] == "uniform": # uniform a b
            return rand_seed.uniform(delayfunc[1], delayfunc[2]);
        elif delayfunc[0] == "exponential": # exponential lambda
            return rand_seed.expovariate(delayfunc[1]);
        elif delayfunc[0] == "pareto": # pareto alpha
            return rand_seed.paretovariate(delayfunc[1]);
        elif delayfunc[0] == "weibull": # weibull alpha beta
            return rand_seed.weibullvariate(delayfunc[1], delayfunc[2]);
        else:
            print(("Unsupported distribution", self.delayfunc));
            sys.exit(-1);

#
# Convert tm value in seconds into microseconds
#
def toSystemTime(tm):
    return tm*1000000;

#
# Increment sequence seed
#
def getSequence():
    global _seq_seed;
    _seq_seed = _seq_seed + 1;
    return _seq_seed;

############################################################################################################################
#                                     Exceptions
############################################################################################################################
#@vvandens, 9/2/09

class BadLinkEndException(Exception) : 
    pass;


############################################################################################################################
#                                     Class CVirtualRouter - Represents a virtual BGP router
############################################################################################################################
class CVirtualRouter :
    """This router only has one neighbor (eBGP). Its only goal is to maintain a BGP session and inject BGP routes on it"""
    def __init__(self, asn, ip):
        self.id=ip
        self.asn=asn
        self.peers={}
        self.loc_rib={}

    def __str__(self):
        return str(self.id) + "(" + str(self.asn) + ")";
        
    def advertise_mrt(self,mrtPath):
#        print mrtPath
        path=CPath()
        items=mrtPath.split("|")
        peer_id=items[3]
        path.local_pref=int(items[9])
        path.med=int(items[10])
        path.nexthop=items[8]
        if path.nexthop!=self.id : 
            print("Warning : Virtual peer IP does not correspond to path nexthop :", self.id, mrtPath, file=sys.stderr)
        prefix=items[5]
        #TODO : Better handling of ASSets
        aspath=items[6].replace('{', "")
        aspath=aspath.replace('}', "")
        path.aspath=[int(x) for x in aspath.split()]
        self.loc_rib[prefix]=[path]
        path_send=False
        for pid in list(self.peers.keys()) :
            if pid==peer_id : 
                update=CUpdate(prefix)
                update.paths.append(path)
                _event_Scheduler.add(CEvent(self.getPeerLink(pid).next_delivery_time(self.id, update.size()), [self.id, pid, update], EVENT_RECEIVE));
                path_send=True
        if not path_send : 
            print("Warning : MRT path could not be sent, no peer matching MRT peer IP", file=sys.stderr)
    #
    # Return the link corresponding to the peer pid
    #
    def getPeerLink(self, pid):
        return getRouterLink(self.id, pid);

    # Do nothing as this is a virtual router
    # 
    def updateIGPCost(self):
        pass
    
    #
    # Receive an  update : Do nothing. 
    #
    def receive(self, pid, update):
        pass
    
    #
    # 
    #
    def peerUp(self, pid):
        if pid in list(peers.keys()) :
            for prefix, path in self.routes.items() : 
                update=CUpdate(prefix)
                update.paths.append(path)
                _event_Scheduler.add(CEvent(self.getPeerLink(pid).next_delivery_time(self.id, update.size()), [self.id, pid, update], EVENT_RECEIVE));
        else : 
            print("Error : Unknown peer for virtual router :", pid, file=sys.stderr)
            sys.exit(-1)
            
    def peerDown(self, pid):
        pass
############################################################################################################################
#                                     Class CRouter - Represents a BGP router
############################################################################################################################


class CRouter:
    # id = None; # 4 octect ip address
    # asn = None; # u_int16_t AS number
    # peers = None;  # dictionary key: router id
    # loc_rib = None; # dictionary key: prefix
    # origin_rib = None; # Rib containing prefixes locally originated
    # best_external_rib = None;
    # next_idle_time = None; # the time to process the next update, guarantee procee in order
    # mrai = None;
    # mrai_setting = None;
    # route_reflector = None;
    # clusterID=None
    # rand_seed = None;
    # bgp_mode=None
    # bgp_num_paths=None

    #
    # Constructor - Initialize all instance variables
    #
    def __init__(self, a, i):
        global MRAI_PEER_BASED, RANDOMIZED_KEY;
        self.id = i;
        self.clusterID=i #Default clusterID is routerID
        self.asn = a;
        self.peers = {}; # rib_ins, rib_outs, mrai_timers
        self.loc_rib = {};
        self.best_external_rib={}
        self.origin_rib = {};
        self.next_idle_time = -1;
        self.mrai = {};
        self.mrai_setting = MRAI_PEER_BASED;
        self.route_reflector = False;
        seed = str(self) + RANDOMIZED_KEY;
        self.rand_seed = random.Random(seed);
        self.bgp_mode=BGP_MODE_NORMAL
        self.bgp_num_paths=1
        self.delay_withdraws=False
    #
    # Produce printable version of the object, i.e. <router-id>(<asnumber>)
    #    
    def __str__(self):
        return str(self.id) + "(" + str(self.asn) + ")";

    #
    # Configure MRAI ??????
    #
    def setMRAI(self, pid, prefix):
        return self.setMRAIvalue(pid, prefix, self.peers[pid].mrai_timer());

    #
    # Configure new MRAI value of the peer with the given timer value
    #
    def setMRAIvalue(self, pid, prefix, value):
        global _systime
        if value <= 0:
            return -1;
        global SHOW_DEBUG, MRAI_PEER_BASED, MRAI_PREFIX_BASED;
        if self.mrai_setting == MRAI_PEER_BASED:
                # MRAI never configured or outdated. 
            if (pid not in self.mrai) or self.mrai[pid] < _systime: # has not been set
                self.mrai[pid] = _systime + value;
                if SHOW_DEBUG:
                    print(str(self), "set mrai timer for ", pid, "to", formatTime(self.mrai[pid]));
            #Else : MRAI is running. 
            return self.mrai[pid];
        else: # MRAI_PREFIX_BASED:
            #First MRAI countdown for this peer
            if pid not in self.mrai:
                self.mrai[pid] = {};
            #MRAI never configured or outdated for this peer-prefix pair
            if (prefix not in self.mrai[pid]) or self.mrai[pid][prefix] < _systime: # if mrai has not been set yet
                self.mrai[pid][prefix] = _systime + value;
                if SHOW_DEBUG:
                    print(str(self), "set mrai timer for ", pid, prefix, "to", formatTime(self.mrai[pid]))
            return self.mrai[pid][prefix];

    #
    # Set MRAI value to 0
    #
    def resetMRAI(self, pid, prefix):
        global MRAI_PEER_BASED, MRAI_PREFIX_BASED;
        if self.mrai_setting == MRAI_PEER_BASED and pid in self.mrai:
            self.mrai[pid] = 0;
                #print str(self), "set mrai timer for ", pid, "to", self.mrai[pid];
        else: # MRAI_PREFIX_BASED:
            if pid in self.mrai and perfix in self.mrai[pid]: # if mrai has not been set yet
                self.mrai[pid][prefix] = 0;
                #print str(self), "set mrai timer for ", pid, prefix, "to", self.mrai[pid];
    #
    # Return next expiring time, or -1 if timer expired.
    #
    def mraiExpires(self, pid, prefix):
        global MRAI_PEER_BASED, MRAI_PREFIX_BASED, _systime;
        if self.mrai_setting == MRAI_PEER_BASED:
            if (pid not in self.mrai) or self.mrai[pid] < _systime:
                return -1; # expires
            else:
                return self.mrai[pid]; # return the expected expiring time
        elif self.mrai_setting ==  MRAI_PERFIX_BASED:
            if (pid not in self.mrai) or \
                (prefix not in self.mrai[pid]) or \
                self.mrai[pid][prefix] < _systime:
                return -1; #expired
            else:
                return self.mrai[pid][prefix]; # return the expected expiring time
        else:
            print("Invalid mrai setting");
            sys.exit(-1);

    #
    # Return the link corresponding to the peer pid
    #
    def getPeerLink(self, pid):
        return getRouterLink(self.id, pid);

    #
    # Recompute IGP distances for all paths in locrib and adjribin
    # Returns prefixes for which igp cost to nexthop has changed for at least
    #  one path
    # 
    def updateIGPCost(self):
        changed_pref=[]
        #Update IGP cost in adjribins
        for peer in list(self.peers.values()):
            for prefix in list(peer.rib_in.keys()) : 
                changed=False
                for path in  peer.rib_in[prefix]:
                    old_cost=path.igp_cost
                    new_cost=_igp_graph.getShortestPathLength(self.id, path.nexthop)
                    ### Added by dimeji fayomi 2020/02/10
                    #if self.id == "0.0.0.2":
                    #    print("In Adjacent RIB IN\n")
                    #    print("Cost of path is %s\n" % path.igp_cost)
                    #    print("New cost of path is %s\n" % new_cost)
                    #    pp(path)
                    #    print("\n\n\n")
                    #IGP cost changed
                    if old_cost!=new_cost : 
                        #print "IGP cost change for router", self, ":", path, old_cost, new_cost
                        #print "New path :",_igp_graph.getShortestPath(self.id, path.nexthop)
                        path.igp_cost=new_cost
                        if prefix not in changed_pref : 
                            changed_pref.append(prefix)
        #Same operation in locrib 
        for prefix in list(self.loc_rib.keys()) : 
            for path in self.loc_rib[prefix] : 
                old_cost=path.igp_cost
                new_cost=_igp_graph.getShortestPathLength(self.id, path.nexthop)
                ### Added by dimeji fayomi 2020/02/10
                #if self.id == "0.0.0.2":
                #    print("In Local  RIB\n")
                #    print("Cost of path is %s\n" % path.igp_cost)
                #    print("New cost of path is %s\n" % new_cost)
                #    pp(path)
                #    print("\n\n\n")
                #IGP cost changed
                if old_cost!=new_cost :
                    #print "IGP cost change for router", self, ":", path, old_cost, new_cost
                    path.igp_cost=new_cost
                    if prefix not in changed_pref : 
                        changed_pref.append(prefix)
        return changed_pref
    def peerReachable(self, peer):
        if not _igp_graph.isReachableFrom(self.id, peer) : 
            return False
        #iBGP peer : Must be reachable via nodes from the same AS
        if peer.asn==self.asn : 
            path=_igp_graph.getShortestPath(self.id, peer)
            for hop in path : 
                if _router_list[hop].asn!=self.asn : 
                    return False
        else : 
            pass
        #eBGP peer : Must be directly reachable
    # IGP graph changed => check for peer reachability and nexthop change
    def IGPChange(self):
        for peer in list(self.peers.keys()) :
            lk=self.getPeerLink(peer)
            #Peer unreachable : 
            if lk.reach==PEER_REACH and \
                (not _igp_graph.isReachableFrom(self.id, peer) or \
                 not _igp_graph.isReachableFrom(peer, self.id)) : #Unreach on any of the two ways
                lk.reach=PEER_UNREACH
                self.peerDown(peer)
                #Peer down for the other end of the link too
                _router_list[peer].peerDown(self.id)
                #print "Router", self.id, "peer down :", peer
            if lk.reach==PEER_UNREACH and \
                _igp_graph.isReachableFrom(self.id, peer) and \
                _igp_graph.isReachableFrom(peer, self.id) : #Two ways reachability
                lk.reach=PEER_REACH
                if lk.status==PEER_UP : 
                    #Sending updates
                    self.peerUp(peer)
                    _router_list[peer].peerUp(self.id)   
        changed_pref=self.updateIGPCost()
        [self.update(pref) for pref in changed_pref]
        # for pref in changed_pref : 
        #     #print "Router", self.id, "updates prefix", pref
        #     self.update(pref)

    #
    # Checking import filter for peer pid and received path. Return boolean
    #
    def importFilter(self, pid, prefix, path):
        global _route_map_list;
        #print "check importFilter", self, pid, prefix, path;
        if self.getPeerLink(pid).ibgp_ebgp() == EBGP_SESSION:
            # loop detection => ASPath
            if self.asn in path.aspath:
                return False;
        else : #IBGP session
            #Check if originator-id==router-id
            if path.originatorID is not None and self.id==path.originatorID :
                if SHOW_DEBUG : 
                    print("Path filtered : OriginatorID==RouterID", path.originatorID, self.id)
                return False
            if self.route_reflector and self.clusterID in path.clusterIDList : 
                if SHOW_DEBUG : 
                    print("Path filtered : clusterID in clusterIDList (pid, clusterid, path.clusteridlist)", self.id, self.clusterID, path.clusterIDList)
                return False
                
        #Retrieved configured maps for this peer
        maps = self.peers[pid].getRouteMapIn();
        for mapname in maps:
            map = _route_map_list[mapname];
            #Check path against route map
            if len(map.action) == 0 and (((not map.permit) and map.isMatch(prefix, path)) or (map.permit and (not map.isMatch(prefix, path)))):
                if DEBUG_ADDPATHS : 
                    print("Path from", pid, "filtered by", self)
                return False;
        return True;

    #
    # Build path to import based on  filters. Return new path instance.
    #
    def importAction(self, pid, prefix, path):
        global _route_map_list, default_local_preference, _router_list, KEEP_VIRTUAL_LOC_PREF
        newpath = CPath();
        newpath.copy(path);
        #EBGP session
        if self.getPeerLink(pid).ibgp_ebgp() == EBGP_SESSION:
            newpath.ibgp_ebgp=EBGP_SESSION
            newpath.weight = default_weight;
            newpath.nexthop = self.peers[pid].id;
            #Reset local pref value only if the router is not virtual and corresponding option is activated.
            if not (KEEP_VIRTUAL_LOC_PREF and isinstance(_router_list[pid],CVirtualRouter)) :
                newpath.local_pref = default_local_preference;
            if len(newpath.aspath) == 0 or newpath.aspath[0] != _router_list[pid].asn:
                newpath.aspath.insert(0, _router_list[pid].asn);
        #IBGP session
        else:
            newpath.ibgp_ebgp=IBGP_SESSION
            newpath.weight = default_weight;
            
                
        #Compute IGP Cost
        newpath.igp_cost=_igp_graph.getShortestPathLength(self.id,newpath.nexthop)
        newpath.src_pid = pid;
        maps = self.peers[pid].getRouteMapIn();
        for mapname in maps:
            map = _route_map_list[mapname];
            if map.permit and len(map.action) > 0 and map.isMatch(prefix, newpath):
                newpath = map.performAction(newpath);
        ### Added by dimeji 2020/02/10
        #print("New path imported for prefix %s by router %s to be returned\n" %(prefix, self.id))
        #pp(newpath)
        #print("\n\n\n")
        return newpath;

    #
    # Check if a path can be exported to a peer : Loop detection & map filtering 
    #
    def exportFilter(self, pid, prefix, path):
        global _router_list, ssld, _route_map_list, SHOW_DEBUG;
        #Loop prevention checks
        if path.src_pid == pid:
            if SHOW_DEBUG:
                print("source loop detection from router",self.id, "to router",\
                    pid, "with prefix", prefix)
            return False;    
        if self.getPeerLink(pid).ibgp_ebgp() == EBGP_SESSION: # Sending to eBGP peer
            # poison reverse
            if len(path.aspath) > 0 and _router_list[pid].asn == path.aspath[0]:
                if SHOW_DEBUG:
                    print("AS path loop detection!");
                return False;
            # send-side loop detection, SSLD
            if ssld and _router_list[pid].asn in path.aspath:
                if SHOW_DEBUG:
                    print("AS path ssld loop detection!");
                return False;
        else: #iBGP peer
            if path.ibgp_ebgp == IBGP_SESSION:
                #Apply iBGP-specific rules
                if (not self.route_reflector) or ((not self.peers[path.src_pid].route_reflector_client) and (not self.peers[pid].route_reflector_client)):
                    if SHOW_DEBUG:
                        print("IBGP rule :", str(self), path.src_pid, self.peers[path.src_pid].route_reflector_client, pid, self.peers[pid].route_reflector_client, "ibgp route-refelctor checking!");
                    return False;
                    
        #Route maps application
        maps = self.peers[pid].getRouteMapOut();
        for mapname in maps:
            map = _route_map_list[mapname];
            if len(map.action) == 0 and (((not map.permit) and map.isMatch(prefix, path)) or (map.permit and (not map.isMatch(prefix, path)))):
                if SHOW_DEBUG:
                    print("route map filtering!")
                    print("Router",self.id, "to peer", pid, "path :", str(path))
                return False;
        return True;

    #
    # Build path to export based on map actions.  Update path attributes
    #

    def exportAction(self, pid, prefix, path):
        global _route_map_list, EPIC, _systime;
        newpath = CPath();
        newpath.copy(path);
        if self.peers[pid].link.ibgp_ebgp() == EBGP_SESSION:
            newpath.local_pref = default_local_preference
            newpath.nexthop=self.id
            #reset iBGP attributes
            newpath.originatorID=None
            newpath.index=0
            newpath.clusterIDList=[]
            newpath.aspath.insert(0, self.asn); # append paths
            newpath.igp_cost = -1;
            newpath.ibgp_ebgp=EBGP_SESSION
            newpath.src_pid=self.id
        else : #IBGP session 
        #For reflected path, add Cluster-ID to Cluster-ID List
            if (self.route_reflector) : 
                if path.src_pid is not None and self.peers[path.src_pid].link.ibgp_ebgp()== IBGP_SESSION \
                    and (self.peers[path.src_pid].route_reflector_client 
                    or self.peers[pid].route_reflector_client) :      
                    newpath.clusterIDList.append(self.clusterID)
                    if newpath.originatorID is None : 
                        newpath.originatorID=newpath.src_pid
            #Nexthop-self
            if self.peers[pid].nexthopself : 
                newpath.nexthop=self.id
                #print "New path with NHS :", newpath
                #print "Nexhopself used!!", newpath.nexthop
        maps = self.peers[pid].getRouteMapOut();
        for mapname in maps:
            map = _route_map_list[mapname];
            if map.permit and len(map.action) > 0 and map.isMatch(prefix, newpath):
                path = map.performAction(newpath);
        ### Added by dimeji 2020/02/10
        #print("New path exported for prefix %s by router %s to be returned\n" %(prefix, self.id))
        #pp(newpath)
        #print("\n\n\n")
        
        return newpath;

    #
    # Compare two paths
    #
    def comparePath(self, path1, path2):
        ## Added by Dimeji Fayomi 2020/02/10
        #print("Evaluating path details in router id: %s\n" %self.id)
        #print("Path1:\n")
        #pp(path1)
        #print("\n")
        #print("Path2:\n")
        #pp(path2)
        #print("\n")
        return path1.compareTo_DP(path2);

    #
    # BGP selection process. Return change in best path and changing trend. 
    # Change = true if best path (or any path in the locrib) changed.  Trend = +1 if new 
    # best path is better than old one, -1 if the old one was better. 
    #
    
    #Path selection based on comparison function => TODO : Alternate selection mode
    def pathSelection(self, prefix, rcv=False):
        global backup_routing
        oldpath=None
        #Get all paths for considered prefix
        inpaths = [];
        #if DEBUG_ADDPATHS and self.id=="1.3" : 
        #    if not self.loc_rib.has_key(prefix) : 
        #        print "Num of paths in 1.3's locrib before DP : 0"
        #    else : 
        #        print "Num of paths in 1.3's locrib before DP : ", len(self.loc_rib[prefix])
        if prefix in self.origin_rib: 
            #Adding local path if exists
            #Caution : If local path exists, this is the only one taken into account - No multipath.
            #          This is logical, because we are at the origin of the path, there can't be alternate path.
            inpaths.append(self.origin_rib[prefix]);
        else:
            #Getting paths from peers adjribins.  There can be more than one path per peer (multipath)
            for peer in list(self.peers.values()):
                if prefix in peer.rib_in:
                    for path in  peer.rib_in[prefix]:
                        #IGP cost must be reachable, i.e. value is not None
                        if path.igp_cost is not None : 
                            inpaths.append(path);
            #Sort paths by preference
            inpaths.sort(key=cmp_to_key(self.comparePath));
            
        


#Updating locrib

        #Create locrib entry if it does not exist
        if prefix not in self.loc_rib:
            self.loc_rib[prefix] = [];
        #print "Decision process :", self.id
        #print "******************"
        #print "Old paths : "
        #for path in self.loc_rib[prefix] : 
        #    print path    
        #print "New paths : "
        #for path in inpaths : 
        #    print path
        change = False;
        trend = 0;
        #Multipath
        if len(self.loc_rib[prefix])>0 :
            oldpath=self.loc_rib[prefix][0] 
# Modif by vvandens on 10/03/09 : adding add path compatibility

        #if MAX_PATH_NUMBER != 1  :
        if self.bgp_num_paths!=1 :
            #pathnum = MAX_PATH_NUMBER;
            #if pathnum==0 : #AddAllPaths 
            #Modif 16/06 : Take all paths in decision process
            #Max number of paths to send is applied upon dissemination
            pathnum=len(inpaths)
            #Not enough paths available => lower path number
            #if pathnum > len(inpaths):
            #    pathnum = len(inpaths);
            i = 0;
#End of add-paths modification

            while i < pathnum or i < len(self.loc_rib[prefix]):#Why second condition? => in case there are less paths available
                                                                # in adjribins than installed in locrib => remove
                if i < pathnum and i < len(self.loc_rib[prefix]):
                    #print pathnum, len(self.loc_rib[prefix]), str(inpaths[i]), str(self.loc_rib[prefix][i]);
                    if inpaths[i].compareTo(self.loc_rib[prefix][i]) != 0:
                        self.loc_rib[prefix][i] = inpaths[i];
                        change = True;
                        trend = self.loc_rib[prefix][i].compareTo(inpaths[i]);
                    i = i + 1;
                #Less paths in adjribins than in locrib => remove 
                elif i >= pathnum and i < len(self.loc_rib[prefix]):
                    self.loc_rib[prefix].pop(i);
                    change = True;
                    trend = -1;
                #More paths available than previously
                elif i < pathnum and i >= len(self.loc_rib[prefix]):
                    self.loc_rib[prefix].append(inpaths[i]);
                    i = i + 1;
                    change = True;
                    trend = 1;
            #Note : Trend and change value for last path only!! 
        else: #One path per prefix
            if len(self.loc_rib[prefix]) == 0 and len(inpaths) > 0:
                #No previous best path => append first best path. 
                self.loc_rib[prefix].append(inpaths[0]);
                trend = 1;
                change = True;
                if SHOW_1PATH_RIB_UPDATE :
                    print("Router",self.id, "select path from peer", inpaths[0].src_pid, "with NH", inpaths[0].nexthop)
                    print(str(inpaths[0]))
            elif len(self.loc_rib[prefix]) > 0 and len(inpaths) == 0:
                #No more path in adjribins
                del self.loc_rib[prefix][0];
                trend = -1;
                change = True;
            #Best path changed
            elif len(self.loc_rib[prefix]) > 0 and len(inpaths) > 0 and self.loc_rib[prefix][0].compareTo(inpaths[0]) != 0:
                trend = self.loc_rib[prefix][0].compareTo(inpaths[0])
                del self.loc_rib[prefix][0];
                self.loc_rib[prefix].append(inpaths[0]);
                change = True;
                if SHOW_1PATH_RIB_UPDATE :
                    print("Router",self.id, "select path from peer", inpaths[0].src_pid, "with NH", inpaths[0].nexthop)
                    print(str(inpaths[0]))
            # print "Decision process for", self.id
            #             if(len(self.loc_rib[prefix])==0) : 
            #                 print "No best path"
            #             else :
            #                 print "New best path :", self.loc_rib[prefix][0]
            #             print "Len locrib :", len(self.loc_rib[prefix])
            
#####################
# <Best external>  #
#####################   
        if len(inpaths)>1 and self.bgp_mode==BGP_MODE_BEST_EXTERNAL : 
            bestpath=inpaths[0]
            #Best path is iBGP-learned
            if (bestpath.src_pid is not None) and self.getPeerLink(bestpath.src_pid).ibgp_ebgp() == IBGP_SESSION :
                #Search best ebgp-learned path
                for path in inpaths[1:] : 
                    if (path.src_pid is not None) and self.getPeerLink(path.src_pid).ibgp_ebgp() == EBGP_SESSION :
                        self.best_external_rib[prefix]=path
                        break
#####################
# </Best external>  #
#####################            
        
        
        
        #if DEBUG_ADDPATHS and self.id=="1.3" : 
        #    if not self.loc_rib.has_key(prefix) : 
        #        print "Num of paths in 1.3's locrib after DP : 0"
        #    else : 
        #        print "Num of paths in 1.3's locrib after DP : ", len(self.loc_rib[prefix])
        
        if SHOW_RIB_UPDATE : 
            if len(inpaths)==0 :
                print(getSystemTimeStr(), "RIB_UPDATE : Router", self, "prefix", prefix, ": NO_PATH")
                if rcv : #Msg was useful
                    print(getSystemTimeStr(), "USEFUL_MSG : Router", self, "prefix", prefix)
            else : 
                if oldpath is None or inpaths[0].compareTo(oldpath)!=0 : 
                    # if len(self.loc_rib[prefix])==0 : 
                    #                         print "No best path"
                    #                     else :
                    #                         print "Old best path : ", self.loc_rib[prefix][0]
                    print(getSystemTimeStr(), "RIB_UPDATE : Router", self, "prefix", prefix, ": NEW_PATH", end=' ') 
                    if checkForwarding(self.id, prefix) : 
                        print("VALID")
                    else : 
                        print("INVALID")
                    if rcv : #Print only upon msg reception
                        print(getSystemTimeStr(), "USEFUL_MSG : Router", self, "prefix", prefix)

        
        return [change, trend];

    #
    # Receive an  update : put paths in adjribin + schedule decision process
    #
    def receive(self, pid, update):
        global _event_Scheduler
        
        if self.bgp_mode!=BGP_MODE_NORMAL and self.bgp_mode!=BGP_MODE_BEST_EXTERNAL and self.getPeerLink(pid).ibgp_ebgp() == IBGP_SESSION :
            self.receive_AddPaths(pid, update)
            return
        #Link is down, update is invalid => discard
        if self.getPeerLink(pid).status == LINK_DOWN \
            or self.getPeerLink(pid).reach==PEER_UNREACH:
            print("Warning : link down or peer unreachable between ", \
                self.id, pid, file=sys.stderr)
            return;
        #print self.id, "received from peer", pid, ":", str(update)
        tmppaths = [];
        for path in update.paths:
            if path.type=="W" : 
                print("Error : AddPath path in Normal receive!", file=sys.stderr)
            #Run import filters on received paths, then create new path entry with filter action applied
            if self.importFilter(pid, update.prefix, path):
                mypath=self.importAction(pid, update.prefix, path)
                tmppaths.append(mypath);
                

        #Replace adjribin entry with new paths. 
        self.peers[pid].rib_in[update.prefix] = tmppaths;
        ### Added by Dimeji Fayomi 2020/02/10
        #if self.id == "0.0.0.2":
        #    print("Router %s has received an update\n" %self.id)
        #    pp(update)
        #self.update(update.prefix);
        #Schedule next event : rerun decision process for this prefix after processing delay
        _event_Scheduler.add(CEvent(self.getIdelTime(), [self.id, update.prefix], EVENT_UPDATE));



    #
    # Update routing tables to remove entries from down peer
    #
    def peerDown(self, pid):
        global EPIC, _router_list;
        prefixlist = list(self.peers[pid].rib_in.keys());
        self.peers[pid].clear();
        #Rerun decision process for each prefix whose nexthop is the failed peer
        for p in prefixlist:
            if p in self.loc_rib and len(self.loc_rib[p]) > 0 and self.loc_rib[p][0].src_pid is not None and self.loc_rib[p][0].src_pid == pid:
                self.update(p);

    #
    # 
    #
    def peerUp(self, pid):
        #print "peerUp", str(self), pid;
        #Set up MRAI and send routing table to new peer
        if self.mrai_setting == MRAI_PEER_BASED:
            for p in list(self.loc_rib.keys()):
                self.peers[pid].enqueue(p);
            next_mrai = self.mraiExpires(pid, None);
            if next_mrai < 0:
                self.sendto(pid, None);
        else:
            for p in list(self.loc_rib.keys()):
                self.peer[pid].enqueue(p);
                next_mrai = self.mraiExpires(pid, p);
                if next_mrai < 0:
                    self.sendto(pid, p);

    #
    #
    # 
    def update(self, prefix, rcv=False):
        global SHOW_UPDATE_RIBS, CHECK_LOOP, SHOW_DEBUG, _systime, WITHDRAW_DELAY
        oldpath=None
        if self.delay_withdraws :
            if prefix in list(self.loc_rib.keys()) and len(self.loc_rib[prefix])>0 :
                oldpath=self.loc_rib[prefix][0]
        [change, trend] = self.pathSelection(prefix, rcv);
        #Best path(s) changed : Send new best path(s) to peers
        if change:
            for pid in list(self.peers.keys()):
                if self.bgp_mode!=BGP_MODE_NORMAL and self.bgp_mode!=BGP_MODE_BEST_EXTERNAL and self.getPeerLink(pid).ibgp_ebgp() == IBGP_SESSION :
                    self.presend2peer_AddPaths(pid, prefix);
                else :  
                    #Delayed withdraws : Setup structure
                    if self.delay_withdraws : 
                        #Check if this is a withdraw and community exists
                        if oldpath is not None and len(self.loc_rib[prefix])==0 and oldpath.has_diversity() :
                            self.peers[pid].DelayedWithdraws=CDelayedWithdraw()
                            self.peers[pid].DelayedWithdraws.expiration_time=_systime+WITHDRAW_DELAY
                            #TODO : Add event starting timer
                        #This is an update after a delayed withdraw
                        elif prefix in self.peers[pid].DelayedWithdraws \
                            and self.peers[pid].DelayedWithdraws[prefix] is not None \
                            and not self.peers[pid].DelayedWithdraws[prefix].sent :
                            self.peers[pid].DelayedWithdraws[prefix].sent=True
                            
                        
                    self.presend2peer(pid, prefix);
            #if SHOW_UPDATE_RIBS:
            #    self.showRib(prefix);
            
        
    
    #
    # Print rib content on stdout for the given prefix
    #
#@vvandens - Rewrited on 2/2/09
    def showRib(self, prefix):
        #tmpstr = getSystemTimeStr() + " RIB: " + str(self) + " * " + prefix + "\n";
       # tmpstr = tmpstr + "\t{";
       # if self.loc_rib.has_key(prefix):
       #     for p in self.loc_rib[prefix]:
       #         tmpstr = tmpstr + " *>" + str(p)+ " ";
       # tmpstr = tmpstr + "}\n ";
        has_best_path=False
        #Check all adjribins
        for p in list(self.peers.values()):
            for path in p.getPaths(prefix) :
                #Best path is the first path of the locrib
                if not has_best_path and \
                    path.compareTo(self.loc_rib[prefix][0])==0 : 
                    print("["+str(p)+"] "+"*> " + prefix+ " "+ str(path)) 
                    has_best_path=True
                #Non best path
                else :
                    print("["+str(p)+"] "+"*  "+ prefix + " "+str(path)) 
        #The best path was not in the ribins
        if not has_best_path : 
            #There should be only one path in locrib
            for path in self.loc_rib[prefix] :  
                print("[Local] "+"*> "+ prefix + " "+str(path))
         #   tmpstr = tmpstr + "\t"+p.getRibInStr(prefix)+"\n";
        #print tmpstr;
#@vvandens - End of modification

    #
    # Print rib content for all prefixes
    #
    def showAllRib(self):
        for p in list(self.loc_rib.keys()):
            self.showRib(p);


###############################################################################
#                        ADD-PATHS DISSEMINATION PROCESS                      #
###############################################################################
    
        #
    # Receive an  update : put paths in adjribin + schedule decision process
    #
    def receive_AddPaths(self, pid, update):
        global _event_Scheduler
        #Link is down, update is invalid => discard
        if self.getPeerLink(pid).status == LINK_DOWN \
            or self.getPeerLink(pid).reach==PEER_UNREACH:
            print("Warning : link down or peer unreachable between ", \
                self.id, pid, file=sys.stderr)
            return
        
        tmppaths = [];
        for path in update.paths:     
            #Remove path with this index from ribin
            index=path.index
            if update.prefix in list(self.peers[pid].rib_in.keys()) : 
                for oldpath in self.peers[pid].rib_in[update.prefix] : 
                    if oldpath.index==index : 
                        self.peers[pid].rib_in[update.prefix].remove(oldpath)
            else : 
                self.peers[pid].rib_in[update.prefix]=[]
            #Run import filters on received paths, then create new path entry with filter action applied
            if path.type!='W' and  self.importFilter(pid, update.prefix, path):
                self.peers[pid].rib_in[update.prefix].append(self.importAction(pid, update.prefix, path))
        #Schedule next event : rerun decision process for this prefix after processing delay
        _event_Scheduler.add(CEvent(self.getIdelTime(), [self.id, update.prefix], EVENT_UPDATE));
    
    
    #
    # Check if msg to send to peer pid is a withdraw, i.e. : 
    #     - No best path
    #     - or path filtered by route map
    #
    def isUrgentWithdrawal_AddPaths(self, pid, prefix):
        
        #No path available at all
        if len(self.loc_rib[prefix]) == 0:
            return True;
        #If eBGP session : Check best path only
        if self.getPeerLink(pid).ibgp_ebgp() == EBGP_SESSION : 
            return self.exportFilter(pid, prefix, self.loc_rib[prefix][0])
        #Check export filters
        for path in self.loc_rib[prefix] : 
            if self.exportFilter(pid, prefix, path) : 
                return False
        #No path passes export filters
        return True

    #
    # Compute paths to add to peer out_queue and check MRAIs 
    #
    def presend2peer_AddPaths(self, pid, prefix):
        global wrate, MRAI_PEER_BASED, LINK_DOWN, EVENT_MRAI_EXPIRE_SENDTO,\
         SHOW_DEBUG, _systime, _event_Scheduler
        if self.getPeerLink(pid).status == LINK_DOWN or self.getPeerLink(pid).reach==PEER_UNREACH :
            return;
        
        is_withdraw=self.isUrgentWithdrawal_AddPaths(pid, prefix)
        
        #Schedule paths sending 
        self.peers[pid].enqueue(prefix)
        
        #Compute sending time
        next_mrai = self.mraiExpires(pid, prefix);
        if next_mrai < 0 and always_mrai: # Need to reschedule msg sending
            tprefix=prefix
            if self.mrai_setting == MRAI_PEER_BASED:
                tprefix = None;
            next_mrai = self.setMRAIvalue(pid, tprefix, self.peers[pid].random_mrai_wait());
            if next_mrai > 0:
                _event_Scheduler.add(CEvent(next_mrai, [self.id, pid, tprefix], EVENT_MRAI_EXPIRE_SENDTO));
        
        #If MRAI expired : Send immediately
        if next_mrai < 0 or (not wrate and is_withdraw): 
            #print "MRAI expires, send immediately ...", pid;
            self.sendto(pid, prefix);
        else: #do nothing, the scheduler will call sendto automatically when mrai timer expires
            if SHOW_DEBUG:
                print(getSystemTimeStr(), self, pid, prefix, "MRAI does not expire, wait...", formatTime(next_mrai - _systime));
   

    #
    # MRAI expired => send update messages to peer pid
    #
    def sendto_AddPaths(self, pid, prefix): # from out_queue
        global _event_Scheduler, SHOW_SEND_EVENTS
        if self.getPeerLink(pid).ibgp_ebgp() == EBGP_SESSION :
            print("Error : AddPaths on eBGP session!", file=sys.stderr)
            sys.exit(-1)
        sendsth = False;
        peer = self.peers[pid];
        sendWithdraw = True;
        if len(peer.out_queue) > 0:
            i = 0;
            #Traverse out_queue
            while i < len(peer.out_queue):
                if prefix is None: #No prefix specified, MRAI peer based => send msg
                    if self.sendtopeer_AddPaths(pid, peer.out_queue[i]):
                            sendsth = True;
                    if not self.isUrgentWithdrawal_AddPaths(pid, peer.out_queue[i]):
                        sendWithdraw = False;
                    peer.out_queue.pop(i);
                elif prefix == peer.out_queue[i]: #Prefix in outqueue correspond => send msg
                    if self.sendtopeer_AddPaths(pid, peer.out_queue[i]):
                        sendsth = True;
                    if not self.isUrgentWithdrawal_AddPaths(pid, peer.out_queue[i]):
                        sendWithdraw = False;
                    peer.out_queue.pop(i);
                    break;
                else: #Skip, prefix is not the one that was specified
                    i = i + 1;
        if sendsth: #Reset MRAI if something was send
            if SHOW_SEND_EVENTS:
                print(getSystemTimeStr(), self, "sendto", pid, prefix, update);
            #If only withdraw and not wrate : withdraw sending independant of mrai, don't reset it. 
            if (not wrate) and sendWithdraw :
                return;
            #Reset MRAI for this peer or this prefix, depending on config.  
            if self.mrai_setting == MRAI_PEER_BASED:
                prefix = None;
            #self.resetMRAI(pid, prefix);
            next_mrai = self.setMRAI(pid, prefix);
            if next_mrai > 0: 
                _event_Scheduler.add(CEvent(next_mrai, [self.id, pid, prefix], EVENT_MRAI_EXPIRE_SENDTO));
                #print "Add EVENT_MRAI_EXPIRE_SENDTO ", str(self), pid, prefix, next_mrai;
      

   #
    # Build update to send to peer pid for this prefix
    #
    def sendtopeer_AddPaths(self, pid, prefix):
        
        # compare update and rib_out
        return self.delivery_AddPaths(pid, prefix, self.compute_paths_for_peer(pid, prefix));


    #
    # Delivery of an update to a peer if there is a change compared to the ribout
    #
    def delivery_AddPaths(self, pid, prefix, paths):
        global _event_Scheduler;
        
        
        newpaths=self.delta_from_ribout(pid, prefix, paths)   
        #Check if there was a path before
        had_paths= prefix in list(self.peers[pid].rib_out.keys()) \
                        and len(self.peers[pid].rib_out[prefix])>0
        # Update ribout
        try : 
            for path in newpaths :
                index=path.index 
                #Remove previous paths with this index : 
                if prefix in list(self.peers[pid].rib_out.keys()) :
                    for oldpath in self.peers[pid].rib_out[prefix] :
                        if oldpath.index==index : 
                            self.peers[pid].rib_out[prefix].remove(oldpath)
                else : 
                    self.peers[pid].rib_out[prefix]=[] 
                if path.type!='W' : 
                    self.peers[pid].rib_out[prefix].append(path)

        except TypeError : 
            print("Bad newpaths : ", newpaths, file=sys.stderr)
            raise
        update=CUpdate(prefix)
        #Mark update as withdraw if ribout is now empty (i.e. we don't want to be used as nexthop for this prefix anymore)
        if had_paths and len(self.peers[pid].rib_out[prefix])==0 : 
            update.is_withdraw=True 
        update.paths=newpaths
        if len(newpaths)>0 :
            _event_Scheduler.add(CEvent(self.getPeerLink(pid).next_delivery_time(self.id, update.size()), [self.id, pid, update], EVENT_RECEIVE));
            return True
        return False;


    #
    # Find path to send to peer based on ribout state
    # paths are the paths to be send from the locrib
    #
    def delta_from_ribout(self, pid, prefix, paths):
        paths_to_send=[]
        newPaths=[]
        oldPaths=[]
#        if DEBUG_ADDPATHS and self.id=="1.3" and pid=="1.4": 
#            print "Paths to send : "
#            for path in paths : 
#                print "\t",path
#            if prefix not in self.peers[pid].rib_out.keys() : 
#                print "Ribout empty"
#            else : 
#                print "Ribout : "
#                for path in self.peers[pid].rib_out[prefix] :
#                    print "\t",path
        #Prefix not yet in ribout : paths to send = all paths, specify index.
        if prefix not in list(self.peers[pid].rib_out.keys()) :   
            i=0
            for path in paths : 
                path.index=i
                paths_to_send.append(path)
                i+=1
            return paths_to_send
        #Compute new paths, i.e. paths that are not yet in ribout
        for path in paths : 
            exist=False
            for entry in self.peers[pid].rib_out[prefix] : 
                if entry is None : 
                    continue
                if path.compareTo(entry)==0 :
                    exist=True
                    break
            if not exist : 
                newPaths.append(path)
        #print "New paths : ", str(newPaths)
        #Compute old paths, i.e. paths that are to be removed from ribout
        for entry in self.peers[pid].rib_out[prefix] :
            if entry is None : 
                continue
            exist=False
            for path in paths : 
                if path.compareTo(entry) ==0 :
                    exist=True
                    break
            if not exist : 
                oldPaths.append(entry)
        
        
        for oldpath in oldPaths : 
            #Replace old path by new path
            if len(newPaths)>0 : 
                newPaths[0].index=oldpath.index
                paths_to_send.append(newPaths[0])
                newPaths=newPaths[1:]
            else : #No new path to replace => withdraw for this index
                withdraw=CPath()
                withdraw.type="W"
                withdraw.index=oldpath.index
                paths_to_send.append(withdraw)
        #More new paths than paths to remove -> find unused index
        holes=[]
        indices = []
        for path in self.peers[pid].rib_out[prefix] : 
            indices.append(path.index)
        for index in range(len(self.peers[pid].rib_out[prefix])) : 
            if index not in indices : 
                holes.append(index)
        #Assign new index to new paths  
        new_index= len(self.peers[pid].rib_out[prefix])
        for newPath in newPaths :
            if len(holes)>0 :
                newPath.index=holes[0]
                holes=holes[1:]
            else : #No holes => increment higher index
                newPath.index=new_index
                new_index+=1
            paths_to_send.append(newPath)
        
        #if DEBUG_ADDPATHS and self.id=="1.3" : 
        #    print "Num of paths in locrib of router 1.3 : ", len(self.loc_rib[prefix])
        #    print "Paths from router", self.id, "to router", pid, ":", len(paths_to_send)
        #    for path in paths_to_send : 
        #        print path
        return paths_to_send
    #
    # Build update to send to peer pid for this prefix
    # Add All Paths function 
    #
    def compute_paths_for_peer(self, pid, prefix):
        paths_to_send=[]
        if prefix not in list(self.loc_rib.keys()) or len(self.loc_rib[prefix])==0 :
            return paths_to_send
        #eBGP session : Send only best path if it passes filters
        if self.getPeerLink(pid).ibgp_ebgp() == EBGP_SESSION :
            if self.exportFilter(pid, prefix, self.loc_rib[prefix][0]):
                paths_to_send.append(self.exportAction(pid, prefix, self.loc_rib[prefix][0]))
            return paths_to_send
        
    ##################################        
        #BEST PATHS  
        elif self.bgp_mode==BGP_MODE_ADD_BEST_PATHS :
            candidates=[]
            for path in self.loc_rib[prefix] :
                #identical path already in candidates?
                if path not in candidates :
                    candidates.append(path)
            best_path=candidates[0]
            for path in candidates : 
                if self.exportFilter(pid, prefix, path):
                    #Compare with best path
                    if path.compareTo_AS_pref(best_path)==0 : 
                        npath = self.exportAction(pid, prefix, path)
                        if npath not in paths_to_send : 
                            paths_to_send.append(npath)
            return paths_to_send
                            
                    
                
    ##################################                
        #AddNPaths
        elif self.bgp_mode==BGP_MODE_ADD_N_PATHS :
            candidates=[]
            for path in self.loc_rib[prefix] :
                #identical path already in candidates?
                if path not in candidates :
                    candidates.append(path)
            
            for path in candidates : 
                if len(paths_to_send)< self.bgp_num_paths : 
                    if self.exportFilter(pid, prefix, path):
                        npath = self.exportAction(pid, prefix, path);
                        if npath not in paths_to_send :
                            paths_to_send.append(npath)
                            
    ##################################        
        #AddNBests
        elif self.bgp_mode== BGP_MODE_ADD_N_BESTS: 
            #Tricky : Need to remove duplicates before applying filters
            #=> definition of add2Best is add 2 best different paths
            candidates=[]
            #Compute N best different paths : 
            for path in self.loc_rib[prefix] :
                if len(candidates)==self.bgp_num_paths : 
                    break
                #identical path already in candidates?
                #Rem : To test loop : Remove if condition
                if path not in candidates :
                    candidates.append(path)
            for path in candidates :
                if self.exportFilter(pid, prefix, path):
                    npath = self.exportAction(pid, prefix, path);
                    if npath not in paths_to_send :
                        paths_to_send.append(npath)
                        
        #Is this needed?
        elif self.bgp_mode==BGP_MODE_NORMAL : #Plain BGP : Only send best path if ok from filters
            if self.exportFilter(pid, prefix, self.loc_rib[prefix][0]):
                paths_to_send.append(self.exportAction(pid, prefix, self.loc_rib[prefix][0]))

    ##################################        
        #BestBin+SecondBin
        elif self.bgp_mode==BGP_MODE_BEST_BIN :
            num_paths=0
            candidates=[]
            for path in self.loc_rib[prefix] :
                #identical path already in candidates?
                if path not in candidates :
                    candidates.append(path)
            best_locpref=candidates[0].local_pref
            second_locpref=0
            for path in candidates : 
                if best_locpref==path.local_pref :
                    num_paths+=1
                    if self.exportFilter(pid, prefix, path):
                        npath = self.exportAction(pid, prefix, path);
                        if npath not in paths_to_send :
                            paths_to_send.append(npath)
                else : 
                    #Only one path with best local preference
                    if num_paths==1 : 
                        #This statement is executed only once
                        second_locpref=path.local_pref
                    num_paths+=1
                    if path.local_pref==second_locpref :
                        if self.exportFilter(pid, prefix, path):
                            npath = self.exportAction(pid, prefix, path);
                            if npath not in paths_to_send :
                                paths_to_send.append(npath)
                        
                    
    ##################################        
        #Group best : For each neighboring AS, take best path. 
        elif self.bgp_mode==BGP_MODE_GROUP_BEST :   
            candidates=[]
            for path in self.loc_rib[prefix] :
                #identical path already in candidates?
                if path not in candidates :
                    candidates.append(path)       
            #First, partition locrib by AS
            neighbors={}
            for path in candidates :
                first_as=path.aspath[0]
                if first_as not in list(neighbors.keys()) : 
                    neighbors[first_as]=[]
                neighbors[first_as].append(path)
            #Second, add first path of each neighbor to path to send
            for neigh in list(neighbors.keys()) : 
                path=neighbors[neigh][0]
                if self.exportFilter(pid, prefix, path):
                    npath = self.exportAction(pid, prefix, path);
                    if npath not in paths_to_send :
                        paths_to_send.append(npath)
        
        
    ##################################        
        #Rexfort : Send a path for each AS using MED
        #TODO : Rexford Group-Best
    
    
    ##################################        
    #Decisive-Step -1 : Send all path remaining before the step that let only one path
        elif self.bgp_mode==BGP_MODE_DECISIVE_STEP : 
            candidates=[]
            for path in self.loc_rib[prefix] :
                #identical path already in candidates?
                if path not in candidates :
                    candidates.append(path)
            #Local pref
            best_locpref=candidates[0].local_pref
            #If second path has different loc_pref : send all paths. 
            #Else :
            if len(candidates)>1 and candidates[1].local_pref == best_locpref : 
                #Decisive step is not local pref
                i=0
                for p in candidates : 
                    if p.local_pref!=best_locpref : 
                        candidates=candidates[:i]
                        break
                    else : i=i+1
                #Check if aspath is decisive step
                if len(candidates)>1 and len(candidates[0].aspath)==len(candidates[1].aspath) : 
                    best_len=len(candidates[0].aspath)
                   #Decisive step is not aspath len
                    #Remove paths with longuer ASPaths
                    i=0
                    for p in candidates : 
                        #Check AS Paths length
                        if len(p.aspath)!=best_len : 
                            candidates=candidates[:i]
                            break
                        else : i=i+1
                    #Check if MED is decisive step
                    if len(candidates)>1 and candidates[0].med==candidates[1].med : 
                        #Decisive step is not aspath med
                        #Remove paths with not better med
                        i=0
                        best_med=candidates[0].med
                        for p in candidates : 
                            if p.med!=best_med : 
                                candidates=candidates[:i]
                                break
                            else : i=i+1
            for path in candidates : 
                if self.exportFilter(pid, prefix, path):
                    npath = self.exportAction(pid, prefix, path);
                    if npath not in paths_to_send : 
                        paths_to_send.append(npath)
                        
    ##################################        
        #AddAllPaths
        else : #All paths 
            candidates=[]
            for path in self.loc_rib[prefix] :
                #identical path already in candidates?
                if path not in candidates :
                    candidates.append(path)
            for path in candidates : 
                if self.exportFilter(pid, prefix, path):
                    npath = self.exportAction(pid, prefix, path);
                    paths_to_send.append(npath)

    ##################################        
     
        return paths_to_send
    
    
   
###############################################################################
#                    END OF ADD-PATHS DISSEMINATION PROCESS                   #
###############################################################################

    #
    # Add to peer out_queue and check MRAIr
    #
    def presend2peer(self, pid, prefix):
        global wrate, MRAI_PEER_BASED, LINK_DOWN, EVENT_MRAI_EXPIRE_SENDTO, SHOW_DEBUG, _systime;
        if self.getPeerLink(pid).status == LINK_DOWN or self.getPeerLink(pid).reach==PEER_UNREACH :
            return;
        #add to peer waiting queue
        if SHOW_DEBUG : 
            print(self.id, "send ", prefix, "to", pid)
        self.peers[pid].enqueue(prefix);
        #print self, "enqueue", pid, prefix;
        #Compute sending time
        next_mrai = self.mraiExpires(pid, prefix);
        tprefix=prefix
        if next_mrai < 0 and always_mrai: # Need to reschedule msg sending
            if self.mrai_setting == MRAI_PEER_BASED:
                tprefix = None;   
            next_mrai = self.setMRAIvalue(pid, tprefix, self.peers[pid].random_mrai_wait());
            if next_mrai > 0:
                _event_Scheduler.add(CEvent(next_mrai, [self.id, pid, tprefix], EVENT_MRAI_EXPIRE_SENDTO));
        #Prefix subject to withdraw delay
        if self.delay_withdraws and prefix in list(self.peers[pid].DelayedWithdraws.keys()) and self.peers[pid].DelayedWithdraws is not None :
            self.peers[pid].DelayedWithdraws[prefix].MRAI_time=next_mrai
        #If withdraw or if MRAI expired : Send immediately
        if next_mrai < 0 or ((not wrate) and self.isWithdrawal(pid, prefix)):
            #print "MRAI expires, send imediately ...", pid;
            self.sendto(pid, prefix);
        else: #do nothing, the scheduler will call sendto automatically when mrai timer expires
            if SHOW_DEBUG:
                print(getSystemTimeStr(), self, pid, prefix, "MRAI does not expire, wait...", formatTime(next_mrai - _systime));

    #
    # Add locally originated prefix, and rerun decision process
    #
    def announce_prefix(self, prefix):
        global default_local_preference;
        npath = CPath();
        npath.nexthop = self.id;
        npath.ibgp_ebgp=LOCAL
        npath.local_pref = default_local_preference;
        self.origin_rib[prefix] = npath;
        self.update(prefix);

    #
    # Remove prefix from origin rib and rerun decision process
    #
    def withdraw_prefix(self, prefix):
        if prefix in self.origin_rib:
            del self.origin_rib[prefix];
            self.update(prefix);

    #
    # MRAI expired => send update messages to peer pid
    #
    def sendto(self, pid, prefix): # from out_queue
        global _event_Scheduler, SHOW_SEND_EVENTS
        #print self, "sendto", pid, prefix;
        #Use AddPaths only on iBGP sessions
        if self.getPeerLink(pid).ibgp_ebgp() == IBGP_SESSION :
            if self.bgp_mode!=BGP_MODE_NORMAL and self.bgp_mode!=BGP_MODE_BEST_EXTERNAL : 
                self.sendto_AddPaths(pid, prefix)
                return
        #If eBGP session : Use normal delivery function
        
        sendsth = False;
        peer = self.peers[pid];
        sendWithdraw = True;
        if len(peer.out_queue) > 0:
            i = 0;
            #Traverse out_queue
            while i < len(peer.out_queue):
                if prefix is None: #No prefix specified, MRAI peer based => send msg
                    if self.bgp_mode==BGP_MODE_BEST_EXTERNAL : 
                        if self.sendtopeer_bestexternal(pid, peer.out_queue[i]):
                            sendsth = True;
                    else : 
                        if self.sendtopeer(pid, peer.out_queue[i]):
                            sendsth = True;
                    if not self.isWithdrawal(pid, peer.out_queue[i]):
                        sendWithdraw = False;
                    peer.out_queue.pop(i);
                elif prefix == peer.out_queue[i]: #Prefix in outqueue correspond => send msg
                    if self.bgp_mode==BGP_MODE_BEST_EXTERNAL : 
                        if self.sendtopeer_bestexternal(pid, peer.out_queue[i]):
                            sendsth = True;
                    else : 
                        if self.sendtopeer(pid, peer.out_queue[i]):
                            sendsth = True;
                    if not self.isWithdrawal(pid, peer.out_queue[i]):
                        sendWithdraw = False;
                    peer.out_queue.pop(i);
                    break;
                else: #Skip, prefix is not the one that was specified
                    i = i + 1;
        if sendsth: #Reset MRAI
            if SHOW_SEND_EVENTS:
                print(getSystemTimeStr(), "EVENT_SENDTO", self, "send",prefix, "to", pid)
            if (not wrate) and sendWithdraw :
                return;
            #Reset MRAI for this peer or this prefix, depending on config
            if self.mrai_setting == MRAI_PEER_BASED:
                prefix = None;
            #self.resetMRAI(pid, prefix);
            next_mrai = self.setMRAI(pid, prefix);
            if next_mrai > 0: 
                _event_Scheduler.add(CEvent(next_mrai, [self.id, pid, prefix], EVENT_MRAI_EXPIRE_SENDTO));
                #print "Add EVENT_MRAI_EXPIRE_SENDTO ", str(self), pid, prefix, next_mrai;
        #else:
        #    self.resetMRAI(pid, prefix);
        #    print str(self) + " send nothing to " + pid;

    #
    # Check if msg to send to peer pid is a withdraw, i.e. : 
    #     - No best path
    #     - or path filtered by route map
    #
    def isWithdrawal(self, pid, prefix):
        if len(self.loc_rib[prefix]) == 0:
            return True;
        i = 0;
        path = self.loc_rib[prefix][0];
        if not self.exportFilter(pid, prefix, path):
            return True;
        return False;


    #
    # Delivery of an update to a peer if there is a change compared to the ribout
    # BGP Normal or eBGP only
    #
    def delivery(self, pid, prefix, update):
        global _event_Scheduler;
        change = False;
        #Ribout not empty => See if path changed
        if prefix in self.peers[pid].rib_out and len(self.peers[pid].rib_out[prefix])!=0 : 
            #Remove this condition because there is an issue when going from iBGP to eBGP with ADDPATHS
            #and len(update.paths) == len(self.peers[pid].rib_out[prefix]):
            
            # if MAX_PATH_NUMBER != 1:
            #                 i = 0;
            #                 while i < len(update.paths):
            #                     if update.paths[i].compareTo(self.peers[pid].rib_out[prefix][i]) != 0:
            #                         change = True;
            #                         break;
            #                     i = i + 1;
            #elif len(update.paths) > 0:
            if len(update.paths) > 0:
                if update.paths[0].compareTo(self.peers[pid].rib_out[prefix][0]) != 0:
                    change = True;
            else : #Update is a withdraw
                change=True
        #Ribout is empty and all paths have been filtered : Do not send empty update
        elif (prefix not in self.peers[pid].rib_out 
            or len(self.peers[pid].rib_out[prefix])==0) \
                    and len(update.paths) ==0 :
            change=False
        else: #Ribout empty and one path to send
            change = True;
        if change:
            self.peers[pid].rib_out[prefix] = update.paths;
            _event_Scheduler.add(CEvent(self.getPeerLink(pid).next_delivery_time(self.id, update.size()), [self.id, pid, update], EVENT_RECEIVE));
            ### Added by Dimeji fayomi 2020/02/10 
            #if self.id == "0.0.0.3" and pid == "0.0.0.2":
            #    print("Router %s is sending update to %s\n" %(self.id, pid))
            #    pp(update)
            #    print("\n\n\n")
        return change;



 

                

    #
    # Build update to send to peer pid for this prefix
    # Normal BGP only
    def sendtopeer(self, pid, prefix):
        global _event_Scheduler, _systime
        #Handling of delayed withdraws with timer not expired
        if len(self.loc_rib[prefix])==0 and self.delay_withdraws :
            if prefix in self.peers[pid].DelayedWithdraws and \
                self.peers[pid].DelayedWithdraws[prefix].expiration_time > _systime :
                pass
                #TODO : Finish this
        
        update = CUpdate(prefix);
        i = 0;
        if len(self.loc_rib[prefix])>0 :
        #while i < len(self.loc_rib[prefix]):
            path = self.loc_rib[prefix][0];
            if self.exportFilter(pid, prefix, path):
                npath = self.exportAction(pid, prefix, path);
                npath.index = 0;
                update.paths.append(npath);
            
        # compare update and rib_out
        return self.delivery(pid, prefix, update);

   
    
    #
    # Build update to send to peer pid for this prefix
    #        
    def sendtopeer_bestexternal(self, pid, prefix) :
        #There is an entry in the BE rib iff the best path is iBGP learned
        if prefix in self.best_external_rib \
                and self.getPeerLink(pid).ibgp_ebgp() == IBGP_SESSION:
            path=self.best_external_rib[prefix]
            if self.exportFilter(pid, prefix, path):
                npath = self.exportAction(pid, prefix, path);
                npath.index = 0;
                update = CUpdate(prefix);
                update.paths.append(npath);
            return self.delivery(pid, prefix, update);
        #No best external or best path is eBGP-learned
        else : 
            self.sendtopeer(pid, prefix)
    
    
    #
    # Compute processing delay based on configured delay fonction
    #
    def processDelay(self):
        return toSystemTime(interpretDelayfunc(self, self.rand_seed, default_process_delay_func));

    #
    # Compute next processing time
    #
    def getIdelTime(self):
        global _systime
        if self.next_idle_time < _systime:
            self.next_idle_time = _systime;
        self.next_idle_time = self.next_idle_time + self.processDelay();
        return self.next_idle_time;

############################################################################################################################
#                                     Class CUpdate - Represents a BGP update
############################################################################################################################

class CUpdate:
    # prefix = None; # prefix
    # paths = None; # array of CPath
    # fesn = None; # forword edge sequence numbers
    # is_withdraw=False
    #
    # Constructor - init variables
    #
    def __init__(self, prefix):
        self.prefix = prefix;
        self.paths = [];
        self.is_withdraw=False
        
    #
    # Return string representation of an update
    #
    def __str__(self):
        global EPIC;
        tmpstr=""
        if self.is_withdraw or len(self.paths)==0: 
            tmpstr="W:"
        tmpstr = tmpstr+self.prefix + "("+str(len(self.paths))+")";
        #for p in self.paths : 
        #     tmpstr= str(p)+ " | "
        
        # if len(self.paths) > 0:
        #     for p in self.paths:            
        #         tmpstr = tmpstr + str(p)    ;
        # else:                              
        #     tmpstr = tmpstr + "W";         
        #tmpstr = tmpstr + ")";
        
        
        return tmpstr
        
    #
    # Return the size of the update
    #
    def size(self):
        sz = 4;
        for p in self.paths:
            sz = sz + p.size();
        return sz;

############################################################################################################################
#                                     Class CPath - Represents a BGP path
############################################################################################################################

class CPath:
    # index = None; # for single path routing, index=0; multipath routing, index=0,1,2,...
    # src_pid = None;
    # #im=None;
    # #type = None;
    # weight = None;
    # local_pref = None;
    # med = None;
    # nexthop = None;
    # community = None;
    # alternative = None;
    # igp_cost = None;
    # aspath = None;
    # fesnpath = None;
    # ibgp_ebgp=None
    # clusterIDList=None
    # originatorID=None
    # #AddPaths Withdraw
    # type=None;

    #
    # Constructor
    #
    def __init__(self):
        global default_local_preference, default_weight, ALTERNATIVE_NONE;
        self.index = 0;
        self.src_pid = None;
        #self.type = ANNOUNCEMENT;
        self.weight = default_weight;
        self.local_pref = default_local_preference;
        self.med = 0;
        self.nexthop = "";
        self.community = [];
        self.aspath = [];
        self.type="U"
        self.clusterIDList=[]
        self.originatorID=None
        self.igp_cost=None
        self.ibgp_ebgp=None

    #
    # Returns the size of the path in bytes
    #
    def size(self):
        if self.type=="W" : 
            #Only index
            return 4
        return 4 + 4 + 4 + 4 + 4*len(self.community) + 2*len(self.aspath);

    #
    # Run decision process between two paths
    # 
    #TODO : Test this! 
    def compareTo_DP(self, path2): # the lower is the superior
        global bgp_always_compare_med;
        #If index is set : paths are classified and the first is the best
        #TODO: Check why this is done! 
        #if self.index != path2.index:
        #    return sgn(self.index - path2.index);
        #if self.type != path2.type:
        #    return sgn(self.type - path2.type);
        if self.weight != path2.weight:
            return sgn(path2.weight - self.weight);
        if self.local_pref != path2.local_pref:
            return sgn(path2.local_pref - self.local_pref);
        if len(self.aspath) != len(path2.aspath):
            return sgn(len(self.aspath) - len(path2.aspath));
        if len(self.aspath) > 0 and len(path2.aspath) > 0 and (((not bgp_always_compare_med) and self.aspath[0] == path2.aspath[0]) or bgp_always_compare_med) and self.med != path2.med:
            return sgn(self.med - path2.med);
        if self.ibgp_ebgp!=path2.ibgp_ebgp : 
            if self.ibgp_ebgp is None : 
                print("this path has no BGP origin : ", str(self))
                print("Other path is : ", str(path2))
            if path2.ibgp_ebgp is None : 
                print("Other path has no BGP origin ", str(path2))
                print("This path is : ", str(self))
            return sgn(path2.ibgp_ebgp - self.ibgp_ebgp)
        if self.igp_cost is None and path2.igp_cost is not None  :
            return 1
        if path2.igp_cost is None and self.igp_cost is not None : 
            return -1
        if self.igp_cost != path2.igp_cost:
            return sgn(self.igp_cost - path2.igp_cost)
        id1=self.src_pid
        id2=path2.src_pid
        if self.originatorID is not None : 
            id1=self.originatorID
        if path2.originatorID is not None : 
            id2=path2.originatorID
        if id1 > id2 :
            return 1;
        elif id1 < id2 : 
            return -1;
        #print "Using ClusterIDList len for DP", len(self.clusterIDList), len(path2.clusterIDList), sgn(len(self.clusterIDList)-len(path2.clusterIDList))
        return sgn(len(self.clusterIDList)-len(path2.clusterIDList))

 

    #
    # Compare two paths for strict equivalence
    # Difference with compareTo_DP : ASPaths are compared ASN per ASN, instead of
    # being compared based on their length
    #
    def compareTo(self, path2): # the lower is the superior
        global bgp_always_compare_med;
        if self.weight != path2.weight:
            return sgn(path2.weight - self.weight);
        if self.local_pref != path2.local_pref:
            return sgn(path2.local_pref - self.local_pref);
        if len(self.aspath) != len(path2.aspath):
            return sgn(len(self.aspath) - len(path2.aspath));
        if self.aspath < path2.aspath : 
            return -1
        if self.aspath>path2.aspath : 
            return 1
        if len(self.aspath) > 0 and len(path2.aspath) > 0 and (((not bgp_always_compare_med) and self.aspath[0] == path2.aspath[0]) or bgp_always_compare_med) and self.med != path2.med:
            return sgn(self.med - path2.med);
        if self.ibgp_ebgp!=path2.ibgp_ebgp : 
            if self.ibgp_ebgp is None : 
                print("this path has no BGP origin : ", str(self))
                print("Other path is : ", str(path2))
            if path2.ibgp_ebgp is None : 
                print("Other path has no BGP origin ", str(path2))
                print("This path is : ", str(self))
            return sgn(path2.ibgp_ebgp - self.ibgp_ebgp)
        if self.igp_cost is None and path2.igp_cost is not None  :
            return 1
        if path2.igp_cost is None and self.igp_cost is not None : 
            return -1
        if self.igp_cost != path2.igp_cost:
            return sgn(self.igp_cost - path2.igp_cost)
        id1=self.src_pid
        id2=path2.src_pid
        if self.originatorID is not None : 
            id1=self.originatorID
        if path2.originatorID is not None : 
            id2=path2.originatorID
        ### Added by Dimeji Fayomi 2020/02/10
        ### Python 3 does not allow comparing NoneType objects
        try:
            if id1 > id2 :
                return 1;
            elif id1 < id2 : 
                return -1;
        except TypeError:
            pass
        if len(self.clusterIDList) != len(path2.clusterIDList):
            return sgn(len(self.clusterIDList) - len(path2.clusterIDList));
        if self.clusterIDList < path2.clusterIDList : 
            return -1
        if self.clusterIDList>path2.clusterIDList : 
            return 1
        return sgn(len(self.clusterIDList)-len(path2.clusterIDList))
    
    #
    # Run AS-pref decision process between two paths
    #
    def compareTo_AS_pref(self, path2): # the lower is the superior
        global bgp_always_compare_med;
        if self.weight != path2.weight:
            return sgn(path2.weight - self.weight);
        if self.local_pref != path2.local_pref:
            return sgn(path2.local_pref - self.local_pref);
        if len(self.aspath) != len(path2.aspath):
            return sgn(len(self.aspath) - len(path2.aspath));
        if len(self.aspath) > 0 and len(path2.aspath) > 0 and (((not bgp_always_compare_med) and self.aspath[0] == path2.aspath[0]) or bgp_always_compare_med) and self.med != path2.med:
            return sgn(self.med - path2.med);
        else :
            return 0;


    #
    # Build a new path with the same attributes
    #
    def copy(self, p2):
        global EPIC;
        self.type= p2.type
        self.index = p2.index;
        self.src_pid = p2.src_pid;
        #self.type = p2.type;
        self.weight = p2.weight;
        self.local_pref = p2.local_pref;
        self.med = p2.med;
        self.nexthop = p2.nexthop;
        self.igp_cost = p2.igp_cost
        self.ibgp_ebgp=p2.ibgp_ebgp
        self.community = [];
        self.community.extend(p2.community);
        self.aspath = [];
        self.aspath.extend(p2.aspath);
        self.originatorID=p2.originatorID
        self.clusterIDList=[]
        self.clusterIDList.extend(p2.clusterIDList)
#        self.alternative = p2.alternative;


    #
    # Return string representation of a path
    #
#@vvandens - Rewrited on 2/2/09
    def __str__(self):
        tmpstr = str(self.index) + " " + str(self.nexthop) + " " +str(self.local_pref) + " "+ str(self.med) + " " + str(self.aspath).replace(" ",  "") + " " + str(self.community).replace(" ","")+ " " + str(self.src_pid)+" "+str(self.igp_cost)+ " "+ str(self.originatorID) + " "+ str(self.clusterIDList).replace(" ","")
        
        
     #   " From " + str(self.src_pid) + " Lpref " + str(self.local_pref) + " Aspath "+ str(self.aspath) + " Med " + str(self.med) + " Nexthop " + 
     #   str(self.nexthop) + " IGP cost " + str(self.igp_cost) + " Comm "+ str(self.community) + " Weight " + str(self.weight) + " Altern " + str(self.alternative);
        

        if self.type=="W" : 
            tmpstr="W" + " " + str(self.index)
        return tmpstr;

#@vvandens - End of modification
    #
    # Compare two CPaths object, i.e. check if purely BGP attributes are equals
    #
    def __cmp__(self, other):
        # if self.src_pid<other.src_pid : 
        #             return -1
        #         if self.src_pid>other.src_pid : 
        #             return 1
        if self.weight!=other.weight :
            return self.weight-other.weight
        if self.local_pref!=other.local_pref : 
            return self.local_pref-other.local_pref
        if self.med!=other.med : 
            return self.med - other.med
        if self.nexthop<other.nexthop : 
            return -1
        if self.nexthop>other.nexthop : 
            return 1
        if self.community<other.community : 
            return -1
        if self.community>other.community : 
            return 1
        if self.igp_cost!=other.igp_cost : 
            return self.igp_cost-other.igp_cost
        if self.aspath<other.aspath : 
            return -1
        if self.aspath>other.aspath : 
                return 1
        if self.ibgp_ebgp!=other.ibgp_ebgp : 
            return self.ibgp_ebgp-other.ibgp_ebgp
        return 0
        
        
############################################################################################################################
#                                     Class CPeer - Represents a peer of a BGP router
############################################################################################################################

class CPeer:
    # id = None;
    # rib_in = None; # key: prefix, store the paths received from peer
    # rib_out = None; # key: prefix, store the paths sent to peer
    # out_queue = None; # store the updates hold by MRAI timer
    # rand_seed = None;
    # mrai_base = None;
    # route_reflector_client = None;
    # route_map_in = None;
    # route_map_out = None;
    # route_map_sorted = None;
    
    #
    # Returns a string representation of the peer, i.e. it's peer id
    #
    def __str__(self):
        return str(self.id);

    #
    # Constructor
    #
    def __init__(self, i, l):
        self.id = i;
        self.link = l;
        self.rib_in = {};
        self.rib_out = {};
        self.out_queue = [];
        self.mrai_base = 0;
        self.rand_seed = None;
        self.route_map_in = None;
        self.route_map_out = None;
        self.route_map_sorted = False;
        self.route_reflector_client = False;
        self.nexthopself=False;
        self.DelayedWithdraws={}
        

    #
    # Clear the routing tables of this peer
    #
    def clear(self):
        global EPIC;
        del self.rib_in; self.rib_in = {};
        del self.rib_out; self.rib_out = {};
        del self.out_queue; self.out_queue = [];
        


    #
    # Return computed value of the MRAI delay for this peer
    #
    def mrai_timer(self):
        global MRAI_JITTER, RANDOMIZED_KEY;
        if MRAI_JITTER:
            if self.rand_seed is None:
                seed = str(self) + RANDOMIZED_KEY;
                self.rand_seed = random.Random(seed);
            delay = self.mrai_base*(3.0 + self.rand_seed.random()*1.0)/4;
        else:
            delay = self.mrai_base;
        return toSystemTime(delay);

    #
    # Another computation of MRAI value
    #
    def random_mrai_wait(self):
        global RANDOMIZED_KEY;
        if self.rand_seed is None:
            seed = str(self) + RANDOMIZED_KEY;
            self.rand_seed = random.Random(seed);
        return toSystemTime(self.rand_seed.random()*self.mrai_base); 

    #
    # Add prefix to MRAI waiting sending queue.  Remove previous announcement because they are up to date
    #
    def enqueue(self, prefix):
        #Remove previous messages for this prefix
        self.dequeue(prefix);
        self.out_queue.append(prefix);

    #
    # Remove prefix from MRAI waiting queue
    #
    def dequeue(self, prefix):
        if prefix in self.out_queue:
            self.out_queue.remove(prefix);
    
    #
    # Return paths received for this prefix
    #
#@vvandens - Added on 2/2/09
    def getPaths(self, prefix):
        if prefix in self.rib_in : 
            return self.rib_in[prefix]
        return []
#@vvandens - End of modification

    #
    # return string representing path in adjribin for this prefix
    #
    def getRibInStr(self, prefix):
        tmpstr = "#" + self.id;
        if self.isUp and prefix in self.rib_in:
            for p in self.rib_in[prefix]:
                tmpstr = tmpstr + "(" + str(p);
        return tmpstr;
    
    #
    # Sort route maps for this peer
    #
    def sortRouteMap(self):
        if self.route_map_out is not None:
            self.route_map_out.sort(key=cmp_to_key(cmpRouteMap));
        if self.route_map_in is not None:
            self.route_map_in.sort(key=cmp_to_key(cmpRouteMap));
        self.route_map_sorted = True;

    #
    # Return outfilters
    #
    def getRouteMapOut(self):
        if self.route_map_out is not None:
            if not self.route_map_sorted:
                self.sortRouteMap();
            return self.route_map_out;
        else:
            return [];
    #
    # Return infilters
    #
    def getRouteMapIn(self):
        if self.route_map_in is not None:
            if not self.route_map_sorted:
                self.sortRouteMap();
            return self.route_map_in;
        else:
            return [];
############################################################################################################################
#                                     Class CIGPLink - Represents an IGP link
############################################################################################################################
class CIGPLink : 
    # start=None
    # end=None
    # status=None
    # cost=-1
    # bandwidth=0
    # delay=0
    # rand_seed=None
    def __init__(self, start, end, cost=500, bw=100000000):
        self.start=start
        self.end=end
        self.cost=cost
        self.bandwidth=bw
        self.rand_seed=None
        #By default, link is down
        status=LINK_DOWN
    #
    # Return value of link delay
    #
    def interpretDelayfunc(self):
        global _link_delay_table;
        if self in _link_delay_table:
            return interpretDelayfunc(self, self.rand_seed, _link_delay_table[self]);
        #if no delay configured but igp cost is not null : Compute delay based on igp cost,
        #interpreted as the distance in kms between the two routers.  
        if cost_based_delay :
            return interpretDelayfunc(self, self.rand_seed, ["deterministic", float(self.cost*1000)/300000000.0])
        else:
            return interpretDelayfunc(self, self.rand_seed, default_link_delay_func);

    #
    # Return link delay: queueing + propagation
    #
    def link_delay(self, size): # queuing delay + propagation delay
        return toSystemTime(self.interpretDelayfunc() + size*1.0/self.bandwidth);
############################################################################################################################
#                                     Class CIGPNetwork - Represents the IGP graph
############################################################################################################################
class NodeUnreachableError(Exception):
    """Exception thrown when a node is not reachable in the IGP graph"""
    pass
    
class CIGPNetwork :     
    #Constructor
    def __init__(self):
        self.networks={}
        #self.apspDict={}
        self.apspLenDict={}
        self.linkList={}
        self.routerList={} #Dictionnary IP-domain
        self.ebgp_neighbors={} #Dictionnary giving the eBGP neighbors of each router

    
    #Add router to the graph of a domain
    def addRouter(self, router_id, domain): 
        try : 
            self.networks[domain]
        except KeyError : 
            self.networks[domain]=nx.Graph()
            self.apspLenDict[domain]={}
        self.routerList[router_id]=domain
        
    #If link already present : change cost and bw values
    def addIGPLink(self,start, end, cost=500, bandwidth=100000000, 
                                    status=LINK_UP, compute=True) :
        try : 
            self.routerList[start]
        except KeyError:
            print("Unknown node : ", start)
        try : 
            self.routerList[end]
        except KeyError :
            print("Unknown node : ", end)
        first=sorted([start, end])[0]
        second=sorted([start, end])[1]
        start_as=self.routerList[first]
        end_as=self.routerList[second]
        try : 
            self.linkList[first]
        except KeyError : 
            self.linkList[first]={}
        ### Added by dimeji 2020/02/10
        #print("In CIGPNetwork, calling CIGPLink for first: %s, second: %s with cost: %s\n" %(first, second, cost))
        self.linkList[first][second]=CIGPLink(first, second, cost, bandwidth)
        #print("Dump self.linkList\n")
        #for key, value in self.linkList.items():
        #    print("     Key: %s     \n " %key)
        #    print("        Value: \n") 
        #    pp(value)
        #Link is up but no dijkstra now
        if status==LINK_UP : 
            if compute==False :
                if start_as==end_as :
                    #self.networks[self.routerList[start]].add_edge(first, second, cost)
                    #self.networks[self.routerList[end]].add_edge(first, second, cost)
                    ## @@fayomidimeji 2020/02/11.
                    ## Patch added to ensure the cost of links is passed as weight to add_edge 
                    ##function and used in selecting shortest path by the
                    ## single_sourc_dikjkstra_path_length function
                    self.networks[self.routerList[start]].add_edge(first, second, weight=cost)
                    self.networks[self.routerList[end]].add_edge(first, second, weight=cost)
                else : 
                    try : 
                        self.ebgp_neighbors[start].append(end)
                    except KeyError : 
                        self.ebgp_neighbors[start]=[end]
                    try : 
                        self.ebgp_neighbors[end].append(start)
                    except KeyError : 
                        self.ebgp_neighbors[end]=[start]
                self.linkList[first][second].status=LINK_UP
            else :
                self.linkUp(start, end)
        return self.linkList[first][second]
        
    def compute(self):
        for net in list(self.networks.keys()) :
            #if self.networks.keys().index(net)%100 == 0 : 
            #print >>sys.stderr, "Computing IGP of AS", net
            #print net, self.networks[net].nodes()
            #print net, self.networks[net].edges()
            for node in self.networks[net].nodes() : 
                #if node =="0.57.0.0" or node=="0.57.0.1" or node== "0.11.0.0" or node =="0.11.0.1":
                #    if node in self.apspLenDict[net].keys() :
                #        print "Old APSP for net", net, "and node", node, ":", self.apspLenDict[net][node]
                self.apspLenDict[net][node] =\
                    nx.single_source_dijkstra_path_length(self.networks[net], node) 
                #print("-----------Start--------------\n")
                #print("In compute function in CIGpNetwork\n")
                #print("Print node:\n")
                #pp(node)
                #print("Print net:\n")
                #pp(net)
                #print("self.apspLenDict:\n")
                #pp(self.apspLenDict)
                #print("-----------End------------------\n")
                #print("\n\n\n\n")
                #if node =="0.57.0.0" or node=="0.57.0.1" or node== "0.11.0.0" or node =="0.11.0.1":
                #    print "new APSP for net", net, "and node", node, ":", self.apspLenDict[net][node]      
    def linkDown(self, start, end) :
        first=sorted([start, end])[0]
        second= sorted([start, end])[1]
        lk=self.linkList[first][second]
        lk.status=LINK_DOWN
        #Get ASes of both end of the link
        start_as=self.routerList[lk.start]
        end_as=self.routerList[lk.end]
        if start_as==end_as : 
            self.networks[start_as].remove_edge(first, second)
            for node in self.networks[start_as].nodes() :
                self.apspLenDict[start_as][node] =\
                    nx.single_source_dijkstra_path_length(self.networks[start_as], node)            
        #print start_as, "removes link", key[0],  key[1]
        # if start_as!=end_as :
        #     self.networks[end_as].remove_edge(first, second)
        #     for node in self.networks[end_as].nodes() :
        #         self.apspLenDict[end_as][node] =\
        #             nx.single_source_dijkstra_path_length(self.networks[end_as], node)
            #print end_as, "removes link", key[0],  key[1]
        #self.compute()
    def linkUp(self, start, end):
        first=sorted([start, end])[0]
        second= sorted([start, end])[1]
        link=self.linkList[first][second]
        link.status=LINK_UP
        start_as=self.routerList[link.start]
        end_as=self.routerList[link.end]
        #Add intradomain link to IGP network of the domain
        if start_as==end_as : 
            ## @@fayomidimeji 2020/02/11 Ensure weight attribute is passed
            ## and included to the add_edge function to ensure
            ## single_source_dijkstra_path_length returns the correct shortest
            ## calculation
            self.networks[start_as].add_edge(first, second, weight=link.cost)
            for node in self.networks[start_as].nodes() :
                self.apspLenDict[start_as][node] =\
                    nx.single_source_dijkstra_path_length(self.networks[start_as], node)
        else : #Interdomain case : Check if link has to be added to database
            try : 
                if end not in self.ebgp_neighbors[start] : 
                    self.ebgp_neighbors[start].append(end)
            except KeyError : 
                self.ebgp_neighbors[start]=[end]
            try : 
                if start not in self.ebgp_neighbors[end] :
                    self.ebgp_neighbors[end].append(start)
            except KeyError : 
                self.ebgp_neighbors[end]=[start]
        # if start_as!=end_as : 
        #     self.networks[end_as].add_edge(first, second, link.cost)
        #     for node in self.networks[end_as].nodes() :
        #         self.apspLenDict[end_as][node] =\
        #             nx.single_source_dijkstra_path_length(self.networks[end_as], node)
        #Should only be called for routers of concerned networks
        #self.compute()
    def hasIGPLink(self, start, end):
        first=sorted([start, end])[0]
        second= sorted([start, end])[1]
        try : 
            self.linkList[first][second]
        except KeyError : 
            return False
        return True
        
    def hasNode(self, node):
        try : 
            self.routerList[node]
        except KeyError :
            return False
        return True
        
    #Return the undirected IGP link between nodes start and end
    def getIGPLink(self,start, end):
        if not self.hasIGPLink(start, end) : 
            return None
        first=sorted([start, end])[0]
        second= sorted([start, end])[1]
        return self.linkList[first][second]
        
    def getShortestPath(self,start, end):
        if not self.isReachableFrom(start,end) : 
            return None
        link=self.getIGPLink(start, end)

        start_as=self.routerList[start]
        end_as=self.routerList[end]
        if start_as!=end_as : #Interdomain path, we cannot rely on the IGP only 
            if link is not None and link.status==LINK_UP :     
                return [start, end]
            min_router=""
            shortest_dist=None
            for neighbor in self.ebgp_neighbors[end] :
                if self.getIGPLink(neighbor, end).status==LINK_DOWN : 
                    continue
                if self.routerList[neighbor]==start_as : 
                    dist=self.apspLenDict[start_as][start][end]
                    if min_router=="" :
                        min_router=neighbor
                        shortest_dist=dist
                    if dist<shortest_dist :
                        min_router=neighbor
                        shortest_dist=dist
            return getShortestPath(start, min_router).append(end)
        #Intradomain path, compute dijkstra
        #print >>sys.stderr, self.networks.keys()
        return nx.dijkstra_path(self.networks[self.routerList[start]], start, end)
        
        
    def getShortestPathLength(self,start, end):
        if not self.isReachableFrom(start,end) : 
            return None
        link=self.getIGPLink(start, end)
        ### Added by Dimeji Fayomi 2020/02/11 
        #print("Finding shortest path length between %s and %s\n" %(start, end))
        #print("Show the CIGPLink object between the routers\n")
        #pp(link)
        #No direct link, need to find the Shortest Path
        start_as=self.routerList[start]
        end_as=self.routerList[end]
        #Interdomain case
        if start_as!=end_as :
            if link is not None and link.status==LINK_UP :    
                #Directly connected routers
                return link.cost
            min_router=""
            shortest_dist=None
            for neighbor in self.ebgp_neighbors[end] :
                if self.getIGPLink(neighbor, end).status==LINK_DOWN : 
                    continue
                if self.routerList[neighbor]==start_as : 
                    dist=self.apspLenDict[start_as][start][neighbor]
                    if min_router=="" :
                        min_router=neighbor
                        shortest_dist=dist
                    if dist<shortest_dist :
                        min_router=neighbor
                        shortest_dist=dist
            ebgp_link=self.getIGPLink(min_router, end)
            #print("Shortest distance between %s and %s is %s\n" %(start,end,shortest_dist))
            #print("eBGP link object is\n")
            #pp(ebgp_link)
            #print("apspLenDict is:\n")
            #pp(self.apspLenDict)
            #print("\n\n\n")
            return shortest_dist+ebgp_link.cost
        #Intradomain case
        return self.apspLenDict[self.routerList[start]][start][end]
        
                
    def getPathTransmissionDelay(self,start, end, size):
        if not self.isReachableFrom(start,end) : 
            print("Node Unreach :", start, end, file=sys.stderr)
            raise NodeUnreachableError
        if start==end : 
            return 0
        path=self.getShortestPath(start, end)
        origin=start
        delay=0
        for dest in path[1:] : 
            delay+=self.getIGPLink(origin, dest).link_delay(size)
            #current link end is the next link start
            origin=dest
        return delay
        
    def isReachableFrom(self, origin, dest):
        #print "Checking reachability between", origin, dest
        start_as=self.routerList[origin]
        end_as=self.routerList[dest]
        link=self.getIGPLink(origin, dest)
        #Interdomain case
        if start_as!=end_as : #Interdomain path, we cannot rely on the IGP only 
            #Check if the routers are directly connected ASBRs
            try : 
                self.ebgp_neighbors[dest]
            except KeyError :
                #Interdomain path, but end of path is intradomain node => not possible
                return False
            if link is not None and link.status==LINK_UP :
                return True
            #Not directly connected
            else : 
                min_router=""
                shortest_dist=None
                for neighbor in self.ebgp_neighbors[dest] :
                    if self.getIGPLink(neighbor, dest).status==LINK_DOWN : 
                        continue
                    if self.routerList[neighbor]==start_as : 
                        if self.isReachableFrom(origin, neighbor) : 
                            #There exist a path between the origin and a local neighbor of dest
                            return True
                #We did not find a reachable local neighbor of dest            
                return False
        #Intradomain case
        try : 
            self.apspLenDict[start_as][origin][dest]
        except KeyError :
            return False
        return True
      
            
        
            
############################################################################################################################
#                                     Class CLink - Represents a BGP session
############################################################################################################################

class CLink:
    # start = None; # CRouter
    # end = None; # CRouter
    # status = None; # PEER_UP/PEER_DOWN
    # reach=None; # PEER_REACH/PEER_UNREACH
    # #cost = None;
    # #bandwidth = None;
    # delayfunc = None;
    # rand_seed = None;
    # next_delivery_time_start = None;
    # next_delivery_time_end = None;
    
    #
    # Return string representation of the link, i.e. both ends. 
    #
    def __str__(self):
        return str(self.start) + "-" + str(self.end);



    #
    # Constructor
    #
    def __init__(self, s, e):
        global default_link_delay_func, PEER_UP;
        self.start = s;
        self.end = e;
        self.status = PEER_UP;
        self.reach=PEER_REACH
        #self.cost = 500; #default value in km. 
        #self.bandwidth = 100000000; # 100MB as default
        #self.delayfunc = ["deterministic", 0.1];
        #self.delayfunc = default_link_delay_func; #["uniform", 0.01, 0.1];
        self.rand_seed = None;
        self.next_delivery_time_start = 0;
        self.next_delivery_time_end = 0;

    #
    # Return time of arrival at the other end of the link
    #
    def next_delivery_time(self, me, size):
        global _systime
        delay=_igp_graph.getPathTransmissionDelay(self.start, self.end, size)
        if me == self.start:
            if self.next_delivery_time_start < _systime:
                self.next_delivery_time_start = _systime;
            self.next_delivery_time_start = self.next_delivery_time_start + delay#self.link_delay(size);
            return self.next_delivery_time_start;
        elif me == self.end:
            if self.next_delivery_time_end < _systime:
                self.next_delivery_time_end = _systime;
            self.next_delivery_time_end = self.next_delivery_time_end + delay#self.link_delay(size);
            return self.next_delivery_time_end;

    

    #
    # Return other end of the link
    #
    def getPeer(self, me):
        if self.start == me:
            return self.end;
        elif self.end == me:
            return self.start;
        else:
            raise BadLinkEndException

    #
    # Return BGP type of the link
    #
    def ibgp_ebgp(self):
        global _router_list;
        if _router_list[self.start].asn == _router_list[self.end].asn:
            return IBGP_SESSION;
        else:
            return EBGP_SESSION;

############################################################################################################################
#                                     Class CRouteMap - Represents a BGP route map, i.e.  BGP filter
############################################################################################################################
class CRouteMap:
    # name = None;
    # priority = None;
    # permit = None;
    # match = None;
    # action = None;

    #
    # Constructor
    #
    def __init__(self, n, pmt, pr):
        self.name = n;
        if pmt == "permit":
            self.permit = True;
        else:
            self.permit = False;
        self.priority = pr;
        self.match = [];
        self.action = [];
        
        
    def __str__(self):
        print(self.name, self.permit, self.match, self.action)
    #
    # Check if this path match the route map conditions
    #
    def isMatch(self, prefix, path):
        i = 0;
        while i < len(self.match):
            cond = self.match[i];
            if cond[0] == "community-list":
                if len(cond) >= 3 and cond[2] == "exact":
                    cmlist = cond[1].split(":");
                    cmlist.sort();
                    if cmlist != path.community:
                        return False;
                elif cond[1] not in path.community:
                    return False;
            elif cond[0] == "as-path":
                pathstr = array2str(path.aspath, " ");
                regexp=array2str(cond[1:], ' ')
                
                if not re.compile(regexp).match(pathstr):
                    return False;
            elif cond[0] == "ip" and cond[1] == "address":
                if cond[2] != prefix:
                    return False;
            elif cond[0] == "metric":
                if int(cond[1]) != path.med:
                    return False;
            i = i + 1;
        return True;

    #
    # Perform action of the route map on the path
    #
    def performAction(self, path):
        i = 0;
        while i < len(self.action):
            act = self.action[i];
            if act[0] == "local-preference":
                path.local_pref = int(act[1]);
            elif act[0] == "community":
                if act[1] == "none":
                    path.community = [];
                else:
                    if len(act) >= 3 and act[2] == "additive":
                        path.community.extend(act[1].split(":"));
                    else:
                        path.community = act[1].split(":");
                    path.community.sort();
            elif act[0] == "as-path" and act[1] == "prepend":
                j = 0;
                while j < len(act) - 2:
                    path.aspath.insert(j, int(act[2+j]));
                    j = j + 1;
            elif act[0] == "metric":
                path.med = int(act[1]);
            i = i + 1;
        return path;

############################################################################################################################
#                                     Class CDelayedWithdraw - Structure for storing info about delayed withdraws
############################################################################################################################
class CDelayedWithdraws :
    def __init__(self, timer, mrai):
        self.expiration_time=None
        self.MRAI_time=None
        self.sent=False

############################################################################################################################
#                                     Class CEvent - Represents a BGP event
############################################################################################################################
class CEvent:
    # seq = 0; # sequence
    # time = None; # when
    # param = None; # where
    # type = None; # what

    #
    # Constructor
    #
    def __init__(self, tm, pr, t):
        self.seq = getSequence();
        self.time = tm;
        self.param = pr;
        self.type = t;


    #
    # Print event representation on stdout
    #
    def showEvent(self):
        global SHOW_RECEIVE_EVENTS, _router_list, SHOW_DEBUG;
        #print self.time
        if self.type == EVENT_RECEIVE:
            [rtid, rvid, update] = self.param;
            #if SHOW_RECEIVE_EVENTS:
            print(formatTime(self.time), "EVENT_RECEIVE",str(_router_list[rvid]), "receive", str(update.prefix), "from", str(_router_list[rtid]) , ":", str(update))
            if SHOW_NH : 
                for path in update.paths : 
                    sys.stdout.write(path.nexthop)
                sys.stdout.write("\n")
        elif self.type == EVENT_UPDATE:
            [rtid, prefix] = self.param;
            print(formatTime(self.time), "EVENT_UPDATE", str(_router_list[rtid]) , "update", prefix)
        elif self.type == EVENT_MRAI_EXPIRE_SENDTO:
            [sdid, rvid, prefix] = self.param;
            #if SHOW_DEBUG:
            print(formatTime(self.time), "EVENT_MRAI_EXPIRES_SENDTO", sdid,  "send", prefix,"to", rvid)
        elif self.type == EVENT_LINK_DOWN:
            [rt1, rt2] = self.param;
            print(formatTime(self.time), "EVENT_LINK_DOWN", str(_router_list[rt1]), "-", str(_router_list[rt2]), "down");
        elif self.type == EVENT_LINK_UP:
            [rt1, rt2] = self.param;
            print(formatTime(self.time), "EVENT_LINK_UP", str(_router_list[rt1]), "-", str(_router_list[rt2]), "up");
        elif self.type == EVENT_PEER_DOWN:
            [rt1, rt2] = self.param;
            print(formatTime(self.time), "EVENT_PEER_DOWN", str(_router_list[rt1]), "-", str(_router_list[rt2]), "down");
        elif self.type == EVENT_PEER_UP:
            [rt1, rt2] = self.param;
            print(formatTime(self.time), "EVENT_PEER_UP", str(_router_list[rt1]), "-", str(_router_list[rt2]), "up");
        elif self.type == EVENT_ANNOUNCE_PREFIX:
            [rtid, prefix] = self.param;
            print(formatTime(self.time), "EVENT_ANNOUNCE_PREFIX", str(_router_list[rtid]), "announces", prefix);
        elif self.type == EVENT_WITHDRAW_PREFIX:
            [rtid, prefix] = self.param;
            print(formatTime(self.time), "EVENT_WITHDRAW_PREFIX", str(_router_list[rtid]), "withdraws", prefix);
        elif self.type == EVENT_TERMINATE:
            print(formatTime(self.time), "EVENT_TERMINATE");
        else:
            print(formatTime(self.time), "UNKNOWN_EVENT");


    #
    # Perform corresponding action when the event happens
    #
    def process(self):
        global _router_list, num_ebgp_msgs;
        #self.showEvent();
        if self.type == EVENT_RECEIVE:
            [rtid, rvid, update] = self.param;
            #if MAX_PATH_NUMBER!=1 : 
            #    _router_list[rvid].receive_AddPaths(rtid, update);
            #else : 
            
            #Increment ebgp counter
            if _router_list[rvid].asn != _router_list[rtid].asn : 
                num_ebgp_msgs+=1
            _router_list[rvid].receive(rtid, update);
            if SHOW_RECEIVE_EVENTS:
                print(formatTime(self.time), "EVENT_RECEIVE",str(_router_list[rvid]), "receive", str(update.prefix), "from", str(_router_list[rtid]) , ":", str(update))
                if SHOW_NH : 
                    for path in update.paths : 
                        sys.stdout.write(path.nexthop)
                    sys.stdout.write("\n")
        elif self.type == EVENT_UPDATE:
            [rtid, prefix] = self.param;
            _router_list[rtid].update(prefix, rcv=True);
        elif self.type == EVENT_TRACEROUTE:
            [prefix] = self.param;
            for router in list(_router_list.keys()) : 
                tracert=checkForwarding(router, prefix)
                print(getSystemTimeStr(), "TRACEROUTE : Router", str(_router_list[router]), "prefix", prefix, ":", end=' ') 
                if tracert : 
                    print("VALID")
                else : print("INVALID")
        elif self.type == EVENT_MRAI_EXPIRE_SENDTO:
            [sdid, rvid, prefix] = self.param;
            _router_list[sdid].resetMRAI(rvid, prefix);
            #if MAX_PATH_NUMBER!=1 : 
                #Prefix=(prefix, index) in this case
            #    _router_list[sdid].sendto_AddPaths(rvid, prefix);
            #else : 
            _router_list[sdid].sendto(rvid, prefix);
        elif self.type == EVENT_PEER_DOWN:
            [rt1, rt2] = self.param;
            lk = getRouterLink(rt1, rt2);
            lk.status = PEER_DOWN;
            _router_list[rt1].peerDown(rt2);
            _router_list[rt2].peerDown(rt1);
        elif self.type == EVENT_PEER_UP:
            [rt1, rt2] = self.param;
            lk = getRouterLink(rt1, rt2);
            lk.status = PEER_UP;
            if lk.reach==PEER_REACH : 
                _router_list[rt1].peerUp(rt2);
                _router_list[rt2].peerUp(rt1);
        elif self.type == EVENT_LINK_DOWN: 
            [rt1, rt2] = self.param;
            if SHOW_LINK_EVENTS:
                print(formatTime(self.time), "EVENT_LINK_DOWN",str(_router_list[rt1]), str(_router_list[rt2]))
            eventLinkDown(rt1,rt2)
        elif self.type == EVENT_LINK_UP:
            [rt1, rt2] = self.param;
            if SHOW_LINK_EVENTS:
                print(formatTime(self.time), "EVENT_LINK_UP",str(_router_list[rt1]), str(_router_list[rt2]))
            eventLinkUp(rt1,rt2)
        elif self.type == EVENT_ANNOUNCE_PREFIX:
            [rtid, prefix] = self.param;
            _router_list[rtid].announce_prefix(prefix);
            
        elif self.type == EVENT_INJECT_MRT :
            [rtid, mrt] = self.param
            _router_list[rtid].advertise_mrt(mrt)
            
        elif self.type == EVENT_WITHDRAW_PREFIX:
            [rtid, prefix] = self.param;
            _router_list[rtid].withdraw_prefix(prefix);
        elif self.type == EVENT_TERMINATE:
            return -1;
        return 0;

    #
    # Compare two event, based on happening time
    #
    def __cmp__(self, o):
        if self.time != o.time:
            return self.time - o.time;
        return self.seq - o.seq;


############################################################################################################################
#                                     Class COrderedList - Represents an ordered list
############################################################################################################################
class COrderedList:
    data = [];
    #
    # Constructor
    #
    def __init__(self):
        self.data = [];

    #
    # Insert object o in the correct position in the ordered list, dichotomical search. Do nothing is object is present
    # 
    def add(self, o):
        start = 0;
        end = len(self.data)-1;
        while start <= end:
            # @@fayomidimeji 2020/02/03. Fix python 3 TypeError: list indices must be integers, not float
            j = (start + end)//2;
            if "__cmp__" in dir(o):
                result = o.__cmp__(self.data[j]);
                if result == 0:
                    return;
                elif result > 0:
                    start = j + 1;
                else:
                    end = j - 1;
            else:
                if o == self.data[j]:
                    return;
                elif o > self.data[j]:
                    start = j + 1;
                else:
                    end = j - 1;
        self.data.insert(start, o);

    #
    # Return item at index idx
    #
    def __getitem__(self, idx):
        return self.data[idx];
    
    #
    # Return len of the list
    #
    def __len__(self):
        return len(self.data);

    #
    # Remove and returns element at index idx
    #
    def pop(self, idx):
        return self.data.pop(idx);


############################################################################################################################
############################################################################################################################
#                                     MAIN
############################################################################################################################
############################################################################################################################





############################################################################################################################
#                                     Miscellaneous utility function
############################################################################################################################

#
# Create link between two routers, and add to database. 
#
def getRouterLink(id1, id2):
    global _router_graph;
    if id1 > id2:
        rt1 = id1;
        rt2 = id2;
    else:
        rt2 = id1;
        rt1 = id2;
    if rt1 not in _router_graph:
        _router_graph[rt1] = {};
    if rt2 not in _router_graph[rt1]:
        lk = CLink(rt1, rt2);
        _router_graph[rt1][rt2] = lk;
    return _router_graph[rt1][rt2];
    
    
#
# Compute all pairs shortest paths lengths
#    
def computeSPLenght():
    global _router_graph
#
# Return string representation of a path array
#
def array2str(path, sep):
        if len(path) == 0:
                return "";
        else:
            tmpstr = str(path[0]);
            for i in range(1, len(path)):
                tmpstr = tmpstr + sep + str(path[i]);
            return tmpstr;

#
# Compare two route maps based on their priority
#
def cmpRouteMap(rm1, rm2):
    global _route_map_list;
    return _route_map_list[rm1].priority - _route_map_list[rm2].priority;

# Enable cmpRouteMap to take two arguments
# @fayomidimeji 2020/02/04 Convert a cmp= function into a key= function'
# python2 to python3 port
def cmp_to_key(mycmp):
    'Convert a cmp= function into a key= function'
    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj

        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0

        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0

        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0 

        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0

        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0

        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K


def eventLinkDown(rt1, rt2):
    _igp_graph.linkDown(rt1,rt2)
    for router in _router_list : 
        #Recompute IGP cost and check for peer reachability
        _router_list[router].IGPChange()
        
def eventLinkUp(rt1,rt2):
    _igp_graph.linkUp(rt1,rt2)
    [_router_list[router].IGPChange() for router in _router_list]
    # for router in _router_list : 
    #     #Recompute IGP cost and check for peer reachability
    #     _router_list[router].IGPChange()
        
        
############################### Traceroute  #####################################

def checkForwarding(routerID, prefix, ForwPath=None):
    if ForwPath is None : 
        ForwPath=[]
    #Is routerID valid?
    try : 
        _router_list[routerID]
    except KeyError : 
        return False
    #Check if prefix is present in locrib : 
    if prefix not in _router_list[routerID].loc_rib \
        or len(_router_list[routerID].loc_rib[prefix])==0 : 
        #print "Prefix not in loc_rib", routerID, prefix
        return False
    #Get path to prefix
    path=_router_list[routerID].loc_rib[prefix][0]
    #Router originates prefix : 
    if path.nexthop==routerID : 
        return True
    #Check for forwarding loops
    if routerID in ForwPath : 
        print("Forwarding loop!", routerID, ForwPath)
        return False
    #Path is not valid
    if not _igp_graph.isReachableFrom(routerID, path.nexthop) :
        print("Nexthop not reachable!", routerID, path.nexthop) 
        return False
    #Path is valid up to the nexthop => Check remaining subpath
    ForwPath.append(routerID)
    return checkForwarding(path.nexthop, prefix, ForwPath)


###################################################################################
#
# Split string at separators pat
#
def splitstr(line, pat):
    ele = [];
    i = 0;
    tmpstr = "";
    while i <= len(line):
        if i < len(line) and line[i] != pat:
            tmpstr = tmpstr + line[i];
        else:
            if tmpstr != "":
                ele.append(tmpstr.lower());
                tmpstr = "";
        i = i + 1;
    return ele;

#
# Return next significant line from config file
#
def readnextcmd(fh):
    try:
        line = fh.readline();
        while len(line) > 0 and (line[0] == '!' or len(splitstr(line[:-1], ' ')) == 0):
            line = fh.readline();
        return splitstr(line[:-1], ' ');
    except:
        print("Exception: ", sys.exc_info()[0]);
        raise;



#
# Interpret bandwith unit of value (last character of the parameter)
# 
def interpretBandwidth(line):
    if line[-1] == 'M' or line[-1] == 'm':
        return float(line[:-1])*1000000;
    elif line[-1] == 'K' or line[-1] == 'k':
        return float(line[:-1])*1000;
    elif line[-1] == 'G' or line[-1] == 'g':
        return float(line[:-1])*1000000000;
    else:
        return float(line);


#
# Parse delay configuration, return array with delay parameters
#
def interpretDelay(param):
    if param[0] not in ["deterministic", "normal", "uniform", "exponential", "pareto", "weibull"]:
        print("Distribution", param[0], "in", param, "is not supported!");
        sys.exit(-1);
    tmparray = [param[0]];
    for i in range(1, len(param)):
        tmparray.append(float(param[i]));
    return tmparray;


######################### BGP Mode Configuration ##########################
def parseBGPModeStr(bgpmode):
    try : 
        #Modes AddNPaths et AddNBest
        num_paths=int(bgpmode[3:-5])
        #print >>sys.stderr, "BGP Mode with N specified : ", bgpmode, num_paths,"\n"
        if bgpmode[4:]=="PATHS" :
            return BGP_MODE_ADD_N_PATHS, num_paths
        if bgpmode[4:]=="BESTS" : 
            return BGP_MODE_ADD_N_BESTS, num_paths
    except ValueError : 
        #No num of paths specified, continue and check other modes
        pass
    except : 
        print("Parsing error with ", bgpmode, file=sys.stderr)
        sys.exit(-1)
    if bgpmode=="BGP_NORMAL" :
        return BGP_MODE_NORMAL, 1
    elif bgpmode=="ADD_ALL_PATHS" :
        return  BGP_MODE_ADD_ALL_PATHS, 0 
    elif bgpmode=="BEST_EXTERNAL" :
        return BGP_MODE_BEST_EXTERNAL, 1
    elif bgpmode=="BEST_BIN" : 
        return BGP_MODE_BEST_BIN, 0
    elif bgpmode=="ADD_BEST_PATHS" : 
        return BGP_MODE_ADD_BEST_PATHS, 0
    elif bgpmode=="GROUP_BEST" :
        return BGP_MODE_GROUP_BEST, 0
    elif bgpmode=="DECISIVE-1" :
        return BGP_MODE_DECISIVE_STEP, 0
    else : 
        print("Warning : Unknown BGP Mode", bgpmode, ", using default normal BGP mode", file=sys.stderr)  
        return BGP_MODE_NORMAL, 1
        
        
def BGPModeAllRouters(BGPmode):
    mode, numpaths=parseBGPModeStr(BGPmode)
    for router in list(_router_list.values()) : 
        router.bgp_mode=mode
        router.bgp_num_paths=numpaths

def BGPModeAllASNButOne(GlobalBGPMode,ASN, ASNSpecBGPMode):
    """Set all routers to GlobalBGPMode, except for routers of AS ASN which have
    ASNSpecBGPMode"""
    gMode, gNumPaths=parseBGPModeStr(GlobalBGPMode)
    asMode, asNumPaths=parseBGPModeStr(ASNSpecBGPMode)
    for router in list(_router_list.values()) : 
        if router.asn==ASN : 
            #print >>sys.stderr, router, asMode, asNumPaths
            router.bgp_mode=asMode
            router.bgp_num_paths=asNumPaths
        else : 
            router.bgp_mode=gMode
            router.bgp_num_paths=gNumPaths
            
    
def BGPModeRRvsASBR(BGPMode):
    """Set RR mode to BGP Mode and ASBR mode to BestExternal"""
    mode, numpaths=parseBGPModeStr(BGPMode)
    for router in list(_router_list.values()) :
        if router.route_reflector : 
            router.bgp_mode=mode
            router.bgp_num_paths=numpaths
        else : 
            router.bgp_mode=BGP_MODE_BEST_EXTERNAL
            router.bgp_num_paths=1
            
def BGPModePerAS(ASdict, defaultMode):
    """Set all routers of each AS to mode given in dict.  All other routers
    are set to default Mode"""
    defMode, defNumPaths=parseBGPModeStr(defaultMode)
    for router in list(_router_list.values()) : 
        if router.asn in list(ASdict.keys()) :
            router.bgp_mode, router.bgp_num_paths=parseBGPModeStr(ASdict[router.asn])
        else :
            router.bgp_mode, router.bgp_num_paths=defMode, defNumPaths
            
def BGPModePerRouter(dict, defaultMode):
    """Set routers to mode given in dict.  All other routers
    are set to default Mode"""
    deftMode, defNumPaths=parseBGPModeStr(defaultMode)
    for router in list(_router_list.values()) : 
        if router.id in list(ASdict.keys()) :
            router.bgp_mode, router.bgp_num_paths=parseBGPModeStr(ASdict[router.id])
        else :
            router.bgp_mode, router.bgp_num_paths=defMode, defNumPaths
    


def readConfig(lines):
    global BEST_EXTERNAL, SHOW_UPDATE_RIBS, SHOW_RECEIVE_EVENTS, SHOW_FINAL_RIBS, wrate, always_mrai, ssld, \
            bgp_always_compare_med, MRAI_JITTER, MAX_PATH_NUMBER,  CHECK_LOOP, BEST_BIN,\
            SHOW_DEBUG, RANDOMIZED_KEY, SHOW_SEND_EVENTS, default_link_delay_func, default_process_delay_func, _link_delay_table, \
            KEEP_VIRTUAL_LOC_PREF
    cur_bgp_mode="BGP_NORMAL"
    curAS=None     
    curRT = None;
    curNB = None;
    curMap = None;
    virtual=False
    for line in lines : 
        line=line.strip()
        if line=="" or line[0]=="!" : 
            continue
        cmd=line.split()
        if cmd[0]=="show" and cmd[1]=="version" :
            print(getRevisionNumber())
        if cmd[0] == "router" and cmd[1] == "bgp":
            curAS = int(cmd[2]);
            virtual=False
            #Configure router adress
        elif cmd[0] == "router" and cmd[1] == "virtual" :
            curAS = int(cmd[2])
            virtual=True
        elif cmd[0] == "bgp" and cmd[1] == "router-id":
            id = cmd[2];
            try :
                curRT=_router_list[id]
            except KeyError :
                if virtual : 
                    curRT=CVirtualRouter(curAS, id)
                else : 
                    curRT = CRouter(curAS, id);
                _router_list[id] = curRT;            
        elif cmd[0] == "bgp":
            if cmd[1] == "cluster-id":
                curRT.route_reflector = True;
                curRT.clusterID=cmd[2]
                # print "router", str(curRT), curRT.route_reflector;
            elif cmd[1] == "prefix-based-timer":
                curRT.mrai_setting = MRAI_PREFIX_BASED;
            else:
                print("unknown bgp configuration", cmd[1], "in", cmd);
                sys.exit(-1);
        elif cmd[0] == "neighbor":
            peerid = cmd[1];
            if peerid not in curRT.peers:
                link = getRouterLink(curRT.id, peerid);
                curNB = CPeer(peerid, link);
                curRT.peers[peerid] = curNB
                #Default value of MRAI is EBGP
                if GLOBAL_MRAI : 
                    curNB.mrai_base=GLOBAL_EBGP_MRAI
            if cmd[2] == "nexthop-self" : 
                curNB.nexthopself=True
            elif cmd[2] == "route-reflector-client":
                curRT.route_reflector=True
                curNB.route_reflector_client = True;
            elif cmd[2] == "route-map":
                if cmd[4] == "in":
                    if curNB.route_map_in is None:
                        curNB.route_map_in = [];
                    curNB.route_map_in.append(cmd[3]);
                elif cmd[4] == "out":
                    if curNB.route_map_out is None:
                        curNB.route_map_out = [];
                    curNB.route_map_out.append(cmd[3]);
            elif cmd[2] == "advertisement-interval": # in seconds
                if not GLOBAL_MRAI : 
                    curNB.mrai_base = float(cmd[3]);
            elif cmd[2] == "remote-as":
                #Check for misconfiguration
                try : 
                    if _router_list[peerid].asn!=int(cmd[3]) :
                        print("Bad neighbor ASN in configuration for router", peerid, curRT.id, cmd, _router_list[peerid].asn, file=sys.stderr)      
                        sys.exit(-1)
                except KeyError : 
                    pass
                #Configure MRAI if global
                if GLOBAL_MRAI : 
                    try : 
                        if int(cmd[3])==curRT.asn :
                            curNB.mrai_base=GLOBAL_IBGP_MRAI
                    except ValueError : 
                        print("Value error with command line : ", cmd, file=sys.stderr)
                        #sys.exit(-1)
            else:
                print("unknown neighbor configuration", cmd[2], "in", cmd);
                sys.exit(-1);
        # route-map <name> permit/deny priority
        elif cmd[0] == "route-map":
            if len(cmd) >= 4:
                pr = int(cmd[3]);
            else:
                pr = 10;
            curMap = CRouteMap(cmd[1], cmd[2], pr);
            _route_map_list[cmd[1]] = curMap;
        elif cmd[0] == "set":
            curMap.action.append(cmd[1:]);
        elif cmd[0] == "match":
            curMap.match.append(cmd[1:]);
        elif cmd[0] == "node" : #Add node to corresponding domain graph
            _igp_graph.addRouter(cmd[1], cmd[3])
        elif cmd[0] == "link":
            if len(cmd)==3 : #No cost or bw config
                #Add link only if it does not exists yet 
                #So we don't erase previous cost or bw
                if not _igp_graph.hasIGPLink(cmd[1],cmd[2]): 
                    _igp_graph.addIGPLink(cmd[1], cmd[2], compute=False)
            elif cmd[3] == "cost":
                if _igp_graph.hasIGPLink(cmd[1],cmd[2]): 
                    bw=_igp_graph.getIGPLink(cmd[1],cmd[2]).bandwidth
                    _igp_graph.addIGPLink(cmd[1], cmd[2], cost=int(cmd[4]),
                        bandwidth=bw, compute=False)
                    ### Added by Dimeji 2020/02/10
                    #print("Bandwidth for link %s-%s is %s\n" %(cmd[1],cmd[2],bw))

                else : 
                    _igp_graph.addIGPLink(cmd[1], cmd[2], cost=int(cmd[4]),
                        compute=False)

                
            elif cmd[3] == "bandwidth":
                bandwidth = interpretBandwidth(cmd[4]);
                if _igp_graph.hasIGPLink(cmd[1],cmd[2]): 
                    cost=_igp_graph.getIGPLink(cmd[1],cmd[2]).cost
                    _igp_graph.addIGPLink(cmd[1], cmd[2], cost=cost,
                            bandwidth=bandwidth, compute=False)
                    
                else : 
                    _igp_graph.addIGPLink(cmd[1], cmd[2], bandwidth=bandwidth,
                            compute=False)
            
            #Option unavailable
            #TODO : Fix this. 
            #elif cmd[3] == "delay":
            #    _link_delay_table[lk] = interpretDelay(cmd[4:]);
            else:
                print("unknown link configuration", cmd[3], "in", cmd);
                sys.exit(-1);
        elif cmd[0] == "event":
            if cmd[1] == "announce-prefix": # event announce-prefix x.x.x.x x.x.x.x sec
                _event_Scheduler.add(CEvent(toSystemTime(float(cmd[4])), [cmd[2], cmd[3]], EVENT_ANNOUNCE_PREFIX));
            elif cmd[1] == "withdraw-prefix": # event withdraw-prefix x.x.x.x x.x.x.x sec
                _event_Scheduler.add(CEvent(toSystemTime(float(cmd[4])), [cmd[2], cmd[3]], EVENT_WITHDRAW_PREFIX));
            elif cmd[1] == "link-down": # event link-down x.x.x.x x.x.x.x sec
                _event_Scheduler.add(CEvent(toSystemTime(float(cmd[4])), [cmd[2], cmd[3]], EVENT_LINK_DOWN));
            elif cmd[1] == "link-up": # event link-up x.x.x.x x.x.x.x sec
                _event_Scheduler.add(CEvent(toSystemTime(float(cmd[4])), [cmd[2], cmd[3]], EVENT_LINK_UP));
            elif cmd[1] == "peer-down": # event peer-down x.x.x.x x.x.x.x sec
                _event_Scheduler.add(CEvent(toSystemTime(float(cmd[4])), [cmd[2], cmd[3]], EVENT_PEER_DOWN));
            elif cmd[1] == "peer-up": # event peer-up x.x.x.x x.x.x.x sec
                _event_Scheduler.add(CEvent(toSystemTime(float(cmd[4])), [cmd[2], cmd[3]], EVENT_PEER_UP));
            elif cmd[1] == "traceroute": # event tracerout prefix sec
                _event_Scheduler.add(CEvent(toSystemTime(float(cmd[3])), [cmd[2]], EVENT_TRACEROUTE));
            elif cmd[1] == "inject-prefix" : #event inject-prefix x.x.x.x MRT-path sec
                mrt=""
                for item in cmd[3:-1] :
                    mrt+=item
                    mrt+=" "
                mrt.strip()
                _event_Scheduler.add(CEvent(toSystemTime(float(cmd[-1])), [cmd[2], mrt], EVENT_INJECT_MRT));

            elif cmd[1] == "terminate":
                _event_Scheduler.add(CEvent(toSystemTime(float(cmd[2])), [], EVENT_TERMINATE));
            else:
                print("unknown event", cmd[1], "in", cmd);
                sys.exit(-1);
        elif cmd[0] == "debug":
            if cmd[1] == "show-update-ribs":
                SHOW_UPDATE_RIBS = True;
            elif cmd[1] == "show-receive-events":
                SHOW_RECEIVE_EVENTS = True;
            elif cmd[1] == "show-final-ribs":
                SHOW_FINAL_RIBS = True;
            elif cmd[1] == "show-debug":
                SHOW_DEBUG = True;
            elif cmd[1] == "check-loop":
                CHECK_LOOP = True;
            elif cmd[1] == "show-send-events":
                SHOW_SEND_EVENTS = True;
            else:
                print("unknown debug option", cmd[1], "in", cmd);
                sys.exit(-1);
        elif cmd[0] == "config":
            #if cmd[1] == "number-of-paths":
            #    MAX_PATH_NUMBER = int(cmd[2]);
            # if cmd[1] =="best-bin" :
            #                 BEST_BIN=True
            #                 MAX_PATH_NUMBER=0
            if cmd[1] == "mrai-jitter":
                if cmd[2] == "true":
                    MRAI_JITTER = True;
                else:
                    MRAI_JITTER = False;
            elif cmd[1] == "always-compare-med":
                bgp_always_compare_med = True;
            elif cmd[1] == "keep-virtual-peer-loc-pref" :
                KEEP_VIRTUAL_LOC_PREF = True
            elif cmd[1] == "withdraw-rate-limiting":
                wrate = True;
            elif cmd[1] == "sender-side-loop-detection":
                ssld = True;
            elif cmd[1] == "always-mrai":
                always_mrai = True;
            elif cmd[1] == "randomize-key":
                if cmd[2] == "random":
                    RANDOMIZED_KEY = str(time.time());
                else:
                    RANDOMIZED_KEY = cmd[2];
            elif cmd[1] == "default-link-delay":
                default_link_delay_func = interpretDelay(cmd[2:]);
            elif cmd[1] == "default-process-delay":
                default_process_delay_func = interpretDelay(cmd[2:]);
            elif cmd[1] == "mode" :
                if len(cmd)<3 : 
                    print("Error : No config mode specified", file=stderr) 
                    sys.exit(-1)
                cur_bgp_mode=cmd[2]
            else:
                print("unknown config option", cmd[1], "in", cmd);
                #sys.exit(-1);
        else:
            print("unkown command", cmd[0], "in", cmd);
        #sys.exit(-1);
    #End of config parsing : Configure all routers
    BGPModeAllRouters(cur_bgp_mode)
    
    
    
def loadConfig(config):
    readConfig(config.splitlines())
#
# Parse config from filename and build topology
#
def readConfigFile(filename):
    try:
        f = open(filename, "r");
        readConfig(f)
        f.close();
    except IOError :
        print("Could not open file : ", filename)
        sys.exit(-1)
        
    
        

#
# Initialization of global variables
#
def init():
    global _event_Scheduler
    global _systime
    global _router_list
    global _router_graph #Graph of BGP sessions
    global _igp_graph
    global _link_list
    global _route_map_list
    global num_ebgp_msgs
    _router_list = {};
    _router_graph = {};
    _link_list ={}
    _igp_graph=CIGPNetwork()
    _route_map_list = {};
    _event_Scheduler=COrderedList()
    _systime=0
    num_ebgp_msgs=0
    KEEP_VIRTUAL_LOC_PREF=False

def computeIGP()  :  
     #Run initial Dijkstra on configured link 
    _igp_graph.compute()
    #Check IGP config and peer reachability
    for router in list(_router_list.values()) : 
        if not _igp_graph.hasNode(router.id) : 
                print("Error : Router not configured in the IGP graph (1)",router.id, file=sys.stderr)
        for peer in list(router.peers.keys()) : 
            lk=getRouterLink(router.id,peer)
            if not _igp_graph.hasNode(peer) : 
                print("Error : Router not configured in the IGP graph (2)",peer, file=sys.stderr)
                sys.exit(-1)
            if not _igp_graph.isReachableFrom(router.id, peer) : 
                lk.reach=PEER_UNREACH
                print("Warning : Peer", peer, "unreachable from", \
                    router, file=sys.stderr)
            else : 
                lk.reach=PEER_REACH
            #We don't call peerUp() or peerDown() because there is 
            # no routing information in the system yet.  
 #
# Launch scheduler
#
def run(): 
    global _systime, _event_Scheduler, num_ebgp_msgs
    #print getSystemTimeStr() + ": Starting simulation"
    #TODO: Compute initial allPairsShortestPathLengths dico
    #TODO: Check reachability of all BGP peers - Set unreachable peers down. 
#    print >>sys.stderr, _router_list.keys()

    while len(_event_Scheduler) > 0:
        # print "Queue status is : "
        #         for item in _event_Scheduler : 
        #             print item.time
        #         print "--"
    #Get first event
        cur_event = _event_Scheduler.pop(0);
    #Update current time
        _systime = cur_event.time;
        #print "Changing system time to",_systime
        #cur_event.showEvent() 
        if cur_event.process() == -1: # Terminating event
            break;
    #Checking for loop
    if CHECK_LOOP:
        nodes = list(_infect_nodes.keys());
        for node in nodes:
            removeInfectNode(node, LOOPCHECK_FAILURE);

    if SHOW_FINAL_RIBOUTS_COUNT: 
        print("#Ribout count")
        prefs={}
        for rt in list(_router_list.values()) :
            for peer in list(rt.peers.keys()) : 
                for prefix in list(rt.peers[peer].rib_out.keys()) : 
                    if prefix not in list(prefs.keys()) : 
                        prefs[prefix]=0
                    prefs[prefix]+=1
        for pref in list(prefs.keys()) : 
            print(pref, prefs[pref])


    #Print all ribs
    if SHOW_FINAL_RIBS:
        print(getSystemTimeStr(), ": End of simulation")
        print("-----======$$$$$$$$ FINISH $$$$$$$$$=======------")

        print("<flags> <prefix> <index> <nexthop> <locpref> <med> <aspath> <communities> <from peer>")
        for rt in list(_router_list.values()):
            if not isinstance(rt,CVirtualRouter) :
                print("#Router "+ str(rt))
                rt.showAllRib();
    
                    
                    
                
#
# Launch simulation from string config
#
def runConfig(config):
    init()
    loadConfig(config)
    computeIGP()
    run()

#
# Launch simulation from file
# 
def runConfigFile(filename):
    init()
    readConfigFile(filename)
    computeIGP()
    run()

def getRevisionNumber() :
    svninfo=subprocess.Popen(["svn", "info", inspect.getsourcefile(run)], stdout=subprocess.PIPE).communicate()[0]
    for line in svninfo.split('\n') :
        if line=="" :
            continue
        if line.split()[0]=="Revision:" :
            version= line.split()[-1]
            version.strip('\'')
            return version

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: SimBGP.py configfile\n");
        sys.exit(-1);
#Read config
    runConfigFile(sys.argv[1])


# TODO : Add-Paths - Is it possible to have two paths with same nexthop? 
