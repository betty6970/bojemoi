curl -X POST -H "Content-Type: application/json" -d '[{
  "labels": {
    "alertname": "TestEmailConfig",
    "severity": "warning",
    "instance": "test-instance"
  },
  "annotations": {
    "summary": "Test avec nouvelle config email",
    "description": "Vérification de l envoi via Proton Mail Bridge"
  },
  "startsAt": "'"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"'"
}]' http://meta-76:9093/api/v2/alerts

