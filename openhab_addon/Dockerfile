ARG BUILD_FROM=alpine:3.19
FROM ${BUILD_FROM}

ARG BUILD_DATE
ARG VCS_REF

ENV \
    JAVA_VERSION="17" \
    OPENHAB_VERSION="4.2.2" \
    CRYPTO_POLICY="limited" \
    EXTRA_JAVA_OPTS="" \
    EXTRA_SHELL_OPTS="" \
    GROUP_ID="9001" \
    KARAF_EXEC="exec" \
    LC_ALL="en_US.UTF-8" \
    LANG="en_US.UTF-8" \
    LANGUAGE="en_US.UTF-8" \
    OPENHAB_BACKUPS="/backup/openhab" \
    OPENHAB_CONF="/config/conf" \
    OPENHAB_HOME="/openhab" \
    OPENHAB_HTTP_PORT="8080" \
    OPENHAB_HTTPS_PORT="8443" \
    OPENHAB_LOGDIR="/config/userdata/logs" \
    OPENHAB_USERDATA="/config/userdata" \
    USER_ID="9001" \
    DEBUG_MODE="false"
    
# Basic build-time metadata as defined at https://github.com/opencontainers/image-spec/blob/main/annotations.md#pre-defined-annotation-keys
LABEL org.opencontainers.image.created=$BUILD_DATE \
    org.opencontainers.image.licenses="EPL-2.0" \
    org.opencontainers.image.title="openHAB" \
    org.opencontainers.image.vendor="openHAB Foundation e.V." \
    org.opencontainers.image.version=$OPENHAB_VERSION \
    org.opencontainers.image.description="An open source, technology agnostic home automation platform" \
    org.opencontainers.image.url="https://www.openhab.org/" \
    org.opencontainers.image.documentation="https://www.openhab.org/docs/installation/docker.html" \
    org.opencontainers.image.revision=$VCS_REF \
    org.opencontainers.image.source="https://github.com/openhab/openhab-docker.git" \
    org.opencontainers.image.authors="openHAB <info@openhabfoundation.org>"

# Set working directory and entrypoint
WORKDIR ${OPENHAB_HOME}
COPY entrypoint /entrypoint
RUN chmod +x /entrypoint
ENTRYPOINT ["/entrypoint"]

# Execute command (Check for debug mode and start appropriate script)
CMD ["/bin/sh", "-c", "if [ \"$DEBUG_MODE\" = \"true\" ]; then su-exec openhab tini -s ./start_debug.sh; else su-exec openhab tini -s ./start.sh; fi"]
