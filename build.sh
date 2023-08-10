#!/bin/bash

docker rmi -f wimp:latest
docker build --tag wimp:latest .

