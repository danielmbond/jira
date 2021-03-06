#! python3

# takt-tickets.py is used to look for new Jira tickets or updated comments and notify
# via Slack.

import jira, shelve, requests

NOTIFICATIONS = {
    'slack':True,
    'email':False
    }

notifyMsg = ''

# Create file to save settings
settings = shelve.open(".settings")

# Add setting to shelve if missing.
def getConfig( x, prompt, new=None ):   
    try:
        thesettings = settings[x]
        if new != None:
            settings[x] = new
    except Exception:
        if new == None:
            settings[x] = input(prompt)
        else:
            settings[x] = new
        thesettings = settings[x]
    return thesettings

def addTrailingSlash(url):
    url = url.strip()
    if url[-1] != '/':
        url += '/'
    return(url)

# Save URL, credentials, and project name.
def setSettings():
    getConfig('jiraURL', 'Enter Jira project URL: ')
    getConfig('username', 'Enter Email Address: ')
    getConfig('password', 'Enter Password: ')
    getConfig('project', 'Enter Project Name: ')
    if NOTIFICATIONS['slack'] == True:
        getConfig('slack', 'Enter Slack Webhook URL: ')

# Login to Jira
def login():
    global jira
    options = {
        'server': settings['jiraURL']}
    try:
       jira = jira.JIRA(options, basic_auth=(settings['username'], settings['password']))
    # Test for bad credentials.
    except Exception as e:
        if 'Unauthorized (401)' in e.text:
            print('Bad username or password; clearing cache.')
            settings.clear()
            setSettings()
            login()

setSettings()
login()

# Pull issues and look for any new ones / changes
issues = jira.search_issues('project=' + settings['project'])
issueCount = getConfig('issueCount', '', len(issues))
if issueCount != settings['issueCount']:
    notifyMsg += str(int(issueCount - int(settings['issueCount']))) + ' new issues.\n'
for issue in issues:
    loopMsg = ''
    newComments = ''
    exists = True
    issueLink = '<' + addTrailingSlash(settings['jiraURL']) + 'browse/' + str(issue) + '|' + str(issue) +  '>'
    issueData = {'assignee':str(issue.fields.assignee), 'commentcount':len(jira.comments(issue)), 'status':str(issue.fields.status)}
    if str(issue) not in notifyMsg:
        try:
            oldData = settings[str(issue)]
            if oldData['assignee'] != issueData['assignee']:
                loopMsg += ' has been assigned to ' + issueData['assignee']
            if oldData['commentcount'] != issueData['commentcount']:
                newCommentCount = int(issueData['commentcount']) - int(oldData['commentcount'])
                loopMsg += ' has ' + str(newCommentCount) + ' new comments'
                try:
                    for i in range(0,newCommentCount):
                        newComments += "Comment: " + jira.comment(issue,jira.comments(issue)[-(newCommentCount-i)]).body + "\n"
                except:
                    continue
            if oldData['status'] != issueData['status']:
                loopMsg += ' and status has changed to ' + issueData['status']
            if len(loopMsg) > 0:
                loopMsg = issueLink + loopMsg + "\n" + newComments
        except KeyError:
            loopMsg += 'New issue: ' + issueLink + ' '  + issueData['status'] + ' ' + issueData['assignee'] + ' ' + issue.fields.summary + '\n'
        notifyMsg += loopMsg
        #print(str(issue), issue.fields.assignee,len(jira.comments(issue)), issue.fields.status)
    getConfig(str(issue), '', issueData)

# Notify on changes
if notifyMsg != '':
    data = {'text':notifyMsg}
    try:
        print(data)
    except Exception as e:
        print(e)
    if NOTIFICATIONS['slack'] != False:
        # https://api.slack.com/apps
        requests.post(getConfig('slack', 'Enter Slack Webhook URL: '), json=data)
        print(settings['slack'])

# TODO: Add email notifications
settings.close()
