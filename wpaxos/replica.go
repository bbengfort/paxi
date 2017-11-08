package wpaxos

import (
	. "paxi"
	"paxi/glog"
)

type Replica struct {
	*Node
	paxi map[Key]*paxos

	Threshold int
}

func NewReplica(config *Config) *Replica {
	r := new(Replica)
	r.Node = NewNode(config)
	r.paxi = make(map[Key]*paxos)
	r.Threshold = config.Threshold
	return r
}

// Run start running replica
func (r *Replica) Run() {
	go r.messageLoop()
	r.Node.Run()
}

func (r *Replica) messageLoop() {
	for {
		msg := <-r.MessageChan
		switch msg := msg.(type) {
		case Request:
			glog.V(2).Infof("Replica %s received %v\n", r.ID, msg)
			r.handleRequest(msg)

		case Prepare:
			glog.V(1).Infof("Replica %s ===[%v]===>>> Replica %s\n", LeaderID(msg.Ballot), msg, r.ID)
			r.handlePrepare(msg)

		case Promise:
			glog.V(1).Infof("Replica %s ===[%v]===>>> Replica %s\n", msg.ID, msg, r.ID)
			r.handlePromise(msg)
			glog.V(2).Infof("Number of keys: %d", r.keys())

		case Accept:
			glog.V(1).Infof("Replica %s ===[%v]===>>> Replica %s\n", LeaderID(msg.Ballot), msg, r.ID)
			r.handleAccept(msg)

		case Accepted:
			glog.V(1).Infof("Replica %s ===[%v]===>>> Replica %s\n", msg.ID, msg, r.ID)
			r.handleAccepted(msg)

		case Commit:
			glog.V(1).Infof("Replica %s ===[%v]===>>> Replica %s\n", LeaderID(msg.Ballot), msg, r.ID)
			r.handleCommit(msg)

		case LeaderChange:
			glog.V(1).Infof("Replica %s ===[%v]===>>> Replica %s\n", msg.From, msg, r.ID)
			r.handleLeaderChange(msg)
		}
	}
}

func (r *Replica) init(key Key) {
	if _, exists := r.paxi[key]; !exists {
		r.paxi[key] = NewPaxos(r, key)
	}
}

func (r *Replica) handleRequest(msg Request) {
	key := msg.Command.Key
	r.init(key)
	r.paxi[key].handleRequest(msg)
}

func (r *Replica) handlePrepare(msg Prepare) {
	key := msg.Key
	r.init(key)
	r.paxi[key].handlePrepare(msg)
}

func (r *Replica) handlePromise(msg Promise) {
	key := msg.Key
	r.paxi[key].handlePromise(msg)
}

func (r *Replica) handleAccept(msg Accept) {
	key := msg.Key
	r.init(key)
	r.paxi[key].handleAccept(msg)
}

func (r *Replica) handleAccepted(msg Accepted) {
	key := msg.Key
	r.paxi[key].handleAccepted(msg)
}

func (r *Replica) handleCommit(msg Commit) {
	key := msg.Key
	r.init(key)
	r.paxi[key].handleCommit(msg)
}

func (r *Replica) handleLeaderChange(msg LeaderChange) {
	key := msg.Key
	r.paxi[key].handleLeaderChange(msg)
}

func (r *Replica) keys() int {
	sum := 0
	for _, paxos := range r.paxi {
		if paxos.active {
			sum++
		}
	}
	return sum
}
