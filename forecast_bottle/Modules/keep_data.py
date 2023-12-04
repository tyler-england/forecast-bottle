import gkeepapi
from pathlib import Path


def set_keep_token(creds_path, token):
    # token kept in credentials doc instead of keyring to facilitate cron job
    with open(creds_path, 'r+') as creds_doc:
        creds = [line.rstrip() for line in creds_doc]
    with open(creds_path, 'w+') as creds_doc:
        for i in range(len(creds)):
            if creds[i].find('token') == 0:  # set new token
                new_cred = f'token: {token}'
                creds_doc.write(new_cred + '\n')
            else:  # keep original credentials
                creds_doc.write(creds[i] + '\n')
    return


def get_content(name):
    folder = Path(__file__).parents[2]
    folder = str(folder)

    creds_path = folder + '/credentials.txt'  # change as necessary

    try:
        creds_doc = open(creds_path, 'r')
    except Exception:
        return 'Error: Unable to find/open credentials doc (' + creds_path + ')'

    info = [line.rstrip() for line in creds_doc]

    un = ''
    pw = ''
    for i in range(len(info)):
        if info[i].lower() == 'keep':
            start = info[i + 1].find(':') + 1
            un = info[i + 1][start:].strip()  # get username
            start = info[i + 2].find(':') + 1
            pw = info[i + 2][start:].strip()  # get password
            start = info[i + 3].find(':') + 1
            token = info[i + 3][start:].strip()  # keep token
            break
    if un == '' or pw == '':
        return 'Error: Issue with username and/or password'

    keep = gkeepapi.Keep()

    try:  # token login
        state = None
        keep.resume(un, token, state=state)
    except:  # set new token
        try:
            print('using pw...')
            keep.login(un, pw)
            del pw
            token_new = keep.getMasterToken()
            set_keep_token(creds_path, token_new)
        except:
            return 'Error: Login failed... Check username / password'

    # change as necessary
    note_id = '<Keep note ID>'

    note = keep.get(note_id)
    content = note.text
    content = content.split('\n')  # organize as list
    content = [i.strip() for i in content]

    # back up data in case of Keep clearout
    backup = str(Path(__file__).parents[2]) + '/data_log.txt'  # data backup
    if not Path(backup).exists():
        with open(backup, 'w'):
            pass
    data_new = []
    with open(backup, 'r+') as data_doc:
        data_ex = [line.rstrip() for line in data_doc]
        for item in data_ex:
            if item.find(name) > -1 or item == '':
                pass
            elif item in content or item.find('--') > -1:  # transfer as is
                data_new.append(item)
            else:  # transfer with -- to show that it's been deleted from Keep doc
                data_new.append('--' + item)
        for item in content:
            if item not in data_ex:
                data_new.append(item)
        i = len(data_new)
        if i > 0:  # add to the data doc
            data_doc.truncate(0)
            data_doc.write(f'{name}\'s Feed History\n')
            for j in range(i):
                data_doc.write('\n' + data_new[j])

    return content
