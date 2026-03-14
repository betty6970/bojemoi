FROM aquasec/trivy:latest AS trivy-bin

FROM alpine:3.19
RUN apk add --no-cache ca-certificates bash

COPY --from=trivy-bin /usr/local/bin/trivy /usr/local/bin/trivy
COPY scan-images.sh /usr/local/bin/scan-images.sh
RUN chmod +x /usr/local/bin/scan-images.sh

# Cron : lundi à 6h UTC — output redirigé vers stdout Docker
RUN echo "0 6 * * 1 root /usr/local/bin/scan-images.sh >> /proc/1/fd/1 2>&1" \
    > /etc/crontabs/root

CMD ["crond", "-f", "-d", "8"]
