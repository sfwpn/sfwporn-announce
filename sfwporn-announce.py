import re
import praw
import HTMLParser
from ConfigParser import SafeConfigParser
import sys, os
from datetime import datetime, timedelta
import itertools

# set up the config parser
cfg_file = SafeConfigParser()
path_to_cfg = os.path.abspath(os.path.dirname(sys.argv[0]))
path_to_cfg = os.path.join(path_to_cfg, 'sfwporn-announce.cfg')
cfg_file.read(path_to_cfg)

# defines the source subreddit
CHECK_SUBREDDIT = 'pornoverlords'
SUBMISSION_BACKLOG_LIMIT = timedelta(days=1)

stop_time = datetime.utcnow() - SUBMISSION_BACKLOG_LIMIT

# login info for the script to log in as, this user must be a mod in the main subreddit
REDDIT_USERNAME = cfg_file.get('reddit', 'username')
REDDIT_PASSWORD = cfg_file.get('reddit', 'password')
REDDIT_UA = cfg_file.get('reddit', 'user_agent')
# id (reddit content_id sans "t3_" identifier part, from PRAW subreddit.id)
LAST_CHECKED_ID = cfg_file.get('subreddit', 'last_checked_id')
LAST_CHECKED_TIME = cfg_file.get('subreddit', 'last_checked_time')


DEBUG = False

def logmsg(message):
    if DEBUG == True:
        print message

def get_permalink(item):
    """Returns the permalink for the item."""
    if isinstance(item, praw.objects.Submission):
        return item.permalink
    elif isinstance(item, praw.objects.Comment):
        return ('http://www.reddit.com/r/'+
                item.subreddit.display_name+
                '/comments/'+item.link_id.split('_')[1]+
                '/a/'+item.id)



# log into reddit
logmsg("Logging in as /u/"+REDDIT_USERNAME+"...")
r = praw.Reddit(user_agent=REDDIT_UA)
r.login(REDDIT_USERNAME, REDDIT_PASSWORD)
logmsg("  Success!")


# get the contributors
logmsg("Getting/compiling approved submitters for /r/"+CHECK_SUBREDDIT+"...")
subreddit = r.get_subreddit(CHECK_SUBREDDIT)
contributors = subreddit.get_contributors()
moderators = subreddit.get_moderators()
approved_submitters = set()
for user in contributors:
    # logmsg("  - "+str(user.name))
    approved_submitters.add(str(user.name))
for user in moderators:
    if str(user.name) not in approved_submitters:
        approved_submitters.add(str(user.name))
logmsg("  Success!")


# get submissions, filter by date
# place_holder=LAST_CHECKED_ID,
submissions = subreddit.get_new(place_holder=LAST_CHECKED_ID, limit=1000)

first = True
sent_count = 0

logmsg("Checking submissions...")
for submission in submissions:    

    # update config file with most recent checked ID and timestamp so we don't check stuff twice
    if first == True:
        first_checked_id = submission.id
        first_checked_time = submission.created_utc
        logmsg("Set 'first_checked_id' = "+str(submission.id))
        logmsg("Set 'first_checked_time' = "+str(submission.created_utc))

        first = False
    
    
    if submission.id == LAST_CHECKED_ID:
        # nothing new since last time
        logmsg("submission.id == LAST_CHECKED_ID")
        break
    if datetime.utcfromtimestamp(float(submission.created_utc)) <= datetime.utcfromtimestamp(float(LAST_CHECKED_TIME)):
        # someone deleted the submission we were referencing
        logmsg("submission.created_utc == LAST_CHECKED_TIME")
        break

    # check if we've run out of recent submissions
    submission_time = datetime.utcfromtimestamp(submission.created_utc)                
    if submission_time <= stop_time:
        logmsg("submission_time <= stop_time")
        logmsg("  "+str(submission.title))
        logmsg("  by "+str(submission.author))
        break


    # if submission author is approved submitter
    if submission.author in moderators or submission.author in contributors:
        logmsg("Approved Author "+str(submission.author))
        # check title for special thread names
        # if re.search('^\[?(brainstorming|(official\s+(vote|announcement)))(\s+thread)?\]?.+', submission.title.lower(), re.IGNORECASE|re.DOTALL|re.UNICODE):
        if re.search('^\[?((official)?\s+(brainstorming|proposal|induction|vote|results|announcement)(\s+thread)?\s*?\]?.+', submission.title.lower(), re.IGNORECASE|re.DOTALL|re.UNICODE):
            logmsg("Matched Title: "+str(submission.title))
            logmsg(" by "+str(submission.author))
            
            subject = "New Thread in /r/PornOverlords Needs Your Attention"
            message = "There is a new thread in /r/PornOverlords that could use your input: [\""+submission.title+"\" by "+str(submission.author)+"]("+get_permalink(submission)+").\n\nPlease do not respond to this message, I am a bot and nobody reads my inbox."
            
            logmsg("Sending Notification PMs...")
            
            for user in approved_submitters:

                # if user == 'dakta':
                #     r.send_message(user, subject, message)
                
                r.send_message(user, subject, message)
                
                # logmsg("  "+str(user))
                sent_count = sent_count + 1
                
            logmsg("  Success!")
            
    print(submission.title+" by "+submission.author.name)
    
# Update 'last_checked_id' here, so it doesn't mess anything up
# try:
cfg_file.set('subreddit', 'last_checked_id', first_checked_id)
cfg_file.set('subreddit', 'last_checked_time', str(first_checked_time))
cfg_file.write(open(path_to_cfg, 'w'))
logmsg("Wrote 'last_checked_id', 'last_checked_time' to config file")
# except:
#     logmsg("Something went wrong updating the config file for 'last_checked_id' or 'last_checked_time'")

if sent_count == 0:
    logmsg("No announcements sent for the past "+str(SUBMISSION_BACKLOG_LIMIT))
else:
    logmsg("Sent "+str(sent_count)+" PMs.")

print("Last run: "+str(datetime.utcnow())+" sent "+str(sent_count)+" PM(s).")
logmsg("Done!")
