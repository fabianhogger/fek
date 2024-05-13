import tweepy
import json
from Summerize import Summerize
from Fek_getter import Fek_getter

f = open("secret_params.json",)
parameters=json.load(f)




# Define your Twitter API credentials
consumer_key = parameters["consumer_key"]
consumer_secret =  parameters["consumer_key_secret"]
access_token =  parameters["access_token"]
access_token_secret =  parameters["access_token_secret"]



client = tweepy.Client(consumer_key=consumer_key,
                       consumer_secret=consumer_secret,
                       access_token=access_token,
                       access_token_secret=access_token_secret)
# Replace the text with whatever you want to Tweet about


fek_object=Fek_getter()
pdf_obj=fek_object.get_fek()
input=pdf_obj[0]

pdf_obj.teyxos='2089'
pdf_obj.fullo='B'
sum=Summerize()
jsonobj=sum.summerize(input)
print(jsonobj)
print(type(jsonobj))
diction=json.loads(jsonobj)
print(diction['output'])
if(diction['output']):
    response = client.create_tweet(text=diction['output']+' Τεύχος: '+('not' or pdf_obj.teyxos)+' Φύλλο: '+('not found ' or pdf_obj.fullo))
else:
    print('not tweeted')
