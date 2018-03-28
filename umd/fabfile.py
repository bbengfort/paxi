# -*- coding: utf-8 -*-
# fabfile
# Fabric command definitions for running ePaxos geo replicated experiments.
#
# Author:   Benjamin Bengfort <benjamin@bengfort.com>
# Created:  Mon Feb 26 09:02:22 2018 -0500
#
# ID: fabfile.py [] benjamin@bengfort.com $

"""
Fabric command definitions for running ePaxos geo replicated experiments.
"""

##########################################################################
## Imports
##########################################################################

import os
import json
import time

from utils import *
from tabulate import tabulate
from dotenv import load_dotenv, find_dotenv

from fabric.contrib import files
from fabric.colors import red, green, cyan
from fabric.api import env, run, cd, get, put, hide
from fabric.api import parallel, task, runs_once, execute, local


##########################################################################
## Environment
##########################################################################

## Load the environment
load_dotenv(find_dotenv())

## Local paths
fixtures = os.path.dirname(__file__)
hostinfo = os.path.join(fixtures, "hosts.json")

## Remote Paths
workspace = "/data/paxi"
repo = "~/workspace/go/src/github.com/ailidani/paxi"

## Load Hosts
hosts = load_hosts(hostinfo)
addrs = {info['hostname']: host for host, info in hosts.items()}
regions = load_host_regions(hosts)
region_ids = list(sorted(regions.keys()))

## Fabric Env
env.hosts = sorted(list(hosts.keys()))
env.user = "ubuntu"
env.colorize_errors = True
env.use_ssh_config = True
env.forward_agent = True


##########################################################################
## Task Helper Functions
##########################################################################

def pproc_command(commands):
    """
    Creates a pproc command from a list of command strings.
    """
    commands = " ".join([
        "\"{}\"".format(command) for command in commands
    ])
    return "pproc {}".format(commands)


def round_robin(n, host, hosts=env.hosts):
    """
    Returns a number n (of clients) for the specified host, by allocating the
    n clients evenly in a round robin fashion. For example, if hosts = 3 and
    n = 5; then this function returns 2 for host[0], 2 for host[1] and 1 for
    host[2].
    """
    num = n / len(hosts)
    idx = hosts.index(host)
    if n % len(hosts) > 0 and idx < (n % len(hosts)):
        num += 1
    return num


def make_string_args(flags=[], args={}):
    sflags = " ".join(["-{}".format(f) for f in flags])
    sargs = " ".join([
        "-{} {}".format(k, v) for k,v in args.items()
    ])

    return "{} {}".format(sflags, sargs).strip()


def make_server_args(config, host):
    name = addrs[host]
    info = hosts[name]

    # Don't run server if not configured
    if name not in config["server"]["hosts"]:
        return None

    # Get the flags and args
    flags = config["server"]["flags"]
    args = config["server"]["args"]

    # Find the master address and port
    args["maddr"] = hosts[config["master"]["host"]]["hostname"]
    args["mport"] = config["master"]["args"]["port"]

    # Specify the address
    args["addr"] = host

    return make_string_args(flags=flags, args=args)


def make_client_args(config, host):
    name = addrs[host]

    # Don't run client if not configured
    if name not in config["client"]["hosts"]:
        return None

    # Get the flags and args
    flags = config["client"]["flags"]
    args = config["client"]["args"]

    # Find the master address and port
    args["maddr"] = hosts[config["master"]["host"]]["hostname"]
    args["mport"] = config["master"]["args"]["port"]

    return make_string_args(flags=flags, args=args)


##########################################################################
## ePaxos Commands
##########################################################################

@task
@parallel
def install():
    """
    Install epaxos for the first time on each machine
    """
    run("mkdir -p {}".format(repo))

    with cd(os.path.dirname(repo)):
        run("git clone git@github.com:bbengfort/paxi.git")

    with cd(repo):
        run("make install")
        run("mkdir -p {}".format(workspace))


@task
@parallel
def uninstall():
    """
    Uninstall ePaxos on every machine
    """
    run("rm -rf {}".format(repo))
    run("rm -rf {}".format(workspace))
    run("rm -rf $GOPATH/bin/paxi-*")


@task
@parallel
def update():
    """
    Update epaxos by pulling the repository and installing the command.
    """
    with cd(repo):
        run("git pull")
        run("make")


@parallel
def _version():
    """
    Get the current epaxos version number
    """
    with cd(repo):
        return run("git rev-parse --short HEAD")


@task
@runs_once
def version():
    """
    Gets the current version and compares with remote versions
    """
    current_version = local("git rev-parse --short HEAD", capture=True)
    table = [["Host", "Version", "Current"], ["local", current_version, "-"]]

    with hide('running', 'stdout'):
        versions = execute(_version)

    for host, line in versions.items():
        current = green(u"✓") if line == current_version else red(u"✗")
        table.append([host, line, current])

    print(tabulate(table, tablefmt="simple", headers="firstrow"))


@task
@parallel
def cleanup():
    """
    Cleans up results and data files so that the experiment can be run again.
    """
    with cd(workspace):
        run("rm -f history")
        run("rm -f latency")
        run("rm -f *.log")


@task
@parallel
def bench(config="config.json"):
    """
    Run the ePaxos server on the specified machine, as well as the ePaxos
    master if this machine is designated master. If this machine is designated
    as a client, run that as well. Designations are defined by the config.
    """
    # Put the config on the remote
    remote = os.path.join(workspace, "config.json")
    put(config, remote)
    time.sleep(3)

    with open(config, 'r') as f:
        config = json.load(f)

    host = addrs[env.host]
    rid = "{}.{}".format(region_ids.index(host_region(host))+1, host_id(host))

    if rid not in config["address"]:
        return

    command = [
        "paxi-server -log_level 1 -id {} -uptime 3m".format(rid),
        "paxi-client -id {} -log_level 1 -delay 5s".format(rid),
    ]

    with cd(workspace):
        run(pproc_command(command))


@task
@parallel
def getmerge(path="data", suffix=None, results=True, latency=True, history=False, logs=False):
    """
    Get the results.txt save them with the specified suffix to the localpath.
    """
    def _getmerge(name):
        remote = os.path.join(workspace, name)
        local = unique_name(
            os.path.join(path, addrs[env.host], add_suffix(name, suffix))
        )

        if files.exists(remote):
            get(remote, local)

    if results:
        _getmerge("results.jsonl")

    if history:
        _getmerge("history")

    if latency:
        _getmerge("latency")

    if logs:
        _getmerge("*.log")


@task
@parallel
def putconfig(config="config.json"):
    remote = os.path.join(workspace, "config.json")
    put(config, remote)
