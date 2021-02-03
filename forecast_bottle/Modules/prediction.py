import pandas as pd
from datetime import date, datetime, timedelta


def get_time_qty(data):
    time_out = 0
    qty_out = 0
    num_days = 3
    today = datetime.today()
    year = today.year  # conditional based on cur month
    cols = []
    for str_in in data:
        x = str_in.find("-")  # single digit day vs. dual digit day
        strtime = str_in[:x] + str(year) + " " + str_in[x:]
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
                ddate = str(dtime.date())
                ttime = str(dtime.time())
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
                cols.append([ddate, ttime, mls, bfs])

    df = pd.DataFrame(cols, columns=["Date", "Time", "mLs", "BF Mins"], dtype=float)

    # find out how much 1 min BF is
    dates = []
    for i in range(1, num_days + 1):  # check total day intake (past 3 days)
        dates.append(datetime.strftime(today - timedelta(days=i), "%Y-%m-%d"))

    mls_sum = df.groupby("Date")["mLs"].sum().to_frame().reset_index()  # grouped sums of mLs
    mls_sum = mls_sum.set_index("Date")  # Date as index
    bfs_sum = df.groupby("Date")["BF Mins"].sum().to_frame().reset_index()  # grouped sums of BF Mins
    bfs_sum = bfs_sum.set_index("Date")  # Date as index

    mls_daily = []
    bfs_daily = []
    for i in range(num_days):
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
    bf_est = 5.3
    if len(mls_daily) < 2:  # can't interpolate -> assume breast output rate
        bf_ml_per_min = bf_est
    else:  # set them equal & approximate the BF content
        x = (mls_daily[0] - mls_daily[1]) / (bfs_daily[1] - bfs_daily[0])
        if len(mls_daily) == 3:  # use the third metric and then average
            y = (mls_daily[1] - mls_daily[2]) / (bfs_daily[2] - bfs_daily[1])
            z = (mls_daily[0] - mls_daily[2]) / (bfs_daily[2] - bfs_daily[0])
            bf_ml_per_min = (x + y + z) / 3
        else:
            bf_ml_per_min = x
    if bf_ml_per_min < 0:  # something went wrong -- should only happen if daily intake is wildly off for one day
        bf_ml_per_min = bf_est
    bf_ml_per_min=0 #for this case, breastfeeds are confounding --- he's bad at breastfeeding

    # find next hunger time
    fmt = "%Y-%m-%d"
    dtarget1 = datetime.strftime(today - timedelta(days=num_days), fmt)  # first day to consider
    dtarget2 = datetime.strftime(today, fmt)  # latest day to consider
    ttarget = df.tail(1).iloc[0, 1]  # time to consider
    fmt = fmt + " %H:%M:%S"
    dttarget = datetime.strptime(df.tail(1).iloc[0, 0] + " " + df.tail(1).iloc[0, 1], fmt)  # datetime of last feed
    last_few_days = df.set_index("Date").truncate(before=dtarget1, after=dtarget2)  # crop df to relevant rows
    last_few_days["BF mL"] = last_few_days["BF Mins"] * bf_ml_per_min  # add in mL for breastfeeds
    mlstarget = last_few_days.tail(1).iloc[0, 1] + last_few_days.tail(1).iloc[0, 3]  # mLs consumed at latest feed
    last_few_days = last_few_days.reset_index()
    t_diff = pd.to_datetime(last_few_days["Time"]) - pd.to_datetime(ttarget)  # check past days at similar time
    closest_times = t_diff.abs().groupby(last_few_days["Date"]).idxmin()  # closest time each past day
    closest_times = closest_times.truncate(after=closest_times.index[len(closest_times.index) - 2])  # don't count today
    day_indices = []  # indices of times we want to look at over last 3 days
    fmt = "%H:%M:%S"

    for i in range(num_days):  # compare each against last index (result can vary depending on midnight switch)
        abs_1 = abs(
            datetime.strptime(last_few_days.iloc[closest_times.iloc[i] - 1, 1], fmt) - datetime.strptime(ttarget, fmt))
        abs_1 = datetime.strptime("23:59:59", fmt) - abs_1  # basically, subtract the time from "24 hours"
        abs_1 = datetime.combine(date.min, abs_1.time()) - datetime.min  # time -> timedelta
        abs_2 = abs(
            datetime.strptime(last_few_days.iloc[closest_times.iloc[i], 1], fmt) - datetime.strptime(ttarget, fmt))
        if abs_1 < abs_2:
            day_indices.append(closest_times.iloc[i] - 1)
        else:
            day_indices.append(closest_times.iloc[i])

    delta = []  # for each index, see how long it took before next feed (proportional adj)
    mls_prop = []  # for each index, ratio of milk (in mLs) at that feed to mLs in recent feed
    delta_adj = []  # theoretical 'next feed' based on each delta & mls_prop
    fmt = "%Y-%m-%d " + fmt  # include date (not only time)
    for i in range(3):
        t1 = datetime.strptime(last_few_days.iloc[day_indices[i], 0] + " " + last_few_days.iloc[day_indices[i], 1], fmt)
        t2 = datetime.strptime(
            last_few_days.iloc[day_indices[i] + 1, 0] + " " + last_few_days.iloc[day_indices[i] + 1, 1], fmt)
        delta.append(t2 - t1)
        mls_prop.append((last_few_days.iloc[day_indices[i], 2] + last_few_days.iloc[day_indices[i], 4]) / mlstarget)
        delta_adj.append(delta[i] / mls_prop[i])

    avg_time_prop = sum(delta_adj, delta_adj[0]) / len(delta_adj)  # avg time until next feed is started
    time_out = dttarget + avg_time_prop

    # find qty expected to be requred at time_out --> at target time, compare last few days
    fmt = "%H:%M:%S"
    ttarget = datetime.strftime(time_out, fmt)  # time to consider
    dtarget1 = datetime.strftime(today - timedelta(days=num_days + 1), fmt)  # first day to consider
    last_few_days = df.set_index("Date").truncate(before=dtarget1, after=dtarget2)  # crop df to relevant rows
    last_few_days["BF mL"] = last_few_days["BF Mins"] * bf_ml_per_min  # add in mL for breastfeeds
    last_few_days = last_few_days.reset_index()
    t_diff = pd.to_datetime(last_few_days["Time"]) - pd.to_datetime(ttarget)  # check past days at similar time
    closest_times = t_diff.abs().groupby(last_few_days["Date"]).idxmin()  # closest time each past day
    closest_times = closest_times.truncate(before=closest_times.index[1],
                                           after=closest_times.index[len(closest_times.index) - 2])  # don't count today

    day_indices = []  # indices of times we want to look at over last 3 days
    for i in range(num_days):  # compare each against last index (result can vary depending on midnight switch)
        abs_1 = abs(
            datetime.strptime(last_few_days.iloc[closest_times.iloc[i] - 1, 1], fmt) - datetime.strptime(ttarget, fmt))
        abs_1 = datetime.strptime("23:59:59", fmt) - abs_1  # basically, subtract the time from "24 hours"
        abs_1 = datetime.combine(date.min, abs_1.time()) - datetime.min  # time -> timedelta
        abs_2 = abs(
            datetime.strptime(last_few_days.iloc[closest_times.iloc[i], 1], fmt) - datetime.strptime(ttarget, fmt))
        if abs_1 < abs_2:
            day_indices.append(closest_times.iloc[i] - 1)
        else:
            day_indices.append(closest_times.iloc[i])

    hrs_lag = 6  # use total consumption over past 6 hours (for now...)
    closest_back = []  # first index in the hrs_lag preceding the closest time (one extra index)
    fmt = "%Y-%m-%d " + fmt
    for i in range(len(day_indices) + 1):  # see past qtys & approximate next qty to match total
        if i < len(day_indices):  # past (not the current time slot)
            j = day_indices[i]
            dtarget1 = datetime.strptime(last_few_days.iloc[j, 0] + " " + last_few_days.iloc[j, 1], fmt)
            dtarget2 = dtarget1 - timedelta(hours=hrs_lag)
        else:  # current time slot (find total up until next feed)
            j = len(last_few_days)
            dtarget1 = time_out
            dtarget2 = dtarget1 - timedelta(hours=hrs_lag)
        while dtarget1 > dtarget2:
            j -= 1
            dtarget1 = datetime.strptime(last_few_days.iloc[j, 0] + " " + last_few_days.iloc[j, 1], fmt)
        closest_back.append(j)

    col_titles = ["Date", "Time", "mLs", "BF mL", "BF Mins"]  # to simplify sum across 2 columns
    last_few_days = last_few_days.reindex(columns=col_titles)
    last_few_days["mLs Tot"] = last_few_days["mLs"] + last_few_days["BF mL"]
    mls_tot = []

    for i in range(len(day_indices) + 1):
        if i < len(day_indices):  # past (not the current time slot)
            x = last_few_days.iloc[closest_back[i]:closest_times[i] + 1, 5].sum()
        else:
            x = last_few_days.iloc[closest_back[i]:len(last_few_days), 5].sum()
        mls_tot.append(int(x))

    avg_mls = (mls_tot[0] + mls_tot[1] + mls_tot[2]) / 3  # mLs for the hrs_lag period])
    x = avg_mls - mls_tot[len(mls_tot) - 1]
    if x < 0:
        qty_out = 0
    else:
        while int(x) % 10 > 0:
            x += 1
        qty_out = int(x)

    # time_out is a datetime object
    # qty_out is an integer (multiple of 10)
    return time_out, qty_out

