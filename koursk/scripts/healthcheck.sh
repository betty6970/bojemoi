#!/bin/bash

# Vérification du processus selon le mode
case "$RSYNC_MODE" in
    "master")
        [ -f /var/run/rsync-master.pid ] && \
        kill -0 $(cat /var/run/rsync-master.pid) 2>/dev/null
        ;;
    "slave")
        [ -f /var/run/rsync-slave.pid ] && \
        pgrep -f "rsync --daemon" > /dev/null
        ;;
    *)
        exit 1
        ;;
esac
