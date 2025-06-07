import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def find_logo_url(website):
    try:
        resp = requests.get(website, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Look for <img> tags with 'logo' in id/class/alt
        for img in soup.find_all('img'):
            attrs = ' '.join([img.get('id', ''), ' '.join(img.get('class', [])), img.get('alt', '')]).lower()
            if 'logo' in attrs:
                src = img.get('src')
                if src:
                    return urljoin(website, src)
        # Fallback: favicon
        icon = soup.find('link', rel=lambda x: x and 'icon' in x)
        if icon and icon.get('href'):
            return urljoin(website, icon['href'])
    except Exception as e:
        print(f"Error with {website}: {e}")
    return None

df = pd.read_csv(r"C:\Users\Sayan\Downloads\AI.csv")
df['Logo_URL'] = df['Link'].apply(find_logo_url)
df.to_csv('with_logos.csv', index=False)
