#!/bin/sh
# Generate a self-signed certificate valid for 365 days
# Supports both localhost and IP addresses via SAN

CERT_DIR="/etc/nginx/certs"
CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"
DAYS_VALID=90
RENEW_BEFORE=30

# Use SERVER_HOST from env, default to localhost
HOST="${SERVER_HOST:-localhost}"

# Build SAN (Subject Alternative Name) for IP or domain
if echo "$HOST" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
  SAN="IP:$HOST,IP:127.0.0.1"
  CN="$HOST"
else
  SAN="DNS:$HOST,DNS:localhost,IP:127.0.0.1"
  CN="$HOST"
fi

generate_cert() {
  echo "$(date): Generating self-signed certificate for $HOST (SAN: $SAN)..."
  openssl req -x509 -nodes -days "$DAYS_VALID" -newkey rsa:2048 \
    -keyout "$KEY_FILE" -out "$CERT_FILE" \
    -subj "/CN=$CN" \
    -addext "subjectAltName=$SAN" 2>&1
  echo "$(date): Certificate generated, valid for $DAYS_VALID days."
}

needs_renewal() {
  if [ ! -f "$CERT_FILE" ]; then
    return 0
  fi
  # Check if cert expires within RENEW_BEFORE days
  if openssl x509 -checkend $((RENEW_BEFORE * 86400)) -noout -in "$CERT_FILE" 2>/dev/null; then
    return 1
  fi
  return 0
}

# Initial generation
if needs_renewal; then
  generate_cert
else
  echo "$(date): Certificate still valid, skipping generation."
fi

# Renewal loop: check daily
while true; do
  sleep 86400
  if needs_renewal; then
    generate_cert
    # Reload nginx to pick up new cert
    echo "$(date): Sending reload signal to nginx..."
    nginx -s reload 2>/dev/null || true
  fi
done
