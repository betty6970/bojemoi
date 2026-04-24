FROM golang:1.22-alpine AS builder
RUN apk add --no-cache git
RUN git clone --depth=1 https://github.com/corelight/suricata_exporter.git /src
WORKDIR /src
RUN go build -o /suricata_exporter .

FROM alpine:latest
COPY --from=builder /suricata_exporter /usr/local/bin/suricata_exporter
EXPOSE 9917
ENTRYPOINT ["/usr/local/bin/suricata_exporter"]
