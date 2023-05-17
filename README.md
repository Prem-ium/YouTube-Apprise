<p align="right"><a href="https://www.youtube.com/channel/UCTBKWIcBRPGh2yhPkrIbJPw"><img src="https://img.shields.io/badge/YouTube-%23FF0000.svg?style=for-the-badge&logo=YouTube&logoColor=white" alt="YouTube"/></a></p>
<h1 align="center">📊 YouTube Analytics Discord Bot 🤖 </h1>

<p align="center">An <i>awesome</i> Python Discord Bot to fetch & display your YouTube Analytics data.</p>

<p align="right"><img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54"/><img src="https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white"/><img src="https://img.shields.io/badge/GoogleCloud-%234285F4.svg?style=for-the-badge&logo=google-cloud&logoColor=white"/><img src="https://img.shields.io/badge/Replit-DD1200?style=for-the-badge&logo=Replit&logoColor=white"/><img src="https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white"/><a href="https://www.buymeacoffee.com/prem.ium" target="_blank"> <img align="right" src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me A Coffee"/></a>
</p>

## Features:
- Collects data on a variety of metrics, including views, revenue, subscriber growth, & more
- Can be used to analyze the performance of a channel and identify areas for improvement
- Discord Button User-Friendly UI
- Docker Support
- Developer Mode
- Efficient API Service Build Methods & Fail-Safe(s)
- Ability to Run 24/7 using Replit & Flask (Dev Mode & Build From Document)



## Input Formatting & Bot Commands:
Start every command with `!`. Optional Command Input is denoted using [brackets]. 

