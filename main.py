import os
import datetime
import traceback
from dotenv import load_dotenv
from time import sleep
import discord
from discord.ext import commands, tasks
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from googleapiclient.discovery import build
import googleapiclient.errors
from google_auth_oauthlib.flow import InstalledAppFlow
import google
import google_auth_oauthlib
import calendar

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/yt-analytics-monetary.readonly"]

if not os.environ["DISCORD_TOKEN"]:
    raise Exception("DISCORD_TOKEN is missing within .env file, please add it and try again.")
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
DISCORD_CHANNEL = os.environ.get("DISCORD_CHANNEL", None)

if DISCORD_CHANNEL:
    DISCORD_CHANNEL = int(DISCORD_CHANNEL)

# Whether to use keep_alive.py
if (os.environ.get("KEEP_ALIVE", "False").lower() == "true"):
    from keep_alive import keep_alive
    keep_alive()

CLIENT_SECRETS_FILE = "CLIENT_SECRET.json"

def get_service(API_SERVICE_NAME='youtubeAnalytics', API_VERSION='v2', SCOPES=SCOPES, CLIENT_SECRETS_FILE=CLIENT_SECRETS_FILE):
    credential_path = os.path.join('./', 'credential_sample.json')
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRETS_FILE, SCOPES)
        credentials = tools.run_flow(flow, store)
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

def execute_api_request(client_library_function, **kwargs):
    return client_library_function(**kwargs).execute()

async def update_dates(startDate, endDate):
    if len(startDate) != 5 or len(endDate) != 5:
        startDate = datetime.datetime.strptime(startDate, '%m/%d/%y').strftime('%Y/%m/%d').replace('/', '-')
        endDate = datetime.datetime.strptime(endDate, '%m/%d/%y').strftime('%Y/%m/%d').replace('/', '-')
    else:
        currentYear = datetime.datetime.now().strftime("%Y")
        if len(startDate) == 5:
            startDate = datetime.datetime.strptime(startDate, '%m/%d').strftime(f'{currentYear}/%m/%d').replace('/', '-')
        if len(endDate) == 5:
            endDate = datetime.datetime.strptime(endDate, '%m/%d').strftime(f'{currentYear}/%m/%d').replace('/', '-')
    return startDate, endDate

async def get_stats(start=datetime.datetime.now().strftime("%Y-%m-01"), end=datetime.datetime.now().strftime("%Y-%m-%d")):
    try:
        youtubeAnalytics = get_service()
        response = execute_api_request(
            youtubeAnalytics.reports().query,
            ids='channel==MINE',
            startDate=start,
            endDate=end,
            metrics='views,estimatedMinutesWatched,estimatedRevenue,playbackBasedCpm',
        )
        # Retrieve the data from the response
        views = response['rows'][0][0]
        minutes = response['rows'][0][1]
        revenue = response['rows'][0][2]
        cpm = response['rows'][0][3]

        # Terminary operator to check if start/end year share a year, and strip/remove if that's the case
        start, end = (start[5:] if start[:4] == end[:4] else f'{start[5:]}-{start[:4]}').replace('-', '/'), (end[5:] if start[:4] == end[:4] else f'{end[5:]}-{end[:4]}').replace('-', '/')

        response = f'YouTube Analytics Report ({start}\t-\t{end})\n\nViews:\t{round(views,2):,}\nMinutes Watched:\t{round(minutes,2):,}\nEstimated Revenue:\t${round(revenue,2):,}\nPlayback CPM:\t${round(cpm,2):,}'
        print(response + '\nSending to Discord...')
        return response
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, please check the logs."


async def top_revenue(results= 10, start=datetime.datetime.now().strftime("%Y-%m-01"), end=datetime.datetime.now().strftime("%Y-%m-%d")):
    try:
        youtubeAnalytics = get_service()
        response = execute_api_request(
            youtubeAnalytics.reports().query,
            ids='channel==MINE',
            startDate=start,
            endDate=end,
            dimensions='video',
            metrics='estimatedRevenue',
            sort='-estimatedRevenue',
            maxResults=results,
        )
        video_ids = []
        earnings = []
        for data in response['rows']:
            video_ids.append(data[0])
            earnings.append(data[1])

        youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=os.environ.get('YOUTUBE_API_KEY'))

        request = youtube.videos().list(
            part="snippet",
            id=','.join(video_ids)
        )
        response = request.execute()
        start, end = (start[5:] if start[:4] == end[:4] else f'{start[5:]}-{start[:4]}').replace('-', '/'), (end[5:] if start[:4] == end[:4] else f'{end[5:]}-{end[:4]}').replace('-', '/')

        top_results = f'Top {results} Earning Videos ({start}\t-\t{end})\n:\n\n'
        for i in range(len(response['items'])):
            top_results += f'{response["items"][i]["snippet"]["title"]} - ${round(earnings[i], 2):,}\n'
        print(top_results)

        return top_results
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, please check the logs."
    
