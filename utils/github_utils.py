import streamlit as st
import pandas as pd
import requests
import base64
import json
from io import BytesIO

def get_github_config():
    try:
        return st.secrets["github"]
    except KeyError:
        st.error("GitHub secrets configuration missing.")
        return None

@st.cache_data(ttl=300)
def read_file_from_github(filepath):
    """
    Reads an Excel file from GitHub and returns a DataFrame.
    """
    config = get_github_config()
    if not config:
        return pd.DataFrame()
        
    token = config.get("token")
    repo = config.get("repo")
    branch = config.get("branch", "main")
    
    # Check if token is the dummy one, fallback to local read for development
    if token == "YOUR_GITHUB_TOKEN":
        try:
            return pd.read_excel(filepath)
        except Exception as e:
            st.error(f"Failed to read local file {filepath}: {e}")
            return pd.DataFrame()

    url = f"https://api.github.com/repos/{repo}/contents/{filepath}?ref={branch}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        content = response.json()
        file_content = base64.b64decode(content['content'])
        try:
            df = pd.read_excel(BytesIO(file_content))
            return df
        except Exception as e:
            st.error(f"Error parsing Excel from GitHub: {e}")
            return pd.DataFrame()
    else:
        st.error(f"Error reading from GitHub: {response.status_code} - {response.text}")
        return pd.DataFrame()

def upload_file_to_github(filepath, dataframe_or_bytes, commit_message):
    """
    Commits a file to GitHub via API.
    """
    config = get_github_config()
    if not config:
        return False
        
    token = config.get("token")
    repo = config.get("repo")
    branch = config.get("branch", "main")
    
    # Provide local save fallback for development
    if token == "YOUR_GITHUB_TOKEN":
        import os
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            if isinstance(dataframe_or_bytes, pd.DataFrame):
                dataframe_or_bytes.to_excel(filepath, index=False)
            else:
                with open(filepath, "wb") as f:
                    f.write(dataframe_or_bytes)
            st.success(f"Berkas berhasil disimpan secara lokal: {filepath}")
            read_file_from_github.clear()
            return True
        except Exception as e:
            st.error(f"Gagal menyimpan secara lokal: {e}")
            return False

    # Convert DataFrame to bytes if necessary
    if isinstance(dataframe_or_bytes, pd.DataFrame):
        output = BytesIO()
        dataframe_or_bytes.to_excel(output, index=False)
        content_bytes = output.getvalue()
    else:
        content_bytes = dataframe_or_bytes
        
    content_b64 = base64.b64encode(content_bytes).decode('utf-8')
    url = f"https://api.github.com/repos/{repo}/contents/{filepath}"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Fetch current SHA to update file
    sha = None
    get_response = requests.get(url + f"?ref={branch}", headers=headers)
    if get_response.status_code == 200:
        sha = get_response.json().get("sha")
        
    payload = {
        "message": commit_message,
        "content": content_b64,
        "branch": branch
    }
    if sha:
        payload["sha"] = sha
        
    put_response = requests.put(url, headers=headers, data=json.dumps(payload))
    
    if put_response.status_code in [200, 201]:
        st.success("Berkas berhasil disimpan ke GitHub.")
        read_file_from_github.clear()  # Clear cache after update
        return True
    else:
        st.error(f"Gagal menyimpan ke GitHub, coba lagi dalam beberapa detik. {put_response.text}")
        return False
