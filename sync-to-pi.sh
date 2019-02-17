#!/bin/bash

#fswatch -o . | xargs -n1 -I{} rsync -av ./ 192.168.1.4:pi/
fswatch -o . | xargs -n1 -I{} rsync -av ./ 192.168.1.15:pi/
#fswatch -o . | xargs -n1 -I{} bash -c 'rsync -av ./ 192.168.1.15:pi/; rsync -av ./ 192.168.1.4:pi/'

