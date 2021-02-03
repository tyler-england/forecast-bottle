import smtplib, ssl
from pathlib import Path
from email.mime.text import MIMEText


def send_email(time, qty):
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

    time_adj = time.strftime("%b %d, %H:%M%p")
    body_text = "Approx. next feed: {time}".format(time=time_adj)
    body_text = body_text + "\n\nApprox. amount required: {qty} mL".format(qty=qty)

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
