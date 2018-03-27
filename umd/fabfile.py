# fabfile
# Fabric command definitions for running ePaxos geo replicated experiments.
#
# Author:   Benjamin Bengfort <benjamin@bengfort.com>
# Created:  Mon Feb 26 09:02:22 2018 -0500
#
# Copyright (C) 2018 Benjamin Bengfort
# For license information, see LICENSE.txt
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

from dotenv import load_dotenv, find_dotenv

from fabric.contrib import files
from fabric.api import env, run, cd, get
from fabric.colors import red, green, cyan
from fabric.api import parallel, task, runs_once, execute


##########################################################################
## Environment Helpers
##########################################################################

# Load the host information
def load_hosts(path):
    with open(path, 'r') as f:
        return json.load(f)


def parse_bool(val):
    if isinstance(val, basestring):
        val = val.lower().strip()
        if val in {'yes', 'y', 'true', 't', '1'}:
            return True
        if val in {'no', 'n', 'false', 'f', '0'}:
            return False
    return bool(val)


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
env.hosts = sorted(list(hosts.keys()))

## Fabric Env
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
def version():
    """
    Get the current epaxos version number
    """
    with cd(repo):
        run("git rev-parse --short HEAD")


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


@parallel
def bench(config="configs/config.json"):
    """
    Run the ePaxos server on the specified machine, as well as the ePaxos
    master if this machine is designated master. If this machine is designated
    as a client, run that as well. Designations are defined by the config.
    """
    command = []

    # load the configuration
    with open(config, 'r') as f:
        config = json.load(f)

    # Create the master command
    args = make_master_args(config, env.host)
    if args:
        command.append("epaxos-master {}".format(args))

    # Create the server command
    args = make_server_args(config, env.host)
    if args:
        command.append("epaxos-server {}".format(args))

    # Create the client command
    args = make_client_args(config, env.host)
    if args:
        command.append("epaxos-client {}".format(args))

    if not command:
        return

    with cd(workspace):
        run(pproc_command(command))


@parallel
def getmerge(name="results.txt", path="data", suffix=None):
    """
    Get the results.txt save them with the specified suffix to the localpath.
    """
    remote = os.path.join(workspace, name)
    hostname = addrs[env.host]
    local = os.path.join(path, hostname, add_suffix(name, suffix))
    local  = unique_name(local)
    if files.exists(remote):
        get(remote, local)
