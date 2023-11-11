import string

from flask import *
from threading import Timer
import random

app = Flask(__name__)

UserData = []
ChatHistory = []
all_Rooms = []
UserS = []
UFile = open('UserData.txt', 'a')
HFile = open('History.txt', 'a')

Linker = {}
Security = {}
IdleManager = {}
NameOf = {}


def newTimer(usr):
    if usr in IdleManager.keys():
        IdleManager[usr].cancel()
    t = Timer(7.0, logout, [usr])
    IdleManager[usr] = t
    t.start()


class USER:
    def __init__(self, name, uname, password):
        self.name = name
        self.uname = uname
        self.password = password
        self.Rooms = []
        NameOf[uname] = name

    def authenticate(self, user, password):
        if user == self.uname and password == self.password:
            return True
        return False

    def update(self, **data):
        if 'id' in data:
            self.uname = data['uname']
        if 'name' in data:
            self.name = data['name']
        if 'password' in data:
            self.password = data['password']

    def add_room(self, room, password):
        if room.password != password:
            print(room.password+' '+password)
            return 'Wrong password'

        if room not in self.Rooms:
            self.Rooms.append(room)
            room.add_user(self)
            return 'Room added'

        return 'Error adding room'

    def remove_room(self, room):
        if room in self.Rooms:
            self.Rooms.remove(room)
            room.remove_user(self)
            return 'Room removed'
        return 'Room was not added'

    def get_rooms(self):
        response = ''
        for x in self.Rooms:
            response += x.identifier + '&' + x.name + '&'
        response = response[:-1]
        return response


def find_user(username):
    for x in UserS:
        if x.uname == username:
            return x


class Room:
    def __init__(self, identifier, name, password, username):
        self.identifier = identifier
        self.name = name
        self.password = password
        self.Creator = username
        self.Chats = []
        self.linker = {}
        self.Users = []

    def get_messages(self, user):
        if user not in self.linker.keys():
            self.add_user(user)
        response = ''
        for a, b, c in self.Chats:
            if b > self.linker[user]:
                if c:
                    response += parse_forward(a) + '&&&'
                else:
                    response += a + '&&&'
                self.linker[user] = b
        response = response[:-3]
        return response

    def add_user(self, user):
        self.Users.append(user)
        self.add_message('Server&'+user.uname+'&'+user.name+' Joined the room')
        self.linker[user] = -1

    def remove_user(self, user):
        self.add_message('Server&' + user.uname + '&' + user.name + ' Left the room')
        self.Users.remove(user)

    def get_users(self):
        resp = ''
        for x in self.Users:
            resp += x.name + '&&&' + x.uname + '&&&'
        resp = resp[:-3]
        return resp

    def add_message(self, message, forwarded=False):
        self.Chats.append((message, len(self.Chats), forwarded))

    def reset_user(self, user):
        self.linker[user] = -1

    def get_message_with_index(self, ind):
        for a, b, c in self.Chats:
            if b == ind:
                return a

    def is_forwarded(self, ind):
        for a, b, c in self.Chats:
            if b == ind:
                if c:
                    return a
                else:
                    return False


def duplicate_room(identifier):
    for x in all_Rooms:
        if x.identifier == identifier:
            return True
    return False


def create_room(identifier, name, password, username):
    if duplicate_room(identifier):
        return 'This room id already exists'
    tmp = Room(identifier, name, password, username)
    tmp.add_message('Server&'+username+'&'+NameOf.get(username)+' Created the room')
    all_Rooms.append(tmp)
    return 'Room Created'


def return_all_rooms():
    response = ''
    for r in all_Rooms:
        response += r.identifier+'&'+r.name+'&'
    response = response[:-1]
    return response


def get_room(identifier):
    for x in all_Rooms:
        if x.identifier == identifier:
            return x


def get_source_message(identifier, ind):
    x = get_room(identifier).is_forwarded(int(ind))
    if not x:
        return get_room(identifier).get_message_with_index(int(ind))
    else:
        return get_source_message(x.split('&')[0], x.split('&')[1])


def parse_forward(raw):
    data = raw.split('&')
    resp = 'Forward&'
    resp += get_source_message(data[0], data[1])+'&'+data[0]+'&'+data[1]+'&'+data[2]+'&'+data[3]
    return resp


def cache():
    tmp = open('UserData.txt', 'r')
    for x in tmp:
        spl = x.replace('\n', '').split(' ')
        tmp = USER(spl[0], spl[1], spl[2])
        UserData.append(tmp)


cache()


@app.route('/')
def hello_world():
    return redirect('/Starter')


