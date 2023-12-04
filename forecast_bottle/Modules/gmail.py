import smtplib
import ssl
from pathlib import Path
from email.mime.text import MIMEText


def send_email(name, sender, time, qty, last_feed, avg_feed, daily_tot, daily_freq):
    folder = Path(__file__).resolve().parents[2]
    # credentials doc (change as necessary)
    creds_path = str(folder) + '/credentials.txt'

    try:
        creds_doc = open(creds_path, 'r')
    except Exception:
        return 'Error: Unable to open credentials doc (' + creds_path + ')'
    info = [line.rstrip() for line in creds_doc]

    recips_path = str(folder) + '/recipients.txt'  # change as necessary
    try:
        recips_doc = open(recips_path, 'r')
    except Exception:
        return 'Error: Unable to find recipients for the email (' + recips_path + ')'
    recips = [line.rstrip() for line in recips_doc]

    for i in range(len(info)):
        if info[i].lower() == 'gmail':
            start = info[i + 1].find(':') + 1
            un = info[i + 1][start:]  # get username
            start = info[i + 2].find(':') + 1
            pw = info[i + 2][start:]  # get password
            break
    if un == '' or pw == '':
        return 'Error: username/password info missing'

    time_adj = time.strftime('%b %d, %I:%M %p')
    last_feed_adj = last_feed.strftime('%b %d, %I:%M %p')
    daily_tot_adj = int(daily_tot)
    t_delta = str(daily_freq).split(':')
    if t_delta[2].find('.') > 0:
        x = t_delta[2].find('.')
        t_delta[2] = t_delta[2][:x]
    daily_freq_adj = t_delta[0] + ' hrs  ' + \
                     t_delta[1] + ' min  ' + t_delta[2] + ' sec'
    body_text = 'ESTIMATES'
    body_text = body_text + f'\n\nNext feed: {time_adj}'
    body_text = body_text + f'\n\nAmount: {qty}'
    body_text = body_text + '\n\n\nPAST DATA'
    body_text = body_text + \
                f'\n\nLast feed\n{last_feed_adj}'
    body_text = body_text + \
                f'\n\nAvg milk amounts\nday: {daily_tot_adj} mL  |  feed: {avg_feed} mL'
    body_text = body_text + f'\n\nAvg time between feeds\n{daily_freq_adj}'

    msg = MIMEText(body_text, 'plain')
    msg['Subject'] = f'{name}\'s Feed Schedule'
    msg['From'] = sender
    msg['To'] = ','.join(recips)

    port = 465  # For SSL
    smtp_server = 'smtp.gmail.com'
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(un, pw)
            server.sendmail(un, recips, msg.as_string())
        return
    except Exception as e:
        ret = 'Error: Unable to send email:\n' + str(e)
        return ret
