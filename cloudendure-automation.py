#!/usr/bin/env python
import requests, boto3, json, sys
from botocore.exceptions import ClientError
from argparse import ArgumentParser

# TODO: better erorr handling on HTTP requests - use raise_for_status()
# TODO: implement debug logging option
def main():
    # Get AWS account name from input param
    parser = ArgumentParser()
    parser.add_argument("--accountName", help="Provide AWS Account Name(ex. ecint-non-prod)", required=True)
    input_args = parser.parse_args()

    # Init HTTP Client Session
    http_client = requests.Session()
    http_client.headers.update({'content-type': 'application/json'})

    # Init EC2 Client
    ec2_client = boto3.client('ec2')

    # Main Cloudendure API URL
    cloudendure_url = "https://console.cloudendure.com/api/latest"
    print(f'Cloudendure API URL set to {cloudendure_url}')

    # Authenticate in Cloudendure
    api_key = "6F1A-C693-6F14-0E7C-F296-C4BE-5CF5-269A-017E-D864-B9D1-2BD6-5693-6A0F-622D-E7E2"
    authenticate(http_client, cloudendure_url, api_key)

    # Get project ID
    project_json_configs = list_projects(http_client, cloudendure_url)
    for project in project_json_configs['items']:
        project_name = project['name']
        project_id = project['id']
        if project_name == input_args.accountName:
            print(f'Working with project [{project_name}]')
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

    # Update blueprint in each cloudendure machine
    for machine in machine_json_configs['items']:
        # Get source EC2's instance id and name
        source_ec2_name = machine['sourceProperties']['name']
        source_ec2_id = machine['sourceProperties']['machineCloudId']

        # Get security groups and subnet from source EC2
        print(f'Get Security Groups from instance {source_ec2_name} / {source_ec2_id}')
        sg_map, subnet = get_ec2_instance_sg_and_subnet(ec2_client, source_ec2_id)
        security_groups = {}
        for security_group in sg_map:
            sg_name = security_group['GroupName']
            sg_id = security_group['GroupId']
            security_groups[sg_name] = sg_id
        print(f'Security groups to be applied {security_groups}')

        # Update security groups in target machine blueprint to match source's
        cloudendure_machine_id = machine['id']
        print(f'Updating Cloudendure Machine with ID: {cloudendure_machine_id}')
        for machine_id, blueprint_id in blueprint_id_map.items():
            if cloudendure_machine_id == machine_id:
                # SG
                print(f'Updating Security Groups in Blueprint with ID: {cloudendure_machine_id}')
                # TODO: temp hardcoded values until tested in internal network
                change_config = "securityGroupIDs"
                security_groups = {
                    'private_db_ecint': 'sg-0244a14e569eaba68',
                    'private_active_directory_client': 'sg-3247085f',
                    'private_db': 'sg-c54906a8',
                    'console': 'sg-d64807bb'
                    }
                update_blueprint(http_client, cloudendure_url, cloudendure_project_id, blueprint_id, machine_id, change_config, security_groups)

                # Subnets
                # TODO: temp hardcoded values until tested in internal network
                change_config = "subnet"
                subnet = "subnet-00741c4d"
                print(f'Updating Subnet in Blueprint with ID: {cloudendure_machine_id}')
                update_blueprint(http_client, cloudendure_url, cloudendure_project_id, blueprint_id, machine_id, change_config, subnet)

                # TODO: print blueprint json after update in case of debug flag 
                #print(get_blueprint(http_client, cloudendure_url, cloudendure_project_id, blueprint_id))

def authenticate(http_client, cloudendure_url, api_key):
    login_url = cloudendure_url + "/login"

    # Login to get Cookie and XSRF token
    resp = http_client.post(url = login_url, json={"userApiToken": api_key})

    if resp.status_code != 200:
        raise Exception('Unable to authenticate to cloudendure, response code:', resp.status_code, resp.reason)

    # Set XSRF Token header for HTTP Session
    xsrf_token = http_client.cookies['XSRF-TOKEN']
    http_client.headers.update({'X-XSRF-TOKEN': xsrf_token})

