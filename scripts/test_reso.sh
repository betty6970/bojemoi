while true; do
echo -n "Test $i: "
timeout 2 curl -4 -k -s -o /dev/null -w "%{http_code} - %{time_total}s" https://grafana.bojemoi.lab
echo " - $(date +%H:%M:%S)"
sleep 1
done
