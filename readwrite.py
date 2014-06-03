import collections
import cPickle as pickle
import gzip
import json
import os
import re
import operator
import csv
import random

import yaml

import hetio

def open_ext(path, *args, **kwargs):
    open_fxn = gzip.open if path.endswith('.gz') else open
    return open_fxn(path, *args, **kwargs)

def write_pickle(graph, path):
    writable = writable_from_graph(graph)
    write_file = open_ext(path, 'wb')
    pickle.dump(writable, write_file)
    write_file.close()
    
def read_pickle(path):
    read_file = open_ext(path)
    writable = pickle.load(read_file)
    read_file.close()
    return graph_from_writable(writable)


def read_yaml(path):
    """ """
    read_file = open_ext(path)
    try:
        loader = yaml.CSafeLoader
    except AttributeError:
        loader = yaml.SafeLoader
    writable = yaml.load(read_file, Loader=loader)
    read_file.close()
    
    return graph_from_writable(writable)

def write_json(graph, path):
    """ """
    writable = writable_from_graph(graph, False)
    write_file = open_ext(path, 'w')
    json.dump(writable, write_file, indent=2)
    write_file.close()

def write_yaml(graph, path):
    """ """
    writable = writable_from_graph(graph, False)
    write_file = open_ext(path, 'w')
    try:
        dumper = yaml.CSafeDumper
    except AttributeError:
        dumper = yaml.SafeDumper
    yaml.dump(writable, write_file, Dumper=dumper)
    write_file.close()

def graph_from_writable(writable):
    """ """
    metaedge_tuples = writable['metaedge_tuples']
    metaedge_tuples = map(tuple, metaedge_tuples)
    metagraph = hetnet.MetaGraph.from_edge_tuples(metaedge_tuples)
    graph = hetnet.Graph(metagraph)

    nodes = writable['nodes']
    for node in nodes:
        graph.add_node(**node)

    edges = writable['edges']
    for edge in edges:
        graph.add_edge(**edge)
    
    return graph

def write_gml(graph, path):
    """ """
    writable = writable_from_graph(graph, int_id=True)

    re_pattern = re.compile(r"[^0-9a-zA-Z ]+")
    gml_nodes = list()
    for node in writable['nodes']:
        gml_node = collections.OrderedDict()
        gml_node['id'] = node['int_id']
        gml_node['label'] = node['id_']
        gml_node['kind'] = node['kind']
        name = node['data'].get('name', '')
        name = re.sub(re_pattern, '_', name)
        gml_node['name'] = name
        gml_nodes.append(gml_node)

    gml_edges = list()
    for edge in writable['edges']:
        gml_edge = collections.OrderedDict()
        gml_edge['source'] = edge['source_int']
        gml_edge['target'] = edge['target_int']
        gml_edge['kind'] = edge['kind']
        gml_edge['direction'] = edge['direction']
        gml_edges.append(gml_edge)

    with open(path, 'w') as write_file:
        gml_writer = GMLWriter(write_file)
        gml_writer.write_graph(gml_nodes, gml_edges)

def write_sif(graph, path, max_edges=None, seed=0):
    if max_edges is not None:
        assert isinstance(max_edges, int)
    sif_file = gzip.open(path, 'wb') if path.endswith('.gz') else open(path, 'w')
    metaedge_to_edges = graph.get_metaedge_to_edges(exclude_inverts=True)
    random.seed(seed)
    for metaedge, edges in metaedge_to_edges.iteritems():
        if max_edges is not None and len(edges) > max_edges:
            edges = random.sample(edges, k=max_edges)
        for i, edge in enumerate(edges):
            if i:
                sif_file.write('\n')
            sif_tuple = edge.source, edge.metaedge.kind, edge.target
            line = '{} {} {}'.format(*sif_tuple)
            sif_file.write(line)
    sif_file.close()

def write_nodetable(graph, path):
    rows = list()
    for node in graph.node_dict.itervalues():
        row = collections.OrderedDict()
        row['id'] = node.id_
        row['name'] = node.data.get('name', '')
        row['kind'] = node.metanode.id_
        rows.append(row)
    rows.sort(key=operator.itemgetter('kind', 'id'))
    fieldnames = ['id', 'name', 'kind']
    write_file = open(path, 'w')
    writer = csv.DictWriter(write_file, fieldnames=fieldnames, delimiter='\t')
    writer.writeheader()
    writer.writerows(rows)
    write_file.close()


