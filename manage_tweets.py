import tweepy
import json
f = open("secret_params.json",)
parameters=json.load(f)




# Define your Twitter API credentials
consumer_key = parameters["consumer_key"]
consumer_secret =  parameters["consumer_key_secret"]
access_token =  parameters["access_token"]
access_token_secret =  parameters["access_token_secret"]

# Authenticate with OAuth2
auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret,access_token,access_token_secret)
api = tweepy.API(auth)
api.update_status(status="fek salkdjadsd")