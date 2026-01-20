#!/bin/ash

# Start rpcbind service
echo "Starting rpcbind..."
rpcbind -f &

# Wait a moment for rpcbind to start
sleep 2

# Function to mount NFS share
mount_nfs() {
    if [[ -n "$NFS_SERVER" && -n "$NFS_PATH" ]]; then
        echo "Mounting NFS share: $NFS_SERVER:$NFS_PATH to $MOUNT_POINT"
        
        # Create mount point if it doesn't exist
        mkdir -p "$MOUNT_POINT"
        
        # Mount the NFS share
        mount -t nfs -o "$NFS_OPTIONS" "$NFS_SERVER:$NFS_PATH" "$MOUNT_POINT"
        
        if [ $? -eq 0 ]; then
            echo "NFS mount successful!"
            df -h "$MOUNT_POINT"
        else
            echo "NFS mount failed!"
            exit 1
        fi
    else
        echo "NFS_SERVER and NFS_PATH environment variables must be set"
        echo "Example: docker run -e NFS_SERVER=192.168.1.100 -e NFS_PATH=/share/data alpine-nfs-client"
    fi
}

# Function to handle graceful shutdown
cleanup() {
    echo "Shutting down..."
    if mountpoint -q "$MOUNT_POINT"; then
        echo "Unmounting NFS share..."
        umount "$MOUNT_POINT"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Mount NFS if environment variables are provided
mount_nfs

# Execute the main command
exec "$@"
