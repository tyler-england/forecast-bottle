from forecast_bottle.Modules import keep_data, prediction, gmail
import os, datetime

data = keep_data.get_content()  # get historical feed data from Google Keep

# time = prediction.get_time(data)  # anticipate next hunger time
time = datetime.datetime(2021, 1, 31, 8, 25)
if time < datetime.datetime.now():  # no longer useful to notify
    print("Too late :(")
    quit()
qty = prediction.get_amount(data)  # anticipate next feed qty/amount (in mL)

log = os.path.dirname(os.getcwd()) + "/prediction_log.txt"  # if already logged, don't send
# check log
print(log)
x = gmail.send_email(time, qty)  # create & send email
if x is None:  # add to log
    print(log)
    logdoc = open(log, "a+")
    logdoc.write(str(time) + " -- " + str(qty) + "mL")
else:
    print(x)
