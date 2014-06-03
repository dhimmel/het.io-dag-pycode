import argparse
import collections
import itertools
import os
import gzip
import csv
import time

import hetio
import pathtools
import readwrite

def compute_features(graph, part_rows, feature_path, dwpc_exponent):

    print('Initial Memory Usage: {:.1f}. Max Memory Usage: {:.1f}'.format(
        hetnet.pathtools.memory_usage() / 1024.0, hetnet.pathtools.max_MB / 1024.0))

    # Define Metapaths
    metagraph = graph.metagraph
    metapaths = metagraph.extract_metapaths('gene', 'disease', max_length=3)
    metapath_GaD = metapaths.pop(0)
    metapath_DaG = metapath_GaD.inverse

    # open output_file
    feature_file = gzip.open(feature_path, 'w')

    total_edges = len(part_rows)
    writer = None
    for i, part_row in enumerate(part_rows):
        time_start = time.clock()

        disease_code = part_row['disease_code']
        gene_symbol = part_row['gene_symbol']
        source = graph.node_dict[gene_symbol]
        target = graph.node_dict[disease_code]

        edge = graph.edge_dict.get((source.id_, target.id_, 'association', 'both'))
        exclude_edges = {edge, edge.inverse} if edge else set()

        features = collections.OrderedDict()
        features['gene_code'] = part_row['gene_code']
        features['gene_symbol'] = gene_symbol
        features['disease_code'] = disease_code
        features['disease_name'] = part_row['disease_name']
        features['status'] = part_row['status']
        features['status_int'] = part_row['status_int']
        features['percentile'] = part_row['percentile']
        features['part'] = part_row['part']

        features['PC_s|G-a-D'] = len(hetnet.pathtools.filtered_crdfs_paths_from(
            source, metapath_GaD, exclude_edges=exclude_edges))
        features['PC_t|G-a-D'] = len(hetnet.pathtools.filtered_crdfs_paths_from(
            target, metapath_DaG, exclude_edges=exclude_edges))

        for metapath in metapaths:
            feature_name = 'DWPC_{}|{}'.format(dwpc_exponent, metapath)

            paths = hetnet.pathtools.crdfs_paths_fromto(target, source, metapath.inverse,
                                                        exclude_edges=exclude_edges)
            dwpc = hetnet.pathtools.degree_weighted_path_count(paths,
                damping_exponent=dwpc_exponent, exclude_edges=exclude_edges)
            features[feature_name] = dwpc
        if writer is None:
            print 'Initializing writer'
            fieldnames = features.keys()
            writer = csv.DictWriter(feature_file, fieldnames=fieldnames, delimiter='\t')
            writer.writeheader()
        writer.writerow(features)

        time_end = time.clock()
        percent = 100.0 * i / total_edges
        print 'cache size {} | memory {:.3f} | seconds {:.3f}'.format(
            len(hetnet.pathtools.cache), hetnet.pathtools.memory_usage() / 1024.0, time_end - time_start)
        print '{:.1f}% -  {:10}{}'.format(percent, gene_symbol, part_row['disease_name'])

    feature_file.close()

def read_graph(network_dir):
    path = os.path.join(network_dir, 'graph.pkl.gz')
    # Load graph
    print 'loading graph'
    graph = readwrite.read_pickle(path)
    print 'graph loaded'
    return graph

def read_part(partition_path):
    partition_file = gzip.open(partition_path)
    part_rows = list(csv.DictReader(partition_file, delimiter='\t'))
    for row in part_rows:
        row['status_int'] = int(row['status_int'])
    partition_file.close()
    return part_rows


if __name__ == '__main__':
    # Parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--network-dir', type=os.path.expanduser, default=
        'networks/')
    parser.add_argument('--partition-path', type=os.path.expanduser)
    parser.add_argument('--feature-path', type=os.path.expanduser)
    parser.add_argument('--dwpc-exponent', default=0.4, type=float)
    parser.add_argument('--max-gb', default=60.0, type=float)
    args = parser.parse_args()

    hetnet.pathtools.max_MB = args.max_gb * 1024.0

    # filesystem
    network_dir = args.network_dir
    path_head, path_tail = os.path.split(args.feature_path)
    if not os.path.isdir(path_head):
        os.mkdir(path_head)

    # Read Objects
    graph = read_graph(network_dir)
    part_rows = read_part(args.partition_path)

    # Compute features
    compute_features(graph, part_rows, args.feature_path, args.dwpc_exponent)
