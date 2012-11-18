import re
import reddit
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

# defines the source and network subreddits
CHECK_SUBREDDIT = 'pornoverlords'
SUBMISSION_BACKLOG_LIMIT = timedelta(days=1)

stop_time = datetime.utcnow() - SUBMISSION_BACKLOG_LIMIT

# login info for the script to log in as, this user must be a mod in the main subreddit
REDDIT_USERNAME = cfg_file.get('reddit', 'username')
REDDIT_PASSWORD = cfg_file.get('reddit', 'password')
REDDIT_UA = cfg_file.get('reddit', 'user_agent')
# id (reddit content_id sans "t3_" identifier part, from PRAW subreddit.id)
LAST_CHECKED_ID = cfg_file.get('subreddit', 'last_checked_id')


# log into reddit
print "Logging in as /u/"+REDDIT_USERNAME+"..."
r = reddit.Reddit(user_agent=REDDIT_UA)
r.login(REDDIT_USERNAME, REDDIT_PASSWORD)
print "  Success!"


# get the contributors
print "Getting/compiling approved submitters for /r/"+CHECK_SUBREDDIT+"..."
subreddit = r.get_subreddit(CHECK_SUBREDDIT)
contributors = subreddit.get_contributors()
moderators = subreddit.get_moderators()
approved_submitters = set()
for user in contributors:
    # print "  - "+str(user.name)
    approved_submitters.add(str(user.name))
for user in moderators:
    if str(user.name) not in approved_submitters:
        approved_submitters.add(str(user.name))
print "  Success!"


def get_permalink(item):
    """Returns the permalink for the item."""
    if isinstance(item, reddit.objects.Submission):
        return item.permalink
    elif isinstance(item, reddit.objects.Comment):
        return ('http://www.reddit.com/r/'+
                item.subreddit.display_name+
                '/comments/'+item.link_id.split('_')[1]+
                '/a/'+item.id)


# get submissions, filter by date
# place_holder=LAST_CHECKED_ID,
submissions = subreddit.get_new_by_date(place_holder=LAST_CHECKED_ID, limit=1000)

first = True
sent_count = 0

print "Checking submissions"
for submission in submissions:    
    
    if submission.id == LAST_CHECKED_ID:
        # nothing new since last time
        print "submission.id == LAST_CHECKED_ID"
        print "  "+str(submission.title)
        print "  by "+str(submission.author)
        break

    # check if we've run out of recent submissions
    submission_time = datetime.utcfromtimestamp(submission.created_utc)                
    if submission_time <= stop_time:
        print "submission_time <= stop_time"
        print "  "+str(submission.title)
        print "  by "+str(submission.author)
        break

    # update config file with most recent checked ID so we don't check stuff twice
    # hack because "submissions" is a generator object
    if first == True:
        first_checked_id = submission.id
        print "Set 'first_checked_id' = "+str(submission.id)
#        cfg_file.set('subreddit', 'last_checked_id', submission.id)
#        cfg_file.write(open(path_to_cfg, 'w'))
        first = False
#        print "Wrote 'last_checked_id' to config file"


    # if submission author is approved submitter
    if submission.author in moderators or submission.author in contributors:
        # print "Approved Author"+str(submission.author)
        # check title for special thread names
        if re.search('^\[?(brainstorming|official\s+vote)\s+(thread)?\]?.+', submission.title.lower(), re.IGNORECASE|re.DOTALL|re.UNICODE):
            print "Matched Title: "+str(submission.title)
            print " by "+str(submission.author)
            
            subject = "New Thread in /r/PornOverlords Needs Your Attention"
            message = "There is a new thread in /r/PornOverlords that could use your input: [\""+submission.title+"\" by "+str(submission.author)+"]("+get_permalink(submission)+").\n\nPlease do not respond to this message, I am a bot and nobody reads my inbox."
            print "Send Notification PMs"
            for user in approved_submitters:
                r.compose_message(user, subject, message)
                # print "  "+str(user)
                sent_count = sent_count + 1
            print "  Success!"
    

# Update 'last_checked_id' here, so it doesn't mess anything up
try:
  cfg_file.set('subreddit', 'last_checked_id', first_checked_id)
  cfg_file.write(open(path_to_cfg, 'w'))
  print "Wrote 'last_checked_id' to config file"
except:
  print "'last_checked_id' no change so not updated"

if sent_count == 0:
    print "No announcements sent for the past "+str(SUBMISSION_BACKLOG_LIMIT)
else:
    print "Sent "+str(sent_count)+" PMs."

print "Done!"