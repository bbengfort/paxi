package paxi

import (
	"encoding/json"
	"flag"
	"os"

	"github.com/ailidani/paxi/log"
)

var configFile = flag.String("config", "config.json", "Configuration file for paxi replica. Defaults to config.json.")

// Config contains every system configuration
type Config struct {
	Addrs           map[ID]string `json:"address"`           // address for node communication
	HTTPAddrs       map[ID]string `json:"http_address"`      // address for client server communication
	Algorithm       string        `json:"algorithm"`         // replication algorithm name
	Quorum          string        `json:"quorum"`            // type of the quorums
	F               int           `json:"f"`                 // number of failure zones in general grid quorums
	Transport       string        `json:"transport"`         // not used
	ReplyWhenCommit bool          `json:"reply_when_commit"` // reply to client when request is committed, instead of executed
	Adaptive        bool          `json:"adaptive"`          // adaptive leader change, if true paxos forward request to current leader
	Policy          string        `json:"policy"`            // leader change policy {consecutive, majority}
	Threshold       int           `json:"threshold"`         // threshold for policy in WPaxos {n consecutive or time interval in ms}
	BackOff         int           `json:"backoff"`           // random backoff interval
	Thrifty         bool          `json:"thrifty"`           // only send messages to a quorum
	BufferSize      int           `json:"buffer_size"`       // buffer size for maps
	ChanBufferSize  int           `json:"chan_buffer_size"`  // buffer size for channels
	MultiVersion    bool          `json:"multiversion"`      // create multi-version database
	Benchmark       bconfig       `json:"benchmark"`         // benchmark configuration

	// for future implementation
	// Batching bool `json:"batching"`
	// Consistency string `json:"consistency"`
	// Codec string `json:"codec"` // codec for message serialization between nodes
}

// Config is global configuration singleton generated by init() func below
var config Config

func init() {
	config = MakeDefaultConfig()
}

// GetConfig returns paxi package configuration
func GetConfig() *Config {
	return &config
}

// MakeDefaultConfig returns Config object with few default values
// only used by init() and master
func MakeDefaultConfig() Config {
	return Config{
		Quorum:         "majority",
		Transport:      "tcp",
		Policy:         "consecutive",
		BufferSize:     1024,
		ChanBufferSize: 1024,
		Benchmark: bconfig{
			T:                    60,
			N:                    0,
			K:                    1000,
			W:                    50,
			Concurrency:          1,
			Distribution:         "uniform",
			LinearizabilityCheck: false,
			Conflicts:            100,
			Min:                  0,
			Mu:                   0,
			Sigma:                60,
			Move:                 false,
			Speed:                500,
			ZipfianS:             2,
			ZipfianV:             1,
		},
	}
}

// NumNodes returns number of total nodes
func (c Config) NumNodes() int {
	return len(c.Addrs)
}

// NumZones returns number of zones
func (c Config) NumZones() int {
	zones := make(map[int]int)
	for id := range c.Addrs {
		zones[id.Zone()]++
	}
	return len(zones)
}

// String is implemented to print the config
func (c Config) String() string {
	config, err := json.Marshal(c)
	if err != nil {
		log.Error(err)
		return ""
	}
	return string(config)
}

// Load loads configuration from config file in JSON format
func (c *Config) Load() {
	file, err := os.Open(*configFile)
	if err != nil {
		log.Fatal(err)
	}
	decoder := json.NewDecoder(file)
	err = decoder.Decode(c)
	if err != nil {
		log.Fatal(err)
	}
}

// Save saves configuration to file in JSON format
func (c *Config) Save() error {
	file, err := os.Create(*configFile)
	if err != nil {
		return err
	}
	encoder := json.NewEncoder(file)
	return encoder.Encode(c)
}
