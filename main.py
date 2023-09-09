# Github Repository: https://github.com/Prem-ium/youtube-analytics-bot

# BSD 3-Clause License
# 
# Copyright (c) 2022-present, Prem Patel
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os, datetime, traceback, calendar, requests, json, asyncio

from calendar                       import monthrange
from dotenv                         import load_dotenv
from time                           import sleep

import discord
import google, google_auth_oauthlib, googleapiclient.errors


from oauth2client.client            import HttpAccessTokenRefreshError
from google_auth_oauthlib.flow      import InstalledAppFlow
from google.auth.exceptions         import RefreshError, GoogleAuthError
from googleapiclient.discovery      import build, build_from_document
from oauth2client.file              import Storage
from discord.ext                    import commands, tasks
from oauth2client                   import client, tools
from google.oauth2.credentials      import Credentials

# Import .env variables
load_dotenv()

if not os.environ["DISCORD_TOKEN"]:
    raise Exception("ERROR: `DISCORD_TOKEN` is missing in .env, please add it and restart.")
elif not os.environ["YOUTUBE_API_KEY"]:
    raise Exception("ERROR: `YOUTUBE_API_KEY` is missing in .env, please add it and restart.")

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
DISCORD_CHANNEL = os.environ.get("DISCORD_CHANNEL", None)

if DISCORD_CHANNEL:
    DISCORD_CHANNEL = int(DISCORD_CHANNEL)

YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]

if (os.environ.get("KEEP_ALIVE", "False").lower() == "true"):
    from keep_alive                 import keep_alive
    keep_alive()

DEV_MODE = (os.environ.get("DEV_MODE", "False").lower() == "true")

if DEV_MODE:
    print(f'{"- "*25}\nAttention: Developer mode enabled.\nThe program will be relying on CLIENT_SECRET JSON Dict to be assigned to the proper .env variable & will not search/use for a CLIENT_SECRET.json file.\n{"- "*25}')
   
    try:        CLIENT_SECRETS = json.loads(os.environ.get("CLIENT_SECRET", None))['installed']
    except:     raise Exception("CLIENT_SECRET is missing within .env file, please add it and try again.")
    
else:
    CLIENT_SECRETS = os.environ.get("CLIENT_PATH", "CLIENT_SECRET.json")

# Declare global scope
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/yt-analytics-monetary.readonly"]

def get_service (API_SERVICE_NAME='youtubeAnalytics', API_VERSION='v2', SCOPES=SCOPES):
    global DEV_MODE, CLIENT_SECRETS

    # Build the service object if DEV_MODE is enabled, otherwise use the credentials.json file
    if DEV_MODE:
        try:
            credentials = Credentials.from_authorized_user_info(CLIENT_SECRETS)
            return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
        except: print(f'Failed to build service: {e}\n{traceback.format_exc()}')

    try:
        credential_path = os.path.join('./', 'credentials.json')
        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRETS, SCOPES)
            credentials = tools.run_flow(flow, store)
        return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    except: print(f'Failed to run client flow service: {e}\n{traceback.format_exc()}')
    
    try:
        credentials = Credentials.from_authorized_user_info(CLIENT_SECRETS)
        json_path = 'API_Service/Analytics-Service.json' if API_SERVICE_NAME == 'youtubeAnalytics' else 'API_Service/YouTube-Data-API.json'
        print(f'Building failed (This is expected behavior on replit.com), trying to build from document: {json_path}')
        with open(json_path) as f:
            service = json.load(f)
        return build_from_document(service, credentials = credentials)
    except Exception as e:
        print(f'Failed: Exhaused all get_service methods: {e}\n{traceback.format_exc()}')
        raise

def refresh_token (token=None):
    print(f'Refreshing Credentials Access Token...')
    global DEV_MODE
    if DEV_MODE:
        global CLIENT_SECRETS
        global YOUTUBE_ANALYTICS
        global YOUTUBE_DATA

        if token is not None:
            try:
                refresh_token = {"refresh_token": token}
                CLIENT_SECRETS.update(refresh_token)
                return f"Dev Mode: Successfully updated refresh token to {token}\nYou will need to update if the bot is restarted.\n"
            except Exception as e: return f"Ran into {e.__class__.__name__} Exception: {e}"

        data = {
            'client_id': CLIENT_SECRETS['client_id'],
            'client_secret': CLIENT_SECRETS['client_secret'],
            'refresh_token': CLIENT_SECRETS['refresh_token'],
            'grant_type': 'refresh_token'
        }
        response = requests.post('https://accounts.google.com/o/oauth2/token', data=data)
        if response.status_code == 200:
            response_json = response.json()
            CLIENT_SECRETS['access_token'] = response_json['access_token']
            CLIENT_SECRETS['expires_in'] = response_json['expires_in']

            # Calculate and update token expiry time
            now = datetime.datetime.now()
            CLIENT_SECRETS['token_expiry'] = (now + datetime.timedelta(seconds=response_json['expires_in'])).isoformat()

            message = f"{response.status_code}:\tSuccessfully refreshed token\n{datetime.datetime.now()}\n"
            YOUTUBE_ANALYTICS = get_service()
            YOUTUBE_DATA = get_service('youtube', 'v3', SCOPES)
        else:
            message = f"{response.status_code}:\tFalied to refresh token\t{datetime.datetime.now()}\n{response.text}"
    else:
        message = None
        with open('credentials.json') as f:
            cred = json.load(f)
            data = {
                'client_id': cred['client_id'],
                'client_secret': cred['client_secret'],
                'refresh_token': cred['refresh_token'],
                'grant_type': 'refresh_token'
            }

            response = requests.post('https://accounts.google.com/o/oauth2/token', data=data)
            if response.status_code == 200:
                response_json = response.json()
            
                # Update token_response with new access token and expiry time
                cred['token_response']['access_token'] = response_json['access_token']
                cred['token_response']['expires_in'] = response_json['expires_in']
                
                # Calculate and update token expiry time
                now = datetime.datetime.now()
                cred['token_expiry'] = (now + datetime.timedelta(seconds=response_json['expires_in'])).isoformat()
                message = f"{response.status_code}:\tSuccessfully refreshed token\n{datetime.datetime.now()}\n"
                # Save updated credentials to file
                with open('credentials.json', 'w') as f:
                    json.dump(cred, f)
            else:
                message = f"{response.status_code}:\tFalied to refresh token\t{datetime.datetime.now()}\n{response.text}"
    return message

