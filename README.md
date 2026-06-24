# forecast-bottle

Reads a Google Doc where baby feed information is logged, predicts the next feed (time and quantity of milk/formula), and emails the result — so a bottle can be ready before the crying starts.

Emails include summary data (avg feed quantity, daily intake, feeding frequency) that's handy to reference at pediatrician appointments.

## How it works

Log each feed in a Google Doc, one entry per line, in this format:

```
Jan 1 - 3:00 pm, 30 mL + 15 min BF
Jan 1 - 3:00 pm, 30 mL
Jan 1 - 3:00 pm, 15 min BF
```

- Bottle feeds are measured in mL
- Breastfeeds are measured in minutes
- Either value can be omitted; if both are present, mL must come first
- "BF" is optional — `15 min` is parsed the same as `15 min BF`

The script uses the past few days of data to predict when the next feed will happen and how much will be needed. Run it on a schedule (e.g. via cron) for consistent notifications.

## Setup

### 1. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Google Docs API (service account)

Feed data is read from a Google Doc via the official Google Docs API using a service account.

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project
2. Enable the **Google Docs API** for that project
3. Go to **IAM & Admin → Service Accounts → Create service account**
4. Under **Keys → Add Key → Create new key → JSON**, download the key file
5. Save it as `service_account.json` in the project root (one level above `forecast_bottle/`)
6. Share your Google Doc with the service account's email address (Viewer access is sufficient)

### 3. Gmail (app password)

The script sends email via Gmail SMTP using an app password.

1. Enable 2-Step Verification on the sending Gmail account if not already enabled
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), create a password, and copy it

### 4. Config files

Copy each `example.*` file, drop the `example.` prefix, and fill it in.

**`credentials.txt`**
```
gmail
username: yourname@gmail.com
password: xxxx xxxx xxxx xxxx
```
Spaces in the app password are fine — the parser handles them correctly.

**`recipients.txt`**
One recipient email address per line.

**`age_info.txt`**
```
birthday: 2025-06-17
0-4,60,120,2,4
4-8,90,150,2,4
8-12,120,180,2,5
12-24,120,210,3,5
```
First line is the baby's birthday. Each subsequent line is:
`week_start-week_end, min_mL, max_mL, min_hrs_between_feeds, max_hrs_between_feeds`

**`data_log.txt`**
Leave empty. Used as a local backup of feed data.

**`service_account.json`**
The JSON key file downloaded in step 2 above. Never commit this file.

### 5. Script configuration

At the top of `forecast_bottle/email_forecast.py`, set:

```python
BABY_NAME = "..."       # used in email subject line
SENDER    = "..."       # display name for outgoing emails
DOC_ID    = "..."       # from the Doc URL: /document/d/THIS_PART/edit
```

### 6. Run

```bash
source venv/bin/activate
python forecast_bottle/email_forecast.py
```

Or use `run.sh` after updating the `PROJECT` path inside it.

## Scheduling

To run automatically, add a cron entry:
```
*/10 * * * * /path/to/forecast-bottle/run.sh >> /path/to/forecast-bottle/cron.log 2>&1
```
This runs every 10 minutes. Duplicate predictions are suppressed via `prediction_log.txt` — only a new prediction triggers a new email.

## File structure

```
forecast-bottle/
├── forecast_bottle/
│   ├── email_forecast.py      ← entry point
│   └── Modules/
│       ├── doc_data.py        ← Google Docs reader
│       ├── gmail.py           ← email sender
│       └── prediction.py      ← feed prediction logic
├── age_info.txt
├── credentials.txt
├── data_log.txt
├── recipients.txt
├── service_account.json       ← never commit this
├── prediction_log.txt         ← auto-generated
├── requirements.txt
└── run.sh
```

## Notes

- The Google Docs API is free for this use case — well within the free tier limits
- The Doc can be shared with multiple editors (useful for two-parent logging)
- BF quantity predictions are less accurate than bottle predictions by nature — breastfeed output isn't directly measurable
