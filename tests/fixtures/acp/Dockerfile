FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential libasound2-dev alsa-ucm-conf git python3 strace ca-certificates \
    && rm -rf /var/lib/apt/lists/*
