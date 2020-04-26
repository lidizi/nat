#!/usr/bin/python3
import socket
import select
import threading
import json
import time
from concurrent.futures import ThreadPoolExecutor

worker_pool = ThreadPoolExecutor(20)
#服务注册
register_servers = {}

#nat配置
nat_config = {}
#sock_connect_queue = queue.Queue(10)

evn="product"
# 远程内网注册端口
nat_port = 6783
#客户端请求端口
server_port = 8080
nat_sock_connects = {}

class Server:
    def __init__(self,config):
        self.name = config['server_name']
        self.src_port = config['src_port']
        self.dst_port = config['dst_port']
        self.timeout = config['timeout'] if config['timeout'] else 10
        self.init_server_sock()

    def init_server_sock(self):
        self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.server.bind(('',self.dst_port))
        self.server.listen()

""" 初始化内网连接 """
def nat_register():
    if evn == 'develop':
        sock_connect = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sock_connect.connect(('120.53.22.183',22))
        nat_sock_connects['22'] = sock_connect
        sock_connect2 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sock_connect2.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
        sock_connect2.connect(('120.53.22.183',3306))
        nat_sock_connects['3306'] = sock_connect2
    else:
        register_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        register_sock.bind(('',nat_port))
        register_sock.listen()
        while True:
    
            sock_connect,addr = register_sock.accept()
            print('{0}:{1} connect...'.format(addr[0],addr[1]))
            if str(addr[1]) in nat_sock_connects.keys():
                data = sock_connect.recv(1024)
                if b'HEART' in data:
                    register_server.sendall('KEEPALIVE')
                else:
                    nat_sock_connects[str(addr[1])] = sock_connect

        


""" 接收处理客户端请求 """
# def ssh_server():
#     server_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
#     server_sock.bind(('',server_port))
#     server_sock.listen()
#     read_list = [server_sock]
#     ssh_listen_port = 8011
#     server_sock_fd = server_sock.fileno()
#     while True:
#         if ssh_listen_port not in nat_sock_connects.keys():
#             continue
#         nat_server = nat_sock_connects[ssh_listen_port]
#         rs,ws,es = select.select(read_list,[],[])
#         for sock in rs:
#             if sock.fileno() == server_sock_fd:
#                 client_socket = server_sock.accept()
#                 worker_pool.submit(ip_forword,nat_server,client_socket)
def start():
    nat_server_mapper = {}
    server_socks = []
    server_timeout = {}
    for server in register_servers.values():

        server_socks.append(server.server)
        #sock 和客户端口映射
        nat_server_mapper[server.server.fileno()] = str(server.src_port)
        server_timeout[server.server.fileno()] = server.timeout
    print('keys : {0}'.format(nat_sock_connects.keys()))
    while True:
        rs,ws,es = select.select(server_socks,[],[])
        for server in rs:
            # 判断服务是否已经注册
            fd = server.fileno()
            if fd in nat_server_mapper.keys():
                client,addr = server.accept()
                print(' client {0} 连接成功...'.format(str(addr)))
                #转发请求
                #查找对应端口好进行数据转发
                src_port = nat_server_mapper[fd]
                #通过端口好找到转发的socket进行转发
                if src_port in nat_sock_connects.keys():
                    nat_sock = nat_sock_connects[src_port]
                    #超时时间
                    timeout = server_timeout[fd]
                    #交给线程池处理
                    worker_pool.submit(ip_forword,nat_sock,client,timeout)


"""初始化服务器映射端口进程"""  
def register_server():
    print('start register server.....')
    for server_name in nat_config.keys():
        config = nat_config[server_name]
        if config['server_name'] and str(config['src_port']) and str(config['dst_port']):
            register_servers[server_name] = Server(config)
            print('server {0} register success...'.format(config['server_name']))
        else:
            print('erro server {0} register faild'.format(config['server_name']))
    
  
#两个sock 之间转发数据包
def ip_forword(sock_server,sock_client,timeout,read_len=0xFFFF):
    sock_server = sock_server
    sock_client = sock_client
    read_list = [sock_client,sock_server]
    #sock 文件描述符
    server_fd = sock_server.fileno()
    client_fd = sock_client.fileno()
    activity = True
    while activity:
        rs,ws,es = select.select(read_list,[],[],timeout)
        if not rs and not ws and not es:
            activity = False
        for sock in rs:
            #判断文件描述符
            if sock.fileno() == server_fd:
                data = sock_server.recv(read_len)
                if not data:
                    activity = False
                sock_client.sendall(data)
            elif sock.fileno() == client_fd:
                data = sock_client.recv(read_len)
                if not data:
                    activity = False
                sock_server.sendall(data)
    print('client {0} server {1} disconnect '.format(sock_client.getsockname,sock_server.getsockname))


def load_config():
    config_file = open('config.json','r')
    config = config_file.read()
    config_file.close()
    config_objs = json.loads(config)
    for conf in config_objs:
        nat_config[conf['server_name']] = conf


def main():
    #加载配置文件
    load_config()
    #注册服务
    register_server()
    #注册内网穿透端口
    register = threading.Thread(target=nat_register)
    #启动服务
    server= threading.Thread(target=start)
    register.start()
    time.sleep(5)
    server.start()
    register.join()
    server.join()
if __name__ == "__main__":
    main()






