#!/bin/bash
# init-proton-bridge.sh

docker exec -it $(docker ps -q -f name=protonmail-bridge) sh -c "
protonmail-bridge --cli <<EOF
login
betty-bombers@proton.me
Sysres@01
615259
info
EOF
"
