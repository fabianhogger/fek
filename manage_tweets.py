from requests_oauthlib import OAuth1Session
import os
import json


# Be sure to add replace the text of the with the text you wish to Tweet. You can also add parameters to post polls, quote Tweets, Tweet with reply settings, and Tweet to Super Followers in addition to other features.
payload = {"text": "gonna be posting fek real soon"}
"""
 #Get request token
request_token_url = "https://api.twitter.com/oauth/request_token?oauth_callback=oob&x_auth_access_type=write"
oauth = OAuth1Session(consumer_key, client_secret=consumer_secret)

#try:
    fetch_response = oauth.fetch_request_token(request_token_url)
except ValueError:
    print(
        "There may have been an issue with the consumer_key or consumer_secret you entered."
    )

resource_owner_key = fetch_response.get("oauth_token")
resource_owner_secret = fetch_response.get("oauth_token_secret")
print("Got OAuth token: %s" % resource_owner_key)

# Get authorization from oauth server
base_authorization_url = "https://api.twitter.com/oauth/authorize"
authorization_url = oauth.authorization_url(base_authorization_url)
print("Please go here and authorize: %s" % authorization_url)
verifier = input("Paste the PIN here: ")

# Get the access token
access_token_url = "https://api.twitter.com/oauth/access_token"
oauth = OAuth1Session(
    consumer_key,
    client_secret=consumer_secret,
    resource_owner_key=resource_owner_key,
    resource_owner_secret=resource_owner_secret,
    verifier=verifier,
)
"""
#oauth_tokens = oauth.fetch_access_token(access_token_url)

#resource_access_token = oauth_tokens["oauth_token"]
#resource_access_token_secret = oauth_tokens["oauth_token_secret"]
#print(resource_access_token)
#print(resource_access_token_secret)
# create the request for resource server
f = open("secret_params.json",)
parameters=json.load(f)

oauth = OAuth1Session(
    parameters['consumer_key'],
    client_secret=parameters['consumer_key_secret'],
    resource_owner_key=parameters['resource_token'],
    resource_owner_secret=parameters['resource_secret'],
)

# Making the request
response = oauth.post(
    "https://api.twitter.com/2/tweets",
    json=payload,
)
if response.status_code != 201:
    raise Exception(
        "Request returned an error: {} {}".format(response.status_code, response.text)
    )

print("Response code: {}".format(response.status_code))

# Saving the response as JSON
json_response = response.json()
print(json.dumps(json_response, indent=4, sort_keys=True))