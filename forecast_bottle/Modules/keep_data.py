import gkeepapi
from pathlib import Path


def get_content(name):
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
    except:
        return "Error: Login failed... Check username / password "  # + str(un) + " " + str(pw)

    note_id = "18i006fRpqyTZ10dTkSfMed5zAGLJ7YL_j5bo4pG9sajuHO1EywLX5jeTB2il7K-LlZyF"  # change as necessary

    note = keep.get(note_id)
    content = note.text
    content = content.split("\n")  # organize as list
    content = [i.strip() for i in content]

    # back up data in case of Keep clearout
    backup = str(Path(__file__).parents[2]) + "/data_log.txt"  # data backup
    if not Path(backup).exists():
        with open(backup, "w"): pass
    data_new = []
    with open(backup, "r+") as datadoc:
        data_ex = [line.rstrip() for line in datadoc]
        for item in data_ex:
            if item.find(name) > -1 or item == "":
                pass
            elif item in content or item.find("--") > -1:  # transfer as is
                data_new.append(item)
            else:  # transfer with -- to show that it's been deleted from Keep doc
                data_new.append("--" + item)
        for item in content:
            if item not in data_ex:
                data_new.append(item)
        i = len(data_new)
        if i > 0:  # add to the data doc
            datadoc.truncate(0)
            datadoc.write(name + "'s Feed History\n")
            for j in range(i):
                datadoc.write("\n" + data_new[j])

    return content
