#!/usr/bin/env python

"""
A basic, multiclient 'chat server' using Python's select module
with interrupt handling.

Entering any input at the terminal will exit the server.
"""

import select
import socket
import sys
import signal
from communication import send, receive

offlinemsg = {'lomea':'' , 'jacky':'' , 'mary':''}
talk = {}

BUFSIZ = 4096


class ChatServer(object):
    """ Simple chat server using select """
    
    def __init__(self, port=3490, backlog=5):
        self.clients = 0
        # Client map
        self.clientmap = {}
        # Output socket list
        self.outputs = []
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('',port))
        print 'Listening to port',port,'...'
        self.server.listen(backlog)
        # Trap keyboard interrupts
        signal.signal(signal.SIGINT, self.sighandler)
        
    def sighandler(self, signum, frame):
        # Close the server
        print 'Shutting down server...'
        # Close existing client sockets
        for o in self.outputs:
            o.close()
            
        self.server.close()

    def getname(self, client):

        # Return the printable name of the
        # client, given its socket...
        info = self.clientmap[client]
        host, name = info[0][0], info[1]
        return '@'.join((name, host))
        
    def serve(self):
        
        inputs = [self.server,sys.stdin]
        self.outputs = []

        running = 1

        while running:

            try:
                inputready,outputready,exceptready = select.select(inputs, self.outputs, [])
            except select.error, e:
                break
            except socket.error, e:
                break

            for s in inputready:

                if s == self.server:
                    # handle the server socket
                    client, address = self.server.accept()
                    print 'chatserver: got connection %d from %s' % (client.fileno(), address)
                    # Read the login name
                    cname = receive(client).split('NAME: ')[1]
                    
                    # Compute client name and send back
                    self.clients += 1
                    send(client, 'CLIENT: ' + str(address[0]))
                    inputs.append(client)

                    self.clientmap[client] = (address, cname)
                    
                    talk.update({cname:''})
                    
                    # Send joining information to other clients
                    msg = '\n(Connected: New client (%d) from %s)' % (self.clients, self.getname(client))
                    for o in self.outputs:
                        # o.send(msg)
                        send(o, msg)
                    
                    self.outputs.append(client)
                    
                    
                    if offlinemsg[self.getname(client).split('@')[0]] != '':
                        msg = offlinemsg[self.getname(client).split('@')[0]]
                        send(client, msg)
            
                elif s == sys.stdin:
                    # handle standard input
                    junk = sys.stdin.readline()
                    running = 0
                else:
                    # handle all other sockets
                    try:
                        # data = s.recv(BUFSIZ)
                        data = receive(s)
                        msg = ''

                        if talk[self.getname(s).split('@')[0]]!='':
                            for n in range(self.clients):
                                if talk[self.getname(s).split('@')[0]] == self.getname(self.outputs[n]).split('@')[0]:
                                    client=self.outputs[n]

                            if  data.split(' ')[0]=='/end':
                                talk[self.getname(s).split('@')[0]]=''
                                break

                            msg = data
                            send(client, msg)

                        else:
                            if data.split(' ')[0]=='/listuser':
                                for n in self.outputs:
                                    msg += self.getname(n) + ','
                                send(s, msg)
                    
                            elif data.split(' ')[0]=='/send':
                                for n in range(self.clients):
                                    if data.split(' ')[1] == self.getname(self.outputs[n]).split('@')[0]:
                                        client=self.outputs[n]
                                msg =' '.join(data.split(' ')[2:])
                                send(client, msg)
                
                            elif data.split(' ')[0]=='/talk':
                            
                                talk[self.getname(s).split('@')[0]]=data.split(' ')[1]
                                print talk
                        
                            elif data.split(' ')[0]=='/offlinemsg':
                                offlinemsg[data.split(' ')[1]] += '\n#[' + self.getname(s) + ']>> ' + ' '.join(data.split(' ')[2:])

                            elif data.split(' ')[0]=='/ban':
                                msg = self.getname(s)+' ban ' + data.split(' ')[1]
                                for o in self.outputs:
                                    if o != s:
                                        # o.send(msg)
                                        send(o, msg)
                                for n in range(self.clients):
                                    if data.split(' ')[1] == self.getname(self.outputs[n]).split('@')[0]:
                                        client=self.outputs[n]
                                send(client, '/ban')
                            elif data:
                                # Send as new client's message...
                                msg = '\n#[' + self.getname(s) + ']>> ' + data
                                # Send data to all except ourselves
                                for o in self.outputs:
                                    if o != s:
                                        # o.send(msg)
                                        send(o, msg)
                            else:
                                print 'chatserver: %d hung up' % s.fileno()
                            
                                offlinemsg[self.getname(s).split('@')[0]]=''
                                self.clients -= 1
                                s.close()
                                inputs.remove(s)
                                self.outputs.remove(s)

                                # Send client leaving information to others
                                msg = '\n(Hung up: Client from %s)' % self.getname(s)
                                for o in self.outputs:
                                    # o.send(msg)
                                    send(o, msg)
                                
                    except socket.error, e:
                        # Remove
                        inputs.remove(s)
                        self.outputs.remove(s)
                        


        self.server.close()

if __name__ == "__main__":
    ChatServer().serve()

