import tweepy
import json
from Summerize import Summerize
from Fek_getter import Fek_getter

f = open("secret_params.json",)
parameters=json.load(f)


class Tweeter_post:
    def __init__(self):
    # Define your Twitter API credentials
    self.consumer_key = parameters["consumer_key"]
    self.consumer_secret =  parameters["consumer_key_secret"]
    self.access_token =  parameters["access_token"]
    self.access_token_secret =  parameters["access_token_secret"]


post=Tweeter_post()
client = tweepy.Client(consumer_key=post.consumer_key,
                       consumer_secret=post.consumer_secret,
                       access_token=post.access_token,
                       access_token_secret=post.access_token_secret)
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
