#!/bin/bash
export LD_LIBRARY_PATH=$(pwd)/lib:$LD_LIBRARY_PATH
./mosquitto -c mosquitto.conf
