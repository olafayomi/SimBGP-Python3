#!/usr/bin/env python


# Copyright (c) 2020, WAND Network Research Group
#                     Department of Computer Science
#                     University of Waikato
#                     Hamilton
#                     New Zealand
#
# Author Dimeji Fayomi (oof1@students.waikato.ac.nz)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330,
# Boston,  MA 02111-1307  USA


import tempfile
import os
import sys
import argparse
from pygraphml import GraphMLParser
from pygraphml import Graph
import xml
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import jinja2
from jinja2 import Environment
from jinja2 import FileSystemLoader
from beeprint import pp

template_file = "SimBGPConfTemplate.j2"
config_directory = "_SimBGPConfigs"


def readGraphMLFile(graphMLFile):
    graphMLParser = GraphMLParser()
    try:
        graphNet = graphMLParser.parse(graphMLFile)
    except xml.parsers.expat.ExpatError as e:
        print("%s is not a GraphML file\n" % graphMLFile)
        print("Error message is %s" % str(e))
        sys.exit(-1)
    return graphNet


def readFileWithNx(gFile, file_type):
    if file_type == 'gml':
        try:
            graphNet = nx.readwrite.gml.read_gml(gFile, label='id')
        except nx.exception.NetworkXError as e:
            print("%s is not a GML file\n" % gFile)
            print(str(e))
            sys.exit(-1)

    if file_type == 'GraphML':
        try:
            graphNet = nx.readwrite.graphml.read_graphml(gFile)
        except nx.exception.NetworkXError as e:
            print("%s is not a GraphML file\n" % gFile)
            print(str(e))
            sys.exit(-1)
    return graphNet


def showGraph(graphNet):
    try:
        graphNet.show(show_label=False)
    except AttributeError as e:
        print("graphNet was not parsed from GraphML file\n")
        plt.subplot(111)
        nx.draw(graphNet, with_labels=True, font_weight='bold')
        plt.show()


def setupJinjaEnv(template_file, config_directory):
    try:
        env = Environment(loader=FileSystemLoader(searchpath="."))
        template = env.get_template(template_file)
    except jinja2.exceptions.TemplateNotFound as e:
        print("%s not found!!!\n" % e.args)
        sys.exit(-1)
    if not os.path.exists(config_directory):
        os.mkdir(config_directory)
    return template, env


def getNodesgraphMLParser(graphNet):
    ''' Get nodes from graph of GraphMLParser '''
    nodeDict = {}
    #print("In getNodesgraphML:\n")
    for node in graphNet.nodes():
        #print("Node is type %s\n" %type(node))
        #print("Node is %s\n" %node)
        nodeDict[node.id] = '1'
        #pp(node)
    #print("\n\n\n")0k
    return nodeDict


def getNodes(graphNet):
    nodeDict = {}
    #print("In getNodesGML: \n")
    for node in list(graphNet.nodes):
        #print("node is type %s\n" %type(node))
        #print("Node:  %s \n" % node)
        if graphNet.nodes[node]['asn']:
            #print("we have ASN/Domain Number\n")
            nodeDict[node] = graphNet.nodes[node]['asn']
        else:
            #print("we don't ASN/Domain Number\n")
            nodeDict[node] = '1'
        #pp(node)
    #print("\n\n\n")
    return nodeDict


def getEdgesgraphMLParser(graphNet):
    ''' Get edges from graph of GraphMLParser '''
    edges = []
    for edge in graphNet.edges():
        edge_t = ()
        edge_t = edge_t + (edge.node1.id,)
        edge_t = edge_t + (edge.node2.id,)
        edge_t = edge_t + ('100',)
        edges.append(edge_t)
    return edges


def getEdges(graphNet):
    edges = []
    for edge in list(graphNet.edges):
        edge_t = ()
        edge_t = edge_t + (edge[0],)
        edge_t = edge_t + (edge[1],)
        if graphNet.edges[edge]['LinkSpeedRaw']:
            cost = float(graphNet.edges[edge]['LinkSpeedRaw'])/(10**9)
            edge_t = edge_t + (str(cost))
        else:
            edge_t = edge_t + ('100',)
        edges.append(edge_t)
    return edges


def getAdj(graphNet):
    ''' Get adjacencies for each node '''
    adj_domain = {}
    for node, adj_list in graphNet.adjacency():
        ## Find the domain for each neighbour in adj_list
        adj_domain_list = []
        for neigh in adj_list:
            ## for now assume all in the same domain
            if graphNet.nodes[neigh]['asn']:
                adj_domain_list.append((neigh, graphNet.nodes[neigh]['asn']))
            else:
                adj_domain_list.append((neigh, '1'))
        adj_domain[node] = adj_domain_list 
    #print("Peering is %s\n" %adj_domain)
    return adj_domain


def printNodeDetails(graphNet):
    ''' See the attributes of a node '''
    #attr = nx.get_node_attributes(graphNet, 'asn')
    #for node in graphNet.nodes:
    print("Node attributes are: %s\n" %graphNet.nodes.data())

def printEdgeDetails(graphNet):
    ''' See the attributes of an edge '''
    print("Edge attributes are: %s\n" % graphNet.edges.data())

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
            description='Convert GraphML and GML files to SimBGP Configfile',
            usage='%(prog)s [options]')
    argparser.add_argument('-G', dest='graphml', help='Convert GraphML file',
                        default=None)
    argparser.add_argument('-g', dest='gml', help='Convert GML file',
            default=None)
    argparser.add_argument('-C', dest='c_bgp', help='Convert C-BGP config file',
            default=None)
    args = argparser.parse_args()

    if args.graphml is not None:
        file_type = 'GraphML'
        graphNet = readFileWithNx(args.graphml, file_type)
        #nodes = getNodesGML(graphNet)
        #edges = getEdgesGML(graphNet)
        #nodes = getNodesgraphML(graphNet)
        #edges = getEdgesgraphML(graphNet)
    elif args.gml is not None:
        file_type = 'gml'
        graphNet = readFileWithNx(args.gml, file_type)
    else:
        # Process C-BGP
        pass
        
    nodes = getNodes(graphNet)
    #print("Nodes: %s\n" % nodes)
    edges = getEdges(graphNet)
    neighbors = getAdj(graphNet)
    #printNodeDetails(graphNet)   
    printEdgeDetails(graphNet) 

    #for node, domain in nodes.items():
    #    print("Node: %s Domain: %s\n" %(node, domain))
    j2Temp, j2Env = setupJinjaEnv(template_file, config_directory)
    print("Config File:\n")
    config = j2Temp.render(graph_dict=nodes, edges=edges, neighbors=neighbors)
    print(config)
    #for node, domain in nodes.items():
    #    print("NODE: %s  ASN: %s\n" % (node, domain))

    #showGraph(graphNet)
