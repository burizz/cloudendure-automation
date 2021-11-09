# cloudendure-automation

Cloudendure automation (tested on Python 3.8.10)

Script arguments:  
 Cloudendure Project name: --cloudEndureProjectName (required)  
 AWS Source Region: --awsSourceRegion (required)  
 AWS Target Region: --awsTargetRegion (required)  

 AWS Profile: --awsProfile (optional)  
 Cloudendure API Key: --cloudEndureApiKey (optional)  
 Script Log Level --logLevel (optional)  

AWS Account name needs to existing in Cloudendure with the same name  
Example :
```shell
python cloudendure-automation.py --cloudEndureProjectName ecint-non-prod --awsSourceRegion eu-west-1 --awsTargetRegion eu-central-1
```

Example with enabled debug Log Level
```shell
python cloudendure-automation.py --cloudEndureProjectName ecint-non-prod --awsSourceRegion eu-west-1 --awsTargetRegion eu-central-1 --logLevel debug
```

Example with different Cloudendure API Key
```shell
python cloudendure-automation.py --cloudEndureProjectName ecint-non-prod --awsSourceRegion eu-west-1 --awsTargetRegion eu-central-1 --cloudEndureApiKey "9F1A-C693-6F14-0E7C-F296-C4BE-5CF5-249A-017E-D864-B9B1-2BD6-5693-6A0F-622D-E7E2"
```

By default AWS credentials are taken from environment variables. Profile can be provided and used instead
Example with different AWS profile
```shell
python cloudendure-automation.py --cloudEndureProjectName ecint-non-prod --awsSourceRegion eu-west-1 --awsTargetRegion eu-central-1 --awsProfile ecint-non-prod
```
