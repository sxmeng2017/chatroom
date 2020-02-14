import asyncore
import asynchat

class EndSession(Exception):
    pass

class ChatServer(asyncore.dispatcher):

    def __init__(self, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket()
        self.set_reuse_addr()
        self.bind('', port)
        self.listen(5)
        self.users = {}

    def handle_accept(self):
        conn, addr = self.accept()
        ChatSession(self, conn)


class ChatSession(asynchat.async_chat):

    def __init__(self, server, socket):
        asynchat.async_chat.__init__(self, socket)
        self.server = server
        self.data = []
        self.set_terminator(b'\n')
        self.name = None
        self.enter(LoginRoom(server))

    def enter(self, room):
        try:
            cur = self.room
        except AttributeError:
            pass
        else:
            cur.remove(self)
        self.room = room
        room.add(self)

    def collect_incoming_data(self, data):
        self.data.append(data)

    def found_terminator(self):
        line = ''.join(self.data)
        self.data = []
        try:
            self.room.handle(self, line.encode('utf-8'))
        except EndSession:
            self.handle_close()

    def handle_close(self):
        asynchat.async_chat.handle_close(self)
        self.enter(LoginoutRoom(self.server))

class CommandHandler:

    def unknown(self, session, cmd):
        session.push(('Unknown command {} \n'.format(cmd))
                     .encode("utf-8"))

    def handle(self, session, line):
        line = line.decode()
        if not line.strip():
            return
        parts = line.split(' ', 1)
        cmd = parts[0]
        try:
            line = parts[1].strip()
        except IndexError:
            line = ''
        method = getattr(self, 'do_' + cmd)
        try:
            method(session, line)
        except TypeError:
            self.unknown(session, cmd)

class Room(CommandHandler):
    def __init__(self, server):
        self.server = server
        self.sessions = []

    def add(self, session):
        self.sessions.append(session)

    def remove(self, session):
        self.sessions.remove(session)

    def broadcast(self, line):
        for session in self.sessions:
            session.push(line)

    def do_logout(self, session, line):
        raise EndSession

class LoginRoom(Room):
    def add(self, session):
        Room.add(self, session)
        session.push(b'Connect Sucess')

    def do_login(self, session, line):
        name = line.strip
        if not name:
            session.push(b'UserName Empty')
        elif name in self.server.users:
            session.push(b'UserName Exist')
        else:
            session.name  = name
            session.enter(self.server.main_room)

class LogoutRoom(Room):
    def add(self, session):
        try:
            del self.server.users[session.name]
        except KeyError:
            pass

class ChatRoom(Room):
    def add(self, session):
        # 广播新用户进入
        session.push(b'Login Success')
        self.broadcast((session.name + ' has entered the room.\n').encode("utf-8"))
        self.server.users[session.name] = session
        Room.add(self, session)

    def remove(self, session):
        # 广播用户离开
        Room.remove(self, session)
        self.broadcast((session.name + ' has left the room.\n').encode("utf-8"))

    def do_say(self, session, line):
        # 客户端发送消息
        self.broadcast((session.name + ': ' + line + '\n').encode("utf-8"))

    def do_look(self, session, line):
        # 查看在线用户
        session.push(b'Online Users:\n')
        for other in self.sessions:
            session.push((other.name + '\n').encode("utf-8"))


if __name__ == '__main__':

    s = ChatServer(PORT)
    try:
        print("chat server run at '0.0.0.0:{0}'".format(PORT))
        asyncore.loop()
    except KeyboardInterrupt:
        print("chat server exit")


