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
