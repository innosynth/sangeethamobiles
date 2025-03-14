import requests

url = "http://localhost:8080/add-staff"
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJSQUhVTEBleGFtcGxlLmNvbSIsInJvbGUiOiJMMyIsInVzZXJfaWQiOiJlNGVmNzJmZi1iYzRlLTQyOTEtODY4Mi1lYjgwZTJjM2NkN2QiLCJleHAiOjE3NDE5NzY2MDd9.ef_8Hz9rVGrMWAMMWftJIJDtU6Ov1Gl2Hyg63L9dwIs",
    "Content-Type": "application/json",
    "accept": "application/json"
}
data = {
    "staff_name": "Rahul_staff",
    "staff_email": "Rahul_staff@mail.com"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
