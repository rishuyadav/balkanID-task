import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

def fetch_repos(access_token, per_page=60):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Create a session object with retries
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[ 500, 502, 503, 504 ])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    # Fetch user repositories
    user_repos_url = "https://api.github.com/user/repos"
    try:
        response = session.get(user_repos_url, headers=headers)
        response.raise_for_status()
        user_repos = response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch user repositories. Error type: {type(e).__name__}. Error message: {str(e)}")
        user_repos = []

    # Fetch organization repositories using pagination
    org_repos_url = "https://api.github.com/orgs/{org}/repos"
    orgs_url = "https://api.github.com/user/orgs"
    org_repos = []
    try:
        response = session.get(orgs_url, headers=headers)
        response.raise_for_status()
        orgs = response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch organizations. Error type: {type(e).__name__}. Error message: {str(e)}")
        orgs = []
        
    for org in orgs:
        page = 1
        while True:
            try:
                response = session.get(org_repos_url.format(org=org["login"]),
                                        headers=headers,
                                        params={"per_page": per_page, "page": page})
                response.raise_for_status()
                org_repos_page = response.json()
            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to fetch organization repositories. Error type: {type(e).__name__}. Error message: {str(e)}")
                org_repos_page = []
            
            if len(org_repos_page) == 0:
                break

            org_repos += org_repos_page
            page += 1
    
    # Return both user and organization repositories
    return user_repos + org_repos