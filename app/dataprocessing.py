# Function to normalize data and deduplicate
def normalize_data(repos):
    normalized_data = []
    seen = set()
    for repo in repos:
        owner = {
            'id': repo['owner']['id'],
            'name': repo['owner']['login'],
            'email': repo['owner'].get('email', '')
        }
        normalized_repo = {
            'id': repo['id'],
            'name': repo['name'],
            'status': 'Public' if repo['private'] == False else 'Private',
            'stars_count': repo['stargazers_count'],
            'owner_id': repo['owner']['id']
        }
        key = (normalized_repo['id'], normalized_repo['owner_id'])
        if key not in seen:
            seen.add(key)
            normalized_data.append({'owner': owner, 'repo': normalized_repo})
    return normalized_data