async def top_countries_by_revenue(results = 10, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")):
    try:
        youtubeAnalytics = get_service()
        # Get top preforming countries by revenue
        response = execute_api_request(
            youtubeAnalytics.reports().query,
            ids='channel==MINE',
            startDate=startDate,
            endDate=endDate,
            dimensions='country',
            metrics='grossRevenue',
            sort='-grossRevenue',
            maxResults=results,
        )
        startDate, endDate = (startDate[5:] if startDate[:4] == endDate[:4] else f'{startDate[5:]}-{startDate[:4]}').replace('-', '/'), (endDate[5:] if startDate[:4] == endDate[:4] else f'{endDate[5:]}-{endDate[:4]}').replace('-', '/')

        returnString = f'Top {results} Countries by Revenue: ({startDate}\t-\t{endDate})\n'
        for row in response['rows']:
            returnString += f'{row[0]}:\t\t${round(row[1],2):,}\n'
            print(row[0], row[1])

        return returnString
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, please check the logs."


async def get_ad_preformance(start=datetime.datetime.now().strftime("%Y-%m-01"), end=datetime.datetime.now().strftime("%Y-%m-%d")):
    try:
        youtubeAnalytics = get_service()
        response = execute_api_request(
            youtubeAnalytics.reports().query,
            ids='channel==MINE',
            startDate=start,
            endDate=end,
            dimensions='adType',
            metrics='grossRevenue,adImpressions,cpm',
            sort='adType'
        )
        # Terminary operator to check if start/end year share a year, and strip/remove if that's the case
        start, end = (start[5:] if start[:4] == end[:4] else f'{start[5:]}-{start[:4]}').replace('-', '/'), (end[5:] if start[:4] == end[:4] else f'{end[5:]}-{end[:4]}').replace('-', '/')

        preformance = f'Ad Preformance ({start}\t-\t{end})\n\n'
        # Parse the response into nice formatted string
        for row in response['rows']:
            preformance += f'{row[0]}:\n\t\t\t\t\t\t\tGross Revenue:\t${round(row[1],2):,}\tImpressions:\t{round(row[2],2):,}\tCPM:\t${round(row[3],2):,}\n'
            print(row[0], row[1], row[2], row[3])
        return preformance
    except Exception as e:
        print(traceback.format_exc())
        return f"Ran into {e.__class__.__name__} exception, please check the logs."


if __name__ == "__main__":
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)
    bot.remove_command('help')

    # Bot event when bot is ready
    if DISCORD_CHANNEL:
        @bot.event
        async def on_ready():
            channel = bot.get_channel(DISCORD_CHANNEL)
            await channel.send('Analytics Bot is ready!')

    # Bot ping-pong
    @bot.command(name='ping')
    async def ping(ctx):
        print('Someone just got ponged!')
        await ctx.send('pong')

    @bot.command(aliases=['lifetime'])
    async def lifetime(ctx):
        print()
        # Get Lifetime stats from the get_stats function, and send it to the channel
        await ctx.send(await get_stats('2005-02-14', datetime.datetime.now().strftime("%Y-%m-%d")))
        print('\nLifetime stats sent\n')

    @bot.command(aliases=['lastMonth'])
    async def lastmonth(ctx):
        startDate = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)
        endDate = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)
        startDate = startDate.replace(day=1)
        endDate = endDate.replace(day=calendar.monthrange(endDate.year, endDate.month)[1])
        # Get last months stats from the get_stats function, and send it to the channel
        await ctx.send(await get_stats(startDate.strftime("%Y-%m-%d"), endDate.strftime("%Y-%m-%d")))
        print('\nLast months stats sent\n')

    @bot.command(aliases=['stats'])
    async def analyze(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")):
        startDate, endDate = await update_dates(startDate, endDate)
        await ctx.send(await get_stats(startDate, endDate))
        print(f'\n{startDate} - {endDate} stats sent')

    @bot.command(aliases=['topEarnings'])
    async def top(ctx, results = 10, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")):
        startDate, endDate = await update_dates(startDate, endDate)
        await ctx.send(await top_revenue(results, startDate, endDate))
        print(f'\n{startDate} - {endDate} top {results} sent')

    @bot.command(aliases=['everything'])
    async def all(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")):
        startDate, endDate = await update_dates(startDate, endDate)
        await ctx.send(await get_stats(startDate, endDate) + '\n\n.')
        await ctx.send(await top_revenue(10, startDate, endDate)+ '\n\n.')
        await ctx.send(await top_countries_by_revenue(10, startDate, endDate)+ '\n\n.')
        await ctx.send(await get_ad_preformance(startDate, endDate)+ '\n\n.')

        print(f'\n{startDate} - {endDate} everything sent')

    @bot.command(aliases=['earningsByCountry'])
    async def country(ctx, results = 10, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")):
        startDate, endDate = await update_dates(startDate, endDate)
        await ctx.send(await top_countries_by_revenue(results,startDate, endDate))
        print(f'\n{startDate} - {endDate} earnings by country sent')

    @bot.command(aliases=['adPreformance'])
    async def ad(ctx, startDate=datetime.datetime.now().strftime("%m/01/%y"), endDate=datetime.datetime.now().strftime("%m/%d/%y")):
        startDate, endDate = await update_dates(startDate, endDate)
        await ctx.send(await get_ad_preformance(startDate, endDate))
        print(f'\n{startDate} - {endDate} ad preformance sent')

    # Help command
    @bot.command()
    async def help(ctx):
        await ctx.send('Available commands:')
        await ctx.send('!everything - Return everything. Call every method and output all available data')
        await ctx.send('!stats [startDate] [endDate]- Return stats within time range. Defaults to current month')
        await ctx.send('!topEarnings [# of countries to return] [startDate] [endDate]- Return top specified highest revenue earning videos.')
        await ctx.send('!earningsByCountry [# of countries to return] [startDate] [endDate] - Top Specific (default 10) countries by revenue')
        await ctx.send('!adPreformance [startDate] [endDate] - Get ad preformance for a given date range')
        await ctx.send('!lifetime - Get lifetime stats')
        await ctx.send('!restart')
        await ctx.send('!help')

    # Restart command
    @bot.command(name='restart')
    async def restart(ctx):
        print("Restarting...")
        print()
        await ctx.send("Restarting...")
        await bot.close()
        os._exit(0)

    # Run Discord bot
    bot.run(DISCORD_TOKEN)
    print('Discord bot is online...')
