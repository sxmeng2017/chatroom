"""
利用Exception将需要终止的scoket弹出
将核心功能封装在最底层
将要用到的存储数据放入下一层
将要延展的功能放入再下一层
ChatServer对应服务器类。提供服务器的接受连接请求的任务
断开请求在这里用raise来完成，有socket程序中断完成
ChatSession对应会话类，用来管理socket数据的接受
CommandHandler类的核心是完成命令的运转，处理命令
Room类继承CommandHandler类开始给出Room类需要的数据存储。和简单的功能扩展
代表最基本的Room应该具有什么功能
LoginRoom和LogoutRoom两个类用于作为用户进入和退出的中间过程。
这里do_logout已经在Room中完成。所以这里的logoutRoom类是无用的类。
可以修改为
"""




import asynchat, asyncore


class EndSession(Exception):
    pass

class ChatServer(asyncore.dispatcher):

    def __init__(self, port):
        self.create_socket()
        self.set_reuse_addr()
        self.bind(('', port))
        self.listen(5)
        self.users = {}
        self.room = None

    def handle_accept(self):
        conn, addr = self.accept()
        ChatSession(self, conn)

class ChatSession(asynchat.async_chat):

    def __init__(self, server, sock):
        asynchat.async_chat.__init__(self)
        self.server = server
        self.sock = sock
        self.set_terminator(b'\n')
        self.buffer = []
        self.room = None

    def enter(self, room):
        r = self.room
        if r:
            r.remove(self)
        self.room = room
        room.add(self)

    def collect_incoming_data(self, data):
        self.buffer.append(data)

    def found_terminator(self):
        line = ''.join(self.buffer)
        self.buffer = []
        try:
            self.room.handle(self, line.encode('utf-8'))
        except EndSession:
            self.handle_close()


class CommandHandler:

    def unkown(self, session, cmd):
        session.push(('Unknown Command {}\n'.format(cmd)).encode('utf-8'))

    def handle(self, session,line):
        line = line.decode()
        if not line:
            return
        line = line.strip()
        parts = line.split(' ', 1)
        cmd = parts[0]
        try:
            sentence = parts[1].strip()
        except IndexError:
            sentence = ''
        method = getattr(self, 'do_'+cmd, None)
        try:
            method(session, sentence)
        except TypeError:
            self.unkown(session, cmd)


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
        name = line.strip
        if not name:
            session.push(b'UserName Empty')
        elif name not in self.server.users:
            session.push(b'Username not Exist')
        else:
            self.server.main_room.remove(session)


        
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
            session.name = name
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
        Room.remove(self, session)
        self.broadcast((session.name + ' has left the room.\n').encode("utf-8"))

    def do_say(self, session, line):
        self.broadcast((session.name + ': ' + line + '\n').encode("utf-8"))

    def do_look(self, session, line):
        session.push(b'Online Users:\n')
        for other in self.sessions:
            session.push((other.name + '\n').encode("utf-8"))