def writable_from_graph(graph, ordered=True, int_id=False):
    """ """
    metanode_kinds = graph.metagraph.node_dict.keys()
    
    metaedge_tuples = [edge.get_id() for edge in
                       graph.metagraph.get_edges(exclude_inverts=True)]
    
    nodes = list()
    for i, node in enumerate(graph.node_dict.itervalues()):
        node_as_dict = collections.OrderedDict() if ordered else dict()
        node_as_dict['id_'] = node.id_
        node_as_dict['kind'] = node.metanode.id_
        node_as_dict['data'] = node.data
        if int_id:
            node_as_dict['int_id'] = i
            node.int_id = i
        nodes.append(node_as_dict)

    edges = list()
    for edge in graph.get_edges(exclude_inverts=True):
        edge_id_keys = ('source_id', 'target_id', 'kind', 'direction')
        edge_id = edge.get_id()
        edge_items = zip(edge_id_keys, edge_id)
        edge_as_dict = collections.OrderedDict(edge_items) if ordered else dict(edge_items)
        edge_as_dict['data'] = edge.data
        if int_id:
            edge_as_dict['source_int'] = edge.source.int_id
            edge_as_dict['target_int'] = edge.target.int_id

        edges.append(edge_as_dict)

    writable = collections.OrderedDict() if ordered else dict()
    writable['metanode_kinds'] = metanode_kinds
    writable['metaedge_tuples'] = metaedge_tuples
    writable['nodes'] = nodes
    writable['edges'] = edges

    return writable


class GMLWriter(object):
    """
    http://www.fim.uni-passau.de/fileadmin/files/lehrstuhl/brandenburg/projekte/gml/gml-technical-report.pdf
    """
    
    def __init__(self, write_file):
        """GML writing and reading class"""
        self.gml_file = write_file  # file to write GML to
        self.write_indent = '\t'
        self.write_level = 0  # indentation level while writing
        
    def write_graph(self, nodes, edges):
        """nodes and edges are lists of dictionaries."""
        
        with GMLBlock(self, 'graph'):
            
            for node in nodes:
                with GMLBlock(self, 'node'):
                    self.write_properties(node)
                    
            for edge in edges:
                with GMLBlock(self, 'edge'):
                    self.write_properties(edge)
    

    def write(self, s):
        """Write string s to self.gml_file prepending the proper indentation."""
        indent = self.write_indent * self.write_level
        self.gml_file.write(indent + s)

    def write_properties(self, dictionary):
        for key, value in dictionary.items():
            self.write_property(key, value)

    def write_property(self, key, value, printing=False):
        """ """
        if not re.match(r'[A-Za-z]\w*\Z', key):
            if printing: print 'Invalid Key:', key
            return
        if isinstance(value, (int, long, float)):
            value = str(value)
        
        elif isinstance(value, basestring):
            #value = value.replace('"', "'")
            #value = value.replace('&', "AMPERSAND")
            if re.search(r'[&"\\]', value):
                if printing: print 'Invalid Value:', value
                return
            value = '"{}"'.format(value)
        
        elif isinstance(value, (list, tuple, set)):
            with GMLBlock(self, key):
                for elem in value:
                    self.write_property('list', elem)
            return
        
        elif isinstance(value, dict):
            with GMLBlock(self, key):
                self.write_properties(value)
            return
        
        else:
            print 'GML formating not specified for', type(value)
            return
        line = '{} {}\n'.format(key, value)
        if len(line) > 254:
            if printing: print 'Line too long:', line
            return
        self.write(line)

class GMLBlock(object):
    
    def __init__(self, gml, key):
        self.gml = gml
        self.key = key
    
    def __enter__(self):
        self.gml.write('%s [\n' % self.key)
        self.gml.write_level += 1
    
    def __exit__(self, *args, **kwargs):
        self.gml.write_level -= 1
        self.gml.write(']\n')