Check [Example Output Folder](https://github.com/Prem-ium/youtube-analytics-bot/blob/main/output-examples/README.MD) for output examples.
- MM / DD Format (MONTH/DATE, Assumes the current year) or MM / DD / YYYY:
```sh
   !stats 01/01 12/01
   !stats 01/01/2021 12/31/2021
```
#### Commands:
| Command | Description |
|---------|-------------|
| `!button [startDate] [endDate]` | Open Discord Button UI with all supported commands |
| `!stats [startDate] [endDate]` | 📅 YouTube Analytics Report Card. Display Views, Watch-Time, Estimated Revenue, CPM, Ad-Impressions, & more. Defaults to current month if date range not specified.  |
| `!getMonth [month/year]` | Return stats for a specific month. 📆 |
| `!lifetime` | Get lifetime stats. 🧮 |
| `!topEarnings [startDate] [endDate] [Length to Return]` | Get a list of the highest revenue earning videos on your channel. 💰 |
| `!geo_revenue [startDate] [endDate] [Length to Return]` | Get a list of your top revenue earning countries. 🌎💰 |
| `!geoReport [startDate] [endDate] [Length to Return]` | More detailed report of views, revenue, cpm, etc by country. 🌎 |
| `!adtype [startDate] [endDate]` | Get highest performing ad types within specified time range. 💰 |
| `!demographics [startDate] [endDate]` | Get demographics data (age and gender) of viewers. 👨‍👩‍👧‍👧 |
| `!shares [startDate] [endDate] [Length to Return]` | Return list of top sharing methods for your videos. 📤 |
| `!search [startDate] [endDate] [Length to Return]` | Return YouTube search terms resulting in the most views of your video(s). 🔍 |
| `!os [startDate] [endDate] [Length to Return]` | Return top operating systems watching your videos (ranked by views). 📟 |
| `!playlist [startDate] [endDate] [Length to Return]` | Retrieve your Playlist Report. |
| `!everything [startDate] [endDate]` | Return everything. Call every method and output all available data. ♾️ |
| `!refresh [token]` | Refresh API Token! |
| `!switch` | Switch Dev Mode On/Off. |
| `!help` | Send all Discord commands with explanations. 🦮 |
| `!ping` | Check to make sure bot is running. |


#### TODO:
- Resend Buttons at Bottom of Embed instead of Editing Stats
- Google & YouTube Keyword SEO Research Command
- Major Refactor Discord Commands

## Set-Up

#### Google Cloud Console (API Setup)

1. To get started, head over to the Google Cloud Console website and create a new project.
2. Click on 'API & Services' and 'Enable APIs and Services'.
3. Search and enable both 'YouTube Data' and 'YouTube Analytics' API.
4. Return to the API & Services page and click on 'credentials'.
5. Select User Type (External) -> Configure OAuth Consent Screen -> Add YouTube Analytics related scopes:
```
   https://www.googleapis.com/auth/youtube.readonly
   https://www.googleapis.com/auth/yt-analytics-monetary.readonly
```
6. Go through the rest of the configuration settings for OAuth
7. Click Create Credentials -> OAuth Credentials -> Desktop Application -> Go through setup.
8. Download the JSON file, name it `CLIENT_SECRET.json` and place the file inside the same folder as the program.
9. Create Credentials -> API Key -> Copy and assign the key to the `YOUTUBE_API_KEY` environment variable.

#### Discord Bot

1. Go to https://discord.com/developers/ and create a new application. Name it YouTube Apprise or whatever you wish, accept the terms.
2. Open the application -> OAuth2 -> URL Generator.
3. Within Scopes, click 'Bot' and enable the desired bot permissions.
4. Enable text permissions such as Send Messages & Read Message History. 
5. Enable general permissions such as View Server Insights.
6. Copy the generated link below Permissions and enter it in a browser. Add the bot to your server of choice (preferably your own private Discord server, as sensitive information such as revenue and CPM is accessible through bot commands).
7. (Optional) Add a pretty profile picture for your bot in Rich Presence.
8. Go to 'Bot' to obtain, reset, and retrieve the token. Assign it to the `DISCORD_TOKEN` environment variable.

## Installation

The bot can be run using Python or Docker.
#### Python Script
1. Clone this repository, cd into it, and install dependancies:
```sh
   git clone https://github.com/Prem-ium/youtube-analytics-bot
   cd youtube-analytics-bot
   pip install -r requirements.txt
   ```
2. Configure your `.env` file (See below and example for options)
3. Run the script:

    ```sh
    python main.py
   ```
#### Docker Container
Build with Docker only after running locally and generating a `credentials.json` file
1. Run script locally with Python to generate credentials json file.
2. Download and install Docker on your system
3. Configure your `.env` file (See below and example for options)
4. To build the image yourself, cd into the repository and run:
   ```sh
   docker build -t youtube-apprise .
   ```
   Then start the bot with:
   ```sh
   docker run -it --env-file ./.env --restart unless-stopped --name youtube-apprise youtube-apprise
   ```
   Both methods will create a new container called `youtube-apprise`. Make sure you have the correct path to your `.env` file you created.

5. Let the bot log in and begin working. DO NOT PRESS `CTRL-c`. This will kill the container and the bot. To exit the logs view, press `CTRL-p` then `CTRL-q`. This will exit the logs view but let the bot keep running.


## Environment Variables:
As always, please refer to the `.env.example' file for examples. 

##### Required .env:
`DISCORD_TOKEN` = Retrieve from https://discord.com/developers/applications


`YOUTUBE_API_KEY` = YouTube Data API Key (Retrieve from Google Cloud Console Credentials's Page after enabling the YouTube Data API)
##### Optional .env:
`CLIENT_PATH` = Path of YouTube/Google Client Secret JSON file. Defaults to current directory (file named "CLIENT_SECRET.json")

`DEV_MODE`= Whether to use experimental features or not. MUST have CLIENT_SECRET configured.

`CLIENT_SECRET`= Contents of CLIENT_SECRET.JSON which includes refresh token value. Check .env.example for a reference. 

`DISCORD_CHANNEL` = Turn on developer mode in advanced settings, right click on text channel, copy ID

`KEEP_ALIVE` = Boolean True/False value. Whether to us a Flask server or not to keep program from dying on platforms like Replit.

## Donations
If you find my project helpful and would like to support its development, please consider making a donation. Every little bit helps and is greatly appreciated!

You can donate by clicking on the following button:
<div style="display:grid;justify-content:center;"><a href="https://www.buymeacoffee.com/prem.ium" target="_blank">
        <img src="https://raw.githubusercontent.com/Prem-ium/youtube-analytics-bot/main/output-examples/media/coffee-logo.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a></div>

Thank you for your support!

## License
This repository uses the [BSD 3-Clause “New” or “Revised” License.](https://choosealicense.com/licenses/bsd-3-clause/#)

## Final Remarks
This project was built thanks to YouTube Analytics & Data API Documentation. 
Please leave a :star2: if you found this project to be cool!
May your analytics skyrocket up📈
