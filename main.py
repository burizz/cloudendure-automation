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

    # security_group_name = "private_alb_windows"
    security_group_name = "sftp-sg"
    subnet_name = "test-subnet"

    # Get SecurityGroup ID from Name
    security_group_id = get_security_group_id(ec2_client, security_group_name)
    print("security group id:", security_group_id)

    # Get SubnetID from Name
    subnet_id = get_subnet_id(ec2_client, subnet_name)
    print("subnet id:", subnet_id)

    # authenticate in cloudendure
    authenticate(http_client, cloudendure_url, api_key)

    # build blueprint api url 
    blueprint_url = cloudendure_url + "/" + cloudendure_project_id + "/blueprints/" + cloudendure_blueprint_id

    # get blueprint config json
    blueprint_config = get_blueprint(http_client, blueprint_url)

    # get machine id from blueprint config
    machine_id = blueprint_config['machineId']

    # TODO: Build a list of Security Groups from eu-west-1 and make sure the same ones are defined in blueprintconfig
    # prepare key/value pairs of configs to be updated
    security_groups = {
        'private_db_ecint': 'sg-0244a14e569eaba68',
        'private_active_directory_client': 'sg-3247085f',
        'private_db': 'sg-c54906a8',
        'console': 'sg-d64807bb',
        }

    # udpate blueprint
    update_blueprint(http_client, blueprint_url, machine_id, security_groups)


def authenticate(http_client, cloudendure_url, api_key):
    login_url = cloudendure_url + "/login"

    # Login to get Cookie and XSRF token
    resp = http_client.post(url = login_url, json={"userApiToken": api_key})

    # Set XSRF Token header for HTTP Session
    xsrf_token = http_client.cookies['XSRF-TOKEN']
    http_client.headers.update({'X-XSRF-TOKEN': xsrf_token})

def get_blueprint(http_client, blueprint_url):
    resp = http_client.get(url = blueprint_url)

    blueprint_config = resp.json()
    return blueprint_config

# TODO: make this a variadic function
def update_blueprint(http_client, blueprint_url, machine_id, change_config):
    # if change_config_values == "securityGroupIDs":
    list_of_sgs = []
    for key, value in change_config.items():
        list_of_sgs.append(value)

    updated_config_values = {
        "machineId": machine_id,
        "securityGroupIDs": list_of_sgs,
        }

    json_config_map = json.dumps(updated_config_values, indent=4)
    print(json_config_map)

    resp = http_client.patch(url = blueprint_url, data=json_config_map)
    print(resp)
    print(resp.content)

def get_security_group_id(ec2_client, security_group_name):
    try:
        response = ec2_client.describe_security_groups(
            Filters=[
                dict(Name='group-name', Values=[security_group_name])
            ]
        )
        print(response)
    except ClientError as e:
        print(e)

    return response['SecurityGroups'][0]['GroupId']

def get_subnet_id(ec2_client, subnet_name):
    subnets = ec2_client.describe_subnets()

    for subnet in subnets['Subnets']:
        # TODO: test with a name of existing subnet
        # if subnet['Name'] == subnet_name:
            # subnet_id = subnet['SubnetId']
        print(subnet['SubnetId'], "\n")

    # TODO: finish this
    subnet_id = "temp"
    # TODO: add error handling
    # if subnet_id:
        # return error

    return subnet_id

if __name__ == "__main__":
    main()
