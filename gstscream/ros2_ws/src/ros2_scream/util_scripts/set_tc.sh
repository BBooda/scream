#!/bin/bash
tc qdisc add dev lo root handle 1: prio
tc qdisc add dev lo parent 1:1 handle 10: tbf rate 1500kbit burst 1600 limit 3000
tc filter add dev lo protocol ip parent 1:0 prio 1 handle 1 fw flowid 1:1
