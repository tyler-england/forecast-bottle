from Modules import keep_data, prediction, gmail
from pathlib import Path
import datetime

name = '<baby name>'  # change baby's name as needed
sender = '<email sender>'  # change as needed

data = keep_data.get_content(name)  # get historical feed data from Google Keep
if isinstance(data, str):  # Google refusing to allow access to Keep note
    print('Trouble fetching Keep data...')
    print(data)
    quit()

time, qty, bf_mins, last_feed, avg_feed, daily_tot, daily_freq = prediction.get_time_qty_summary(data)

if time == 0 or qty == 0:
    print(f'Failed to predict time/qty: {time} / {qty}')
    quit()
if time < datetime.datetime.now():  # no longer useful to notify
    print('Prediction found too late :(')
    print(time, qty)
    quit()

# if already logged, don't send
log = str(Path(__file__).resolve().parents[1]) + '/prediction_log.txt'
if not Path(log).exists():
    with open(log, 'w'):
        pass
loglines = []
try:
    with open(log, 'r+') as logdoc:
        loglines = [line.rstrip() for line in logdoc]
        chkstr = f'{time} -- {qty} mL'
        for logline in loglines:
            if logline == chkstr:  # Keep doc hasn't been updated since last check
                print('No update (already in log -> no email will send)')
                quit()
        loglines.append(chkstr)
except Exception:
    print('Error: Unable to find/open the prediction log (' + log + ')')
    quit()

qty = f'{qty}mL ({bf_mins} mins BF)'
x = gmail.send_email(name, sender, time, qty, last_feed, avg_feed,
                     daily_tot, daily_freq)  # create & send email
if x is None:
    if loglines:  # add to log
        with open(log, 'w+') as logdoc:
            for i in range(max(len(loglines) - 6, 0), len(loglines)):
                logdoc.write(loglines[i] + '\n')
    else:
        print('Email sent successfully, but prediction log could not be updated')
else:
    print(x)
