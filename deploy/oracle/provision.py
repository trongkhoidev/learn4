"""Provision an idempotent Oracle A1 host and public network for Learn4."""

import argparse
import base64
import json
from pathlib import Path

import oci

PREFIX = "learn4"
SHAPE = "VM.Standard.A1.Flex"


def first(items, name):
    return next((item for item in items if item.display_name == name), None)


def signer_for(config):
    token_file = config.get("security_token_file")
    if not token_file:
        return None
    token = Path(token_file).expanduser().read_text(encoding="utf-8")
    private_key = oci.signer.load_private_key_from_file(config["key_file"])
    return oci.auth.signers.SecurityTokenSigner(token, private_key)


def client(cls, config, signer):
    return cls(config, **({"signer": signer} if signer else {}))


def wait(client_, response, state, *, seconds=900):
    return oci.wait_until(
        client_, response, "lifecycle_state", state, max_wait_seconds=seconds,
    ).data


def ensure_network(network, compartment_id):
    vcns = network.list_vcns(compartment_id).data
    vcn = first(vcns, f"{PREFIX}-vcn")
    if not vcn:
        response = network.create_vcn(oci.core.models.CreateVcnDetails(
            compartment_id=compartment_id,
            display_name=f"{PREFIX}-vcn",
            cidr_blocks=["10.42.0.0/16"],
            dns_label="learn4",
        ))
        vcn = wait(network, network.get_vcn(response.data.id), "AVAILABLE")

    gateways = network.list_internet_gateways(compartment_id, vcn_id=vcn.id).data
    gateway = first(gateways, f"{PREFIX}-internet-gateway")
    if not gateway:
        response = network.create_internet_gateway(oci.core.models.CreateInternetGatewayDetails(
            compartment_id=compartment_id,
            vcn_id=vcn.id,
            display_name=f"{PREFIX}-internet-gateway",
            is_enabled=True,
        ))
        gateway = wait(
            network, network.get_internet_gateway(response.data.id), "AVAILABLE",
        )

    route_table = network.get_route_table(vcn.default_route_table_id).data
    if not any(rule.destination == "0.0.0.0/0" for rule in route_table.route_rules):
        network.update_route_table(route_table.id, oci.core.models.UpdateRouteTableDetails(
            route_rules=[*route_table.route_rules, oci.core.models.RouteRule(
                destination="0.0.0.0/0",
                destination_type="CIDR_BLOCK",
                network_entity_id=gateway.id,
            )],
        ))

    security = network.get_security_list(vcn.default_security_list_id).data
    wanted_ports = {22, 80, 443}
    existing = {
        rule.tcp_options.destination_port_range.min
        for rule in security.ingress_security_rules
        if rule.protocol == "6" and rule.tcp_options and rule.tcp_options.destination_port_range
        and rule.tcp_options.destination_port_range.min == rule.tcp_options.destination_port_range.max
    }
    if wanted_ports - existing:
        ingress = list(security.ingress_security_rules)
        for port in sorted(wanted_ports - existing):
            ingress.append(oci.core.models.IngressSecurityRule(
                protocol="6", source="0.0.0.0/0", source_type="CIDR_BLOCK",
                tcp_options=oci.core.models.TcpOptions(
                    destination_port_range=oci.core.models.PortRange(min=port, max=port),
                ),
                description=f"Learn4 TCP {port}",
            ))
        network.update_security_list(security.id, oci.core.models.UpdateSecurityListDetails(
            ingress_security_rules=ingress,
            egress_security_rules=security.egress_security_rules,
        ))

    subnets = network.list_subnets(compartment_id, vcn_id=vcn.id).data
    subnet = first(subnets, f"{PREFIX}-public-subnet")
    if not subnet:
        response = network.create_subnet(oci.core.models.CreateSubnetDetails(
            compartment_id=compartment_id,
            vcn_id=vcn.id,
            display_name=f"{PREFIX}-public-subnet",
            cidr_block="10.42.1.0/24",
            dns_label="public",
            route_table_id=vcn.default_route_table_id,
            security_list_ids=[vcn.default_security_list_id],
            prohibit_public_ip_on_vnic=False,
        ))
        subnet = wait(network, network.get_subnet(response.data.id), "AVAILABLE")
    return subnet


