FROM postgres:16-alpine@sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777

# Keep the official entrypoint semantics while replacing its Go-based local
# privilege-drop helper. The upstream gosu binary is built with an older Go
# standard library that creates package-level vulnerability matches even
# though PostgreSQL never uses gosu for network or TLS processing.
RUN apk upgrade --no-cache \
    && apk add --no-cache su-exec \
    && sed -i 's/exec gosu postgres/exec su-exec postgres/' /usr/local/bin/docker-entrypoint.sh \
    && ! grep -q 'gosu postgres' /usr/local/bin/docker-entrypoint.sh \
    && rm -f /usr/local/bin/gosu \
    && su-exec postgres true
