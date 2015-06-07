'''
Created on May 20, 2015

@author: jmessmer
'''
import challonge
import socket
import threading
import time
import datetime
import Tkinter
import json
from httplib import HTTPException
from firebase import firebase
import urllib

#URL = None

#players = []
#player_dict = {}
#player_dict_reversed = {}

#match_id_dir = {}
#match_list = []
#match_str = None

#setup_list = {}

class ThreadedServer(object):
    
    def __init__(self,log, num_setups, url, interval=1):
        """ Constructor

        :type interval: int
        :param interval: Check interval, in seconds
        """
        self.interval = interval
        self.log = log
        self.num_setups = num_setups
        #self.setups = {}
        self.url = url
        #output(self.log, "message2")
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    
    def run(self):
        setups = {}
        for x in xrange(0, self.num_setups):
            setups["Setup " + str(x + 1)] = "Open"
        try:
            player_dict, player_dict_reversed, match_list, match_id_dir, match_str, setup_list = getMatchInfo(refreshMatchInfo(self.url), self.url, setups)
            print "Setups: " + str(setup_list)
            print "Matches: " + match_str
        except HTTPException:
            output(self.log, "Error in authentication")
        
        
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind(('', 1215))
        serversocket.listen(5)
        
        output(self.log, "Server is active, listening on port 1215")
        
        #showSetups(setups)    
        
        
        while 1:
            (clientsocket, addr) = serversocket.accept()
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
            #output(self.log, "(" + str(st) + ") - Connection from " + str(addr))
            #print "Connection from " + str(addr)
            ct = threading.Thread(target=client_thread, args=[clientsocket, self.log, self.url, setup_list])
            ct.start()
        
        clientsocket.close()
        serversocket.close()

def client_thread(client, gui_log, url, setups):
    msg = str(client.recv(1024))
    command = msg[:4]
    print "hello"
    player_dict, player_dict_reversed, match_list, match_id_dir, match_str, _ = getMatchInfo(refreshMatchInfo(url), url, setups)
    #output(gui_log, str(setup_list))
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
    #output(gui_log, "(" + str(st) + ") - Command: " + str(command))
    if(command == 'list'):
        #print match_id_dir
        if match_str == "":
            client.send("Tournament finished")
        else:
            client.send(match_str)
    elif command == 'rept':
        #print match_id_dir
        data = msg[4:]
        dataArr = data.split(",")
        
        p1 = dataArr[0]
        p2 = dataArr[1]
        score = dataArr[2]
        winner = dataArr[3]
        for setup in setups:
            if setups[setup] == str(p1 + "-" + p2):
                setups[setup] = "Open"
        #print match_id_dir
        match_id = match_id_dir[str(player_dict_reversed[p1])+","+str(player_dict_reversed[p2])]
        output(gui_log, "(" + str(st) + ") - Match Report: " + p1 + " vs " + p2 + ": " + str(score))
        challonge.matches.update(url, match_id, scores_csv=str(score), winner_id=player_dict_reversed[winner])
    client.close()
    #output(gui_log, "Connection closed")

def refreshMatchInfo(url_str):
    return challonge.matches.index(url_str)
    
def getMatchInfo(matchesVar, url, setups):
    playerList = []
    playerDict = {}
    playerDictRev = {}
    
    temp = []
    matchList = []
    matchIDDir = {}
    matchStr = ""
    print "URL:  " + url
    for match in matchesVar:
        if(match['state'] == "open"):
            competitors = str(match["player1-id"]) + "," + str(match["player2-id"])
            temp.append(competitors)
            matchIDDir[str(match["player1-id"]) + "," + str(match["player2-id"])] = match['id']
            playerList.append(match["player1-id"])
            playerList.append(match["player2-id"])
    for player in playerList:
        playerinfo = challonge.participants.show(url, player)
        playerDict[player] = playerinfo['display-name']
        playerDictRev[playerinfo['display-name']] = player
    print "Temp: " + str(temp)
    for match in temp:
        names = match.split(',')
        namematch = ""
        for name in names:
            realname = playerDict[int(name)]
            namematch = namematch + str(realname) +"-"
        namematch = namematch[:-1]
        setup = findSetup(namematch, setups)
        if(setup != None):
            setups[setup] = namematch
            matchList.append(namematch + ":" + setup)
    for match in matchList:
        matchStr = matchStr + match + ","    
    matchStr = matchStr[:-1]  
    print setups
    return playerDict, playerDictRev, matchList, matchIDDir, matchStr, setups

def findSetup(match, setups):
    for setup in setups:
        if(setups[setup] == match):
            return setup
    for setup in setups:
        if setups[setup] == "Open":
            return setup
    return None

def output(textField, message):
    textField.configure(state=Tkinter.NORMAL)
    textField.insert(Tkinter.INSERT, message + "\n")
    textField.configure(state=Tkinter.DISABLED)
    
def showSetups(setups):
        window = Tkinter.Tk()
        i = 0
        for setup in setups:
            setup_label = Tkinter.Label(window, text=setup + ": " + setups[setup]).grid(row=i, padx=10, pady=10)
            i += 1
            window.update_idletasks()
        window.mainloop()

def server(name_field, api_field, url_field, setups_field, logbox):
    #output(logbox, name_field)
    #print firebase.get("/message", None)
    
    ip = str(get_ip())
    firebase.put("https://crackling-torch-3374.firebaseio.com", "/tournaments/"+url_field, ip)
    URL = url_field
    print "URL: " + URL
    logbox.see(Tkinter.END)
    challonge.set_credentials(name_field, api_field)
    server = ThreadedServer(logbox, int(setups_field), url_field)
    
def get_ip():
    #req = urllib2.Request('http://www.whatismyip.org')
    data = json.loads(urllib.urlopen("http://api.hostip.info/get_json.php").read())
    return data['ip']

if __name__ == '__main__':    
    firebase = firebase.FirebaseApplication("https://crackling-torch-3374.firebaseio.com/", None)

    top = Tkinter.Tk()
    
    challonge_name_label = Tkinter.Label(top, text="What is your Challonge username?").grid(row=0, column=0, padx=10, pady=10)
    challonge_api_label = Tkinter.Label(top, text="What is your Challonge API key").grid(row=1, column=0, padx=10, pady=10)
    challonge_tournament_url_label = Tkinter.Label(top, text="What is your Challonge URL").grid(row=2, column=0, padx=10, pady=10)
    setups_label = Tkinter.Label(top, text="How many setups are there in total").grid(row=3, column=0, padx=10, pady=10)
    
    name_entry = Tkinter.Entry(top)
    name_entry.grid(row=0, column=1)
    api_entry = Tkinter.Entry(top)
    api_entry.grid(row=1, column=1)
    url_entry = Tkinter.Entry(top)
    url_entry.grid(row=2, column=1)
    setups_entry = Tkinter.Entry(top)
    setups_entry.grid(row=3, column=1)
    
    log = Tkinter.Text(top, relief=Tkinter.GROOVE, borderwidth=2, state=Tkinter.DISABLED)
    log.grid(row=4, columnspan=2, padx=10, pady=10)
    
    start_button = Tkinter.Button(top, text="Start", command= lambda: server(name_entry.get(), api_entry.get(),url_entry.get(), setups_entry.get(), log)).grid(row=5, columnspan=2, pady=10)
    
    top.mainloop()