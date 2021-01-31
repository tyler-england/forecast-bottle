import pandas
import datetime


def get_time(data):
    # example: strtime = "Jan 30 - 11:35 pm, 20 mL"
    time = 0
    strtime = data[0]
    year = datetime.datetime.today().year
    strtime = strtime[:7] + year + " " + strtime[7:]
    x = strtime.find(",")
    dateout = datetime.datetime.strptime(strtime[:x], "%b %d %Y - %I:%M %p")
    return time


def get_amount(data):
    amt = 70
    return amt