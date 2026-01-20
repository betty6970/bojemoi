docker run -it --network backend --name zaproxy --hostname zaproxy -d oblast:latest -daemon -host 0.0.0.0 -port 8090 -config api.addrs.addr.name=.* -config api.addrs.addr.regex=true -config api.disablekey=true

