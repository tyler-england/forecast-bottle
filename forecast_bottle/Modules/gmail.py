import smtplib, ssl
from pathlib import Path
from email.mime.text import MIMEText


def send_email(time, qty, last_feed, avg_feed, daily_tot, daily_freq):
    folder = Path(__file__).parents[2]
    folder = str(folder)

    doc_path = folder + "/credentials.txt"  # credentials doc (change as necessary)
    try:
        logindoc = open(doc_path, "r")
    except Exception:
        return "Error: Unable to open credentials doc (" + doc_path + ")"
    info = [line.rstrip() for line in logindoc]

    doc_path = folder + "/recipients.txt"  # change as necessary
    try:
        recipdoc = open(doc_path, "r")
    except Exception:
        return "Error: Unable to find recipients for the email (" + doc_path + ")"
    recips = [line.rstrip() for line in recipdoc]

    for i in range(len(info)):
        if info[i].lower() == "gmail":
            x = info[i + 1].find(":") + 1
            un = info[i + 1][x:]  # get username
            x = info[i + 2].find(":") + 1
            pw = info[i + 2][x:]  # get password
    if un == "" or pw == "":
        return "Error: username/password info missing"

    time_adj = time.strftime("%b %d, %I:%M %p")
    last_feed_adj = last_feed.strftime("%b %d, %I:%M %p")
    daily_tot_adj = int(daily_tot)
    t_delta = str(daily_freq).split(":")
    if t_delta[2].find(".") > 0:
        x = t_delta[2].find(".")
        t_delta[2] = t_delta[2][:x]
    daily_freq_adj = t_delta[0] + " hrs  " + t_delta[1] + " min  " + t_delta[2] + " sec"
    body_text = "ESTIMATES"
    body_text = body_text + "\n\nNext feed: {time}".format(time=time_adj)
    body_text = body_text + "\n\nAmount: {qty} mL".format(qty=qty)
    body_text = body_text + "\n\n\nPAST DATA"
    body_text = body_text + "\n\nLast feed\n{last_feed}".format(last_feed=last_feed_adj)
    body_text = body_text + "\n\nAvg milk amounts\nday: {daily_tot} mL  |  feed: {avg_feed} mL".format(
        daily_tot=daily_tot_adj, avg_feed=avg_feed)
    body_text = body_text + "\n\nAvg time between feeds\n{daily_freq}".format(daily_freq=daily_freq_adj)

    msg = MIMEText(body_text, "plain")
    msg['Subject'] = "Corwin's Feed Schedule"
    msg['From'] = "Tyler England"
    msg['To'] = ",".join(recips)

    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(un, pw)
            server.sendmail(un, recips, msg.as_string())
        return
    except Exception:
        return "Error: Unable to send email"
