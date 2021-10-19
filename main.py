#!/usr/bin/env python
import requests, boto3, json
from botocore.exceptions import ClientError

# TODO: configurable input params
def main():
    api_key = "6F1A-C693-6F14-0E7C-F296-C4BE-5CF5-269A-017E-D864-B9D1-2BD6-5693-6A0F-622D-E7E2"

    cloudendure_url = "https://console.cloudendure.com/api/latest"
    cloudendure_project_id = "projects/d5aed277-b6fb-4c6c-bedf-bb52799c99f2"
    # TODO: update to make it configurable
    cloudendure_blueprint_id = "f320947e-1555-4cee-9128-58a6cc4dd99c"

    # Init HTTP Client Session
    http_client = requests.Session()
    http_client.headers.update({'content-type': 'application/json'})

    # Init EC2 Client
    ec2_client = boto3.client('ec2')

    # TODO: replace with hardcoded values with values from get_sg and get_subnet functins
    security_group_name = "sftp-sg"
    subnet_name = "eduspire-terraform-subnet-1-private"

    # Get SecurityGroup ID from Name
    security_group_id = get_security_group_id(ec2_client, security_group_name)
    print("security group id:", security_group_id)

    # Get SubnetID from Name
    subnet_id = get_subnet_id(ec2_client, subnet_name)
    print("subnet id:", subnet_id)

    # Authenticate in cloudendure
    authenticate(http_client, cloudendure_url, api_key)

    # Get list of project names and their IDs
    project_json_configs = list_projects(http_client, cloudendure_url)
    projects = {}
    for project in project_json_configs['items']:
        proj_name = project['name']
        proj_id = project['id']
        projects[proj_name] = proj_id
        print(projects)

    # TODO: List all machines and get their IDs
    # TODO: Go through all machines and take SG and Subnet from eu-west-1 and update the same ones in the blueprint

    # get blueprint config json
    blueprint_config = get_blueprint(http_client, cloudendure_url, cloudendure_project_id, cloudendure_blueprint_id)

    # get machine id from blueprint config
    machine_id = blueprint_config['machineId']

    # TODO: Build a list of Security Groups from eu-west-1 and make sure the same ones are defined in blueprintconfig
    # prepare key/value pairs of configs to be updated
    change_config = "securityGroupIDs"
    security_groups = {
        'private_db_ecint': 'sg-0244a14e569eaba68',
        'private_active_directory_client': 'sg-3247085f',
        'private_db': 'sg-c54906a8',
        'console': 'sg-d64807bb',
        }

    # TODO: test with case switches - seems to be supported only by python3.10
    # match change_config:
        # case "securityGroupIDs":
            # update_blueprint(http_client, blueprint_url, machine_id, change_config, security_groups)
        # case _:
            # print("incorrect config value")

# Security Group case
    if change_config == "securityGroupIDs":
        update_blueprint(http_client, cloudendure_url, cloudendure_project_id, cloudendure_blueprint_id, machine_id, change_config, security_groups)
        # udpate blueprint

    change_config = "subnetIDs"
    subnets = {
        'private_subnet1': 'subnet-00741c4d',
        # 'private_subnet2': 'subnet-b70e54dc',
        }

    # Subnet case
    if change_config == "subnetIDs":
        # udpate blueprint
        update_blueprint(http_client, cloudendure_url, cloudendure_project_id, cloudendure_blueprint_id, machine_id, change_config, subnets)


def authenticate(http_client, cloudendure_url, api_key):
    login_url = cloudendure_url + "/login"

    # Login to get Cookie and XSRF token
    resp = http_client.post(url = login_url, json={"userApiToken": api_key})

    # Set XSRF Token header for HTTP Session
    xsrf_token = http_client.cookies['XSRF-TOKEN']
    http_client.headers.update({'X-XSRF-TOKEN': xsrf_token})

def list_projects(http_client, cloudendure_url):
    # Get Projects definition and return as JSON
    projects_url = cloudendure_url + "/projects"
    resp = http_client.get(url = projects_url)

    project_list = resp.json()
    return project_list

def list_machines(http_client, cloudendure_url, cloudendure_project_id):
    machines_url = cloudendure_url + "/" + cloudendure_project_id + "/machines"
    resp = http_client.get(url = machines_url)

    machine_list = resp.json()
    return machine_list

def get_blueprint(http_client, cloudendure_url, cloudendure_project_id, cloudendure_blueprint_id):
    blueprint_url = cloudendure_url + "/" + cloudendure_project_id + "/blueprints/" + cloudendure_blueprint_id

    # Get Blueprint definition and return as JSON
    resp = http_client.get(url = blueprint_url)

    blueprint_config = resp.json()
    return blueprint_config

# TODO: make this a variadic function
# def update_blueprint(http_client, blueprint_url, machine_id, change_config, change_values):
    # # Security Group case
    # if change_config == "security_groups":
        # list_of_sgs = []
        # for key, value in change_values.items():
            # list_of_sgs.append(value)

        # updated_config_values = {
            # "machineId": machine_id,
            # "securityGroupIDs": list_of_sgs,
            # }

    # # Subnet case
    # if change_config == "subnet":
        # list_of_subnets = []
        # for key, value in change_values.items():
            # list_of_subnets.append(value)

        # updated_config_values = {
            # "machineId": machine_id,
            # "subnetIDs": list_of_subnets,
            # }

    # json_config_map = json.dumps(updated_config_values, indent=4)
    # print(json_config_map)

    # resp = http_client.patch(url = blueprint_url, data=json_config_map)
    # print(resp)
    # print(resp.content)

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
    print(json_config_map)

    resp = http_client.patch(url = blueprint_url, data=json_config_map)
    print(resp)
    print(resp.content)

def get_security_group_id(ec2_client, security_group_name):
    try:
        resp = ec2_client.describe_security_groups(
            Filters=[
                dict(Name='group-name', Values=[security_group_name])
            ]
        )
        print(resp)
    except ClientError as e:
        print(e)

    return resp['SecurityGroups'][0]['GroupId']

def get_subnet_id(ec2_client, subnet_name):
    subnets = ec2_client.describe_subnets()

    for subnet in subnets['Subnets']:
        # TODO: test with a name of existing subnet
        # if subnet['Name'] == subnet_name:
            # subnet_id = subnet['SubnetId']
        print(subnet['SubnetId'], "\n")
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
