from Modules import keep_data, prediction, gmail
from pathlib import Path
import datetime


def update_chktime(filepath, dt_chk, fmt):
    try:
        with open(chktime, "w") as timedoc:  # check update time (to reduce freq. of Google access & account suspicion)
            timedoc.write(datetime.datetime.strftime(dt_chk, fmt))
    except:
        print("Error: unable to update the next 'check' time in " + filepath)
    return


chktime = str(Path(__file__).parents[1]) + "/check_time.txt"
fmt = "%Y-%m-%d %H:%M:%S"
try:
    with open(chktime, "r+") as timedoc:  # check update time (to reduce freq. of Google access & account suspicion)
        chk_time_txt = timedoc.read()
except:
    pass

b_cont = False  # boolean to continue with the program
try:  # find the time & evaluate
    dt_chk = datetime.datetime.strptime(chk_time_txt, fmt)
    if datetime.datetime.now() >= dt_chk:
        b_cont = True
except Exception:  # something wrong with the datetime(missing, etc.)
    b_cont = True
    try:
        dt_chk
    except NameError:
        dt_chk = datetime.datetime.min

if not b_cont:  # retry later
    quit()

name = "Corwin"  # change baby's name as needed
sender = "Tyler England"  # change as needed

data = keep_data.get_content(name)  # get historical feed data from Google Keep

time, qty, last_feed, avg_feed, daily_tot, daily_freq = prediction.get_time_qty_summary(data)

if time == 0 or qty == 0:
    print("Failed to predict time/qty: " + str(time) + "   " + str(qty))
    quit()
if time < datetime.datetime.now():  # no longer useful to notify
    print("Prediction found too late :(")
    quit()

log = str(Path(__file__).parents[1]) + "/prediction_log.txt"  # if already logged, don't send
loglines = []
try:
    with open(log, "r+") as logdoc:
        loglines = [line.rstrip() for line in logdoc]
        chkstr = str(time) + " -- " + str(qty) + "mL"
        for logline in loglines:
            if logline == chkstr:  # Keep doc hasn't been updated since last check
                print("No update (no email sent)")
                if dt_chk < time:
                    dt_chk = time + datetime.timedelta(minutes=30)  # check again 30 min after feed
                else:
                    dt_chk = dt_chk + datetime.timedelta(minutes=15)  # check again in 15 min
                update_chktime(chktime, dt_chk, fmt)
                quit()
        loglines.append(chkstr)
except Exception:
    print("Error: Unable to find/open the prediction log (" + log + ")")
    quit()

x = gmail.send_email(name, sender, time, qty, last_feed, avg_feed, daily_tot, daily_freq)  # create & send email
dt_chk = time - datetime.timedelta(minutes=30)  # check for updates 30 min before next feed
update_chktime(chktime, dt_chk, fmt)
if x is None:
    if loglines:  # add to log
        with open(log, "w+") as logdoc:
            for i in range(max(len(loglines) - 6, 0), len(loglines)):
                logdoc.write(loglines[i] + "\n")
    else:
        print("Email sent successfully, but prediction log could not be updated")
else:
    print(x)
