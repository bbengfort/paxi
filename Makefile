# Script to build Paxi for deployment on GeoNet
SHELL := /bin/bash

PACKAGE = paxi
LOCAL_BIN = $(CURDIR)/bin
GLOBAL_BIN = $(GOPATH)/bin

GO = go
BM  = $(shell printf "\033[34;1m▶\033[0m")
GM = $(shell printf "\033[32;1m▶\033[0m")
RM = $(shell printf "\033[31;1m▶\033[0m")

# Export targets not associated with files.
.PHONY: all server client cmd install clean

# Build paxi server client and cmd
all: server client cmd

server:
	$(info $(BM) building server …)
	@$(GO) build -o $(LOCAL_BIN)/$(PACKAGE)-server ./server

client:
	$(info $(BM) building client …)
	@$(GO) build -o $(LOCAL_BIN)/$(PACKAGE)-client ./client

cmd:
	$(info $(BM) building cmd …)
	@$(GO) build -o $(LOCAL_BIN)/$(PACKAGE)-cmd ./cmd

install: all
	$(info $(GM) installing to $(GLOBAL_BIN))
	@ln -s $(LOCAL_BIN)/$(PACKAGE)-server $(GLOBAL_BIN)/$(PACKAGE)-server
	@ln -s $(LOCAL_BIN)/$(PACKAGE)-client $(GLOBAL_BIN)/$(PACKAGE)-client
	@ln -s $(LOCAL_BIN)/$(PACKAGE)-cmd $(GLOBAL_BIN)/$(PACKAGE)-cmd

clean:
	$(info $(RM) cleaning up build …)
	@rm $(LOCAL_BIN)/$(PACKAGE)-server
	@rm $(LOCAL_BIN)/$(PACKAGE)-client
	@rm $(LOCAL_BIN)/$(PACKAGE)-cmd
	@rm $(GLOBAL_BIN)/$(PACKAGE)-*
