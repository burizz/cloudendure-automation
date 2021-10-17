#!/usr/bin/env python
import requests, boto3
from botocore.exceptions import ClientError

def main():
    api_key = "6F1A-C693-6F14-0E7C-F296-C4BE-5CF5-269A-017E-D864-B9D1-2BD6-5693-6A0F-622D-E7E2"
    cloudendure_url = "https://console.cloudendure.com/api/latest"
    cloudendure_project_id = "projects/d5aed277-b6fb-4c6c-bedf-bb52799c99f2"

    test_blueprint_id = "f320947e-1555-4cee-9128-58a6cc4dd99c"

    # Init HTTP Client Session
    client = requests.Session()
    client.headers.update({'content-type': 'application/json'})

    # Init EC2 Client
    ec2_client = boto3.client('ec2')

    authenticate(client, cloudendure_url, api_key)
    blueprint_config = get_blueprint(client, cloudendure_url, cloudendure_project_id, test_blueprint_id)

    print(blueprint_config)

    get_security_group_by_name(ec2_client, "private_alb_windows")

def authenticate(client, cloudendure_url, api_key):
    login_url = cloudendure_url + "/login"

    # Login to get Cookie and XSRF token
    resp = client.post(url = login_url, json={"userApiToken": api_key})

    # Set XSRF Token header for HTTP Session
    xsrf_token = client.cookies['XSRF-TOKEN']
    client.headers.update({'X-XSRF-TOKEN': xsrf_token})

def get_blueprint(client, cloudendure_url, cloudendure_project_id, cloudendure_blueprint_id):
    blueprint_url = cloudendure_url + "/" + cloudendure_project_id + "/blueprints/" + cloudendure_blueprint_id

    print(blueprint_url)

    resp = client.get(url = blueprint_url)

    blueprint_config = resp.json()
    return blueprint_config

def get_security_group_by_name(ec2_client, security_group_name):
    try:
        response = ec2_client.describe_security_groups(
            Filters=[
                dict(Name='group-name', Values=[security_group_name])
            ]
        )
        print(response)
    except ClientError as e:
        print(e)

    # return security_groups

def get_vpcs(ec2_client):
    response = ec2_client.describe_vpcs()
    # TODO: test by name instead of ID
    vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')


if __name__ == "__main__":
    main()
