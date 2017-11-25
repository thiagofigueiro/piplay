#!/bin/bash

fswatch -o . | xargs -n1 -I{} rsync -av ./ 192.168.1.15:pi/

