
docker run -d -it\
  --name nfs-client-custom \
  -v shared_logs:/mnt \
  --privileged \
  vladimir-1:latest sh
