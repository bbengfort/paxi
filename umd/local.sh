#!/bin/bash
# Run paxis/ePaxos locally

# Define important paths
CURDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESULTS="$CURDIR/results.txt"
BIN="$CURDIR/../bin"
CONFIG="$CURDIR/config.json"
LOGS="$CURDIR/logs"

# Define the commands
SERVER="$BIN/server"
CLIENT="$BIN/client"
CMD="$BIN/cmd"

# Define the IDs of the server to run
IDS=("1.1" "1.2" "1.3" "2.1" "2.2" "2.3" "3.1" "3.2" "3.3")

# Run the servers
for (( I=0; I<${#IDS[@]}; I+=1 )); do
    $SERVER -config $CONFIG -log_dir $LOGS -log_level 1 -id ${IDS[$I]} & PIDS[$I]=$!
done

# Run the benchmark after a slight delay
sleep 3
$CLIENT -id 1.1 -config $CONFIG -log_dir $LOGS -log_level 1

# Kill the server PIDS
for p in "${PIDS[@]}"; do
    kill -15 "$p"
done