def find_image(compute, compartment_id):
    images = compute.list_images(
        compartment_id,
        operating_system="Canonical Ubuntu",
        operating_system_version="24.04",
        shape=SHAPE,
        sort_by="TIMECREATED",
        sort_order="DESC",
    ).data
    images = [image for image in images if image.lifecycle_state == "AVAILABLE"]
    if not images:
        raise RuntimeError("No compatible Ubuntu 24.04 ARM image found")
    return images[0]


def ensure_instance(compute, network, identity, config, compartment_id, subnet, ssh_key, cloud_init):
    instances = compute.list_instances(compartment_id, display_name=f"{PREFIX}-a1").data
    instance = next((item for item in instances if item.lifecycle_state not in {"TERMINATED", "TERMINATING"}), None)
    if not instance:
        image = find_image(compute, compartment_id)
        domains = identity.list_availability_domains(config["tenancy"]).data
        last_error = None
        for domain in domains:
            try:
                response = compute.launch_instance(oci.core.models.LaunchInstanceDetails(
                    availability_domain=domain.name,
                    compartment_id=compartment_id,
                    display_name=f"{PREFIX}-a1",
                    shape=SHAPE,
                    shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                        ocpus=4, memory_in_gbs=24,
                    ),
                    source_details=oci.core.models.InstanceSourceViaImageDetails(
                        source_type="image", image_id=image.id,
                    ),
                    create_vnic_details=oci.core.models.CreateVnicDetails(
                        subnet_id=subnet.id,
                        assign_public_ip=True,
                        display_name=f"{PREFIX}-primary-vnic",
                        hostname_label="api",
                    ),
                    metadata={
                        "ssh_authorized_keys": ssh_key.strip(),
                        "user_data": base64.b64encode(cloud_init.encode()).decode(),
                    },
                ))
                instance = wait(compute, compute.get_instance(response.data.id), "RUNNING", seconds=1800)
                break
            except oci.exceptions.ServiceError as exc:
                last_error = exc
        if not instance:
            raise RuntimeError(f"A1 capacity was unavailable in every availability domain: {last_error}")
    elif instance.lifecycle_state == "STOPPED":
        compute.instance_action(instance.id, "START")
        instance = wait(compute, compute.get_instance(instance.id), "RUNNING")

    attachments = compute.list_vnic_attachments(
        compartment_id, instance_id=instance.id,
    ).data
    vnic = network.get_vnic(attachments[0].vnic_id).data
    return instance, vnic.public_ip


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--profile", default="LEARN4")
    parser.add_argument("--compartment-id")
    parser.add_argument("--ssh-public-key", type=Path, required=True)
    parser.add_argument("--state", type=Path, default=Path(__file__).with_name("state.json"))
    args = parser.parse_args()
    config = oci.config.from_file(str(args.config), args.profile)
    signer = signer_for(config)
    compartment_id = args.compartment_id or config["tenancy"]
    compute = client(oci.core.ComputeClient, config, signer)
    network = client(oci.core.VirtualNetworkClient, config, signer)
    identity = client(oci.identity.IdentityClient, config, signer)
    subnet = ensure_network(network, compartment_id)
    instance, public_ip = ensure_instance(
        compute, network, identity, config, compartment_id, subnet,
        args.ssh_public_key.read_text(encoding="utf-8"),
        Path(__file__).with_name("cloud-init.yaml").read_text(encoding="utf-8"),
    )
    state = {
        "instance_id": instance.id,
        "public_ip": public_ip,
        "backend_host": f"{public_ip}.sslip.io",
        "ssh_user": "ubuntu",
        "region": config["region"],
    }
    args.state.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
