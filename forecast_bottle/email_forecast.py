from forecast_bottle.Modules import keep_data, prediction, gmail
import os, datetime

data = keep_data.get_content()  # get historical feed data from Google Keep

time, qty = prediction.get_time_qty(data)

if time == 0 or qty == 0:
    print("Failed to predict time/qty: " + str(time) + "   " + str(qty))
    quit()
if time < datetime.datetime.now():  # no longer useful to notify
    print("Prediction found too late :(")
    quit()

log = os.path.dirname(os.getcwd()) + "/prediction_log.txt"  # if already logged, don't send
try:
    logdoc = open(log, "r")
except Exception:
    print("Error: Unable to find/open the prediction log (" + log + ")")
    quit()
loglines = [line.rstrip() for line in logdoc]
chkstr = str(time) + " -- " + str(qty) + "mL"
for logline in loglines:
    if logline == chkstr:  # Keep doc hasn't been updated since last check
        print("No update (no email sent)")
        quit()

x = gmail.send_email(time, qty)  # create & send email
if x is None:  # add to log
    logdoc = open(log, "a+")
    logdoc.write("\n" + chkstr)
else:
    print(x)