@app.route('/Starter', methods=["GET", "POST"])
def starter():
    if request.method == "POST":
        username = request.form['Username']
        if request.form.__contains__('PasswordConfirm'):
            if user_exists(username):
                return 'ERROR DUPLICATIVE'
            else:
                register(request.form['Name'], username, request.form["Password"])
                return 'OK'
        else:
            if UserS.__contains__(find_user(username)):
                return 'User is already logged in!'
            if logger(username, request.form['Password']):
                return 'OK' + Security[request.form['Username']]
            else:
                return 'Wrong username or password'
    else:
        return render_template("login.html")


@app.route('/Management', methods=['GET', 'POST'])
def management():
    if request.method == "POST":
        purpose = request.form['Purpose']
        username = request.form['Username']

        if username not in Security.values():
            return ''

        username = translate_security(username)
        if purpose == 'Create':
            return create_room(request.form['Identifier'], request.form['Name'], request.form['Password'], username)

        if purpose == 'RawData':
            return return_all_rooms()

        if purpose == 'Add':
            return find_user(username).add_room(get_room(request.form['ID']), request.form['Password'])

        if purpose == 'Remove':
            return find_user(username).remove_room(get_room(request.form['ID']))

        if purpose == 'UserData':
            return find_user(username).get_rooms()

        if purpose == 'RoomInfo':
            room = get_room(request.form['ID'])
            return str(len(room.Chats))+'&&&'+room.get_users()

    return render_template('Room_Management.html')


@app.route('/ChatRoom', methods=['GET', 'POST'])
def manager():
    if request.method == "POST":
        username = request.form['Username']
        purpose = request.form['Purpose']
        if username not in Security.values():
            return ''
        else:
            username = translate_security(username)
        if purpose == 'Update':
            return sendUpdate(username)

        if purpose == 'Send':
            get_room(request.form['Target']).add_message("Message&"+NameOf.get(username)+'&'+username+'&'+request.form['Message']+'&'+request.form['Reply'])
            return 'DONE'

        if purpose == 'Rooms':
            return find_user(username).get_rooms()

        if purpose == 'Forward':
            get_room(request.form['Target']).add_message(request.form['ID']+'&'+request.form['NUM']+'&'+username+'&'+NameOf.get(username), True)

        if purpose == 'LOGOUT':
            logout(username)

    return render_template('Room.html')


@app.route('/RoomInfo/<identifier>', methods=['POST', 'GET'])
def room_giver(identifier):
    if request.method == 'POST':
        resp = ''
        room = get_room(identifier)
        for x in room.Users:
            resp += x.uname + '&' + x.name + '&'
        resp = resp[:-1]
        return resp


@app.route("/Profile/<username>", methods=['POST', 'GET'])
def prof_giver(username):
    if request.method == 'POST':
        for x in UserData:
            if x.uname == username:
                return "Username = "+x.uname+"&Name = "+x.name
    return render_template('Prof.html')


@app.route('/SYNC', methods=['POST', 'GET'])
def func():
    if request.method == 'POST':
        username = request.form['Username']

        if username not in Security.values():
            return 'ERROR401'

        newTimer(translate_security(request.form['Username']))
        return 'DONE'

    return 'this page is not meant to be accessed'


def user_exists(user):
    for x in UserData:
        if x.uname == user:
            return True
    return False


def translate_security(enc):
    return list(Security.keys())[list(Security.values()).index(enc)]


def register(name, user, password):
    UserData.append(USER(name, user, password))
    UFile.write(name+' '+user+' '+password+'\n')
    UFile.flush()


def logger(username, password):
    for x in UserData:
        if x.uname == username and x.password == password:
            UserS.append(x)
            Security[username] = ''.join(random.SystemRandom().choice(string.digits + string.ascii_letters) for _ in range(14))
            newTimer(username)
            for y in find_user(username).Rooms:
                y.add_message('Server&'+username+'&'+NameOf.get(username)+' is now Online')
            return True
    return False


def sendUpdate(usr):
    usr = find_user(usr)
    resp = ''
    for x in usr.Rooms:
        resp += x.identifier+'&&&&&'+x.get_messages(usr)+'&&&&&'
    resp = resp[:-5]
    return resp


def user_reset(user):
    for room in user.Rooms:
        room.reset_user(user)


def logout(username):
    for x in find_user(username).Rooms:
        x.add_message('Server&'+username+'&'+NameOf.get(username)+' is now Offline')
    user_reset(find_user(username))
    UserS.remove(find_user(username))
    Security.pop(username)
    return redirect('tst.html', 200)


if __name__ == '__main__':
    app.run(host="0.0.0.0")
