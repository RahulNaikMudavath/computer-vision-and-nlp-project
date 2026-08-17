import requests
import os
from PIL import Image

# 1. Create a dummy image
img = Image.new('RGB', (100, 100), color = 'red')
img_path = 'dummy_test.png'
img.save(img_path)
print("Saved dummy image:", img_path)

try:
    # 2. Login to get access token
    auth_url = "http://localhost:8000/auth/login"
    login_data = {"email": "user_3@example.com", "password": "password3"}
    print("Logging in...")
    token_res = requests.post(auth_url, json=login_data)
    print("Login response status:", token_res.status_code)
    print("Login response:", token_res.text)
    
    if token_res.status_code == 200:
        token = token_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Upload the image to /document/analyze
        upload_url = "http://localhost:8000/document/analyze"
        print("Uploading dummy image...")
        with open(img_path, 'rb') as f:
            files = {'file': (img_path, f, 'image/png')}
            upload_res = requests.post(upload_url, headers=headers, files=files)
            print("Upload response status:", upload_res.status_code)
            print("Upload response text:", upload_res.text)
    else:
        # Try registering a new user first if user_3 doesn't exist
        print("User login failed, attempting registration...")
        reg_url = "http://localhost:8000/auth/register"
        reg_data = {"email": "user_3@example.com", "password": "password3", "full_name": "User Three"}
        reg_res = requests.post(reg_url, json=reg_data)
        print("Registration response:", reg_res.status_code, reg_res.text)
        
        if reg_res.status_code in [200, 201]:
            # Login again
            token_res = requests.post(auth_url, json=login_data)
            token = token_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            upload_url = "http://localhost:8000/document/analyze"
            print("Uploading dummy image...")
            with open(img_path, 'rb') as f:
                files = {'file': (img_path, f, 'image/png')}
                upload_res = requests.post(upload_url, headers=headers, files=files)
                print("Upload response status:", upload_res.status_code)
                print("Upload response text:", upload_res.text)

finally:
    if os.path.exists(img_path):
        os.remove(img_path)
        print("Removed dummy image")
