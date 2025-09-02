import requests

url = "http://x:x/api-token-auth/"
payload = {
    "username": "x",#change
    "password": "x" #change
}

response = requests.post(url, json=payload)

print("Status Code:", response.status_code)
print("Response:", response.text)
