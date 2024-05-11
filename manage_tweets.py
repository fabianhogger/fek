import tweepy
import json
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
response = client.create_tweet(text='hello world')