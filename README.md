# cloudendure-automation

Cloudendure automation (tested on Python 3.8.10)

Take AWS account name argument: --accountName (required)
Take Cloudendure API Key argument: --apiKey (optional)
Login to Cloudendure (configure Cookies and XSRF token header)
Find Cloudendure project that matches AWS account name
Go through all machines in Project
Get EC2 instance id associated with machine - take its SGs and Subnet
Update SGs and Subnet in Target machine Blueprint to be the same as source machine - found by name as they have same names but different IDs in the different AWS regions

Example
```
python cloudendure-automation.py --accountName ecint-non-prod
```

Example with different Cloudendure API Key
```
python cloudendure-automation.py --accountName ecint-non-prod --apiKey "9F1A-C693-6F14-0E7C-F296-C4BE-5CF5-249A-017E-D864-B9B1-2BD6-5693-6A0F-622D-E7E2"
```
