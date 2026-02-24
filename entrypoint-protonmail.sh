#!/bin/bash
set -e

SECRETS_DIR=/run/secrets

# Initialize GPG + pass on first run
if ! gpg --list-keys 2>/dev/null | grep -q "pass-key"; then
    echo "[bridge] First run: initializing GPG key and pass store..."
    gpg --generate-key --batch /protonmail/gpgparams
    pass init pass-key
    echo "[bridge] GPG and pass initialized."
fi

# Start socat proxies (bridge only accepts connections from 127.0.0.1)
socat TCP-LISTEN:25,fork TCP:127.0.0.1:1025 &
socat TCP-LISTEN:143,fork TCP:127.0.0.1:1143 &

# Start bridge with auto-login if secrets are available
if [ -f "$SECRETS_DIR/proton_username" ] && [ -f "$SECRETS_DIR/proton_password" ]; then
    USERNAME=$(cat "$SECRETS_DIR/proton_username")
    PASSWORD=$(cat "$SECRETS_DIR/proton_password")

    expect << EXPECT_EOF
set timeout 300
log_user 1
spawn protonmail-bridge --cli

# Wait for bridge to fully start
expect {
    -re {>>>} {}
    timeout { puts "\[bridge\] Startup timeout"; exit 1 }
    eof { exit 1 }
}

# Attempt login (safe to call even if already logged in)
send "login\r"

expect {
    -re {[Uu]sername} {
        send "${USERNAME}\r"
        expect -re {[Pp]assword}
        send "${PASSWORD}\r"
        expect {
            -re {[Tt]wo.factor} {
                send "\r"
                exp_continue
            }
            -re {(logged in|signed in|>>>)} {}
            timeout { puts "\[bridge\] Login timeout"; exit 1 }
        }
    }
    -re {(already|logged in|signed in)} {}
    timeout { puts "\[bridge\] Login response timeout"; exit 1 }
    eof { exit 1 }
}

# Query account info to expose bridge SMTP password in Docker logs
send "info\r"
expect {
    -re {>>>} {}
    timeout {}
}

puts "\[bridge\] Logged in, running."
set timeout -1
expect eof
EXPECT_EOF

else
    echo "[bridge] No secrets found, starting in interactive mode..."
    rm -f faketty
    mkfifo faketty
    cat faketty | protonmail-bridge --cli
fi
