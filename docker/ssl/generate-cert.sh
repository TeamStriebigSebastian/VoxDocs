#!/bin/bash
# Generate self-signed SSL certificate for local development
# This allows getUserMedia to work on local network devices

CERT_DIR="$(dirname "$0")"

# Generate private key and certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$CERT_DIR/server.key" \
  -out "$CERT_DIR/server.crt" \
  -subj "/C=DE/ST=Local/L=Local/O=VoxDocs/CN=voxdocs.local" \
  -addext "subjectAltName=DNS:localhost,DNS:voxdocs.local,IP:127.0.0.1,IP:192.168.0.0/16,IP:10.0.0.0/8,IP:172.16.0.0/12"

echo "SSL certificate generated successfully!"
echo "Certificate: $CERT_DIR/server.crt"
echo "Private key: $CERT_DIR/server.key"
