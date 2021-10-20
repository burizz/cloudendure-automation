#!/usr/bin/env python
import requests, boto3, json, sys
from botocore.exceptions import ClientError

def main():
    # TODO: input param project name i.e. - ecint-non-prod
    # TODO: List all projects and get their IDs
    # TODO: List all machines and get their IDs
    # TODO: Go through all machines and take SG and Subnet from eu-west-1 and update the same ones in the blueprint
    # TODO: Build a list of Security Groups and Subnets from eu-west-1 and make sure the same ones are set in blueprint

    # Init HTTP Client Session
    http_client = requests.Session()
    http_client.headers.update({'content-type': 'application/json'})

    # Init EC2 Client
    ec2_client = boto3.client('ec2')

    # Main API URL
    cloudendure_url = "https://console.cloudendure.com/api/latest"

    # TODO: get from project list 
    cloudendure_project_id = "projects/d5aed277-b6fb-4c6c-bedf-bb52799c99f2"
    # TODO: get from machine
    cloudendure_blueprint_id = "f320947e-1555-4cee-9128-58a6cc4dd99c"

    # Get SecurityGroup ID from Name
    # TODO: take name from current SG assigned to EC2 instance
    security_group_name = "sftp-sg"
    security_group_id = get_security_group_id(ec2_client, security_group_name)
    print("security group id:", security_group_id)

    # Get SubnetID from Name
    # TODO: take subnet name(tag) from current subnet of EC2 instance
    subnet_name = "eduspire-terraform-subnet-1-private"
    subnet_id = get_subnet_id(ec2_client, subnet_name)
    print("subnet id:", subnet_id)

    # Authenticate in Cloudendure
    api_key = "6F1A-C693-6F14-0E7C-F296-C4BE-5CF5-269A-017E-D864-B9D1-2BD6-5693-6A0F-622D-E7E2"
    authenticate(http_client, cloudendure_url, api_key)

    # Get list of project names and their IDs
    project_json_configs = list_projects(http_client, cloudendure_url)
    projects = {}
    for project in project_json_configs['items']:
        project_name = project['name']
        project_id = project['id']
        projects[project_name] = project_id

    # Get list of machine objects in each project
    machines = {}
    for project, project_id in projects.items():
        machine_json_configs = list_machines(http_client, cloudendure_url, project_id)
        for machine in machine_json_configs['items']:
            # machine_name = machine['name']
            machine_id = machine['id']
            # ec2_id = machine['machineCloudId']
            # print(machine_name)
            print("machine id:", machine_id)
            # print(ec2_id)
        # items 
            # "id":"700628b3-64aa-41c5-a751-e7ed7f4ad8c2",
            # "machineCloudId":"i-05ac151fba79cd429",
            # "name":"00434-qa-eu-west-1-be-investment-list-dist-db",

    # get blueprint config json
    blueprint_config = get_blueprint(http_client, cloudendure_url, cloudendure_project_id, cloudendure_blueprint_id)

    # get machine id from blueprint config
    machine_id = blueprint_config['machineId']

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
    blueprint_url = cloudendure_url + "/" + cloudendure_project_id + "/blueprints/" + cloudendure_blueprint_id

    # Get Blueprint definition and return as JSON
    resp = http_client.get(url = blueprint_url)

    blueprint_config = resp.json()

    if resp.status_code != 200:
        raise Exception('Unable to get blueprint, response code:', resp.status_code, resp.reason)

    return blueprint_config

def update_blueprint(http_client, cloudendure_url, cloudendure_project_id, cloudendure_blueprint_id, machine_id, change_config, change_values):
    blueprint_url = cloudendure_url + "/" + cloudendure_project_id + "/blueprints/" + cloudendure_blueprint_id
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

def get_security_group_id(ec2_client, security_group_name):
    try:
        resp = ec2_client.describe_security_groups(
            Filters=[
                dict(Name='group-name', Values=[security_group_name])
            ]
        )
        # print(resp)
    except ClientError as e:
        print(e)

    return resp['SecurityGroups'][0]['GroupId']

def get_subnet_id(ec2_client, subnet_name):
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
