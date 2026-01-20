docker run -d \
  --name nfs-server \
  --network base_nfs-network \
  --restart unless-stopped \
  --privileged \
  --cap-add SYS_ADMIN \
  -p 2049:2049 \
  -p 111:111 \
  -p 111:111/udp \
  -v /opt/bojemo/nfs-exports:/exports:rw \
  -v /lib/modules:/lib/modules:ro \
  -e NFS_EXPORT_0="/exports *(rw,sync,no_subtree_check,no_root_squash,fsid=0)" \
  vladimir:latest

