# utils
# Utilities for the various python scripts
#
# Author:  Benjamin Bengfort <benjamin@bengfort.com>
# Created: Tue Mar 27 06:54:05 2018 -0400
#
# ID: utils.py [] benjamin@bengfort.com $

"""
Utilities for the various python scripts
"""

##########################################################################
## Imports
##########################################################################

import os
import json

from collections import defaultdict


##########################################################################
## Environment Helpers
##########################################################################

def load_hosts(path):
    with open(path, 'r') as f:
        return json.load(f)


def load_host_regions(hosts):
    if isinstance(hosts, basestring):
        hosts = load_hosts(hosts)

    # Returns a dict of regions to hostname
    locations = defaultdict(list)
    for host in hosts:
        locations[host_region(host)].append(host)
    return locations


def host_region(name):
    # Get the region from a host name
    return " ".join(name.split("-")[1:-1])


def host_id(name):
    # Get the id from a host name
    return int(name.split("-")[-1])


def parse_bool(val):
    if isinstance(val, basestring):
        val = val.lower().strip()
        if val in {'yes', 'y', 'true', 't', '1'}:
            return True
        if val in {'no', 'n', 'false', 'f', '0'}:
            return False
    return bool(val)


##########################################################################
##  Path Helpers
##########################################################################

def add_suffix(path, suffix=None):
    if suffix:
        base, ext = os.path.splitext(path)
        path = "{}-{}{}".format(base, suffix, ext)
    return path


def unique_name(path, start=0, maxtries=1000):
    for idx in range(start+1, start+maxtries):
        ipath = add_suffix(path, idx)
        if not os.path.exists(ipath):
            return ipath

    raise ValueError(
        "could not get a unique path after {} tries".format(maxtries)
    )


##########################################################################
## Stats Helpers
##########################################################################

def mean(vals):
    return sum([float(v) for v in vals]) / float(len(vals))
