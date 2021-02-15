# forecast-bottle

This program accesses a Google Keep note where baby feed information is tracked. It uses the data to predict the next feed (both the time and the quantity of milk/formula) so that a bottle can be ready prior to the baby starting to cry.

Once the time and quantity of the next feed are estimated, the results are emailed to all email addresses in the recipients.txt file. In addition to the estimated time and quantity of the next feed, the emails also contain some summary data (feeding frequency, average feed quantity, etc). This can be helpful to reference when answering pediatrician questions.

-----

#USE:
Log baby's feeds in a Google Keep note using the proper format. Bottle feeds to be measured in milliliters and breast feeds to be measured in minutes. For each feed, either the mL value or the BF value can be omitted. However, the bottle feed value must precede the breastfeed value if both are present.
Example inputs:
Jan 1 - 3:00 pm, 30 mL + 15 min BF
Jan 1 - 3:00 pm, 30 mL
Jan 1 - 3:00 pm, 15 min BF
The first is an example where a direct breastfeed immediately follows a bottle feed (to supplement the bottle feed).

The program can be run manually, but scheduling it to run frequently will ensure consistent updates.

-----

#REQUIREMENTS:
gkeepapi, pandas
Note -- gkeepapi is unofficial, and is not supported by Google. https://github.com/kiwiz/gkeepapi

-----

#STARTUP:
age_info.txt -- Enter the baby's birthday in the designated format on the first line. The age milestone values on all following lines can be adjusted if desired.
credentials.txt -- The Gmail credentials are used to access the Google account which will send the emails. The Keep credentials are used to access the note with logged feed data. These do not need to be the same Google account. If you haven't already done so, you will also need to enable the Gmail API.  https://developers.google.com/gmail/api/quickstart/python (this will involve putting a Gmail token json file in the project directory as well)
recipients.txt -- These are the email addresses of everyone who will receive updates when the next feed time has been estimated.

Some script values are hard-coded because I created this project for my own use. They should be changed before running the program.
email_forecast.py, lines 38/39: Change baby's name and the sender name for all outgoing emails.
keep_data.py, line 33: Change note_id to match the ID of the Google Keep note containing the logged feed data.
