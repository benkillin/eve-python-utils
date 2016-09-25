# taxes.py
# this script uses this python library: https://github.com/eve-val/evelink/
# this script calculates ratting taxes for an alliance (or really any set of corps for which the API keys are available in the text file apikeys.txt)
#
# Usage: python taxes.py MonthNumber [DisplayRawData]
#       MonthNumber is the number of the month you want to run taxes against (12 = December, etc...)
#   DisplayRawData is an optional flag to determine if the raw wallet journal entries should be printed out for each corp.
##################################

import evelink.api  # Raw API access
import evelink.char # Wrapped API access for the /char/ API path
import evelink.eve  # Wrapped API access for the /eve/ API path
import datetime
import sys

import requests.packages.urllib3
requests.packages.urllib3.disable_warnings() #disable ssl warning

if len(sys.argv) < 2:
                print "Specify month to run numbers against"
                sys.exit(999)

outputEntries = False

if len(sys.argv) == 3:
        outputEntries = True

month = sys.argv[1]
monthName = datetime.date(1900, int(month), 1).strftime('%B')
fileHandle = open('apikeys.txt', 'r')
totals={}
taxes={}
ratters={}

print "Month number: ", month, " AKA ", monthName

#format of input file:
# keyID vCode taxRate corpTicker Everything after the corp ticker is considered the CEO name
#the input file is delimited by spaces except for the last bit which is the entire CEO name

for line in fileHandle:
                if line.strip() != '':
                                fields = line.split(' ')

                                keyID = fields[0]
                                vCode = fields[1]
                                taxRate = fields[2]
                                ticker = fields[3]
                                CEO = ' '.join(fields[4::]).strip()

                                if outputEntries:
                                        print "Ticker: ", ticker, "CEO: ", CEO

                                entries=[] # current corp wallet journal entries matchin the criteria
                                go = True
                                startID = None
                                minId = sys.maxint
                                corpTotal = 0
                                api = evelink.api.API(api_key=(int(keyID), vCode))
                                corp = evelink.corp.Corp(api)
                                taxes[ticker] = float(taxRate.strip())

                                # while there are still more entries to check, grab the entries, 2560 at a time, and filter them by type ID for bounties and by month into the entries list
                                while go:
                                        journal = corp.wallet_journal(account=1000, limit=2560, before_id=startID)

                                        for row in journal.result:
                                                        # type_id defined here: http://wiki.eve-id.net/APIv2_Eve_RefTypes_XML
                                                        # 85 is bounty prizes
                                                        # 92 is "bounty prize corporation tax" which im not sure how its related to 85
                                                        # 96 PI import tax
                                                        # 97 PI export tax
                                                        if row['type_id'] == 85 and row['party_1']['name'] == 'CONCORD':
                                                        # TODO: rather than grabbing every possible entry in the wallet journal for each corp, save some time by only going back until the specified month is not found at all in the list of results. This would have the disadvantage of being unable to pull metrics for previous months
                                                                        if datetime.datetime.fromtimestamp(int(row['timestamp'])).strftime('%B') == monthName:
                                                                                        entries.append(row)
                                                                                        if row["id"] < minId:
                                                                                                minId = row["id"]
                                        row = None

                                        startId = minId #now that we have the minimum ID use this as the id to specify grabbing all entries previous to it

                                        if len(journal.result) < 2560:
                                                go = False # if there are fewer than the maximum number of rows, this means we don't need to go back any further.
                                                startId = None

                                # at this point we know all the rows in the entries list are for the specified month, so tally up the totals:
                                for entry in entries:
                                        if outputEntries:
                                                print "TransID: ", entry["id"], "Time: ", datetime.datetime.fromtimestamp(int(entry['timestamp'])).strftime('%Y-%m-%d %H:%M:%S'), "Player: ", entry['party_2']['name'], "\tAmmount: ", '{:20,.2f}'.format(int(entry['amount']))
                                        corpTotal += int(entry['amount'])

                                        #let's save per-player stats
                                        if ratters.has_key(ticker):
                                                if ratters[ticker].has_key(entry["party_2"]['name']):
                                                        #print "Adding to existing entry for ", entry["party_2"]['name']
                                                        ratters[ticker][entry["party_2"]['name']] += int(entry['amount'])
                                                else:
                                                        #print "Adding new entry for ", entry["party_2"]['name']
                                                        ratters[ticker][entry["party_2"]['name']] = int(entry['amount'])
                                        else:
                                                #print "Adding new corp ", ticker, " and new entry for ", entry["party_2"]['name']
                                                ratters[ticker] = {}
                                                ratters[ticker][entry["party_2"]['name']] = int(entry['amount'])

                                if outputEntries:
                                        print "\tTotal: ", '{:20,.2f}'.format(corpTotal)
                                totals[ticker] = corpTotal


#print "Totals: ", totals
print "Totals: "

for key in totals:
        print key, ": ", '{:20,.2f}'.format(totals[key]), "; Tax Rate: ", taxes[key], "; Tax Owed:", '{:20,.2f}'.format(totals[key] * taxes[key])


print "Top ratters by corp: "

for corpTag in ratters:
        maxBounties = -1
        maxPlayer = None

        for bountyPlayer in ratters[corpTag]:
                if ratters[corpTag][bountyPlayer] > maxBounties:
                        maxPlayer = bountyPlayer
                        maxBounties = ratters[corpTag][bountyPlayer]

        print corpTag, ": ", maxPlayer, '{:20,.2f}'.format(maxBounties)
