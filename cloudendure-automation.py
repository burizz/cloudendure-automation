#!/usr/bin/env python
import requests
import json
import logging
import boto3

from botocore.exceptions import ClientError
from argparse import ArgumentParser
from datetime import datetime


def main():
    parser = ArgumentParser()
    parser.add_argument("--cloudEndureProjectName", help="Provide Cloudendure Project Name - matches AWS Account Names(ex. ecint-non-prod)", required=True)
    parser.add_argument("--awsSourceRegion", help="Provide Source AWS Region. ", required=True)
    parser.add_argument("--awsTargetRegion", help="Provide Target AWS Region. ", required=True)
    parser.add_argument("--cloudEndureApiKey", help="Provide Cloudendure authentication API Key")
    parser.add_argument("--awsProfile", help="Provide AWS Profile name. If not provided looks for credentials in environment variables")
    parser.add_argument("--logLevel", help="Provide Log level. If not provided defaults to Info", choices=["debug", "DEBUG", "Debug"])
    input_args = parser.parse_args()

    # Configure Log Level
    if input_args.logLevel == 'debug' or input_args.logLevel == 'DEBUG' or input_args.logLevel == 'Debug':
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s DEBUG: %(message)s"
        )
    else:
        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s INFO: %(message)s"
        )

    # Init HTTP Client Session
    http_client = requests.Session()
    http_client.headers.update({'content-type': 'application/json'})

    # Configure AWS Region
    if input_args.awsSourceRegion:
        aws_source_region = input_args.awsSourceRegion
        aws_target_region = input_args.awsTargetRegion

    # Init EC2 Client
    if input_args.awsProfile:
        boto3.setup_default_session(profile_name=input_args.awsProfile)
    ec2_client = boto3.client('ec2', region_name=aws_source_region)

    # Main Cloudendure API URL
    cloudendure_url = "https://console.cloudendure.com/api/latest"
    # print(f'Cloudendure API URL set to {cloudendure_url}')
    logging.warning(f'Cloudendure API URL set to {cloudendure_url}')

    # Configure Cloudendure API Key
    if input_args.cloudEndureApiKey:
        api_key = input_args.cloudEndureApiKey
    else:
        api_key = "6F1A-C693-6F14-0E7C-F296-C4BE-5CF5-269A-017E-D864-B9D1-2BD6-5693-6A0F-622D-E7E2"

    # Authenticate in Cloudendure
    authenticate(http_client, cloudendure_url, api_key)

    # Get project ID
    project_json_configs = list_projects(http_client, cloudendure_url)
    for project in project_json_configs['items']:
        project_name = project['name']
        project_id = project['id']
        if project_name == input_args.cloudEndureProjectName:
            # print(f'Working with project [{project_name}]')
            logging.warning(f'Working with project [{project_name}]')
            cloudendure_project_id = project_id

    # Get blueprint objects
    blueprint_json_configs = list_blueprints(http_client, cloudendure_url, cloudendure_project_id)

    # Build blueprint id to machine id mapping
    blueprint_id_map = {}
    for blueprint in blueprint_json_configs['items']:
            cloudendure_machine_id = blueprint['machineId']
            cloudendure_blueprint_id = blueprint['id']
            blueprint_id_map[cloudendure_machine_id] = cloudendure_blueprint_id

    # Get machine objects
    machine_json_configs = list_machines(http_client, cloudendure_url, cloudendure_project_id)
    machine_counter = len(machine_json_configs['items'])
    logging.warning(f'Total cloudendure machines to be updated [{machine_counter}]')

    # Update blueprint in each cloudendure machine
    for machine in machine_json_configs['items']:
        # Get source EC2's instance id and name
        source_ec2_name = machine['sourceProperties']['name']
        source_ec2_id = machine['sourceProperties']['machineCloudId']

        logging.warning(f'\nSTART UPDATE OF CLOUDENDURE MACHINE - {source_ec2_name}\n')

        # Update replication settings in each machine
        change_config = "useLowCostDisks"
        low_cost_disks = True
        update_machine_replication_config(http_client, cloudendure_url, cloudendure_project_id, cloudendure_machine_id, change_config, low_cost_disks)

        # Get security groups and subnet from source EC2
        logging.info(f'Get Security Groups from EC2 instance {source_ec2_name} / {source_ec2_id}\n')
        sg_map, subnet_map = get_ec2_instance_sg_and_subnet(ec2_client, source_ec2_id, aws_source_region, aws_target_region)

        # Update security groups in target machine blueprint to match source's
        cloudendure_machine_id = machine['id']
        logging.info(f'Updating Cloudendure Machine with ID: {cloudendure_machine_id}')
        for machine_id, blueprint_id in blueprint_id_map.items():
            if cloudendure_machine_id == machine_id:

                # Subnets - should be updated before security groups
                change_config = "subnetIDs"
                logging.info(f'Updating Subnet in Blueprint with ID: {blueprint_id}')
                update_blueprint(http_client, cloudendure_url, cloudendure_project_id, blueprint_id, machine_id, change_config, subnet_map)

                # SG - should be updated after subnet is set
                logging.info(f'Updating Security Groups in Blueprint with ID: {blueprint_id}')
                change_config = "securityGroupIDs"
                update_blueprint(http_client, cloudendure_url, cloudendure_project_id, blueprint_id, machine_id, change_config, sg_map)

                blueprint_config = get_blueprint(http_client, cloudendure_url, cloudendure_project_id, blueprint_id)
                logging.info(f'Blueprint updated to: {blueprint_config}')

                machine_counter -= 1
                logging.warning(f'\nFINISHED UPDATE OF CLOUDENDURE MACHINE - {source_ec2_name}; remaining machines [{machine_counter}]\n')


