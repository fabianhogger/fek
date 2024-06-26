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


if __name__=='__main__':
    import sys
    import time
    fek_object=Fek_getter()
    pdf_obj=fek_object.get_fek(year= (int(sys.argv[1]) or 2024), teuxos= (int(sys.argv[2]) or 2), fullo= (int(sys.argv[3]) or 2820 ))
    print(type(pdf_obj  ))
    inpt=pdf_obj[0]   
    sum=Summerize()
    jsonobj=sum.summerize(inpt)
    print(jsonobj)
    print(type(jsonobj))
    diction=json.loads(jsonobj)
    print(diction['output'])
    with open("edit_floor.txt", "w",encoding="utf-8") as f:
        f.write(str(diction['output']))
        print("write anything to stop edit")
        f.close()
    wait=input()
    f=open("edit_floor.txt", "r",encoding="utf-8")
    tweet=f.read()   
    if(diction['output']):
        response = client.create_tweet(text=tweet)
    else:
        print('not tweeted')
