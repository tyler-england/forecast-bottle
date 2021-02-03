import gkeepapi
from pathlib import Path


def get_content():
    folder = Path(__file__).parents[2]
    folder = str(folder)
    cred_doc_path = folder + "/credentials.txt"  # change as necessary

    try:
        logindoc = open(cred_doc_path, "r")
    except Exception:
        return "Error: Unable to find/open credentials doc (" + cred_doc_path + ")"

    info = [line.rstrip() for line in logindoc]

    for i in range(len(info)):
        if info[i].lower() == "keep":
            x = info[i + 1].find(":") + 1
            un = info[i + 1][x:]  # get username
            x = info[i + 2].find(":") + 1
            pw = info[i + 2][x:]  # get password

    if un == "" or pw == "":
        return "Error: Issue with username and/or password"

    keep = gkeepapi.Keep()
    try:
        keep.login(un, pw)
    except Exception:
        return "Error: Login failed... Check username / password"

    note_id = "18i006fRpqyTZ10dTkSfMed5zAGLJ7YL_j5bo4pG9sajuHO1EywLX5jeTB2il7K-LlZyF"  # change as necessary

    note = keep.get(note_id)
    content = note.text
    content = content.split("\n")[2:]  # remove header, organize as list

    return content


x = "['Jan 30 - 12:00 am, 90 mL', 'Jan 30 - 2:30 am, 50 mL', 'Jan 30 - 4:45 am, 40 mL', 'Jan 30 - 6:15 am, 60 mL + 3 min BF', 'Jan 30 - 9:00 am, 60 mL + 1 min BF', 'Jan 30 - 11:45 am, 22 min BF', 'Jan 30 - 1:30 pm, 20 mL', 'Jan 30 - 3:40 pm, 70 mL + 10 min BF', 'Jan 30 - 5:50 pm, 90 mL', 'Jan 30 - 8:15 pm, 60 mL + 5 min BF', 'Jan 30 - 9:45 pm, 70 mL', '', 'Jan 31 - 12:05 am, 50 mL', 'Jan 31 - 1:35 am, 70 mL', 'Jan 31 - 3:50 am, 30 mL', 'Jan 31 - 6:05 am, 50 mL + 8 min BF', 'Jan 31 - 8:45 am, 60 mL', 'Jan 31 - 10:30 am, 30 mL', 'Jan 31 - 11:40 am, 60 mL + 6 min BF', 'Jan 31 - 1:35 pm, 60 mL + 11 min BF', 'Jan 31 - 4:30 pm, 90 mL', 'Jan 31 - 7:35 pm, 90 mL + 3 min BF', 'Jan 31 - 9:45 pm, 80 mL', '', 'Feb 1 - 12:45 am, 90 mL', 'Feb 1 - 4:10 am, 100 mL', 'Feb 1 - 6:45 am, 90 mL + 5 min BF', 'Feb 1 - 9:30 am, 90 mL', 'Feb 1 - 11:45 am, 90 mL', 'Feb 1 - 1:50 pm, 26 min BF', 'Feb 1 - 3:00 pm, 60 mL', 'Feb 1 - 6:00 pm, 70 mL', 'Feb 1 - 8:45 pm, 100 mL', 'Feb 1 - 11:40 pm, 70 mL', '', 'Feb 2 - 1:40 am, 75 mL', 'Feb 2 - 3:00 am, 20 mL', 'Feb 2 - 5:10 am, 70 mL', 'Feb 2 - 6:50 am, 50 mL', 'Feb 2 - 8:40 am, 30 mL', 'Feb 2 - 10:50 am, 80 mL', 'Feb 2 - 12:20 pm, 70 mL', 'Feb 2 - 2:50 pm, 80 mL', 'Feb 2 - 4:15pm, 60 mL', 'Feb 2 - 5:50 pm, 60 mL ', 'Feb 2 - 7:45 pm, 70 mL', 'Feb 2 - 9:25 pm, 50 mL', '', 'Feb 3 - 12:05 am, 90 mL', 'Feb 3 - 2:15 am, 80 mL', 'Feb 3 - 3:45 am, 50 mL', 'Feb 3 - 4:55 am, 40 mL', 'Feb 3 - 6:45 am, 70 mL', 'Feb 3 - 9:50 am, 70 mL', 'Feb 3 - 12:00 pm, 90 mL', '', '']"

y = x.replace("'", "\"")
print(y)