def list_projects(http_client, cloudendure_url):
    # Get Projects definition and return as JSON
    projects_url = cloudendure_url + "/projects"
    resp = http_client.get(url = projects_url)

    project_list = resp.json()

    if resp.status_code != 200:
        raise Exception('Unable to get list of projects, response code:', resp.status_code, resp.reason)

    return project_list

def list_machines(http_client, cloudendure_url, cloudendure_project_id):
    # Get Machines definition and return as JSON
    machines_url = cloudendure_url + "/projects/" + cloudendure_project_id + "/machines"
    resp = http_client.get(url = machines_url)

    machine_list = resp.json()

    if resp.status_code != 200:
        raise Exception('Unable to get list of machines, response code:', resp.status_code, resp.reason)

    return machine_list

def list_blueprints(http_client, cloudendure_url, cloudendure_project_id):
    # Get Projects definition and return as JSON
    blueprints_url = cloudendure_url + "/projects/" + cloudendure_project_id + "/blueprints"
    resp = http_client.get(url = blueprints_url)

    blueprint_list = resp.json()

    if resp.status_code != 200:
        raise Exception('Unable to get list of projects, response code:', resp.status_code, resp.reason)

    return blueprint_list

def get_blueprint(http_client, cloudendure_url, cloudendure_project_id, cloudendure_blueprint_id):
    blueprint_url = cloudendure_url + "/projects/" + cloudendure_project_id + "/blueprints/" + cloudendure_blueprint_id

    # Get Blueprint definition and return as JSON
    resp = http_client.get(url = blueprint_url)

    blueprint_config = resp.json()

    if resp.status_code != 200:
        raise Exception('Unable to get blueprint, response code:', resp.status_code, resp.reason)

    return blueprint_config

def update_blueprint(http_client, cloudendure_url, cloudendure_project_id, cloudendure_blueprint_id, machine_id, change_config, change_values):
    blueprint_url = cloudendure_url + "/projects/" + cloudendure_project_id + "/blueprints/" + cloudendure_blueprint_id

    if change_config == "SecurityGroups":
        list_of_changes = []
        for key, value in change_values.items():
            list_of_changes.append(value)

        updated_config_values = {
            "machineId": machine_id,
            change_config: list_of_changes,
            }

    # TODO: fix this
    elif change_config == "Subnet":
        updated_config_values = {
            "machineId": machine_id,
            change_config: "",
        }

    else:
        # TODO: change this to an exception
        print(f'change_config value not provided to update_blueprint() function')

    json_config_map = json.dumps(updated_config_values, indent=4)

    resp = http_client.patch(url = blueprint_url, data=json_config_map)

    if resp.status_code != 200:
        raise Exception('Unable to update blueprint, response code:', resp.status_code, resp.reason)
        # TODO: switch this to HTTPError
        # raise Exception('Unable to update blueprint, response code:', resp.status_code, resp.reason)
    else:
        print(f'Update blueprint {cloudendure_blueprint_id} - status {resp.status_code} {resp.reason}')

# TODO: Refactor to both get the security groups and subnet
def get_ec2_instance_sg_and_subnet(ec2_client, ec2_id):
    try:
        # TODO: add better error handling when instance id doesn't match
        resp = ec2_client.describe_instances(
            Filters=[
                # # TODO: uncomment once tested
                # dict(Name='instance-id', Values=[ec2_id])
                dict(Name='instance-id', Values=["i-063f0d9ced870fe0b"])
            ]
        )
    except ClientError as describeInstancesErr:
        print(describeInstancesErr)

    security_group_map = resp['Reservations'][0]['Instances'][0]['SecurityGroups']
    subnet = resp['Reservations'][0]['Instances'][0]['SubnetId']

    return security_group_map, subnet

if __name__ == "__main__":
    main()