# Swap between dev mode and normal mode
async def dev_mode():
    global DEV_MODE, CLIENT_SECRETS
    DEV_MODE = not DEV_MODE
    if DEV_MODE:
        print(f'Developer mode is enabled. The program will be relying on CLIENT_SECRET JSON Dict to be assigned to the proper .env variable. (Not JSON file). Check .env.example for an example--Remember to add your refresh token in the JSON.\n\n')
        try:        CLIENT_SECRETS = json.loads(os.environ.get("CLIENT_SECRET", None))['installed']
        except:     raise Exception("CLIENT_SECRET is missing within .env file, please add it and try again.")
        
    else:
        CLIENT_SECRETS = os.environ.get("CLIENT_PATH", "CLIENT_SECRET.json")

def execute_api_request(client_library_function, **kwargs):
    return client_library_function(**kwargs).execute()

# Refresh the token
async def refresh(return_embed=False, token=None):
    message = refresh_token(token)
    if return_embed:
        embed = discord.Embed(title=f"YouTube Analytics Bot Refresh", color=0x00ff00)
        embed.add_field(name="Status", value=message, inline=False)
        return embed
    else:
        return message

# Change dates to API format
async def update_dates (startDate, endDate):
    #print(f'Received start date: {startDate} and end date: {endDate}')
    splitStartDate, splitEndDate = startDate.split('/'), endDate.split('/')

    # If the start and end dates are in the first month of the year & they are the same date
    if (splitStartDate[1] == '01' and (splitStartDate[0] == splitEndDate[0] and splitEndDate[1] in ['01', '02', '03'])):
        year = startDate.split('/')[2] if (len(startDate.split('/')) > 2) else datetime.datetime.now().strftime("%Y")
        year = str(int(year) - 1 if int(splitStartDate[0]) == 1 else year)
        year = f'20{year}' if len(year) == 2 else year

        previousMonth = int(splitStartDate[0]) - 1 if int(splitStartDate[0]) > 1 else 12
        lastDay = monthrange(int(year), previousMonth)[1]

        # Set the start and end dates to the previous month
        startDate = datetime.datetime.strptime(f'{previousMonth}/01', '%m/%d').strftime(f'{year}/%m/%d').replace('/', '-')
        endDate = datetime.datetime.strptime(f'{previousMonth}/{lastDay}', '%m/%d').strftime(f'{year}/%m/%d').replace('/', '-')

    # If the start or end date is missing the year
    elif len(startDate) != 5 or len(endDate) != 5:
        # Set the start and end dates to the full date including the year
        startDate = datetime.datetime.strptime(startDate, '%m/%d/%y').strftime('%Y/%m/%d').replace('/', '-')
        endDate = datetime.datetime.strptime(endDate, '%m/%d/%y').strftime('%Y/%m/%d').replace('/', '-')
    else:
        currentYear = datetime.datetime.now().strftime("%Y")
        if len(startDate) == 5:
            startDate = datetime.datetime.strptime(startDate, '%m/%d').strftime(f'{currentYear}/%m/%d').replace('/', '-')
        if len(endDate) == 5:
            endDate = datetime.datetime.strptime(endDate, '%m/%d').strftime(f'{currentYear}/%m/%d').replace('/', '-')

    #print(f'Updated dates to {startDate} - {endDate}')
    return startDate, endDate


# Discord bot command methods.
async def get_stats (start=datetime.datetime.now().strftime("%Y-%m-01"), end=datetime.datetime.now().strftime("%Y-%m-%d")):
    try:
        # Query the YouTube Analytics API
        response = execute_api_request(
            YOUTUBE_ANALYTICS.reports().query,
            ids='channel==MINE',
            startDate=start,
            endDate=end,
            metrics='views,estimatedMinutesWatched,subscribersGained,subscribersLost,estimatedRevenue,cpm,monetizedPlaybacks,playbackBasedCpm,adImpressions,likes,dislikes,averageViewDuration,shares,averageViewPercentage,subscribersGained,subscribersLost',
        )

        # Retrieve the data from the response
        views = response['rows'][0][0]
        minutes = response['rows'][0][1]
        subscribersGained = response['rows'][0][2] - response['rows'][0][3]
        revenue = response['rows'][0][4]
        cpm = response['rows'][0][5]
        monetizedPlaybacks = response['rows'][0][6]
        playbackCpm = response['rows'][0][7]
        adImpressions = response['rows'][0][8]
        likes = response['rows'][0][9]
        dislikes = response['rows'][0][10]
        averageViewDuration = response['rows'][0][11]
        shares = response['rows'][0][12]
        averageViewPercentage = response['rows'][0][13]
        subscribersGained = response['rows'][0][14]
        subscribersLost = response['rows'][0][15]
        netSubscribers = subscribersGained - subscribersLost

        # Terminary operator to check if start/end year share a year, and strip/remove if that's the case
        start, end = (start[5:] if start[:4] == end[:4] else f'{start[5:]}-{start[:4]}').replace('-', '/'), (end[5:] if start[:4] == end[:4] else f'{end[5:]}-{end[:4]}').replace('-', '/')

        # create a Discord Embed object
        embed = discord.Embed(title=f"YouTube Analytics Report ({start} - {end})", color=0x00ff00)

        # add fields to the embed
        embed.add_field(name="Views", value=f"{round(views,2):,}", inline=True)
        embed.add_field(name="Ratings", value=f"{100*round(likes/(likes + dislikes),2):,}%", inline=True)
        embed.add_field(name="Minutes Watched", value=f"{round(minutes,2):,}", inline=True)
        embed.add_field(name="Average View Duration", value=f"{round(averageViewDuration,2):,}s ({round(averageViewPercentage,2):,}%)", inline=True)
        embed.add_field(name="Net Subscribers", value=f"{round(netSubscribers,2):,}", inline=True)
        embed.add_field(name="Shares", value=f"{round(shares,2):,}", inline=True)
        
        embed.add_field(name="\u200b", value="\u200b", inline=False)

        embed.add_field(name="Estimated Revenue", value=f"${round(revenue,2):,}", inline=True)
        embed.add_field(name="CPM", value=f"${round(cpm,2):,}", inline=True)
        embed.add_field(name="Monetized Playbacks (±2.0%)", value=f"{round(monetizedPlaybacks,2):,}", inline=True)
        embed.add_field(name="Playback CPM", value=f"${round(playbackCpm,2):,}", inline=True)
        embed.add_field(name="Ad Impressions", value=f"{round(adImpressions,2):,}", inline=True)

        # Build the response string
        response_str = f'YouTube Analytics Report ({start}\t-\t{end})\n\n'
        response_str += f'Views:\t{round(views,2):,}\nRatings:\t{100*round(likes/(likes + dislikes),2):,}%\nMinutes Watched:\t{round(minutes,2):,}\nAverage View Duration:\t{round(averageViewDuration,2):,}s ({round(averageViewPercentage,2):,}%)\nNet Subscribers:\t{round(netSubscribers,2):,}\nShares:\t{round(shares,2):,}\n\n'
        response_str += f'Estimated Revenue:\t${round(revenue,2):,}\nCPM:\t${round(cpm,2):,}\nMonetized Playbacks (±2.0%):\t{round(monetizedPlaybacks,2):,}\nPlayback CPM:\t${round(playbackCpm,2):,}\nAd Impressions:\t{round(adImpressions,2):,}'
        print(response_str + '\nSending to Discord...')

        return embed, response_str
    
    except HttpAccessTokenRefreshError:     return "The credentials have been revoked or expired, please re-run the application to re-authorize."
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, {traceback.format_exc()}"


