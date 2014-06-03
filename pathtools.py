import resource
import sys
import collections
import itertools
import random
import operator
import gc
import os

import hetnet


cache_gets = 0
cache_sets = 0
i_memcheck = 0
max_MB = 60 * 1024
prune_fraction = 0.2
memcheck_interval = 1000
cache = collections.OrderedDict()



# Set memory_usage to a function that returns memory usage in MB.
# Python resource module returns max session memory rather than current usage.

try:
    import psutil

    def memory_usage_psutil():
        """
        May not be able to install package in pypy
        """
        # return the memory usage in MB
        process = psutil.Process(os.getpid())
        mem = process.get_memory_info()[0] / float(2 ** 20)
        return mem

    memory_usage = memory_usage_psutil

except ImportError:
    import subprocess

    def memory_usage_ps():
        out = subprocess.Popen(['ps', 'v', '-p', str(os.getpid())],
            stdout=subprocess.PIPE).communicate()[0].split(b'\n')
        vsz_index = out[0].split().index(b'RSS')
        mem = float(out[1].split()[vsz_index]) / 1024
        return mem

    memory_usage = memory_usage_ps


def cache_get(key):
    global cache_gets
    cache_gets += 1
    value = cache.pop(key)
    cache[key] = value
    return value

def cache_set(key, value):
    cache[key] = value
    global cache_sets
    global i_memcheck
    cache_sets += 1
    if i_memcheck < memcheck_interval:
        i_memcheck += 1
        return
    i_memcheck = 0
    if memory_usage() > max_MB:
        n_remove = int(len(cache) * prune_fraction)
        remove_keys = tuple(itertools.islice(cache.iterkeys(), n_remove))
        for key in remove_keys:
            del cache[key]
        gc.collect()
        memory = memory_usage()
        hitrate = cache_hit_rate()
        print_str = 'Deleted {} cached items. Using {:.1f}GB for {:.2f} item cache. Hitrate {:.5f}'
        print(print_str.format(n_remove, memory / 1024.0, len(cache), hitrate))


def cache_hit_rate():
    """
    Returns the cache hit rate, which is the percent of lookups
    that succeed (where the result is cached).
    """
    return float(cache_gets) / (cache_sets + cache_gets)


def crdfs_paths_from(node, metapath):
    """
    Cached recursive depth-first-search: computes all paths from
    source_node of kind metapath. Paths with duplicate nodes are excluded.
    Returns a tuple of tuple paths where the elements of the tuple path are
    hetnet.Edge() objects. Refer to the cache_get and cache_set functions for
    the specifics of the caching algorithm.
    """
    if not metapath:
        return tuple(),
    args = node, metapath
    if args in cache:
        return cache_get(args)
    paths = list()
    metapath_tail = metapath.sub
    for edge in node.edges[metapath[0]]:
        for tail in crdfs_paths_from(edge.target, metapath_tail):
            if node in (e.target for e in tail):
                continue
            paths.append((edge, ) + tail)
    paths = tuple(paths)
    cache_set(args, paths)
    return paths

def filtered_crdfs_paths_from(node, metapath, exclude_masked=False,
                              exclude_nodes=set(), exclude_edges=set()):
    paths = list()
    for edge_list in crdfs_paths_from(node, metapath):
        if exclude_edges and exclude_edges & set(edge_list):
            continue
        path = hetnet.Path(edge_list)
        if exclude_masked and path.is_masked():
            continue
        if exclude_nodes and exclude_nodes & set(path.get_nodes()):
            continue
        paths.append(path)
    return tuple(paths)

def crdfs_paths_fromto(source_node, target_node, metapath, exclude_nodes=set(), exclude_edges=set()):
    """
    Cached recursive depth-first-search: computes all paths from
    source_node to target_node of kind metapath. Paths with duplicate
    nodes, with nodes in exclude_nodes, or edges in exclude_edges are excluded.
    Returns of tuple of hetnet.Path() objects.
    """
    paths = list()
    for edge_list in crdfs_paths_from(source_node, metapath):
        if edge_list[-1].target != target_node:
            continue
        if exclude_edges and exclude_edges & set(edge_list):
            continue
        path = hetnet.Path(edge_list)
        if exclude_nodes and exclude_nodes & set(path.get_nodes()):
            continue
        paths.append(path)
    return tuple(paths)



