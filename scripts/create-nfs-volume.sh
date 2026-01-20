docker volume create --driver local \
  --opt type=nfs \
  --opt o=addr=192.168.1.121,rw,nfsvers=4,hard,intr \
  --opt device=:/ \
  shared_logs 