def authenticate(http_client, cloudendure_url, api_key):
    # Login to Cloudendure and get Cookie and XSRF token
    login_url = cloudendure_url + "/login"

    resp = http_client.post(url=login_url, json={"userApiToken": api_key})
    # Error handling
    resp.raise_for_status()

    # Set XSRF Token header for HTTP Session
    xsrf_token = http_client.cookies['XSRF-TOKEN']
    http_client.headers.update({'X-XSRF-TOKEN': xsrf_token})

    logging.warning('Authenticated to cloudendure successfully')


def list_projects(http_client, cloudendure_url):
    # Get Projects definition and return as JSON
    projects_url = cloudendure_url + "/projects"
    resp = http_client.get(url=projects_url)
    # Error handling
    resp.raise_for_status()

    project_list = resp.json()

    return project_list


def list_machines(http_client, cloudendure_url, cloudendure_project_id):
    # Get Machines definition and return as JSON
    machines_url = cloudendure_url + "/projects/" + cloudendure_project_id + "/machines"
    resp = http_client.get(url=machines_url)
    # Error handling
    resp.raise_for_status()

    machine_list = resp.json()

    return machine_list


def list_blueprints(http_client, cloudendure_url, cloudendure_project_id):
    # Get Projects definition and return as JSON
    blueprints_url = cloudendure_url + "/projects/" + cloudendure_project_id + "/blueprints"
    resp = http_client.get(url=blueprints_url)
    # Error handling
    resp.raise_for_status()

    blueprint_list = resp.json()

    return blueprint_list


def get_blueprint(http_client, cloudendure_url, cloudendure_project_id, cloudendure_blueprint_id):
    # Get Blueprint definition and return as JSON
    blueprint_url = cloudendure_url + "/projects/" + cloudendure_project_id + "/blueprints/" + cloudendure_blueprint_id

    resp = http_client.get(url=blueprint_url)
    # Error handling
    resp.raise_for_status()

    blueprint_config = resp.json()

    return blueprint_config


def update_machine_replication_config(http_client, cloudendure_url, cloudendure_project_id, cloudendure_machine_id, change_config, change_values):
    # Update Cloudendure Machine - currently supports update of replication settings tags
    machine_url = cloudendure_url + "/projects/" + cloudendure_project_id + "/machines/" + cloudendure_machine_id

    list_of_changes = []

    if change_config == "useLowCostDisks":
        list_of_changes = change_values
    else:
        raise ValueError(f'Update Machine Error: change_config value not provided or incorrect')

    logging.info(f'Updating replication config for machine with id {cloudendure_machine_id}')

    currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    updated_config_values = {
        "replicationConfiguration": {
            change_config: list_of_changes,
            "replicationTags": [
                {
                    "key": "ManagedBy",
                    "value": "PythonScript"
                },
                {
                    "key": "LastUpdate",
                    "value": currentTime
                }
            ]
        }
    }

    json_config_map = json.dumps(updated_config_values, indent=4)
    logging.info(f'Update machine replication config - request: \n{json_config_map}')

    resp = http_client.patch(url=machine_url, data=json_config_map)
    # Error handling
    resp.raise_for_status()

    logging.warning(f'Update replication config on machine {cloudendure_machine_id} successful - status {resp.status_code} {resp.reason}\n')


def update_blueprint(http_client, cloudendure_url, cloudendure_project_id, cloudendure_blueprint_id, cloudendure_machine_id, change_config, change_values):
    # Update Cloudendure Blueprint - currently supports update of securityGroupIDs and subnetIDs
    blueprint_url = cloudendure_url + "/projects/" + cloudendure_project_id + "/blueprints/" + cloudendure_blueprint_id

    list_of_changes = []

    if change_config == "securityGroupIDs" or change_config == "subnetIDs":
        for key, value in change_values.items():
            list_of_changes.append(value)

    else:
        raise ValueError(f'Update Blueprint Error: change_config value not provided or incorrect - supported values are \'securityGroupIDs\' and \'subnetIDs\'')

    currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    updated_config_values = {
        "machineId": cloudendure_machine_id,
        change_config: list_of_changes,
        "tags": [
            {
                "key": "ManagedBy",
                "value": "PythonScript"
            },
            {
                "key": "LastUpdate",
                "value": currentTime
            }
        ]
    }

    json_config_map = json.dumps(updated_config_values, indent=4)
    logging.info(f'Update blueprint config - request: \n{json_config_map}')

    resp = http_client.patch(url=blueprint_url, data=json_config_map)
    # Error handling
    resp.raise_for_status()

    logging.warning(f'Update blueprint\'s {change_config} config {cloudendure_blueprint_id} successful - status {resp.status_code} {resp.reason}\n')


