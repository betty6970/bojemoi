#!/bin/bash
set -e

# Initialize GPG + pass on first run
if ! gpg --list-keys 2>/dev/null | grep -q "pass-key"; then
    echo "[bridge] First run: initializing GPG key and pass store..."
    gpg --generate-key --batch /protonmail/gpgparams
    pass init pass-key
    echo "[bridge] GPG and pass initialized."
fi

# Start socat proxies (bridge only listens on 127.0.0.1)
socat TCP-LISTEN:25,fork TCP:127.0.0.1:1025 &
socat TCP-LISTEN:143,fork TCP:127.0.0.1:1143 &

echo "[bridge] Starting..."

# Start bridge and keep it running — no auto-login.
# If vault has a valid session, accounts load automatically.
# For first login, run: docker run --rm -it --volume protonmail_data:/root \
#   --secret proton_username --secret proton_password --network mail \
#   localhost:5000/protonmail-bridge:latest bash -c "protonmail-bridge --cli"
exec expect -c "
    set timeout 60
    log_user 1
    spawn protonmail-bridge --cli

    expect {
        -re {No active accounts} {
            puts \"\[bridge\] No accounts in vault — login manually via one-shot container.\"
            expect -re {>>>}
        }
        -re {>>>} {
            puts \"\[bridge\] Account loaded from vault.\"
        }
        timeout { puts \"\[bridge\] Startup timeout\"; exit 1 }
        eof { exit 1 }
    }

    send \"info\r\"
    expect -re {>>>}

    puts \"\[bridge\] Running.\"
    set timeout -1
    expect eof
"
