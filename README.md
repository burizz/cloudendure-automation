# cloudendure-automation

Cloudendure automation (tested on Python 3.8.10)

Script arguments :
 AWS Account name: --accountName (required)  
 AWS Region: --awsRegion (required)

 AWS Profile: --awsProfile (optional)
 Cloudendure API Key: --apiKey (optional)  

AWS Account name needs to existing in Cloudendure with the same name
Example
```
python cloudendure-automation.py --accountName ecint-non-prod --awsRegion eu-west-1
```

Example with different Cloudendure API Key
```
python cloudendure-automation.py --accountName ecint-non-prod --awsRegion eu-west-1 --apiKey "9F1A-C693-6F14-0E7C-F296-C4BE-5CF5-249A-017E-D864-B9B1-2BD6-5693-6A0F-622D-E7E2"
```

By default AWS credentials are taken from environment variables. Profile can be provided and used instead
Example with different AWS profile
```
python cloudendure-automation.py --accountName ecint-non-prod --awsProfile ecint-non-prod
```
