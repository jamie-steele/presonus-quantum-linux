FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential libasound2-dev alsa-ucm-conf git python3 strace ca-certificates libspa-0.2-modules libpipewire-0.3-0 \
    && rm -rf /var/lib/apt/lists/*
