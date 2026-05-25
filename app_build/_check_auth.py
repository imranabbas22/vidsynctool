import sys, os
sys.path.insert(0, '.')
from youtube_analytics import YouTubeAnalyticsFetcher

fetcher = YouTubeAnalyticsFetcher()
creds = fetcher._get_credentials()
if creds:
    print('Credentials found')
    print('Scopes:', creds.scopes)
    print('Valid:', creds.valid)
    print('Expired:', creds.expired)
    print('Has refresh:', creds.refresh_token is not None)
else:
    print('No credentials found')