async def top_revenue (results=10, start=datetime.datetime.now().strftime("%Y-%m-01"), end=datetime.datetime.now().strftime("%Y-%m-%d")):
    try:
        # Query the YouTube Analytics API
        response = execute_api_request(
            YOUTUBE_ANALYTICS.reports().query,
            ids='channel==MINE',
            startDate=start,
            endDate=end,
            dimensions='video',
            metrics='estimatedRevenue',
            sort='-estimatedRevenue',
            maxResults=results,
        )

        # Retrieve video IDs and earnings from the response
        video_ids = []
        earnings = []
        for data in response['rows']:
            video_ids.append(data[0])
            earnings.append(data[1])

        # Query the YouTube Data API
        request = YOUTUBE_DATA.videos().list(
            part="snippet",
            id=','.join(video_ids)
        )
        response = request.execute()

        # Format the start and end dates
        start, end = (start[5:] if start[:4] == end[:4] else f'{start[5:]}-{start[:4]}').replace('-', '/'), (end[5:] if start[:4] == end[:4] else f'{end[5:]}-{end[:4]}').replace('-', '/')

        # create a Discord Embed object
        embed = discord.Embed(title=f"Top {results} Earning Videos ({start} - {end})", color=0x00ff00)

        total = 0
        for i in range(len(response['items'])):
            embed.add_field(name=f"{i + 1}) {response['items'][i]['snippet']['title']}:\t${round(earnings[i], 2):,}", value=f"------------------------------------------------------------------------------------", inline=False)
            total += earnings[i]
        embed.add_field(name="\u200b", value="\u200b", inline=False)
        embed.add_field(name=f"Top {results} Total Earnings", value=f"${round(total, 2):,}", inline=False)

        # Build the response string
        response_str = f'Top {results} Earning Videos ({start}\t-\t{end}):\n\n'
        total = 0
        for i in range(len(response['items'])):
            response_str += f'{i + 1}) {response["items"][i]["snippet"]["title"]} - ${round(earnings[i], 2):,}\n'
            total += earnings[i]
        response_str += f'\n\nTop {results} Total Earnings: ${round(total, 2):,}'
        print(response_str)

        return embed, response_str
    
    except HttpAccessTokenRefreshError:     return "The credentials have been revoked or expired, please re-run the application to re-authorize."
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, {traceback.format_exc()}"


