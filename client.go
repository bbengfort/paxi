package paxi

import (
	"bytes"
	"encoding/json"
	"io"
	"io/ioutil"
	"net/http"
	"net/http/httputil"
	"strconv"
	"sync"
	"time"

	"github.com/ailidani/paxi/lib"
	"github.com/ailidani/paxi/log"
)

// http client
var httpClient = &http.Client{Timeout: time.Second * 1}

// Client main access point of client lib
type Client struct {
	ID        ID // client id use the same id as servers in local site
	N         int
	addrs     map[ID]string
	http      map[ID]string
	algorithm string

	cid int // command id
}

// NewClient creates a new Client from config
func NewClient(id ID) *Client {
	return &Client{
		ID:        id,
		N:         len(config.Addrs),
		addrs:     config.Addrs,
		http:      config.HTTPAddrs,
		algorithm: config.Algorithm,
	}
}

// rest accesses server's REST API with url = http://ip:port/key
// if value == nil, it's read
func (c *Client) rest(id ID, key Key, value Value) Value {
	url := c.http[id] + "/" + strconv.Itoa(int(key))

	method := http.MethodGet
	var body io.Reader
	if value != nil {
		method = http.MethodPut
		body = bytes.NewBuffer(value)
	}
	r, err := http.NewRequest(method, url, body)
	if err != nil {
		// TODO should return error for the operation
		log.Error(err)
		return nil
	}
	r.Header.Set(HTTPClientID, string(c.ID))
	r.Header.Set(HTTPCommandID, strconv.Itoa(c.cid))
	// r.Header.Set(HTTPTimestamp, strconv.FormatInt(time.Now().UnixNano(), 10))
	res, err := httpClient.Do(r)
	if err != nil {
		log.Error(err)
		return nil
	}
	defer res.Body.Close()
	if res.StatusCode == http.StatusOK {
		b, _ := ioutil.ReadAll(res.Body)
		if value == nil {
			log.Debugf("node=%v type=%s key=%v value=%x", id, method, key, Value(b))
		} else {
			log.Debugf("node=%v type=%s key=%v value=%x", id, method, key, value)
		}
		return Value(b)
	}
	dump, _ := httputil.DumpResponse(res, true)
	log.Debugf("%q", dump)
	return nil
}

// RESTGet gets value of given key
func (c *Client) RESTGet(key Key) Value {
	c.cid++
	id := c.ID
	if id == "" {
		for id = range c.http {
			break
		}
	}
	return c.rest(id, key, nil)
}

// RESTPut puts new value as http.request body and return previous value
func (c *Client) RESTPut(key Key, value Value) Value {
	c.cid++
	id := c.ID
	if id == "" {
		for id = range c.http {
			break
		}
	}
	return c.rest(id, key, value)
}

// Get gets value of given key (use REST)
func (c *Client) Get(key Key) Value {
	return c.RESTGet(key)
}

// Put puts new key value pair and return previous value (use REST)
func (c *Client) Put(key Key, value Value) Value {
	return c.RESTPut(key, value)
}

func (c *Client) json(id ID, key Key, value Value) Value {
	url := c.http[id]
	cmd := Command{
		Key:       key,
		Value:     value,
		ClientID:  c.ID,
		CommandID: c.cid,
	}
	data, err := json.Marshal(cmd)
	res, err := httpClient.Post(url, "json", bytes.NewBuffer(data))
	if err != nil {
		log.Error(err)
		return nil
	}
	defer res.Body.Close()
	if res.StatusCode == http.StatusOK {
		b, _ := ioutil.ReadAll(res.Body)
		log.Debugf("key=%v value=%x", key, Value(b))
		return Value(b)
	}
	dump, _ := httputil.DumpResponse(res, true)
	log.Debugf("%q", dump)
	return nil
}

// JSONGet posts get request in json format to server url
func (c *Client) JSONGet(key Key) Value {
	c.cid++
	return c.json(c.ID, key, nil)
}

// JSONPut posts put request in json format to server url
func (c *Client) JSONPut(key Key, value Value) Value {
	c.cid++
	return c.json(c.ID, key, value)
}

// QuorumGet concurrently read values from majority nodes
func (c *Client) QuorumGet(key Key) []Value {
	c.cid++
	out := make(chan Value)
	i := 0
	for id := range c.http {
		i++
		if i > c.N/2 {
			break
		}
		go func(id ID) {
			out <- c.rest(id, key, nil)
		}(id)
	}
	set := lib.NewCSet()
	for ; i >= 0; i-- {
		set.Put(<-out)
	}
	res := make([]Value, 0)
	for _, v := range set.Array() {
		res = append(res, v.(Value))
	}
	return res
}

// QuorumPut concurrently write values to majority of nodes
func (c *Client) QuorumPut(key Key, value Value) {
	c.cid++
	var wait sync.WaitGroup
	i := 0
	for id := range c.http {
		i++
		if i > c.N/2 {
			break
		}
		wait.Add(1)
		go func(id ID) {
			c.rest(id, key, value)
			wait.Done()
		}(id)
	}
	wait.Wait()
}

// Consensus collects /history/key from every node and compare their values
func (c *Client) Consensus(k Key) bool {
	h := make(map[ID][]Value)
	for id, url := range c.http {
		h[id] = make([]Value, 0)
		r, err := httpClient.Get(url + "/history?key=" + strconv.Itoa(int(k)))
		if err != nil {
			log.Error(err)
			continue
		}
		b, err := ioutil.ReadAll(r.Body)
		if err != nil {
			log.Error(err)
			continue
		}
		holder := h[id]
		err = json.Unmarshal(b, &holder)
		if err != nil {
			log.Error(err)
			continue
		}
		h[id] = holder
		log.Debugf("node=%v key=%v h=%v", id, k, holder)
	}
	n := 0
	for _, v := range h {
		if len(v) > n {
			n = len(v)
		}
	}
	for i := 0; i < n; i++ {
		set := make(map[string]struct{})
		for id := range c.http {
			if len(h[id]) > i {
				set[string(h[id][i])] = struct{}{}
			}
		}
		if len(set) > 1 {
			return false
		}
	}
	return true
}

// Crash stops the node for t seconds then recover
// node crash forever if t < 0
func (c *Client) Crash(id ID, t int) {
	url := c.http[id] + "/crash?t=" + strconv.Itoa(t)
	r, err := httpClient.Get(url)
	if err != nil {
		log.Error(err)
		return
	}
	r.Body.Close()
}

// Drop drops every message send for t seconds
func (c *Client) Drop(from, to ID, t int) {
	url := c.http[from] + "/drop?id=" + string(to) + "&t=" + strconv.Itoa(t)
	r, err := httpClient.Get(url)
	if err != nil {
		log.Error(err)
		return
	}
	r.Body.Close()
}

// Start connects to server before actual requests (for future)
func (c *Client) Start() {}

// Stop disconnects from server (for future)
func (c *Client) Stop() {}
