# Systemd sample of the runtime tests (support-nested-systemd-containers, design D6).
# Rocky Linux 9's init image already starts systemd: the recipe has no build step,
# so it builds without network from an empty context, and the systemd cases repeat
# on any host that holds the pinned base. Pin the base by digest through the
# maintenance procedure in docs/validation.md.
FROM docker.io/rockylinux/rockylinux:9-ubi-init@sha256:99cbe0f114cc4a71cca40a014d690251bb13df65ebc3fb06ff6ec1037e0e1086
STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
