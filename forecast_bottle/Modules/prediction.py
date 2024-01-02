import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path
from dateutil.relativedelta import relativedelta


def get_time_qty_summary(data_list):
    time_next = 0
    qty_next = 0
    num_days = 3
    today = datetime.today()
    cols = []
    for str_in in data_list:
        # ex: Jan 1 - 3:00 pm, 30 mL + 15 min BF
        if len(str_in) > 0:
            day_info = str_in.split('-')
            day = day_info[0].strip().replace(',', '')
            info = day_info[1].strip()
            try:  # if year is specified, use that (Jan 1 likely)
                year = datetime.strptime(day, '%b %d %Y').year
                strtime = f'{day} - {info}'.lower()
            except:
                year = today.year
                try:
                    if datetime.strptime(day + ' ' + str(year), '%b %d %Y') > today:
                        year = year - 1
                    strtime = f'{day} {year} - {info}'.lower()
                except:
                    strtime = ''
        else:
            strtime = ''

        # ex: Jan 1 - 3:00 pm, 30 mL + 15 min BF
        x = strtime.find(',')
        y = strtime.find('ml')
        z = strtime.find('+')
        if x > 0:  # time + qty given
            try:  # date/time typos (some common ones from typing in Keep)
                dt = datetime.strptime(
                    strtime[:x], '%b %d %Y - %I:%M %p')  # date/time
            except Exception:
                try:
                    dt = datetime.strptime(
                        strtime[:x], '%b %d %Y - %I:%M%p')  # date/time
                except Exception:
                    try:
                        dt = datetime.strptime(
                            strtime[:x], '%b %d%Y - %I:%M %p')  # date/time
                    except Exception:
                        try:
                            dt = datetime.strptime(
                                strtime[:x], '%b %d %Y -%I:%M %p')  # date/time
                        except Exception:
                            dt = 0
            if dt != 0:
                str_date = str(dt.date())
                str_time = str(dt.time())
                if y > 0:  # bottle was given
                    mls = int(strtime[x + 1:y])  # qty of milk (mL)
                else:
                    mls = 0
                min_start = strtime.lower().find('min')
                if min_start > 0:
                    if z > 0:  # add'l breast feed (min)
                        bfs = int(strtime[z + 1:min_start])
                    else:  # bf only (no bottle)
                        bfs = int(strtime[x + 1:min_start])
                else:  # no 'min'
                    bfs = 0
                cols.append([str_date, str_time, mls, bfs])

    df = pd.DataFrame(
        cols, columns=['Date', 'Time', 'mLs', 'BF Mins'])
    # so Keep note can be organized however is easiest
    df = df.sort_values(by=['Date', 'Time']).reset_index(drop=True)

    df['dt'] = pd.to_datetime(df['Date'])
    df = df[df['dt'] > (today - timedelta(days=30))]
    df = df.drop(columns='dt')

    # find out how much 1 min BF is
    dates = []
    for i in range(1, num_days + 1):  # check total day intake (past 3 days)
        dates.append(datetime.strftime(today - timedelta(days=i), '%Y-%m-%d'))

    mls_sum = df.groupby('Date', as_index=False)['mLs'].sum()  # grouped daily sums of mLs
    bfs_sum = df.groupby('Date', as_index=False)['BF Mins'].sum()  # grouped sums of BF Mins
    mls_daily = []
    bfs_daily = []
    for i in range(num_days):
        try:
            ml = mls_sum['mLs'].iloc[len(mls_sum) - 1 - i]
        except:
            ml = 0
        try:
            bf = bfs_sum['BF Mins'].iloc[len(bfs_sum) - 1 - i]
        except:
            bf = 0
        if ml > 0 or bf > 0:
            mls_daily.append(ml)
            bfs_daily.append(bf)

    bf_est = 2  # estimated mL per minute
    if len(mls_daily) < 2 or sum(mls_daily) < 100:  # can't interpolate -> assume breast output rate
        bf_ml_per_min = bf_est
    else:  # set them equal & approximate the BF content
        x = y = z = 0
        if bfs_daily[0] > 0 or bfs_daily[1] > 0:
            x = (mls_daily[0] - mls_daily[1]) / (bfs_daily[1] - bfs_daily[0])
        if len(mls_daily) == 3:  # use the third metric and (average if multiple results)
            if bfs_daily[1] > 0 or bfs_daily[2] > 0:
                y = (mls_daily[1] - mls_daily[2]) / \
                    (bfs_daily[2] - bfs_daily[1])
            if bfs_daily[2] > 0 or bfs_daily[0] > 0:
                z = (mls_daily[0] - mls_daily[2]) / \
                    (bfs_daily[2] - bfs_daily[0])

        ls_tmp = [x, y, z]  # temp to find nonzeros
        ls_avg = [i for i in ls_tmp if i > 0]
        if len(ls_avg) > 1:
            bf_ml_per_min = sum(ls_avg) / len(ls_avg)
        else:
            bf_ml_per_min = 0
    if bf_ml_per_min <= 0 or bf_ml_per_min > 10:  # something went wrong
        bf_ml_per_min = bf_est
    df['BF mL'] = df['BF Mins'] * bf_ml_per_min  # add in mL for breastfeeds

    if df['mLs'].iloc[len(df.index) - 1] == 0 and df['BF mL'].iloc[len(df.index) - 1] == 0:
        print('data processed before latest feed was finished being entered')
        return 0, 0, 0, 0, 0, 0, 0

    bf_ml_sum = df.groupby('Date', as_index=False)['BF mL'].sum()  # grouped sums of BF Mins
    bf_daily = bf_ml_sum['BF mL'].tolist()

    mls_tot = []  # for calculating total daily intake

    for i in range(max(len(mls_daily), len(bf_daily))):
        try:
            ml_bot = mls_daily[i]
        except:
            ml_bot = 0
        try:
            ml_bf = bf_daily[i]
        except:
            ml_bf = 0
        mls_tot.append(ml_bot + ml_bf)
    if len(mls_tot) > 0:
        info_daily_tot = sum(mls_tot) / len(mls_tot)
    else:
        info_daily_tot = '???'

    # find next hunger time
    fmt = '%Y-%m-%d'
    dtarget1 = datetime.strftime(
        today - timedelta(days=num_days), fmt)  # first day to consider
    dtarget2 = datetime.strftime(today, fmt)  # latest day to consider
    time_target = df.tail(1).iloc[0, 1]  # time to consider in past days
    fmt = fmt + ' %H:%M:%S'
    time_last = datetime.strptime(df.tail(
        1).iloc[0, 0] + ' ' + df.tail(1).iloc[0, 1], fmt)  # time of last feed
    last_few_days = df.set_index('Date').truncate(
        before=dtarget1, after=dtarget2)  # crop df to relevant rows
    # mLs consumed at latest feed
    mls_target = last_few_days.tail(1).iloc[0, 1] + last_few_days.tail(1).iloc[0, 3]
    if mls_target == 0:  # current 'lastest feed' line is unfinished?
        mls_target = last_few_days.tail(2).iloc[0, 1] + last_few_days.tail(2).iloc[0, 3]
    last_few_days = last_few_days.reset_index()
    # check past days at similar time
    last_few_days['tdiff'] = abs(pd.to_datetime(
        last_few_days['Time'], format='%H:%M:%S') - pd.to_datetime(time_target, format='%H:%M:%S'))
    closest_times = last_few_days.groupby('Date', as_index=False)['tdiff'].min()  # closest time each past day
    if len(closest_times) > num_days:  # includes current day
        closest_times = closest_times.head(len(closest_times) - 1)  # don't count today

    day_indices = []  # indices of times we want to look at over last 3 days
    fmt = '%H:%M:%S'
    # compare each against last index (result can vary depending on midnight switch)
    for i in range(len(closest_times)):
        df_ind = last_few_days[(last_few_days['Date'] == closest_times['Date'].iloc[i]) & (
                last_few_days['tdiff'] == closest_times['tdiff'].iloc[i])]
        ind = df_ind.index[0]
        # check if midnight is an issue
        # ex: time=12:10 am, day's closest time is 2:15 am, previous day has 11:55 pm
        try:
            td = timedelta(hours=24)
            val_tst = td - last_few_days['tdiff'].iloc[ind - 1]
            if val_tst < last_few_days['tdiff'].iloc[ind]:
                ind = ind - 1
        except:
            pass
        day_indices.append(ind)

    delta = []  # for each index, see how long it took before next feed
    # for each index, ratio of milk (in mLs) at that feed to mLs in recent feed
    mls_prop = []
    delta_adj = []  # theoretical 'next feed' based on each delta & mls_prop
    fmt = '%Y-%m-%d ' + fmt  # include date (not only time)

    for i in range(len(day_indices)):
        try:  # will fail on last iteration if new day AND no feed yet
            t1 = datetime.strptime(last_few_days.iloc[day_indices[i], 0] + ' ' + last_few_days.iloc[day_indices[i], 1],
                                   fmt)
            t2 = datetime.strptime(
                last_few_days.iloc[day_indices[i] + 1, 0] + ' ' + last_few_days.iloc[day_indices[i] + 1, 1], fmt)
        except Exception:  # use previous time gap
            t1 = datetime.strptime(
                last_few_days.iloc[day_indices[i] - 1, 0] +
                ' ' + last_few_days.iloc[day_indices[i] - 1, 1],
                fmt)
            t2 = datetime.strptime(
                last_few_days.iloc[day_indices[i], 0] + ' ' + last_few_days.iloc[day_indices[i], 1], fmt)
        delta.append(t2 - t1)
        x = (last_few_days.iloc[day_indices[i], 2] +
             last_few_days.iloc[day_indices[i], 4]) / mls_target
        # may be comparing to unusually low amount from prior day(s)
        x = max(x, .625)
        mls_prop.append(x)
        try:
            delta_adj.append(delta[i] / mls_prop[i])
        except Exception:
            delta_adj.append(delta[i])

    avg_time_prop = timedelta(days=0)  # avg time until next feed is started
    for i in range(len(delta_adj)):
        avg_time_prop = avg_time_prop + delta_adj[i]
    avg_time_prop = avg_time_prop / len(delta_adj)
    time_next = time_last + avg_time_prop
    # 4 hours max between feedings
    time_max = time_last + timedelta(hours=4)
    if time_next > time_max:
        time_next = time_max

    feed = []
    freqs = []
    age_doc = str(Path(__file__).parents[2]) + \
              '/age_info.txt'  # find birthday_doc
    try:
        with open(age_doc, 'r') as agedoc:
            # check time difference against recommended standard
            age_lines = [line.rstrip() for line in agedoc]
    except Exception:
        print('Error: Unable to find the age doc (' + age_doc + ')')
        age_lines = []
    if len(age_lines) > 0:
        try:
            x = age_lines[0].find(' ') + 1
            birthday = datetime.strptime(age_lines[0][x:].strip(), '%Y-%m-%d')
            # double // --> rounds results down to nearest int
            num_wks = (today - birthday).days // 7
            for i in age_lines:
                try:
                    recs = i.split(',')
                    if int(recs[0][:recs[0].find('-')]) <= num_wks <= int(
                            recs[0][recs[0].find('-') + 1:]):  # correct line for current age
                        feed.append(int(recs[1]))
                        feed.append(int(recs[2]))
                        if len(recs) > 3:
                            freqs.append(int(recs[3]))
                            freqs.append(int(recs[4]))
                        break  # exit for loop
                except Exception:  # birthday line, header line, etc.
                    pass
            if len(freqs) > 0:  # min & max hrs were found --> evaluate time_next
                x = 0
                while (time_next - time_last).seconds // 3600 < freqs[
                    0]:  # increase time_next until hrs eclipse minimum diff
                    time_next = time_next + timedelta(minutes=15)
                    x += 1
                    if x > 100:
                        break
                while (time_next - time_last).seconds / 3600 > freqs[
                    1]:  # decrease time_next until hrs are under maximum diff
                    time_next = time_next - timedelta(minutes=15)
                    x += 1
                    if x > 200:
                        break
        except Exception:
            pass

    # find qty expected to be requred at time_out --> at target time, compare last few days
    fmt = '%Y-%m-%d'
    dtarget1 = datetime.strftime(
        today - timedelta(days=num_days + 1), fmt)  # first day to consider
    fmt = '%H:%M:%S'
    time_target = datetime.strftime(time_next, fmt)  # time to consider
    last_few_days = df.set_index('Date').truncate(
        before=dtarget1, after=dtarget2)  # crop df to relevant rows
    last_few_days = last_few_days.reset_index()
    # check past days at similar time
    last_few_days['tdiff'] = abs(pd.to_datetime(
        last_few_days['Time'], format='%H:%M:%S') - pd.to_datetime(time_target, format='%H:%M:%S'))
    closest_times = last_few_days.groupby('Date', as_index=False)['tdiff'].min()  # closest time each past day
    if len(closest_times) > num_days:  # includes current day
        closest_times = closest_times.head(len(closest_times) - 1)  # don't count today

    day_indices = []  # indices of times we want to look at over last 3 days
    fmt = '%H:%M:%S'
    # compare each against last index
    for i in range(len(closest_times)):
        df_ind = last_few_days[(last_few_days['Date'] == closest_times['Date'].iloc[i]) & (
                last_few_days['tdiff'] == closest_times['tdiff'].iloc[i])]
        ind = df_ind.index[0]
        # check if midnight is an issue
        # ex: time=12:10 am, day's closest time is 2:15 am, previous day has 11:55 pm
        try:
            td = timedelta(hours=24)
            val_tst = td - last_few_days['tdiff'].iloc[ind - 1]
            if val_tst < last_few_days['tdiff'].iloc[ind]:
                ind = ind - 1
        except:
            pass
        day_indices.append(ind)

    hrs_lag = 10  # use total consumption over past [hrs_lag] hours
    # first index in the hrs_lag preceding the closest time (one extra index)
    closest_back = []
    fmt = '%Y-%m-%d ' + fmt
    # see past qtys & approximate next qty to match total
    for i in range(len(day_indices) + 1):
        if i < len(day_indices):  # past (not the current time slot)
            j = day_indices[i]
            dtarget1 = datetime.strptime(
                last_few_days.iloc[j, 0] + ' ' + last_few_days.iloc[j, 1], fmt)
            dtarget2 = dtarget1 - timedelta(hours=hrs_lag)
        else:  # current time slot (find total up until next feed)
            j = len(last_few_days)
            dtarget1 = time_next
            dtarget2 = dtarget1 - timedelta(hours=hrs_lag)
        while dtarget1 > dtarget2 and j > 0:
            j -= 1
            dtarget1 = datetime.strptime(
                last_few_days.iloc[j, 0] + ' ' + last_few_days.iloc[j, 1], fmt)
        closest_back.append(j)

    # to simplify sum across 2 columns
    last_few_days['mLs Tot'] = last_few_days['mLs'] + last_few_days['BF mL']
    mls_tot = []

    for i in range(len(day_indices) + 1):
        if i < len(day_indices):  # past (not the current time slot)
            x = last_few_days['mLs Tot'].iloc[closest_back[i]:day_indices[i]].sum()
        else:  # this current time slot
            x = last_few_days['mLs Tot'].iloc[closest_back[i]:len(last_few_days)].sum()
        mls_tot.append(int(x))

    # mLs for the hrs_lag period
    avg_mls = (sum(mls_tot) - mls_tot[len(mls_tot) - 1]) / (len(mls_tot) - 1)

    # x=theoretically how many mL still needed to fill current 10hr slot
    x = avg_mls - mls_tot[len(mls_tot) - 1]
    if x < 0:  # low amount from past day may be dragging down avg
        x = max(mls_tot) - mls_tot[len(mls_tot) - 1]
    if x < 0:  # enough food was eaten already for this entire period
        qty_next = 0
        print('Program says no food will be needed... mls_tot: ' + str(mls_tot))
    else:
        if len(age_lines) > 0:  # set min/max based on age
            if len(feed) > 0:  # min/max were found
                feed_min = feed[0]
                feed_max = feed[1]
        else:
            # default values
            feed_min = 60
            feed_max = 180
        while x < feed_min:  # bring up to at least minimum
            x += 10
        while x > feed_max:  # bring down to the max amount
            x -= 10
        while int(x) % 10 > 0:  # easier to measure into a bottle
            x += 1
        qty_next = int(x)

    # find avg feed size
    info_avg = last_few_days.groupby(
        'Date')['mLs Tot'].mean()  # grouped avgs of mLs
    info_avg = sum(info_avg) / len(info_avg)
    info_avg = int(info_avg)
    if qty_next == 0:  # use average feed size
        if feed:  # min/max for age were found
            qty_next = max(info_avg, feed[0])
        else:
            qty_next = info_avg
    bf_mins = int(qty_next / bf_ml_per_min)
    while bf_mins % 5 > 0:  # mults of 5
        bf_mins -= 1

    # find avg frequency of feeds
    t_delta = []
    for i in range(len(last_few_days) - 1):
        t1 = datetime.strptime(
            last_few_days.iloc[i, 0] + ' ' + last_few_days.iloc[i, 1], fmt)
        t2 = datetime.strptime(
            last_few_days.iloc[i + 1, 0] + ' ' + last_few_days.iloc[i + 1, 1], fmt)
        t_delta.append(t2 - t1)
    info_freq = sum(t_delta, timedelta()) / len(t_delta)

    # time_next is a datetime object
    # qty_next is an integer (multiple of 10)
    # bf_mins is an integer (multiple of 5)
    # time_last is a datetime object
    # info_daily_tot is integer/float
    # info_freq is a time
    return time_next, qty_next, bf_mins, time_last, info_avg, info_daily_tot, info_freq
