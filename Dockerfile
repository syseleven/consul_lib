# this file is used to speed up development

FROM ubuntu:xenial
COPY build-deb-with-docker-deps /tmp/build-deb-with-docker-deps
RUN bash -x /tmp/build-deb-with-docker-deps
