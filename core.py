import os
import re

from ciscoconfparse import CiscoConfParse
import numpy as np
import ipaddress
import networkx as nx
import matplotlib.pyplot as plt

############################
# SPoF Identification Demo #
############################

# This script demonstrates using NetworkX and configuration manipulation to identify single points of failure at the IP layer 
# We extend the same principle to OSPF 

# Author : Samuel Thomas

# Note - we use ciscoconfparse to simplify feeding configuration. There are better way to do this in practice, i.e. directly from the device.

def convert_ip_binary(ip_add):
    return ''.join([bin(int(x)+256)[3:] for x in ip_add.split('.')])

def load_interfaces():
    """
    Generate single table containg all interfaces, subnetmask and device they are configured on.
    """

    devices_intfs = []

    for filename in os.listdir(os.getcwd()+ "/configurations"):
        parse = CiscoConfParse(config=f'configurations/{filename}', ignore_blank_lines=True)

        intfs = parse.find_objects_w_parents(r'^interface',r'^ ip add')
        device = parse.re_match_iter_typed(r'^hostname\s+(\S+)', default='')


        for intfobj in intfs:
            ip_add_cap_pattern = '^ip address (\d+\.\d+\.\d+\.\d+) (\d+\.\d+\.\d+\.\d+)$'
            ip_add_intf = re.search(ip_add_cap_pattern, intfobj.text.strip())

            intf_add = ip_add_intf.group(1)
            intf_subnetmask = ip_add_intf.group(2)
            intf_add_binary = convert_ip_binary(intf_add)
            intf_subnetmask_binary = convert_ip_binary(intf_subnetmask)
            
            devices_intfs.append([device,intf_add,intf_subnetmask,intf_add_binary,intf_subnetmask_binary])

        devices_intfs_matrix = np.array(devices_intfs)

    return devices_intfs_matrix

def convert_interfaces_adj_list(parsed_intfs):
    """
    Convert interface table to an edge list
    """

    nodes = set(parsed_intfs[:, 0])
    nodes = {k:[] for k in nodes} #zero node list with lists

    #Create list of networks and their node
    node_network_map = []
    for intf in parsed_intfs:
        node_name = intf[0]
        int_addr = intf[1]
        intf_mask = intf[2]
        intf_network = ipaddress.IPv4Network(f'{int_addr}/{intf_mask}', strict=False)
        node_network_map.append([node_name, intf_network])

    for intf in parsed_intfs:
        intf_addr = ipaddress.ip_address(intf[1])

        for intf_node_network in node_network_map:
            if (intf_addr in intf_node_network[1]) and (intf_node_network[0] != intf[0]):
                nodes[intf_node_network[0]].append(intf[0])
    
    return nodes
        

def convert_adj_list_networkx(adj_list):
    """
    Convert adjacency list to networkx graph 
    """
    G = nx.from_dict_of_lists(adj_list)

    return G

def identify_spofs(net_graph):
    """
    Identify single points of failure
    """

    spof_nodes = []
    for node in net_graph.nodes:
        demo_graph = net_graph.copy()
        demo_graph.remove_node(node)
        if not nx.is_connected(demo_graph):
            spof_nodes.append(node)
    
    return spof_nodes

parsed_intfs = load_interfaces()
nodes_adj = convert_interfaces_adj_list(parsed_intfs)
net_graph = convert_adj_list_networkx(nodes_adj)
spof_nodes = identify_spofs(net_graph)
print(spof_nodes)