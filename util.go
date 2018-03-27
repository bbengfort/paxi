package paxi

import (
	"encoding/gob"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"time"

	"github.com/ailidani/paxi/log"
)

// Max of two int
func Max(a, b int) int {
	if a < b {
		return b
	}
	return a
}

// VMax of a vector
func VMax(v ...int) int {
	max := v[0]
	for _, i := range v {
		if max < i {
			max = i
		}
	}
	return max
}

// Retry function f sleep time between attempts
func Retry(f func() error, attempts int, sleep time.Duration) error {
	var err error
	for i := 0; ; i++ {
		err = f()
		if err == nil {
			return nil
		}

		if i >= attempts-1 {
			break
		}

		// exponential delay
		time.Sleep(sleep * time.Duration(i+1))
	}
	return fmt.Errorf("after %d attempts, last error: %s", attempts, err)
}

// Schedule repeatedly call function with intervals
func Schedule(f func(), delay time.Duration) chan bool {
	stop := make(chan bool)

	go func() {
		for {
			f()
			select {
			case <-time.After(delay):
			case <-stop:
				return
			}
		}
	}()

	return stop
}

// ConnectToMaster connects to master node and set global Config
func ConnectToMaster(addr string, client bool, id ID) {
	conn, err := net.Dial("tcp", addr)
	if err != nil {
		log.Fatal(err)
	}
	dec := gob.NewDecoder(conn)
	enc := gob.NewEncoder(conn)
	msg := &Register{
		ID:     id,
		Client: client,
		Addr:   "",
	}
	enc.Encode(msg)
	err = dec.Decode(&config)
	if err != nil {
		log.Fatal(err)
	}
}

func AppendJSON(path string, val interface{}) error {
	// Open the file for appending, creating it if necessary
	f, err := os.OpenFile(path, os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0644)
	if err != nil {
		return err
	}
	defer f.Close()

	// Marshal the JSON in one line without indents
	data, err := json.Marshal(val)
	if err != nil {
		return err
	}

	// Append a newline to the data
	data = append(data, byte('\n'))

	// Append the data to the file
	_, err = f.Write(data)
	return err
}
