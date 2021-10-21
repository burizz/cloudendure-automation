#!/usr/bin/env python
import requests, boto3, json, sys
from botocore.exceptions import ClientError
from argparse import ArgumentParser

def main():
    # TODO: Go through all machines and take SG and Subnet from eu-west-1 and update the same ones in the blueprint
    # TODO: Build a list of Security Groups and Subnets from eu-west-1 and make sure the same ones are set in blueprint
    # Get AWS account name from input param
    parser = ArgumentParser()
    parser.add_argument("--accountName", help="Provide AWS Account Name(ex. ecint-non-prod)", required=True)
    input_args = parser.parse_args()

    # Init HTTP Client Session
    http_client = requests.Session()
    http_client.headers.update({'content-type': 'application/json'})

    # Init EC2 Client
    ec2_client = boto3.client('ec2')

    # Main API URL
    cloudendure_url = "https://console.cloudendure.com/api/latest"

    # Authenticate in Cloudendure
    api_key = "6F1A-C693-6F14-0E7C-F296-C4BE-5CF5-269A-017E-D864-B9D1-2BD6-5693-6A0F-622D-E7E2"
    authenticate(http_client, cloudendure_url, api_key)

    # Get list of project names and their IDs
    project_json_configs = list_projects(http_client, cloudendure_url)
    for project in project_json_configs['items']:
        project_name = project['name']
        project_id = project['id']
        # projects[project_name] = project_id
        if project_name == input_args.accountName:
            cloudendure_project_id = project_id

    # TODO: find blueprint id from machine ?
    cloudendure_blueprint_id = "f320947e-1555-4cee-9128-58a6cc4dd99c"

    # Get list of machine objects in each project
    machine_json_configs = list_machines(http_client, cloudendure_url, project_id)
    for machine in machine_json_configs['items']:
        source_ec2_name = machine['sourceProperties']['name']
        source_ec2_id = machine['sourceProperties']['machineCloudId']
        cloudendure_machine_id = machine['id']
        print("source ec2 name:", source_ec2_name)
        print("source ec2 id:", source_ec2_id)
        print("cloudendure machine id:", cloudendure_machine_id)

    # get blueprint config json
    blueprint_config = get_blueprint(http_client, cloudendure_url, cloudendure_project_id, cloudendure_blueprint_id)

    # get machine id from blueprint config
    machine_id = blueprint_config['machineId']

    # Get SecurityGroup ID from Name
    # TODO: take name from current SG assigned to EC2 instance
    # security_group_name = "sftp-sg"
    security_group_ids = get_ec2_instance_sgs(ec2_client, source_ec2_id)
    for security_group_id in security_group_ids:
        print("security group id:", security_group_id)

    # Get SubnetID from Name
    # TODO: take subnet name(tag) from current subnet of EC2 instance
    # subnet_name = "eduspire-terraform-subnet-1-private"
    # subnet_id = get_subnet(ec2_client, subnet_name)
    # print("subnet id:", subnet_id)

    # prepare key/value pairs of configs to be updated
    change_config = "securityGroupIDs"
    security_groups = {
        'private_db_ecint': 'sg-0244a14e569eaba68',
        'private_active_directory_client': 'sg-3247085f',
        'private_db': 'sg-c54906a8',
        'console': 'sg-d64807bb'
        }

    # change_config = "subnetIDs"
    # subnets = {
        # 'private_subnet1': 'subnet-00741c4d',
        # # 'private_subnet2': 'subnet-b70e54dc',
        # }

    # Security Group case
    update_blueprint(http_client, cloudendure_url, cloudendure_project_id, cloudendure_blueprint_id, machine_id, change_config, security_groups)

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
    machines_url = cloudendure_url + "/projects/" + cloudendure_project_id + "/machines"
    resp = http_client.get(url = machines_url)

    machine_list = resp.json()

    if resp.status_code != 200:
        raise Exception('Unable to get list of machines, response code:', resp.status_code, resp.reason)

    return machine_list

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
    list_of_changes = []
    for key, value in change_values.items():
        list_of_changes.append(value)

    updated_config_values = {
        "machineId": machine_id,
        change_config: list_of_changes,
        }

    json_config_map = json.dumps(updated_config_values, indent=4)

    resp = http_client.patch(url = blueprint_url, data=json_config_map)

    if resp.status_code != 200:
        raise Exception('Unable to update blueprint, response code:', resp.status_code, resp.reason)

def get_ec2_instance_sgs(ec2_client, ec2_id):
    try:
        # TODO: add better error handling when instance id doesn't match
        resp = ec2_client.describe_instances(
            Filters=[
                # dict(Name='instance-id', Values=[ec2_id])
                dict(Name='instance-id', Values=["i-063f0d9ced870fe0b"])
            ]
        )
    except ClientError as err:
        print(err)

    return resp['Reservations'][0]['Instances'][0]['SecurityGroups']

def get_ec2_instance_subnet(ec2_client, ec2_id):
    pass

def get_subnet(ec2_client, subnet_name):
    try:
        subnets = ec2_client.describe_subnets()
    except ClientError as e:
        print(e)

    # for subnet in subnets['Subnets']:
        # TODO: test with a name of existing subnet
        # if subnet['Name'] == subnet_name:
            # subnet_id = subnet['SubnetId']
        # print(subnet['SubnetId'], "\n")
        # TODO: figure out how to match subnet by tag
        # print(subnet['Tags'], "\n")

    # TODO: finish this
    subnet_id = "temp"
    # TODO: add error handling
    # if subnet_id:
        # return error

    return subnet_id

if __name__ == "__main__":
    main()
