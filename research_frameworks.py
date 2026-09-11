import urllib.request
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(
    'https://html.duckduckgo.com/html/?q=how+to+chunk+million+documents+python+generator+yield+memory+efficient',
    headers={'User-Agent': 'Mozilla/5.0'}
)

try:
    with urllib.request.urlopen(req, context=ctx) as response:
        html = response.read().decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        results = soup.find_all('a', class_='result__snippet')

        for r in results[:3]:
            print(r.text)
            print('-'*40)
except Exception as e:
    print(f'Error: {e}')