def get_ec2_instance_sg_and_subnet(ec2_client, ec2_id, aws_source_region, aws_target_region):
    # Find EC2 instance by ID and get its security groups and subnet id; find equivalent subnet id in the target region and generate a map of security groups and subnets to be applied on blueprint

    # Validate that provided instance is running
    response = ec2_client.describe_instance_status(InstanceIds=[ec2_id])
    if response['InstanceStatuses'][0]['InstanceState']['Name'] == 'running':
        try:
            # Get ec2 instance object
            resp = ec2_client.describe_instances(
                Filters=[
                    dict(Name='instance-id', Values=[ec2_id])
                ]
            )
        except ClientError as describeInstancesErr:
            logging.error(describeInstancesErr)

    # SUBNETS
    # Get Subnet name/id from source EC2
    source_subnet_id = resp['Reservations'][0]['Instances'][0]['SubnetId']

    # Find subnet name from id
    source_subnet_name = get_subnet_name(ec2_client, source_subnet_id)

    # Replace AWS region in Subnet name, ex. - from eu-west-1a-private to eu-central-1a-private
    target_subnet_name = convert_subnet_name(source_subnet_name, aws_source_region, aws_target_region)

    # Find subnet id of equivalent subnet in target AWS region
    target_subnet_id = get_subnet_id(aws_target_region, target_subnet_name)

    # Map of subnet name/id
    target_subnet_map = {}
    target_subnet_map[target_subnet_name] = target_subnet_id

    # SECURITY GROUPS
    # Get Security group name/id from source EC2
    source_sg_map = resp['Reservations'][0]['Instances'][0]['SecurityGroups']

    # Find matching security group id in target aws account
    target_sg_map = {}
    for security_group in source_sg_map:
        target_sg_name = security_group['GroupName']
        target_sg_id = get_security_group_id(aws_target_region, target_sg_name)
        target_sg_map[target_sg_name] = target_sg_id

    return target_sg_map, target_subnet_map


def get_subnet_name(ec2_client, subnet_id):
    set_name = False

    # Get subnet name from id
    list_of_subnets = ec2_client.describe_subnets()
    for subnet in list_of_subnets['Subnets']:
        if subnet_id == subnet['SubnetId']:
            for tag in subnet['Tags']:
                if tag["Key"] == 'Name':
                    subnet_name = tag["Value"]
                    set_name = True
                    return subnet_name

    if not set_name:
        raise Exception(f'Provided subnet id does not exist, subnet id: {subnet_id}')


def get_subnet_id(target_aws_region, target_subnet_name):
    # Init EC2 client to target aws_region
    ec2_client = boto3.client('ec2', region_name=target_aws_region)

    id_set = False

    # Get subnet id from name
    list_of_subnets = ec2_client.describe_subnets()
    for subnet in list_of_subnets['Subnets']:
        for tag in subnet['Tags']:
            if tag["Key"] == 'Name':
                current_subnet = tag["Value"]
                if target_subnet_name == current_subnet:
                    subnet_id = subnet["SubnetId"]
                    id_set = True
                    return subnet_id

    if not id_set:
        raise Exception(f'Provided subnet name does not exist, subnet name: {target_subnet_name}')


def convert_subnet_name(source_subnet_name, aws_source_region, aws_target_region):
    # Replace AWS region in Subnet name, ex. - from eu-west-1a-private to eu-central-1a-private
    try:
        converted_subnet_name = source_subnet_name.replace(aws_source_region, aws_target_region)
    except:
        raise Exception(f'Subnet name: {source_subnet_name} could not be converted to target region')

    return converted_subnet_name


def get_security_group_id(target_aws_region, target_security_group_name):
    # Init EC2 client to target aws_region
    ec2_client = boto3.client('ec2', region_name=target_aws_region)

    try:
        # Get subnet id from name
        ec2_response = ec2_client.describe_security_groups(
            Filters=[
                dict(Name='group-name', Values=[target_security_group_name])
            ]
        )
        security_group_id = ec2_response['SecurityGroups'][0]['GroupId']
    except:
        raise Exception(f'Error retrieving target security group: {target_security_group_name}')

    return security_group_id


if __name__ == "__main__":
    main()
