#Libraries
import logging
from logging.handlers import RotatingFileHandler
import paramiko
import socket
import threading

#constants
logging_format = logging.Formatter('%(message)s')
SSH_BANNER = 'SSH-2.0-MySSHServer_1.0'

host_key = paramiko.RSAKey(filename='server.key')

#logger
funnel_logger = logging.getLogger('FunnelLogger')
funnel_logger.setLevel(logging.INFO)

funnel_handler = RotatingFileHandler('audits.log', maxBytes=2000, backupCount=5)
funnel_handler.setFormatter(logging_format)

funnel_logger.addHandler(funnel_handler)


creds_logger = logging.getLogger('CredsLogger')
creds_logger.setLevel(logging.INFO)

creds_handler = RotatingFileHandler('cmd_audits.log', maxBytes=2000, backupCount=5)
creds_handler.setFormatter(logging_format)

creds_logger.addHandler(creds_handler)

#emulated shell

def emulated_shell(channel, client_ip):
    channel.send(b'corporate-jumpbox2$')
    command = b""
    while True:
        char = channel.recv(1)
        channel.send(char)
        if not char:
            channel.close()

        command += char

        if char == b'\r':
            if command.strip() == b'exit':
                response = b'\n Goodbye\n'
                channel.close()
            elif command.strip() == b'pwd':
                response = b'\n' + b'\\usr\\local' + b'\r\n'
                creds_logger.info(f'Command: {command.strip()} executed by {client_ip}')
            elif command.strip() == b'whoami':
                response = b'\n' + b"copruser1" + b'\r\n'
                creds_logger.info(f'Command: {command.strip()} executed by {client_ip}')
            elif command.strip() == b'ls':
                response = b'\n' +b'jumpbox.conf' + b'\r\n'
                creds_logger.info(f'Command: {command.strip()} executed by {client_ip}')
            elif command.strip() == b'cat jumpbox.conf':
                response = b'\n' + b'nothing to see here' + b'\r\n'
                creds_logger.info(f'Command: {command.strip()} executed by {client_ip}')
            else:
                response = b'\n' + bytes(command.strip()) + b'\r\n'
                creds_logger.info(f'Command: {command.strip()} executed by {client_ip}')


            channel.send(response)
            channel.send(b'corporate-junkbox2$ ')
            command = b""

### SSH Server + Sockets
class Server(paramiko.ServerInterface):
    def __init__(self, client_ip, input_username = None, input_pw = None):
        self.event = threading.Event()
        self.client_ip = client_ip
        self.input_username = input_username
        self.input_pw = input_pw

    def check_channel_request(self, kind:str, chanid:int) -> int:
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
    
    def get_allowed_auths(self):
        return "password"

    def check_auth_password(self, username, password):
        funnel_logger.info(f'Client : {self.client_ip} attemped connection with ' + f'username : {username}' + f'password: {password}')
        creds_logger.info(f'{self.client_ip}, {username}, {password}')
        if self.input_username is not None and self.input_pw is not None:
            if username == self.input_username and password == self.input_pw:
                return paramiko.AUTH_SUCCESSFUL
            else:
                return paramiko.AUTH_FAILED
        else:
            return paramiko.AUTH_SUCCESSFUL
    
    def check_channel_shell_request(self, channel):
        self.event.set()
        return True
    
    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True
    
    def check_channel_exec_request(self, channel, command):
        command = str(command)
        return True

def client_handle(client, addr, username, pw):
    client_ip = addr[0]
    print(f"{client_ip} connected")

    try:
        transport = paramiko.Transport(client)
        transport.local_version = SSH_BANNER
        server = Server(client_ip=client_ip, input_username=username, input_pw=pw)
        
        transport.add_server_key(host_key)

        transport.start_server(server=server)

        channel = transport.accept(100)

        if channel is None:
            print("No channel opened")

        standard_banner = "Welcome To Ubuntu 22.04 LTS!\r\n\r\n"


    except Exception as error:
        print(error)
        print("sum ting wong")
    finally:
        try:
            transport.close()
        except Exception as error:
            print(error)
            print("sum ting wong trying to close")
        client.close()
    
### Provision honeypot
def honeypot(addr, port, username, pw):
    socks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socks.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socks.bind((addr, port))

    socks.listen(100)
    print(f"SSH server listening on port {port}")

    while True:
        try:
            client, address = socks.accept()
            ssh_honeypot_thread = threading.Thread(target=client_handle, args=(client, address, username, pw))
            ssh_honeypot_thread.start()
        except Exception as error:
            print(error)

honeypot('127.0.0.1', 4444, None, None)