import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path
from dateutil.relativedelta import relativedelta


def get_time_qty_summary(data):
    time_next = 0
    qty_next = 0
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
                if dtime > today:  # the year should likely be last year
                    dtime=dtime-relativedelta(years=1)
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
    df = df.sort_values(by=["Date", "Time"]).reset_index(drop=True)  # so Keep note can be organized however is easiest

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
        x = y = z = 0
        if bfs_daily[0] > 0 or bfs_daily[1] > 0:
            x = (mls_daily[0] - mls_daily[1]) / bfs_daily[1] - bfs_daily[0]
        if len(mls_daily) == 3:  # use the third metric and (average if multiple results)
            if bfs_daily[1] > 0 or bfs_daily[2] > 0:
                y = (mls_daily[1] - mls_daily[2]) / (bfs_daily[2] - bfs_daily[1])
            if bfs_daily[2] > 0 or bfs_daily[0] > 0:
                z = (mls_daily[0] - mls_daily[2]) / (bfs_daily[2] - bfs_daily[0])
        ls_av = [x, y, z]  # temp to find nonzeros
        ls_avg = []  # tool to easily average unknown qty of numbers
        for i in ls_av:
            if i > 0:
                ls_avg.append(i)
        if len(ls_avg) == 0:
            bf_ml_per_min = 0
        else:
            bf_ml_per_min = sum(ls_avg) / len(ls_avg)
    if bf_ml_per_min < 0:  # something went wrong -- should only happen if daily intake is wildly off for one day
        bf_ml_per_min = bf_est
    mls_tot = []  # for calculating total daily intake
    for i in range(len(mls_daily)):
        mls_tot.append(mls_daily[i] + (bfs_daily[i] * bf_ml_per_min))
    info_daily_tot = "???"  # default if nothing was found
    if len(mls_tot) > 0:
        info_daily_tot = sum(mls_tot) / len(mls_tot)

    # find next hunger time
    fmt = "%Y-%m-%d"
    dtarget1 = datetime.strftime(today - timedelta(days=num_days), fmt)  # first day to consider
    dtarget2 = datetime.strftime(today, fmt)  # latest day to consider
    ttarget = df.tail(1).iloc[0, 1]  # time to consider
    fmt = fmt + " %H:%M:%S"
    info_last = datetime.strptime(df.tail(1).iloc[0, 0] + " " + df.tail(1).iloc[0, 1], fmt)  # datetime of last feed
    last_few_days = df.set_index("Date").truncate(before=dtarget1, after=dtarget2)  # crop df to relevant rows
    last_few_days["BF mL"] = last_few_days["BF Mins"] * bf_ml_per_min  # add in mL for breastfeeds
    mlstarget = last_few_days.tail(1).iloc[0, 1] + last_few_days.tail(1).iloc[0, 3]  # mLs consumed at latest feed
    last_few_days = last_few_days.reset_index()
    t_diff = pd.to_datetime(last_few_days["Time"]) - pd.to_datetime(ttarget)  # check past days at similar time
    closest_times = t_diff.abs().groupby(last_few_days["Date"]).idxmin()  # closest time each past day
    if len(closest_times) > 3:  # includes current day
        closest_times = closest_times.truncate(
            after=closest_times.index[len(closest_times.index) - 1])  # don't count today
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

    delta = []  # for each index, see how long it took before next feed
    mls_prop = []  # for each index, ratio of milk (in mLs) at that feed to mLs in recent feed
    delta_adj = []  # theoretical 'next feed' based on each delta & mls_prop
    fmt = "%Y-%m-%d " + fmt  # include date (not only time)

    for i in range(3):
        try:  # will fail on last iteration if new day AND no feed yet
            t1 = datetime.strptime(last_few_days.iloc[day_indices[i], 0] + " " + last_few_days.iloc[day_indices[i], 1],
                                   fmt)
            t2 = datetime.strptime(
                last_few_days.iloc[day_indices[i] + 1, 0] + " " + last_few_days.iloc[day_indices[i] + 1, 1], fmt)
        except Exception:  # use previous time gap
            t1 = datetime.strptime(
                last_few_days.iloc[day_indices[i] - 1, 0] + " " + last_few_days.iloc[day_indices[i] - 1, 1],
                fmt)
            t2 = datetime.strptime(
                last_few_days.iloc[day_indices[i], 0] + " " + last_few_days.iloc[day_indices[i], 1], fmt)
        delta.append(t2 - t1)
        x = (last_few_days.iloc[day_indices[i], 2] + last_few_days.iloc[day_indices[i], 4]) / mlstarget
        x = max(x, .625)  # may be comparing to unusually low amount from prior day(s)
        mls_prop.append(x)
        try:
            delta_adj.append(delta[i] / mls_prop[i])
        except Exception:
            delta_adj.append(delta[i])

    avg_time_prop = (delta_adj[0] + delta_adj[1] + delta_adj[2]) / len(delta_adj)  # avg time until next feed is started
    time_next = info_last + avg_time_prop
    time_max = info_last + timedelta(minutes=45, hours=3)  # 4 hours max between feedings
    if time_next > time_max:
        time_next = time_max

    age_lines = []  # check time difference against recommended standard
    feed = []
    freqs = []
    age = str(Path(__file__).parents[2]) + "/age_info.txt"  # find birthday_doc
    try:
        with open(age, "r") as agedoc:
            age_lines = [line.rstrip() for line in agedoc]
    except Exception:
        print("Error: Unable to find the age doc (" + age + ")")
    if len(age_lines) > 0:
        try:
            x = age_lines[0].find(" ") + 1
            birthday = datetime.strptime(age_lines[0][x:].strip(), "%Y-%m-%d")
            num_wks = (today - birthday).days // 7  # double // --> rounds results down to nearest int
            # i = 0
            # while not age_lines[i][:1].isnumeric():
            #     i += 1
            # age_lines = age_lines[i:]  # remove the header info -- keep only the numeric data
            for i in age_lines:
                try:
                    recs = i.split(",")
                    if int(recs[0]) <= num_wks <= int(recs[1]):  # correct line for current age
                        feed.append(int(recs[2]))
                        feed.append(int(recs[3]))
                        if len(recs) > 3:
                            freqs.append(int(recs[4]))
                            freqs.append(int(recs[5]))
                        break  # exit for loop
                except Exception:  # birthday line, header line, etc.
                    pass
            if freqs:  # min & max were found --> evaluate time_next
                x = 0
                while (time_next - info_last).seconds // 3600 < freqs[
                    0]:  # increase time_next until hrs eclipse minimum diff
                    time_next = time_next + timedelta(minutes=15)
                    x += 1
                    if x > 100:
                        break
                while (time_next - info_last).seconds / 3600 > freqs[
                    1]:  # decrease time_next until hrs are under maximum diff
                    time_next = time_next - timedelta(minutes=15)
                    x += 1
                    if x > 200:
                        break
        except Exception:
            pass

    # find qty expected to be requred at time_out --> at target time, compare last few days
    fmt = "%Y-%m-%d"
    dtarget1 = datetime.strftime(today - timedelta(days=num_days + 1), fmt)  # first day to consider
    fmt = "%H:%M:%S"
    ttarget = datetime.strftime(time_next, fmt)  # time to consider
    last_few_days = df.set_index("Date").truncate(before=dtarget1, after=dtarget2)  # crop df to relevant rows
    last_few_days["BF mL"] = last_few_days["BF Mins"] * bf_ml_per_min  # add in mL for breastfeeds
    last_few_days = last_few_days.reset_index()
    t_diff = pd.to_datetime(last_few_days["Time"]) - pd.to_datetime(ttarget)  # check past days at similar time
    closest_times = t_diff.abs().groupby(last_few_days["Date"]).idxmin()  # closest time each past day
    closest_times = closest_times.truncate(before=closest_times.index[1])  # remove '4th day back'
    if len(closest_times) > 3:  # don't count today
        closest_times = closest_times.truncate(
            after=closest_times.index[len(closest_times.index) - 2])

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

    hrs_lag = 10  # use total consumption over past [hrs_lag] hours
    closest_back = []  # first index in the hrs_lag preceding the closest time (one extra index)
    fmt = "%Y-%m-%d " + fmt
    for i in range(len(day_indices) + 1):  # see past qtys & approximate next qty to match total
        if i < len(day_indices):  # past (not the current time slot)
            j = day_indices[i]
            dtarget1 = datetime.strptime(last_few_days.iloc[j, 0] + " " + last_few_days.iloc[j, 1], fmt)
            dtarget2 = dtarget1 - timedelta(hours=hrs_lag)
        else:  # current time slot (find total up until next feed)
            j = len(last_few_days)
            dtarget1 = time_next
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
    if x < 0:  # low amount from past day may be dragging down avg
        x = max(mls_tot) - mls_tot[len(mls_tot) - 1]
    if x < 0:  # enough food was eaten already for this entire period
        qty_next = 0
        print("Program says no food will be needed... mls_tot: " + str(mls_tot))
    else:
        # default values
        feed_min = 60
        feed_max = 180
        if len(age_lines) > 0:  # set min/max based on age
            if feed:  # min/max were found
                feed_min = feed[0]
                feed_max = feed[1]
        while x < feed_min:  # bring up to at least minimum
            x += 10
        while x > feed_max:  # bring down to the max amount
            x -= 10
        while int(x) % 10 > 0:  # easier to measure into a bottle
            x += 1
        qty_next = int(x)

    # find avg feed size
    info_avg = last_few_days.groupby("Date")["mLs Tot"].mean()  # grouped avgs of mLs
    info_avg = sum(info_avg) / len(info_avg)
    info_avg = int(info_avg)
    if qty_next == 0:  # use average feed size
        if feed:  # min/max for age were found
            qty_next = max(info_avg, feed[1])
        else:
            qty_next = info_avg

    # find avg frequency of feeds
    t_delta = []
    for i in range(len(last_few_days) - 1):
        t1 = datetime.strptime(last_few_days.iloc[i, 0] + " " + last_few_days.iloc[i, 1], fmt)
        t2 = datetime.strptime(last_few_days.iloc[i + 1, 0] + " " + last_few_days.iloc[i + 1, 1], fmt)
        t_delta.append(t2 - t1)
    info_freq = sum(t_delta, timedelta()) / len(t_delta)

    # time_next is a datetime object
    # qty_next is an integer (multiple of 10)
    # info_last is a datetime object
    # info_daily_tot is integer/float
    # info_freq is a time
    return time_next, qty_next, info_last, info_avg, info_daily_tot, info_freq