async def top_countries_by_revenue (results=10, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")):
    try:
        # Query the YouTube Analytics API
        response = execute_api_request(
            YOUTUBE_ANALYTICS.reports().query,
            ids='channel==MINE',
            startDate=startDate,
            endDate=endDate,
            dimensions='country',
            metrics='estimatedRevenue',
            sort='-estimatedRevenue',
            maxResults=results,
        )

        # Format the start and end dates
        startDate, endDate = (startDate[5:] if startDate[:4] == endDate[:4] else f'{startDate[5:]}-{startDate[:4]}').replace(
            '-', '/'), (endDate[5:] if startDate[:4] == endDate[:4] else f'{endDate[5:]}-{endDate[:4]}').replace('-', '/')

        # Build the response string
        return_str = f'Top {results} Countries by Revenue: ({startDate}\t-\t{endDate})\n'

        embed = discord.Embed(title=f"Top {results} Countries by Revenue: ({startDate} - {endDate})", color=0x00ff00)
        for row in response['rows']:
            embed.add_field(name=f"{row[0]}:\t\t${round(row[1],2):,}", value=f"${round(row[1],2):,}", inline=False)
            return_str += f'{row[0]}:\t\t${round(row[1],2):,}\n'
            print(row[0], row[1])
        
        embed.add_field(name="\u200b", value="\u200b", inline=False)

        return embed, return_str
    
    except HttpAccessTokenRefreshError:     return "The credentials have been revoked or expired, please re-run the application to re-authorize."
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, {traceback.format_exc()}"


async def get_ad_preformance (start=datetime.datetime.now().strftime("%Y-%m-01"), end=datetime.datetime.now().strftime("%Y-%m-%d")):
    try:
        response = execute_api_request(
            YOUTUBE_ANALYTICS.reports().query,
            ids='channel==MINE',
            startDate=start,
            endDate=end,
            dimensions='adType',
            metrics='grossRevenue,adImpressions,cpm',
            sort='-grossRevenue'
        )

        # Terminary operator to check if start/end year share a year, and strip/remove if that's the case
        start_str = (start[5:] if start[:4] == end[:4] else f'{start[5:]}-{start[:4]}').replace('-', '/')
        end_str = (end[5:] if start[:4] == end[:4] else f'{end[5:]}-{end[:4]}').replace('-', '/')

        response_str = f'Ad Preformance ({start_str}\t-\t{end_str})\n\n'
        embed = discord.Embed(title=f"Ad Preformance ({start_str} - {end_str})", color=0x00ff00)
        # Parse the response into nice formatted string
        for row in response['rows']:
            embed.add_field(name=f"{row[0]}:\t\t${round(row[1],2):,}", value=f"Gross Revenue:\t${round(row[1],2):,}\tCPM:\t${round(row[3],2):,}\tImpressions:\t{round(row[2],2):,}", inline=False)
            response_str += f'Ad Type:\t{row[0]}\n\tGross Revenue:\t${round(row[1],2):,}\tCPM:\t${round(row[3],2):,}\tImpressions:\t{round(row[2],2):,}\n\n\n'

        return embed, response_str
    
    except HttpAccessTokenRefreshError:     return "The credentials have been revoked or expired, please re-run the application to re-authorize."
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, {traceback.format_exc()}"

# More detailed geo data/report
async def get_detailed_georeport (results=5, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")):
    try:
        # Get top preforming countries by revenue
        response = execute_api_request(
            YOUTUBE_ANALYTICS.reports().query,
            ids='channel==MINE',
            startDate=startDate,
            endDate=endDate,
            dimensions='country',
            metrics='views,estimatedRevenue,estimatedAdRevenue,estimatedRedPartnerRevenue,grossRevenue,adImpressions,cpm,playbackBasedCpm,monetizedPlaybacks',
            sort='-estimatedRevenue',
            maxResults=results,
        )

        # Parse the response using rows and columnHeaders
        response_str = f'Top {results} Countries by Revenue: ({startDate} - {endDate})\n\n'
        embed = discord.Embed(title=f"Top {results} Countries by Revenue: ({startDate} - {endDate})", color=0x00ff00)
        for row in response['rows']:
            response_str += f'{row[0]}:\n'
            for i in range(len(row)):
                if "country" in response["columnHeaders"][i]["name"]:
                    continue
                response_str += f'\t{response["columnHeaders"][i]["name"]}:\t{round(row[i],2):,}\n'
                embed.add_field(name=f"{response['columnHeaders'][i]['name']}:", value=f"{round(row[i],2):,}", inline=False)
            response_str += '\n'

        print(f'Data received:\t{response}\n\nReport Generated:\n{response_str}')
        return embed, response_str
    
    except HttpAccessTokenRefreshError:     return "The credentials have been revoked or expired, please re-run the application to re-authorize."
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, {traceback.format_exc()}"

async def get_demographics (startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")):
    try:
        # Get top preforming countries by revenue
        response = execute_api_request(
            YOUTUBE_ANALYTICS.reports().query,
            dimensions="ageGroup,gender",
            ids='channel==MINE',
            startDate=startDate,
            endDate=endDate,
            metrics="viewerPercentage",
            sort="-viewerPercentage",
        )
        startDate, endDate = (startDate[5:] if startDate[:4] == endDate[:4] else f'{startDate[5:]}-{startDate[:4]}').replace('-', '/'), (endDate[5:] if startDate[:4] == endDate[:4] else f'{endDate[5:]}-{endDate[:4]}').replace('-', '/')
        response_str = f'Gender Viewership Demographics ({startDate}\t-\t{endDate})\n\n'
        embed = discord.Embed(title=f"Gender Viewership Demographics ({startDate}\t-\t{endDate})", color=0x00ff00)

        # Parse the response into nice formatted string
        for row in response['rows']:
            if round(row[2],2) < 1: break
            row[0] = row[0].split('e')

            response_str += f'{round(row[2],2)}% Views come from {row[1]} with age of {row[0][1]}\n'
            embed.add_field(name=f"{round(row[2],2)}% Views come from {row[1]} with age of {row[0][1]}", value=f"{round(row[2],2)}%", inline=False)
        print(f'Demographics Report Generated & Sent:\n{response_str}')
        return embed, response_str
    
    except HttpAccessTokenRefreshError:     return "The credentials have been revoked or expired, please re-run the application to re-authorize."
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, {traceback.format_exc()}"

async def get_shares (results = 5, start=datetime.datetime.now().strftime("%Y-%m-01"), end=datetime.datetime.now().strftime("%Y-%m-%d")):
    try:
        request = YOUTUBE_ANALYTICS.reports().query(
            dimensions="sharingService",
            startDate=start,
            endDate=end,
            ids="channel==MINE",
            maxResults=results,
            metrics="shares",
            sort="-shares"
        ).execute()

        # Terminary operator to check if start/end year share a year, and strip/remove if that's the case
        start_str, end_str = (start[5:] if start[:4] == end[:4] else f'{start[5:]}-{start[:4]}').replace('-', '/'), (end[5:] if start[:4] == end[:4] else f'{end[5:]}-{end[:4]}').replace('-', '/')

        response_str = f'Top Sharing Services ({start_str}\t-\t{end_str})\n\n'
        embed = discord.Embed(title=f"Top Sharing Services ({start_str}\t-\t{end_str})", color=0x00ff00)
        # Parse the response into nice formatted string
        for row in request['rows']:
            response_str += f'{row[0].replace("_", " ")}:\t{row[1]:,}\n'
            embed.add_field(name=f'{row[0].replace("_", " ")}:', value=f"{row[1]:,}", inline=False)
        print(f'Shares Report Generated & Sent:\n{response_str}')
        return embed, response_str
    
    except HttpAccessTokenRefreshError:     return "The credentials have been revoked or expired, please re-run the application to re-authorize."
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, {traceback.format_exc()}"

async def get_traffic_source (results=10, start=datetime.datetime.now().strftime("%Y-%m-01"), end=datetime.datetime.now().strftime("%Y-%m-%d")):
    try:
        request = YOUTUBE_ANALYTICS.reports().query(
            dimensions="insightTrafficSourceDetail",
            endDate=end,
            filters="insightTrafficSourceType==YT_SEARCH",
            ids="channel==MINE",
            maxResults=results,
            metrics="views",
            sort="-views",
            startDate=start
        ).execute()

        # Terminary operator to check if start/end year share a year, and strip/remove if that's the case
        start_str, end_str = (start[5:] if start[:4] == end[:4] else f'{start[5:]}-{start[:4]}').replace('-', '/'), (end[5:] if start[:4] == end[:4] else f'{end[5:]}-{end[:4]}').replace('-', '/')

        response_str = f'Top Search Traffic Terms ({start_str}\t-\t{end_str})\n\n'
        embed = discord.Embed(title=f"Top Search Traffic Terms ({start_str}\t-\t{end_str})", color=0x00ff00)
        # Parse the response into nice formatted string
        for row in request['rows']:
            response_str += f'{row[0].replace("_", " ")}:\t{row[1]:,}\n'
            embed.add_field(name=f'{row[0].replace("_", " ")}:', value=f"{row[1]:,}", inline=False)
        print(f'Traffic Report Generated:\n{response_str}')

        return embed, response_str
    
    except HttpAccessTokenRefreshError:     return "The credentials have been revoked or expired, please re-run the application to re-authorize."
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, {traceback.format_exc()}"


async def get_operating_stats (results = 10, start=datetime.datetime.now().strftime("%Y-%m-01"), end=datetime.datetime.now().strftime("%Y-%m-%d")):
    try:
        request = YOUTUBE_ANALYTICS.reports().query(
            dimensions="operatingSystem",
            endDate=end,
            maxResults=results,
            ids="channel==MINE",
            metrics="views,estimatedMinutesWatched",
            sort="-views,estimatedMinutesWatched",
            startDate=start
        ).execute()
        start_str, end_str = (start[5:] if start[:4] == end[:4] else f'{start[5:]}-{start[:4]}').replace('-', '/'), (end[5:] if start[:4] == end[:4] else f'{end[5:]}-{end[:4]}').replace('-', '/')
        response_str = f'Top Operating System ({start_str}\t-\t{end_str})\n'
        embed = discord.Embed(title=f"Top Operating System ({start_str}\t-\t{end_str})", color=0x00ff00)
        for row in request['rows']:
            response_str += f'\t{row[0]}:\n\t\tViews:\t\t{round(row[1], 2):,}\n\t\tEstimated Watchtime:\t\t{round(row[2],2):,}\n'
            embed.add_field(name=f'{row[0]}:', value=f"Views:\t\t{round(row[1], 2):,}\nEstimated Watchtime:\t\t{round(row[2],2):,}", inline=False)
        print(response_str)
        return embed, response_str
    
    except HttpAccessTokenRefreshError:     return "The credentials have been revoked or expired, please re-run the application to re-authorize."
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, {traceback.format_exc()}"
    
async def get_playlist_stats (results = 5, start=datetime.datetime.now().strftime("%Y-%m-01"), end=datetime.datetime.now().strftime("%Y-%m-%d")):
    try:
        request = YOUTUBE_ANALYTICS.reports().query(
            dimensions="playlist",
            endDate=end,
            filters="isCurated==1",
            ids="channel==MINE",
            maxResults=results,
            metrics="estimatedMinutesWatched,views,playlistStarts,averageTimeInPlaylist",
            sort="-views",
            startDate=start
        )
        response = request.execute()

        playlist_ids = ','.join([row[0] for row in response['rows']])
        playlist_ids = []
        views = []
        playlist_starts = []
        average_time_in_playlist = []
        estimated_minutes_watched = []
        for row in response['rows']:
            playlist_ids.append(row[0])
            views.append(row[1])
            playlist_starts.append(row[2])
            average_time_in_playlist.append(row[3])
            estimated_minutes_watched.append(row[4])

        request = YOUTUBE_DATA.playlists().list(
            part="snippet",
            id=playlist_ids
        )
        response = request.execute()
        start, end = (start[5:] if start[:4] == end[:4] else f'{start[5:]}-{start[:4]}').replace('-', '/'), (end[5:] if start[:4] == end[:4] else f'{end[5:]}-{end[:4]}').replace('-', '/')
        response_str = f'```YouTube Analytics Report ({start}\t-\t{end})\n\n'
        embed = discord.Embed(title=f"Top Operating System ({start}\t-\t{end})", color=0x00ff00)
        for row in response['items']:
            response_str += f"{row['snippet']['title']}:\nViews: {views[playlist_ids.index(row['id'])]}\nPlaylist Starts: {playlist_starts[playlist_ids.index(row['id'])]}\nAverage Time Spent in Playlist: {average_time_in_playlist[playlist_ids.index(row['id'])]}\nEstimated Minutes Watched: {estimated_minutes_watched[playlist_ids.index(row['id'])]}\n\n"
            embed.add_field(name=f'{row["snippet"]["title"]}:', value=f"Views: {views[playlist_ids.index(row['id'])]}\nPlaylist Starts: {playlist_starts[playlist_ids.index(row['id'])]}\nAverage Time Spent in Playlist: {average_time_in_playlist[playlist_ids.index(row['id'])]}\nEstimated Minutes Watched: {estimated_minutes_watched[playlist_ids.index(row['id'])]}", inline=False)
        response_str += '```'
        print('Playlist Report Generated:\n', response_str)
        return embed, response_str
    
    except HttpAccessTokenRefreshError:     return "The credentials have been revoked or expired, please re-run the application to re-authorize."
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, {traceback.format_exc()}"



# Start the bot
if __name__ == "__main__":
    print('Gaining Access to API Services...')
    YOUTUBE_ANALYTICS = get_service()
    YOUTUBE_DATA = get_service("youtube", "v3", YOUTUBE_API_KEY)
    print('API Services Built.')
    
    # Refresh Token & Retrieve Channel ID at Launch 
    try: refresh_token()
    except FileNotFoundError as e: print(f'{e.__class__.__name__, e}{get_service()}')

    try:    CHANNEL_ID = YOUTUBE_DATA.channels().list(part="id",mine=True).execute()['items'][0]['id']
    except: print(traceback.format_exc())

    
    # View class for Discord bot, handles all button interactions
    class SimpleView(discord.ui.View):     
        startDate: datetime = datetime.datetime.now().strftime("%Y-%m-01")
        endDate: datetime = datetime.datetime.now().strftime("%Y-%m-%d")

        def __init__(self, startDate, endDate, timeout=None):
            super().__init__(timeout=timeout)
            async def initialize_dates():
                self.startDate, self.endDate = await update_dates(startDate, endDate)
            
            asyncio.ensure_future(initialize_dates())
        
        ##TODO: Add a way to resend buttons without making bot edit the message & destroy old stats
        async def update_buttons(self, interaction: discord.Interaction, embed: discord.Embed, response_str: str):
            await interaction.response.edit_message(content=response_str, embed=embed, view=self)

        @discord.ui.button(label='Analytics', style=discord.ButtonStyle.blurple)
        async def channel_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed, response_str = await get_stats(start=self.startDate, end=self.endDate)
            await self.update_buttons(interaction, embed, response_str)

        @discord.ui.button(label="Top Revenue Videos", style=discord.ButtonStyle.blurple)
        async def top_earners(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed, response_str = await top_revenue(results=10, start=self.startDate, end=self.endDate)
            await self.update_buttons(interaction, embed, response_str)

        @discord.ui.button(label="Search Keyword Terms", style=discord.ButtonStyle.blurple)
        async def search_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed, response_str = await get_traffic_source(results=10, start=self.startDate, end=self.endDate)
            await self.update_buttons(interaction, embed, response_str)

        @discord.ui.button(label='Playlist Stats', style=discord.ButtonStyle.blurple)
        async def playlist_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed, response_str = await get_playlist_stats(results=5, start=self.startDate, end=self.endDate)
            await self.update_buttons(interaction, embed, response_str)
        
        @discord.ui.button(label='Geographic', style=discord.ButtonStyle.blurple)
        async def geo_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed, response_str = await get_detailed_georeport(results=5, startDate=self.startDate, endDate=self.endDate)
            await self.update_buttons(interaction, embed, response_str)

            embed, response_str = await top_countries_by_revenue(results=5, start=self.startDate, end=self.endDate)
            await interaction.response.edit_message(content=response_str, embed=embed, view=self)

        @discord.ui.button(label='OS Stats', style=discord.ButtonStyle.blurple)
        async def os_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed, response_str = await get_operating_stats(results=5, start=self.startDate, end=self.endDate)
            await self.update_buttons(interaction, embed, response_str)
        
        @discord.ui.button(label='Traffic Source', style=discord.ButtonStyle.blurple)
        async def traffic_source(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed, response_str = await get_traffic_source(results=5, start=self.startDate, end=self.endDate)
            await self.update_buttons(interaction, embed, response_str)
        
        @discord.ui.button(label='Shares', style=discord.ButtonStyle.blurple)
        async def shares(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed, response_str = await get_shares(results=5, start=self.startDate, end=self.endDate)
            await self.update_buttons(interaction, embed, response_str)
        
        @discord.ui.button(label='Top Earning Countries', style=discord.ButtonStyle.blurple)
        async def highest_earning_countries(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed, response_str = await top_countries_by_revenue(results=5, startDate=self.startDate, endDate=self.endDate)
            await self.update_buttons(interaction, embed, response_str)

        @discord.ui.button(label='Refresh Token', style=discord.ButtonStyle.success)
        async def token_ref(self, interaction: discord.Interaction, button: discord.ui.Button):
            status = await refresh(return_embed=False)
            print(status)
            await interaction.response.send_message(status)

        @discord.ui.button(label='Ping!', style=discord.ButtonStyle.grey)
        async def got_ping(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message('Pong!')


    discord_intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=discord_intents)
    bot.remove_command('help')

    if DISCORD_CHANNEL:
        @bot.event
        async def on_ready():
            channel = bot.get_channel(DISCORD_CHANNEL)
            embed = discord.Embed(title="YouTube Analytics Bot is Online!", description="Ready to explore your Channel Analytics with you!", color=0x00ff00)
            embed.add_field(name="What can I do?", value="I'm a bot built to traverse YouTube API(s) to provide you with insights of your channel's analytics! Use the `!help` command to learn more about my features. You can specify date ranges using `mm/dd` or `mm/dd/yyyy` format.", inline=False)
            embed.set_footer(text="Bot developed by Sazn Games (GitHub: Prem-ium).\nReport any issues to the Github Repository: https://github.com/Prem-ium/youtube-analytics-bot")
            await channel.send(embed=embed)
            await channel.send(view=SimpleView(startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")))

    # Bot ping-pong command
    @bot.command(name='ping')
    async def ping(ctx):
        # Send a 'pong' message to the user & print user and time to console
        await ctx.send('pong')
        print(f'\n{ctx.author.name} just got ponged!\t{datetime.datetime.now().strftime("%m/%d %H:%M:%S")}\n')

    @bot.command()
    async def button(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")):
        await ctx.send(f'{startDate} - {endDate} Button Session')
        view = SimpleView(startDate, endDate, timeout=None)
        await ctx.send(view=view)


    # Retrieve Analytic stats within specified date range, defaults to current month
    @bot.command(aliases=['stats', 'thisMonth', 'this_month'])
    async def analyze(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")):
        # Update the start and end dates to be in the correct format
        startDate, endDate = await update_dates(startDate, endDate)
        try:
            # Get the stats for the specified date range
            stats = await get_stats(startDate, endDate)        
            try:    await ctx.send(embed=stats[0])
            except: pass
            finally: await ctx.send(stats[1])
            
            # Print a message to the console indicating that the stats were sent
            print(f'\n{startDate} - {endDate} stats sent')
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Lifetime stats
    @bot.command(aliases=['lifetime', 'alltime', 'allTime'])
    async def lifetime_method(ctx):
        try:
            stats = await get_stats('2005-02-14', datetime.datetime.now().strftime("%Y-%m-%d"))
            try:    await ctx.send(embed=stats[0])
            except: pass
            finally: await ctx.send(stats[1])
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Last month's stats
    @bot.command(aliases=['lastMonth'])
    async def lastmonthct(ctx):
        # Get the last month's start and end dates
        startDate = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)
        endDate = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)
        startDate = startDate.replace(day=1)
        endDate = endDate.replace(day=calendar.monthrange(endDate.year, endDate.month)[1])
        try:
            stats = await get_stats(startDate.strftime("%Y-%m-%d"), endDate.strftime("%Y-%m-%d"))
            try:    await ctx.send(embed=stats[0])
            except: pass
            finally: await ctx.send(stats[1])
            print(f'\nLast month ({startDate} - {endDate}) stats sent\n')
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Retrieve top earning videos within specified date range between any month/year, defaults to current month
    @bot.command(aliases=['getMonth', 'get_month'])
    async def month(ctx, period=datetime.datetime.now().strftime("%m/%Y")):
        period = period.split('/')
        month, year = period[0], period[1]
        year = f'20{year}' if len(year) == 2 else year
        lastDate = monthrange(int(year), int(month))[1]
        startDate = datetime.datetime.strptime(f'{month}/01', '%m/%d').strftime(f'{year}/%m/%d').replace('/', '-')
        endDate = datetime.datetime.strptime(f'{month}/{lastDate}', '%m/%d').strftime(f'{year}/%m/%d').replace('/', '-')

        try:
            stats = await get_stats(startDate, endDate)
            try:    await ctx.send(embed=stats[0])
            except: pass
            finally: await ctx.send(stats[1])
            print(f'\nLast month ({startDate} - {endDate}) stats sent\n')
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Retrieve top earning videos within specified date range, defaults to current month
    @bot.command(aliases=['topEarnings', 'topearnings', 'top_earnings'])
    async def top(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y"), results=10):
        startDate, endDate = await update_dates(startDate, endDate)
        try:
            # Get the stats for the specified date range
            stats = await top_revenue(results, startDate, endDate)      
            try:    await ctx.send(embed=stats[0])
            except: pass
            finally: await ctx.send(stats[1])
            print(f'\n{startDate} - {endDate} top {results} sent')
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Top revenue by country
    @bot.command(aliases=['geo_revenue', 'geoRevenue', 'georevenue'])
    async def detailed_georeport(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y"), results=10):
        startDate, endDate = await update_dates(startDate, endDate)        
        try:
            stats = await top_countries_by_revenue(results, startDate, endDate)
            try:    await ctx.send(embed=stats[0])
            except: pass
            finally: await ctx.send(stats[1])
            print(f'\nLast month ({startDate} - {endDate}) geo-revenue report sent\n')
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Geo Report (views, revenue, cpm, etc)
    @bot.command(aliases=['geo_report', 'geoReport', 'georeport'])
    async def country(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y"), results=3):
        startDate, endDate = await update_dates(startDate, endDate)
        try:
            stats = await get_detailed_georeport(results, startDate, endDate)
            try:    await ctx.send(embed=stats[0])
            except: pass
            finally: await ctx.send(stats[1])
            print(f'\n{startDate} - {endDate} earnings by country sent')
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Ad Type Preformance Data
    @bot.command(aliases=['adtype', 'adPreformance', 'adpreformance'])
    async def ad(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")):
        startDate, endDate = await update_dates(startDate, endDate)
        try:
            stats = await get_ad_preformance(startDate, endDate)
            try:    await ctx.send(embed=stats[0])
            except: pass
            finally: await ctx.send(stats[1])
            print(f'\n{startDate} - {endDate} ad preformance sent')
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Demographics Report
    @bot.command(aliases=['demographics', 'gender', 'age'])
    async def demo_graph(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")):
        startDate, endDate = await update_dates(startDate, endDate)
        try:
            stats = await get_demographics(startDate, endDate)
            try:    await ctx.send(embed=stats[0])
            except: pass
            finally: await ctx.send(stats[1])

            print(f'\n{startDate} - {endDate} demographics sent')
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')
    # Shares Report
    @bot.command(aliases=['shares', 'shares_report', 'sharesReport', 'share_report', 'shareReport'])
    async def share_rep(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y"), results=5):
        startDate, endDate = await update_dates(startDate, endDate)
        try:
            stats = await get_shares(results, startDate, endDate)
            try:    await ctx.send(embed=stats[0])
            except: pass
            finally: await ctx.send(stats[1])

            print(f'\n{startDate} - {endDate} shares result sent')
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Search Terms Report
    @bot.command(aliases=['search', 'search_terms', 'searchTerms', 'search_report', 'searchReport'])
    async def search_rep(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y"), results=10):
        startDate, endDate = await update_dates(startDate, endDate)
        try:
            stats = await get_traffic_source(results, startDate, endDate)
            try:    await ctx.send(embed=stats[0])
            except: pass
            finally: await ctx.send(stats[1])
            print(f'\n{startDate} - {endDate} search terms result sent')
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')
            
    # Top Operating Systems
    @bot.command(aliases=['os', 'operating_systems', 'operatingSystems', 'topoperatingsystems'])
    async def top_os(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y"), results=10):
        startDate, endDate = await update_dates(startDate, endDate)
        try:
            stats = await get_operating_stats(results, startDate, endDate)
            try:    await ctx.send(embed=stats[0])
            except: pass
            finally: await ctx.send(stats[1])
            print(f'\n{startDate} - {endDate} operating systems result sent')
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Playlist Report
    @bot.command(aliases=['playlist', 'playlist_report', 'playlistReport'])
    async def playlist_rep(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y"), results=5):
        startDate, endDate = await update_dates(startDate, endDate)
        try:
            stats = await get_playlist_stats(results, startDate, endDate)
            try:    await ctx.send(embed=stats[0])
            except: pass
            finally: await ctx.send(stats[1])
            print(f'\n{startDate} - {endDate} playlist stats result sent')
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Refresh Token
    @bot.command(aliases=['refresh', 'refresh_token', 'refreshToken'])
    async def refresh_API_token(ctx, token=None):
        try:
            status = await refresh(return_embed=True, token=token)
            await ctx.send(embed=status)
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Swap Dev Mode
    @bot.command(aliases=['switch', 'devToggle'])
    async def sw_dev(ctx):
        try:
            embed = discord.Embed(title=f"Switch Dev Mode", color=0x00ff00)
            embed.add_field(name="Previous Dev Status:", value=DEV_MODE, inline=False)
            await dev_mode()
            embed.add_field(name="Updated Dev Status:", value=DEV_MODE, inline=False)
            await ctx.send(embed=embed)
        except Exception as e:  await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Send everything.
    @bot.command(aliases=['everything', 'all_stats', 'allStats', 'allstats'])
    async def all(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y"), results=10):
        startDate, endDate = await update_dates(startDate, endDate)
        try:
            # Get statistics
            stats = await get_stats(startDate, endDate)
            stats = stats[0]
            await ctx.send(embed=stats)
            
            # Get top revenue
            top_rev = await top_revenue(results, startDate, endDate)
            top_rev = top_rev[0]
            await ctx.send(embed=top_rev)
            
            # Get top countries by revenue
            top_countries = await top_countries_by_revenue(results, startDate, endDate)
            top_countries = top_countries[0]
            await ctx.send(embed=top_countries)

            # Get ad performance
            ad_performance = await get_ad_preformance(startDate, endDate)
            ad_performance = ad_performance[0]
            await ctx.send(embed=ad_performance)
            
            # Get detailed georeport
            georeport = await get_detailed_georeport(3, startDate, endDate)
            georeport = georeport[0]
            await ctx.send(embed=georeport)
            
            # Get demographics report
            demographics = await get_demographics(startDate, endDate)
            demographics = demographics[0]
            await ctx.send(embed=demographics)

            # Get shares report
            shares = await get_shares(results, startDate, endDate)
            shares = shares[0]
            await ctx.send(embed=shares)

            # Get search terms report
            search_terms = await get_traffic_source(results, startDate, endDate)
            search_terms = search_terms[0]
            await ctx.send(embed=search_terms)

            # Get top operating systems
            top_os = await get_operating_stats(results, startDate, endDate)
            top_os = top_os[0]
            await ctx.send(embed=top_os)

            # Get Playlist Report
            playlist_report = await get_playlist_stats(results, startDate, endDate)
            playlist_report = playlist_report[0]
            await ctx.send(embed=playlist_report)

            print(f'\n{startDate} - {endDate} everything sent')
        except Exception as e:      await ctx.send(f'Error:\n {e}\n{traceback.format_exc()}')

    # Help command
    @bot.command()
    async def help(ctx):
        available_commands = [
            "!button [startDate] [endDate]- Opens a view shortcut for all available commands.\nExamples: !button\t,\t!button 01/01 12/01\n\n",
            "!stats [startDate] [endDate] - Return stats within time range. Defaults to current month\nExample: !stats 01/01 12/01\t,\t!stats 01/01/2021 01/31/2021\n\n",
            "!getMonth [month/year] - Return stats for a specific month.\nExample: !getMonth 01/21\t,\t!getMonth 10/2020\n",
            "!lifetime - Get lifetime stats - Get lifetime stats\n",
            "!topEarnings [startDate] [endDate] [# of countries to return (Default: 10)] - Return top specified highest revenue earning videos.\nExample: !topEarnings 01/01 12/1 5\n\n",
            "!geo_revenue [startDate] [endDate] [# of countries to return] - Top Specific (default 10) countries by revenue\nExample: !geo_revenue 01/01 12/1 5\n\n",
            "!geoReport [startDate] [endDate] [# of countries to return] - More detailed report of views, revenue, cpm, etc by country\nExample: !geoReport 01/01 12/1 5\n\n",
            "!adtype [startDate] [endDate] - Get highest preforming ad types within specified time range\nExample: !adtype 01/01 12/1\n\n",
            "!demographics [startDate] [endDate] - - Get demographics data (age and gender) of viewers\nExample: !demographics 01/01 12/1\n\n",
            "!shares [startDate] [endDate] [# of results to return (Default: 5)] - Return top specified highest shares videos.\nExample: !shares 01/01 12/1 5\n\n",
            "!search [startDate] [endDate] [# of results to return (Default: 10)] - Return top specified highest search terms (ranked by views).\nExample: !search 01/01 12/1 5\n\n",
            "!os [startDate] [endDate] [# of results to return (Default: 10)] - Return top operating systems watching your videos (ranked by views).\nExample: !os 01/01 12/1 5\n\n",
            "!playlist [startDate] [endDate] [# of results to return (Default: 5)] - Return playlist stats\nExample: !playlist 01/01 12/1\n\n",
            "!everything [startDate] [endDate] - Return everything. Call every method and output all available data\nExample: !everything 01/01 12/1\n\n",
            "!refresh - Refresh the API token!!\n",
            "!switch - (Temp) Toggle between dev and user mode\n"
            "!restart - Restart the bot",
            "!help\t!ping"
        ]
        # Create an embed
        embed = discord.Embed(title=f"Help: Available Commands", color=0x00ff00)

        # Add each command as a field
        for command in available_commands:
            embed.add_field(name=f'{command.split(" ")[0]}:', value=command, inline=False)

        embed.set_footer(text="Bot developed by Prem-ium. Official Github Repository: https://github.com/Prem-ium/youtube-analytics-bot")
        await ctx.send(embed=embed)
        available_commands = "\n".join(available_commands)
        await ctx.send(f"Available commands:\n\n{available_commands}")
        await ctx.send(f"\n\n\n\n[brackets indicate optional values to pass in, if none are provided, default values will be used.]\nMost commands can be called without specifying a date range. If no date range is specified, usually current or last month will be used.\n\nBot developed by Prem-ium. Report any issues to the Github Repository: https://github.com/Prem-ium/youtube-analytics-bot\n\n")

    # Restart command
    @bot.command(name='restart')
    async def restart(ctx):
        print(f"Restarting...\n")
        await ctx.send(f"Restarting the bot...\nNote: Restart may not work if the bot is running on a Free Tier Repl on Replit.")
        await bot.close()
        os._exit(0)

    print(f"Booting up Discord Bot...\n{'-'*150}")
    bot.run(DISCORD_TOKEN)