def rdfs_paths_from(node, metapath):
    """
    CAUTION: SLOW NOT CACHED
    Recursive depth-first-search to find all paths corresponding to metapath
    and starting at node. Paths with duplicate nodes are excluded.
    Returns a tuple of paths (as tuples of hetnet.Edge() objects
    rather than a hetnet.Path() objects).
    """
    raise Exception # We do not want to be using the non-cached method
    if not metapath:
        return (),
    paths = list()
    metapath_tail = metapath.sub
    for edge in node.edges[metapath[0]]:
        for tail in rdfs_paths_from(edge.target, metapath_tail):
            if node in (e.target for e in tail):
                continue
            paths.append((edge, ) + tail)
    return tuple(paths)

def rdfs_paths_fromto(source_node, target_node, metapath, exclude_masked=False,
                      exclude_nodes=set(), exclude_edges=set()):
    """
    CAUTION: SLOW NOT CACHED
    Recursive depth-first-search to find all paths corresponding to metapath,
    originating on source_node and terminating on target_node. Paths with
    duplicate nodes ARE excluded currently. Returns a generator of
    hetnet.Path() objects.
    """
    raise Exception # We do not want to be using the non-cached method
    paths = list()
    for edge_list in rdfs_paths_from(source_node, metapath):
        if edge_list[-1].target != target_node:
            continue
        if exclude_edges and exclude_edges & set(edge_list):
            continue
        path = hetnet.Path(edge_list)
        if exclude_masked and path.is_masked():
            continue
        if exclude_nodes and exclude_nodes & set(path.get_nodes()):
            continue
        paths.append(path)
    return tuple(paths)

def path_based_features(source_node, target_node, metapath, exclude_masked=False,
                        exclude_nodes=set(), exclude_edges=set()):
    """
    Return a dictionary where items store:
    -- paths between the source and target node
    -- paths from the source
    -- paths from the target
    where paths follow the provided metapath.
    """
    paths_s = filtered_crdfs_paths_from(source_node, metapath, exclude_masked, exclude_nodes, exclude_edges)
    paths_t = filtered_crdfs_paths_from(target_node, metapath.inverse, exclude_masked, exclude_nodes, exclude_edges)
    paths_st = tuple(path for path in paths_s if path[-1].target == target_node)
    return {'source_target': paths_st, 'from_source': paths_s, 'from_target': paths_t}


def path_degree_product(path, damping_exponent, exclude_edges=set(), exclude_masked=True):
    """ """
    degrees = list()
    for edge in path:
        source_edges = edge.source.get_edges(edge.metaedge, exclude_masked)
        target_edges = edge.target.get_edges(edge.metaedge.inverse, exclude_masked)
        if exclude_edges:
            source_edges -= exclude_edges
            target_edges -= exclude_edges
        source_degree = len(source_edges)
        target_degree = len(target_edges)
        degrees.append(source_degree)
        degrees.append(target_degree)

    damped_degrees = [degree ** damping_exponent for degree in degrees]
    degree_product = reduce(operator.mul, damped_degrees)
    return degree_product


def degree_weighted_path_count(paths, damping_exponent, exclude_edges=set(), exclude_masked=True):
    degree_products = (path_degree_product(path, damping_exponent, exclude_edges=exclude_edges, exclude_masked=exclude_masked) for path in paths)
    path_weights = (1.0 / degree_product for degree_product in degree_products)
    dwpc = sum(path_weights)
    return dwpc

def normalized_path_count(paths_s, paths_t):
    if len(paths_t) == 0:
        paths = list()
    else:
        target = paths_t[0].source()
        paths = tuple(path for path in paths_s if path.target() == target)
    denom = len(paths_s) + len(paths_t)
    if denom:
        return 2.0 * len(paths) / denom
    else:
        return None
