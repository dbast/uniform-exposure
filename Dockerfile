FROM debian:stretch-slim

# hadolint ignore=DL3008
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    python3 \
    ufraw \
    enfuse \
    imagemagick \
    libimage-exiftool-perl \
    jpegoptim \
  && rm -rf /var/lib/apt/lists/*

COPY uniform_exposure.py /usr/local/bin/

WORKDIR /tmp/

CMD ["python3", "/usr/local/bin/uniform_exposure.py"]
