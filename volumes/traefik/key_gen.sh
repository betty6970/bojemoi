#!/bin/bash

# Génération de certificats auto-signés pour lab.local
set -e

DOMAIN="bojemoi.lab"
CERT_DIR="./certs"

echo "=== Génération des certificats pour *.${DOMAIN} ==="

# Créer le répertoire
mkdir -p ${CERT_DIR}

# Générer la clé privée du CA
openssl genrsa -out ${CERT_DIR}/ca-key.pem 4096

# Générer le certificat du CA
openssl req -new -x509 -days 3650 -key ${CERT_DIR}/ca-key.pem \
    -out ${CERT_DIR}/ca-cert.pem \
    -subj "/C=FR/ST=Lab/L=Lab/O=Lab/CN=Lab CA"

echo "✓ CA créé"

# Générer la clé privée du certificat wildcard
openssl genrsa -out ${CERT_DIR}/${DOMAIN}-key.pem 4096

# Créer la demande de certificat
openssl req -new -key ${CERT_DIR}/${DOMAIN}-key.pem \
    -out ${CERT_DIR}/${DOMAIN}.csr \
    -subj "/C=FR/ST=Lab/L=Lab/O=Lab/CN=*.${DOMAIN}"

# Créer le fichier de configuration pour les SAN
cat > ${CERT_DIR}/${DOMAIN}.ext << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${DOMAIN}
DNS.2 = *.${DOMAIN}
EOF

# Signer le certificat avec le CA
openssl x509 -req -days 3650 \
    -in ${CERT_DIR}/${DOMAIN}.csr \
    -CA ${CERT_DIR}/ca-cert.pem \
    -CAkey ${CERT_DIR}/ca-key.pem \
    -CAcreateserial \
    -out ${CERT_DIR}/${DOMAIN}-cert.pem \
    -extfile ${CERT_DIR}/${DOMAIN}.ext

echo "✓ Certificat wildcard *.${DOMAIN} créé"

# Créer un fichier fullchain
cat ${CERT_DIR}/${DOMAIN}-cert.pem ${CERT_DIR}/ca-cert.pem > ${CERT_DIR}/${DOMAIN}-fullchain.pem

# Nettoyer
rm ${CERT_DIR}/${DOMAIN}.csr
rm ${CERT_DIR}/${DOMAIN}.ext

echo ""
echo "=== Certificats générés dans ${CERT_DIR}/ ==="
echo ""
echo "Fichiers créés:"
echo "  - ca-cert.pem          : Certificat du CA (à installer sur vos machines)"
echo "  - ${DOMAIN}-cert.pem   : Certificat du serveur"
echo "  - ${DOMAIN}-key.pem    : Clé privée du serveur"
echo "  - ${DOMAIN}-fullchain.pem : Certificat complet (cert + CA)"
echo ""
echo "IMPORTANT: Installez ca-cert.pem sur vos machines pour faire confiance aux certificats"
echo ""

