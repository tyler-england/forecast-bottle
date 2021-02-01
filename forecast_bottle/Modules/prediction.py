import pandas as pd
from datetime import datetime, timedelta

def get_time_qty(data):
    time_out = 0
    qty_out = 0
    year = datetime.today().year  # conditional based on cur month
    cols = []
    for str_in in data:
        strtime = str_in[:7] + str(year) + " " + str_in[7:]
        x = strtime.find(",")
        y = strtime.lower().find("ml")
        z = strtime.find("+")
        if x > 0:
            try:  # date/time typos (some common ones from typing in Keep)
                dtime = datetime.strptime(strtime[:x], "%b %d %Y - %I:%M %p")  # date/time
            except Exception:
                try:
                    dtime = datetime.strptime(strtime[:x], "%b %d %Y - %I:%M%p")  # date/time
                except Exception:
                    try:
                        dtime = datetime.strptime(strtime[:x], "%b %d%Y - %I:%M %p")  # date/time
                    except Exception:
                        try:
                            dtime = datetime.strptime(strtime[:x], "%b %d %Y -%I:%M %p")  # date/time
                        except Exception:
                            dtime = 0
            if not dtime == 0:
                date = str(dtime.date())
                time = dtime.time()
                if y > 0:
                    mls = int(strtime[x + 1:y])  # qty of milk (mL)
                else:
                    mls = 0
                zz = strtime.lower().find("min")
                if zz > 0:
                    if z > 0:  # add'l breast feed (min)
                        bfs = int(strtime[z + 1:zz])
                    else:  # bf only (no bottle)
                        bfs = int(strtime[x + 1:zz])
                else:  # no "min"
                    bfs = 0
                cols.append([date, time, mls, bfs])

    df = pd.DataFrame(cols, columns=["Date", "Time", "mLs", "BF Mins"], dtype=float)

    # find out how much 1 min BF is
    dates = []
    for i in range(1, 4):  # check total day intake (past 3 days)
        dates.append(datetime.strftime(datetime.today() - timedelta(days=i), "%Y-%m-%d"))

    mls_sum = df.groupby("Date")["mLs"].sum().to_frame().reset_index()  # grouped sums of mLs
    mls_sum = mls_sum.set_index("Date")  # Date as index
    bfs_sum = df.groupby("Date")["BF Mins"].sum().to_frame().reset_index()  # grouped sums of BF Mins
    bfs_sum = bfs_sum.set_index("Date")  # Date as index

    mls_daily = []
    bfs_daily = []
    for i in range(3):
        try:
            x = mls_sum.loc[dates[i], "mLs"]
        except:
            x = 0
        try:
            y = bfs_sum.loc[dates[i], "BF Mins"]
        except:
            y = 0
        if x > 0 or y > 0:
            mls_daily.append(x)
            bfs_daily.append(y)
    if len(mls_daily) < 2:  # assume breast output rate
        bf_ml_per_min = 5.3
    else:  # set them equal & approximate the BF content
        x = (mls_daily[0] - mls_daily[1]) / (bfs_daily[1] - bfs_daily[0])
        if len(mls_daily) == 3:  # use the third metric and then average
            y = (mls_daily[1] - mls_daily[2]) / (bfs_daily[2] - bfs_daily[1])
            z = (mls_daily[0] - mls_daily[2]) / (bfs_daily[2] - bfs_daily[0])
            bf_ml_per_min = (x + y + z) / 3
        else:
            bf_ml_per_min = x

    # find next time
    # ----check past days at similar time
    # ----check past days' qtys to see if qty lines up (bottle + bf)

    # find qty
    # ----at target time, compare last few days
    # ----see past qtys & approximate next qty to match total [quarter/half] hour?

    return time_out, qty_out


x = ["Jan 30 - 12:00 am, 90 mL", "Jan 30 - 2:30 am, 50 mL", "Jan 30 - 4:45 am, 40 mL",
     "Jan 30 - 6:15 am, 60 mL + 3 min BF", "Jan 30 - 9:00 am, 60 mL + 1 min BF", "Jan 30 - 11:45 am, 22 min BF",
     "Jan 30 - 1:30 pm, 20 mL", "Jan 30 - 3:40 pm, 70 mL + 10 min BF", "Jan 30 - 5:50 pm, 90 mL",
     "Jan 30 - 8:15 pm, 60 mL + 5 min BF", "Jan 30 - 9:45 pm, 70 mL", "", "Jan 31 - 12:05 am, 50mL",
     "Jan 31 - 1:35 am, 70 mL", "Jan 31 - 3:50 am, 30 mL", "Jan 31 - 6:05 am, 50 mL + 8 min BF",
     "Jan 31 - 8:45 am, 60 mL", "Jan 31 - 10:30 am, 30 mL", "Jan 31 - 11:40 am, 60 mL + 6 min BF",
     "Jan 31 - 1:35 pm, 60 mL + 11 min BF", "Jan 31 - 4:30 pm, 90 mL", "Jan 31 - 7:35 pm, 90 mL + 3 min BF",
     "Jan 31 - 9:45pm, 80 mL"]

y = get_time_qty(x)
