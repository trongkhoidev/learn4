# Oracle A1 deployment

This deployment moves the FastAPI API, persistent SQLite data, uploaded audio,
and self-hosted faster-whisper from the development Mac to an Oracle Ampere A1
instance. Vercel remains the frontend. Caddy provides HTTPS using the instance's
`<public-ip>.sslip.io` hostname.

Resources created by `provision.py`:

- one `VM.Standard.A1.Flex` instance with 4 OCPU and 24 GB RAM;
- one VCN, public subnet, internet gateway, and routes;
- ingress for SSH, HTTP, and HTTPS;
- an Ubuntu 24.04 ARM64 image and cloud-init Docker installation.

The provisioner is idempotent by display name. It reuses the instance and network
on later runs. Authentication stays in `.oci-private/`, which Git ignores.

```sh
mkdir -p .oci-private
ssh-keygen -t ed25519 -f .oci-private/learn4-oracle -N ''

/private/tmp/learn4-oci-cli/bin/python deploy/oracle/provision.py \
  --config .oci-private/config \
  --profile LEARN4 \
  --ssh-public-key .oci-private/learn4-oracle.pub

deploy/oracle/deploy.sh
```

Do not change the Vercel proxy until `/ready`, a real Speaking submission, and
the persistent database have been verified on Oracle. Keep the previous ngrok
origin available until the two production aliases pass after cutover.
