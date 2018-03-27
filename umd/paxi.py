#!/usr/bin/env python
# -*- coding: utf-8 -*-
# paxi
# Helper scripts for managing paxi environment and experiments.
#
# Author:   Benjamin Bengfort <benjamin@bengfort.com>
# Created:  Tue Mar 27 06:38:19 2018 -0400
#
# ID: paxi.py [] benjamin@bengfort.com $

"""
Helper scripts for managing paxi environment and experiments.
"""

##########################################################################
## Imports
##########################################################################

import os
import json
import argparse

from utils import *
from tabulate import tabulate
from operator import itemgetter
from fabric.colors import red, green, cyan, magenta


BASE = os.path.dirname(__file__)
CONFIGS = os.path.join(BASE, "configs")
HOSTS = os.path.join(BASE, "hosts.json")
DEFAULT_CONFIG = os.path.join(BASE, "config.json")


##########################################################################
## Commands
##########################################################################

def config(args):
    """
    Makes a config from a hosts.json file and a default config
    """
    with open(args.config, 'r') as f:
        config = json.load(f)

    with open(args.hosts, 'r') as f:
        hosts = json.load(f)

    regions = load_host_regions(hosts)
    region_ids = list(sorted(regions.keys()))

    if not os.path.exists(args.outdir):
        os.makedirs(args.outdir)

    for n in args.size:
        for c in args.conflict:
            path = os.path.join(args.outdir, "config-{}-{}.json".format(n,c))
            config["address"], config["http_address"] = {}, {}
            config["benchmark"]["Conflicts"] = c

            for i in range(n):
                region = region_ids[i%len(region_ids)]

                # TODO: better round robin here
                host = regions[region][0]
                addr = hosts[host]["hostname"]  + ":3264"
                http = "http://{}:3265".format(hosts[host]["hostname"])

                rid = "{}.{}".format(region_ids.index(region)+1, host_id(host))
                config["address"][rid] = addr
                config["http_address"][rid] = http

            with open(path, 'w') as f:
                json.dump(config, f, indent=2)


def tput(args):
    """
    Reads a latency file and computes the throughput
    """

    def _tput(path):
        host = os.path.basename(os.path.dirname(path))
        total, count = 0.0, 0.0

        with open(path) as f:
            for val in f:
                if not val.strip(): continue
                total += float(val) # val is milliseconds
                count += 1

        return host, count/(total/1000.0)

    results = [
        dict(zip(("host", "ops/sec"), _tput(path))) for path in args.latency
    ]
    results.sort(key=itemgetter("ops/sec"), reverse=True)
    results.append({
        "host": cyan("average"), "ops/sec": cyan(mean([r["ops/sec"] for r in results]))
    })

    print(tabulate(results, tablefmt="simple", headers="keys"))




if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=cyan("helpers to manage paxi environment and experiments"),
        epilog=magenta("beta version and subject to change")
    )

    subparsers = parser.add_subparsers()

    helpers = {
        "config": {
            "help": "make config from hosts.json file",
            "func": config,
            "args": {
                ("-C", "--clean"): {
                    "action": "store_true",
                    "help": "remove all prior configs from the directory"
                },
                ("--config"): {
                    "default": DEFAULT_CONFIG, "metavar": "JSON",
                    "help": "base config.json to build config from",
                },
                ("-H", "--hosts"): {
                    "default": HOSTS, "metavar": "JSON",
                    "help": "hosts.json to create replicas from",
                },
                ("-o", "--outdir"): {
                    "default": CONFIGS, "metavar": "DIR",
                    "help": "directory to write configs to",
                },
                "--conflict": {
                    "default": [50], "type": int, "nargs": "*", "metavar": "%",
                    "help": "conflict percentages"
                },
                "size": {
                    "type": int, "metavar": "N", "nargs": "*", "default": [3],
                    "help": "number of replicas in the quorum",
                },
            },
        },
        "tput": {
            "help": "compute throughput from latency measurements",
            "func": tput,
            "args": {
                "latency": {
                    "nargs": "*",
                    "help": "latency file output by client benchmark",
                },
            },
        },
    }

    for helper, hargs in helpers.items():
        sp = subparsers.add_parser(helper, help=hargs["help"])
        for pargs, kwargs in hargs["args"].items():
            if isinstance(pargs, basestring):
                pargs = (pargs,)
            sp.add_argument(*pargs, **kwargs)
        sp.set_defaults(func=hargs["func"])


    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as e:
        parser.error(red(str(e)))
