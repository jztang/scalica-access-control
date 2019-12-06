#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys, os
import time
import itertools
from cStringIO import StringIO
from struct import calcsize, pack, unpack
from weakref import KeyedRef, ref, WeakValueDictionary, WeakKeyDictionary
import traceback
import functools
import uuid
import zlib

from socket import error as socket_error, EBADF, AF_INET, SOL_SOCKET, SO_REUSEADDR

from gevent.socket import socket, create_connection
from gevent.coros import Semaphore
from gevent import GreenletExit, spawn, Timeout, sleep, getcurrent
from gevent.event import AsyncResult

#from pickle import loads as pickle_loads, dumps as pickle_dumps, HIGHEST_PROTOCOL
from cPickle import loads as pickle_loads, dumps as pickle_dumps, HIGHEST_PROTOCOL

from msgpack import loads, dumps, load
def use_list(use):
    global loads, load
    loads = functools.partial(loads, use_list=use)
    load = functools.partial(load, use_list=use)
use_list(True)

#try:
#    #warn:msgpack turn list to tuple
#    #print 'use msgpack'
#except ImportError:
#    from cPickle import loads, dumps, load, dump


from logging import root as logger, currentframe

DEBUG = 0
PICKLE_PROTOCOL = HIGHEST_PROTOCOL

def log1():
    from gevent import socket
    old_read = socket.wait_read
    def _wait_read(*args, **kw):
        if DEBUG:
            s = traceback.format_stack()
            printf(s)
        return old_read(*args, **kw)
    socket.wait_read = _wait_read


class RpcError(StandardError):
    pass

class RpcFuncNoFound(RpcError):
    pass
class RpcExportNoFound(RpcError):
    pass
class RpcCallError(RpcError):
    pass
class RpcRuntimeError(RpcError):
    pass
class RpcTimeout(RpcError):
    pass
class UnrecoverableError(RpcError):
    pass
class RPCCloseError(RpcError):
    pass

class FakeTimeout:
    def __enter__(self):
        pass
    def __exit__(self, typ, value, tb):
        pass
fake_timeout = FakeTimeout()
timeout_error = RpcTimeout()

#rpc数据类型
RT_REQUEST = 1 << 0
RT_RESPONSE = 1 << 1
RT_HEARTBEAT = 1 << 2
RT_EXCEPTION = 1 << 3
#rpc处理类型
ST_NO_RESULT = 1 << 5
ST_NO_MSG = 1 << 6
#rpc参数类型
DT_PICKLE = 1 << 7 #默认用msgpack
DT_ZIP = 1 << 8
DT_PROXY = 1 << 9 #标示传递的第1个参数是obj, 需要转换成proxy

#rpc数据类型 mark
RT_MARK = ST_NO_RESULT - 1

RT_RESULTS = (RT_RESPONSE, RT_EXCEPTION)

RECONNECT_TIMEOUT = 0 #wait reconnect time, zero will disable reconnect wait
HEARTBEAT_TIME = 60 #heartbeat, if disconnect time > (HEARTBEAT_TIME + RECONNECT_TIMEOUT), connect lost
CALL_TIMEORUT = 240
ZIP_LENGTH = 1024 * 2 #if argkw > Nk, use zlib to compress
ZIP_LEVEL = 3
MAX_INDEX = (1 << 32) - 1


use_logging = False
log_head = '[p%s]' % os.getpid()
def printf(msg, *args):
    if args:
        msg = msg % args
    if use_logging:
        logger.warn(msg)
    else:
        print('%s%s' % (log_head, msg))


def log_except(*args, **kw):
    ei = sys.exc_info()
    if args:
        lines = [args[0] % args[1:], '\n']
    else:
        lines = []
    lines.append('Traceback (most recent call last):\n')
    st = traceback.extract_stack(f=ei[2].tb_frame.f_back)
    et = traceback.extract_tb(ei[2])
    lines.extend(traceback.format_list(st))
    lines.append('  ****** Traceback ******  \n')
    lines.extend(traceback.format_list(et))
    lines.extend(traceback.format_exception_only(ei[0], ei[1]))
    exc = ''.join(lines)
    if kw.get('clear', False):
        sys.exc_clear()
    printf(exc)



def unlink(path):
    from errno import ENOENT
    try:
        os.unlink(path)
    except OSError, ex:
        if ex.errno != ENOENT:
            raise

def link(src, dest):
    from errno import ENOENT
    try:
        os.link(src, dest)
    except OSError, ex:
        if ex.errno != ENOENT:
            raise

def tcp_listener(address, backlog=50, reuse_addr=True, family=AF_INET):
    """A shortcut to create a TCP socket, bind it and put it into listening state."""
    sock = socket(family=family)
    if reuse_addr is not None:
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, reuse_addr)
    try:
        sock.bind(address)
    except socket_error:
        ex = sys.exc_info()[1]
        strerror = getattr(ex, 'strerror', None)
        if strerror is not None:
            ex.strerror = strerror + ': ' + repr(address)
        raise
    sock.listen(backlog)
    return sock

def bind_unix_listener(path, backlog=50, reuse_addr=True, user=None):
    from socket import AF_UNIX, SOCK_STREAM
    pid = os.getpid()
    tempname = '%s.%s.tmp' % (path, pid)
    backname = '%s.%s.bak' % (path, pid)
    unlink(tempname)
    unlink(backname)
    link(path, backname)
    try:
        sock = socket(AF_UNIX, SOCK_STREAM)
        sock.bind(tempname)
        try:
            if user is not None:
                import pwd
                user = pwd.getpwnam(user)
                os.chown(tempname, user.pw_uid, user.pw_gid)
                os.chmod(tempname, 0600)
            sock.listen(backlog)
            try:
                os.rename(tempname, path)
            except:
                os.rename(backname, path)
                backname = None
                raise
            tempname = None
            return sock
        finally:
            if tempname is not None:
                unlink(tempname)
    finally:
        if backname is not None:
            unlink(backname)

def create_unix_connection(address):
    """    """
    from socket import AF_UNIX, SOCK_STREAM
    sock = socket(AF_UNIX, SOCK_STREAM)
    sock.connect(address)
    return sock


def parse_kw(kw, default_timeout=CALL_TIMEORUT):
    no_result = kw.pop('_no_result', False)
    timeout = kw.pop('_timeout', default_timeout)
    pickle = kw.pop('_pickle', False)
    proxy = kw.pop('_proxy', False)
    return no_result, timeout, pickle, proxy


class AbsExport(object):
    _rpc_name_ = '' #unique name
    _rpc_id_ = None
    if 0:
        def _rpc_proxy_(self):
            """ return can transport's proxy """
            pass

def wrap_pickle_result(func):
    func._rpc_pickle_result_ = True
    return func

def wrap_nonblock(func):
    func._block_ = False
    return func


class RpcBase(object):
    def __init__(self, size=None):
        self.stoped = True
        self.addr = None
        self.bind_addr = None
        self._socket = None
        self.pool_size = size
        self._exports = {}
        def remove(wr, selfref=ref(self)):
            self = selfref()
            if self is not None:
                self._exports.pop(wr.key, None)
        self._remove = remove

    def _resolve_endpoint(self, endpoints):
        if not isinstance(endpoints, (tuple, list)):
            yield endpoints
        else:
            for p in endpoints:
                yield p

    def bind(self, address, reuse_addr=True):
        self.addr = address
        self.bind_addr = address
        if not isinstance(address, str):
            self._socket = tcp_listener(address, reuse_addr=reuse_addr)
        else:
            self._socket = bind_unix_listener(address, reuse_addr=reuse_addr)
        _my_servers_[address] = self

    def connect(self, address):
        self.addr = address
        if not isinstance(address, str):
            self._socket = create_connection(address)
        else:
            self._socket = create_unix_connection(address)

    def _close(self):
        if not self._socket:
            return
        try:
            self._socket._sock.close()
        except socket_error:
            pass
        self._socket.close()
        self._socket = None
        #_rpcs_.append('-%s' % str(self.addr))

    def after_start(self):
        pass

    def start(self):
        if not self.stoped:
            return
        self.stoped = False
        self.after_start()
        #_rpcs_.append(self.addr)

    def before_stop(self):
        pass

    def stop(self):
        if self.stoped:
            return
        self.stoped = True
        try:
            self.before_stop()
        finally:
            self._close()

    def _handle(self, parts):
        """ 单个数据包处理 """
        pass


    def proxy(self, obj):
        """ 代理obj,可以通过pickle传递到远程 """
        self.register(obj)

    def register(self, export, name=None):
        if name is None:
            name = getattr(export, '_rpc_name_', None)
        if name:
            if name in self._exports and export != self._exports[name]():
                raise ValueError, 'export name(%s) existed!' % name
            export_id = name
        else:
            export_id = id(export)
        self._exports[export_id] = KeyedRef(export, self._remove, export_id)
        setattr(export, '_rpc_id_', export_id)
        return export_id

    def unregister(self, export):
        export_id = getattr(export, '_rpc_id_', None)
        self._exports.pop(export_id, None)

    def get_export(self, export_id):
        try:
            return self._exports[export_id]()
        except KeyError:
            return None

    def get_export_proxy(self, export):
        assert export._rpc_id_ in self._exports
        return RpcProxy(export._rpc_id_, addr=self.addr)

    def execute(self, func, *args, **kw):
        raise NotImplementedError

class RpcService(object):
    """ service for one socket """
    UID_LEN = 32
    def __init__(self, svr, sock, uid, size=None):
        if 0:
            self.svr = RpcServer()
        self.svr = svr
        #self._pool = Pool(size=size)
        self.sock = sock
        if isinstance(svr, RpcClient):
            self.sock_addr = svr.addr
        else:
            self.sock_addr = self.sock.getpeername()
        self.uid = str(uid)
        if len(self.uid) != self.UID_LEN:
            raise ValueError, 'uid length error: len(uid)=%d <> %d' % (len(uid), self.UID_LEN)

        self._slock = Semaphore()
        self._reconnected = None
        self.reconnect_timeout = RECONNECT_TIMEOUT
        #self.iter_id = itertools.cycle(xrange(MAX_INDEX))
        self._next_id = 0
        self._resps = {}
        self._proxys = WeakValueDictionary()
        self.stoped = True
        self.sock_error = False
        if HEARTBEAT_TIME > 0:
            self._heart_time = time.time()
            self._heart_task = spawn(self.heartbeat)
        self.shells = {}

    def next_id(self):
        self._next_id += 1
        if self._next_id >= MAX_INDEX:
            self._next_id = 1
        return self._next_id

    def start(self):
        if not self.stoped:
            return
        self.stoped = False
        self._recv_task = spawn(self._recver)
        self._recver_on_error = False
        #_services_.append(self.sock_addr)

    def remote_stop(self):
        #printf('remote_stop:%s', self.sock_addr)
        self.sock_error = True
        self.stop()

    def close(self):
        if not self.sock:
            return
        try:
            self.sock._sock.close()
        except socket_error:
            pass
        self.sock.close()
        self.sock = None

    def stop(self):
        if self.stoped:
            return
        self.stoped = True
        self._recv_task.kill(block=0)
        self._recv_task = None
        if 1 and not self.sock_error:
            try:
                #printf('remote_stop:%s', self.sock_addr)
                self.call('', 'remote_stop', tuple(), None, no_result=True)
                sleep(0.01)
            except:
                pass
        self.svr.svc_stop(self)
        if getattr(self, '_heart_task', None):
            self._heart_task.kill(block=False)
            self._heart_task = None
        try:
            self._stop_resps()
            self._stop_proxys()
        finally:
            self.close()
            #_services_.append('-%s' % str(self.sock_addr))

    def _stop_resps(self):
        error = RpcRuntimeError('service stoped')
        for k,v in self._resps.iteritems():
            v.set_exception(error)
        self._resps.clear()

    def _stop_proxys(self):
        if not len(self._proxys):
            return
        proxys = self._proxys.values()
        self._proxys.clear()
        for p in proxys:
            p.on_close()

##    def _sender(self):
##        running = True
##        _send = self.sock.sendall
##        try:
##            for data in self._send_queue:
##                _send('%s%s' %(pack('I', len(data)), data))
##        except GreenletExit:
##            pass


    def _recver(self):
        """ 接收处理数据 """
        recv_func = self.sock.recv
        def _read(c):
            d = recv_func(c)
            if d:
                return d
            if self.stoped:
                raise GreenletExit
            self._recver_on_error = True
            self._on_socket_error(None)
            self._recver_on_error = False
            return None

        try:
            sio = StringIO()
            while not self.stoped:
                dlen = 4
                d = ''
                while dlen > 0:
                    data = _read(dlen)
                    if data is None:
                        continue
                    d += data
                    dlen -= len(data)
                dlen = unpack('I', d)[0]
                #rs = []
                sio.seek(0)
                sio.truncate()
                while dlen > 0:
                    data = _read(dlen)
                    if data is None:
                        continue
                    #rs.append(data)
                    sio.write(data)
                    dlen -= len(data)
                #spawn(self._handle, loads(''.join(rs)))
                sio.seek(0)
                self._handle(load(sio))
                #self._pool.spawn(self._handle, loads(''.join(rs)))
        except GreenletExit:
            pass
        except Exception as err:
            printf('[RpcService._recver]%s', err)
        finally:
            self.stop()

    def _on_socket_error(self, err):
        if self.stoped or self.reconnect_timeout <= 0:
            self.sock_error = True
            self.stop()
            return
        def _reconnect():
            #尝试重连或等待重连
            while not self.stoped:
                try:
                    self.svr.reconnect()
                    break
                except socket_error:
                    pass
                sleep(0.5)

        if self._reconnected is None:
            self._reconnected = AsyncResult()
            printf('socket error:%s,  RpcService try reconnect', err)
            self.send = self.send_wait
            if hasattr(self.svr, 'reconnect'):#RpcClient.reconnect
                spawn(_reconnect)

        self._wait_reconnect()

    def _wait_reconnect(self):
        _reconnected = self._reconnected
        try:
            _reconnected.get(timeout=self.reconnect_timeout)
        except Timeout:
            pass
        if not _reconnected.successful():
            self.stop()
            if self.sock_error or _reconnected.exception is None:
                return
            self.sock_error = True
            raise _reconnected.exception

    def reconnect(self, sock):
##        if not self._recver_on_error:
##            self._recv_task.kill(exception=socket_error('reconnect'))
        self.sock = sock
        self.send = self.send_imme
        if self._reconnected is not None:
            self._reconnected.set(True)
            self._reconnected = None

    def send_imme(self, *args):
        data = dumps(args)
        with self._slock:
            try:
                self.sock.sendall('%s%s' %(pack('I', len(data)), data))
            except socket_error as err:
                self._on_socket_error(err)
                #重新发送
                self.sock.sendall('%s%s' %(pack('I', len(data)), data))
##        self._send_queue.put(dumps(args))

    def send_wait(self, *args):
        if self._reconnected is not None:
            self._wait_reconnect()
        self.send_imme(*args)
    send = send_imme

    def _read_response(self, index, timeout):
        rs = AsyncResult()
        self._resps[index] = rs
        resp = rs.wait(timeout)
        self._resps.pop(index, None)
        if not rs.successful():
            error = rs.exception
            if error is None:
                error = Timeout
            raise error
        return resp

    def _reg_obj(self, obj):
        if hasattr(obj, 'proxy_pack'):
            return obj.proxy_pack(), False
        if isinstance(obj, RpcProxy):
            return obj._id, False
        if hasattr(obj, '_rpc_proxy_'):
            return obj._rpc_proxy_(), True
        return self.svr.register(obj), False

    def call(self, obj_id, name, args, kw, no_result=False,
            timeout=CALL_TIMEORUT, pickle=False, proxy=False):
        dtype = RT_REQUEST
        if proxy:
            objs = args[0] #first arg is proxy(str, RpcProxy or list)
            if isinstance(objs, (tuple, list)):
                obj_ids = []
                for o in objs:
                    obj, is_pickle = self._reg_obj(o)
                    pickle = pickle or is_pickle
                    obj_ids.append(obj)
            else:
                obj, is_pickle = self._reg_obj(objs)
                pickle = pickle or is_pickle
                obj_ids = obj
            args = (obj_ids, ) + args[1:]
            dtype |= DT_PROXY
        if pickle:
            dtype |= DT_PICKLE
            argkw = pickle_dumps((args, kw), PICKLE_PROTOCOL)
        else:
            argkw = dumps((args, kw))
        if len(argkw) >= ZIP_LENGTH:
            dtype |= DT_ZIP
            argkw = zlib.compress(argkw, ZIP_LEVEL)
        if no_result:
            dtype |= ST_NO_RESULT
        index = self.next_id() #iter_id.next()
        self.send(dtype, obj_id, index, name, argkw)
        if no_result:
            return
        result = self._read_response(index, timeout)
        return result

    def _handle_request(self, parts):
        dtype, obj_id, index, name, argkw = parts
        try:
            obj = self.get_export(obj_id)
            if obj is None:
                raise RpcExportNoFound, obj_id
            func = getattr(obj, name)
            if not callable(func):
                raise RpcFuncNoFound, name

            if dtype & DT_ZIP:
                argkw = zlib.decompress(argkw)
            if dtype & DT_PICKLE:
                args, kw = pickle_loads(argkw)
            else:
                args, kw = loads(argkw)

            if dtype & DT_PROXY:
                export_ids = args[0]
                if isinstance(export_ids, (tuple, list)):
                    proxys = []
                    for e in export_ids:
                        proxys.append(self.get_proxy(e))
                else:
                    proxys = self.get_proxy(export_ids)
                args = (proxys, ) + tuple(args[1:])

            if getattr(func, "_block_", True):
                spawn(self._handle_request_call, func, args, kw, dtype, index, obj_id, name, argkw)
            else:
                self._handle_request_call(func, args, kw, dtype, index, obj_id, name, argkw)
        except Exception as e:
            log_except('export(%s).%s(%s)', obj_id, name, repr(argkw))
            if dtype & ST_NO_RESULT or self.svr.stoped:
                return
            self.send(RT_EXCEPTION, index, str(e))

    def _handle_request_call(self, func, args, kw, dtype, index, obj_id, name, argkw):
        try:
            let = getcurrent()
            setattr(let, _service_name_, self)
            if args is None:
                rs = func()
            else:
                rs = func(*args, **kw) if kw is not None else func(*args)
            if dtype & ST_NO_RESULT:
                return
            if not getattr(func, '_rpc_pickle_result_', False):
                self.send(RT_RESPONSE, index, dumps(rs))
            else:
                self.send(RT_RESPONSE | DT_PICKLE, index, pickle_dumps(rs, PICKLE_PROTOCOL))
        except Exception as e:
            log_except('export(%s).%s(%s)', obj_id, name, repr(argkw))
            if dtype & ST_NO_RESULT or self.svr.stoped:
                return
            self.send(RT_EXCEPTION, index, str(e))

    def _handle_response(self, parts):
        dtype, index, argkw = parts
        try:
            rs = self._resps.pop(index)
            if dtype & DT_PICKLE:
                result = pickle_loads(argkw)
            else:
                result = loads(argkw)
            rs.set(result)
        except KeyError:
            pass

    def _handle_exception(self, parts):
        RT_EXCEPTION, index, error = parts
        #try:
        #    error = pickle_loads(error)
        #except:
        error = RpcCallError(str(error))
        try:
            rs = self._resps.pop(index)
            rs.set_exception(error)
        except KeyError:
            pass

    def _handle(self, parts):
        #parts = (parts[0], ) + loads(parts[1]) if len(parts) ==2 else loads(parts[0])
        rt = parts[0] & RT_MARK
        if rt == RT_REQUEST:
            self._handle_request(parts)
        elif rt == RT_RESPONSE:
            self._handle_response(parts)
        elif rt == RT_EXCEPTION:
            self._handle_exception(parts)
        elif rt == RT_HEARTBEAT:
            self._heart_time = time.time()
        else:
            raise ValueError('unknown data:%s' % str(rt))

    def heartbeat(self):
        beat = RT_HEARTBEAT
        btime = HEARTBEAT_TIME
        check_times = HEARTBEAT_TIME * max(3, RECONNECT_TIMEOUT)
        try:
            while not self.stoped:
                self.send(beat)
                sleep(btime)
                if (self._heart_time + check_times) < time.time():
                    printf('heartbeat timeout!!!!!!!!')
                    self.sock_error = True
                    break
        finally:
            self.stop()

    @classmethod
    def handshake_svr(cls, sock):
        uid = sock.recv(cls.UID_LEN)
        return uid

    def handshake_cli(self):
        self.sock.sendall(self.uid)


    #######remote call##############
    def get_export(self, export_id):
        """ get export obj by export_name """
        if not export_id:
            return self
        return self.svr.get_export(export_id)


    def get_proxy(self, export_id, proxy_cls=None):
        """ remote call: get export obj by id """
        if isinstance(export_id, RpcProxy):
            return export_id
        if isinstance(export_id, (tuple, list)):
            export_cls = PROXYS[export_id[0]]
            return export_cls.proxy_unpack(export_id, svc=self)

        if proxy_cls in (None, RpcProxy):
            try:
                return self._proxys[export_id]
            except KeyError:
                proxy_cls = RpcProxy
                proxy = proxy_cls(export_id, svc=self)
                self.reg_proxy(export_id, proxy)
                return proxy
        else:
            p = proxy_cls(export_id, svc=self)
            self.reg_proxy(id(p), p)
            return p

    def reg_proxy(self, key, proxy):
        self._proxys[key] = proxy

    def stop_shell(self, shell_id):
        shell = self.shells.pop(shell_id, None)
        if not shell:
            return
        shell.stop()

    def start_shell(self, console_proxy, pre_prompt):
        from rpc_shell import RpcShell
        if self.svr.access and not self.svr.access.access_shell(self):
            printf('[rpc]shell deny:%s', self.sock_addr)
            return 0
        printf('[rpc]shell start:%s', self.sock_addr)
        shell = RpcShell(self, console_proxy, pre_prompt=pre_prompt)
        shell.start()
        #shell.stop remove shell from self.shells
        shell_id = id(shell)
        self.shells[shell_id] = shell
        return shell_id

    def stop_console(self, shell_id):
        self.call('', 'stop_shell', (shell_id, ), None, no_result=True, timeout=20)

    def start_console(self, pre_prompt='', shell=None):
        from rpc_shell import RpcLocalConsole, RpcProxyConsole
        console = RpcLocalConsole(self) if shell is None else RpcProxyConsole(self, shell)
        shell_id = self.call('', 'start_shell', (console, pre_prompt), None, proxy=True, timeout=20)
        try:
            console.wait(shell_id)
        finally:
            pass

    def execute(self, func, args, kw, **others):
        return self.svr.execute(func, args, kw)

    def valid_proxy(self, export_id):
        return self.get_export(export_id) != None


class RpcClient(RpcBase):
    def __init__(self, size=None, uid=None):
        RpcBase.__init__(self, size=size)
        if uid is None:
            self.uid = uuid.uuid4().hex
        else:
            self.uid = uid

    def __del__(self):
        self.stop()

    def after_start(self):
        self.svc = RpcService(self, self._socket, self.uid, size=self.pool_size)
        self.svc.handshake_cli()
        self.svc.start()

    def reconnect(self):
        if not self.addr:
            return
        self.stop()
        self.connect(self.addr)
        self.svc.sock = self._socket
        self.svc.handshake_cli()
        self.svc.reconnect(self._socket)

    def _handle(self, parts):
        """ 单个数据包处理 """
        self.svc._handle(parts)

    def before_stop(self):
        if self.addr in _addr_clients:
            _addr_clients.pop(self.addr, None)
        self.svc.stop()

    def svc_stop(self, service):
        if service == self.svc:
            self.stop()
        else:
            raise ValueError

    def execute(self, func, args, kw, **others):
        return self.svc.call('', 'execute', (func, args, kw),
                pickle=True, **others)

class AccessCtrl(object):
    def access_sock(self, sock, addr):
        pass

    def access_shell(self, proxy):
        pass

class RpcServer(RpcBase):
    """ rpc services """
    def __init__(self, size=None, access=None):
        """ access:AccessCtrl object """
        RpcBase.__init__(self, size=size)
        self._services = {}
        self.access = access

    def after_start(self):
        self._accept_task = spawn(self._accept)

    def before_stop(self):
        if self.addr in _my_servers_:
            _my_servers_.pop(self.addr, None)
        self._accept_task.kill(block=False)
        for svc in self._services.values():
            svc.stop()

    def get_service(self, uid):
        try:
            return self._services[uid]
        except KeyError:
            return None

    def init_service(self, sock):
        uid = RpcService.handshake_svr(sock)
        svc = self.get_service(uid)
        if svc is None:
            svc = RpcService(self, sock, uid)
            self._services[uid] = svc
        else:
            svc.reconnect(sock)
        return svc

    def _handle(self, parts):
        """ 单个数据包处理 """
        sc = self.get_service(parts[0])
        sc._handle(parts[1:])

    def svc_stop(self, service):
        self._services.pop(service.uid, None)

    def _accept(self):
        while not self.stoped:
            try:
                client_socket, address = self._socket.accept()
                def _accept_sock(client_socket, address):
                    if self.access and \
                            not self.access.access_sock(client_socket, address):
                        client_socket.close()
                        printf('[rpc]access deny:%s', address)
                        return
                    #printf('[rpc]access:%s', address)

                    svc = self.init_service(client_socket)
                    if svc:
                        svc.start()
                spawn(_accept_sock, client_socket, address)
            except socket_error as ex:
                if ex.errno == EBADF:
                    return
                log_except(clear=True)
                sleep(0.05)

    def execute(self, func, args, kw, **others):
        rs = func(*args, **kw)
        return rs



#import pickle
def proxy_reconstructor(proxy_cls, addr, export_id, timeout):
    proxy = get_proxy_by_addr(addr, export_id, proxy_cls=proxy_cls)
    if proxy:
        proxy.timeout = timeout
    return proxy

class RpcProxy(object):
    """ 可以被序列化的代理类,可以被继承 """
    def __init__(self, export_id, svc=None, addr=None):
        if 0:
            self._svc = RpcService()
        self._svc = svc
        self._id = export_id
        if addr:
            self._addr = addr
        else:
            self._addr = self._svc.sock_addr
        self.timeout = CALL_TIMEORUT
        self._methods = {}
        self._closes = {}#WeakKeyDictionary()

    def __reduce__(self):
        """ 支持pickle,
        __reduce__返回3元数组,
            1:创建对象的方法
            2:上面方法的参数(对象的类继承关系)
            3:对象的数据
        """
        return (proxy_reconstructor,
                (self.__class__, self.get_addr(), self._id, self.timeout),
                self.__getstate__(), )

    def __setstate__(self, adict):
        pass
    def __getstate__(self):
        return None

    def __call__(self, *args, **kw):
        no_result, timeout, pickle, proxy = parse_kw(kw, self.timeout)
        return self._svc.call(self._id, '__call__', args, kw,
            no_result=no_result, timeout=timeout, pickle=pickle, proxy=proxy)

    def __getattr__(self, attribute):
        try:
            return self._methods[attribute]
        except KeyError:
            def _func(*args, **kw):
                no_result, timeout, pickle, proxy = parse_kw(kw, self.timeout)
                return self._svc.call(self._id, attribute, args, kw,
                    no_result=no_result, timeout=timeout, pickle=pickle, proxy=proxy)
            _func.func_name = attribute
            _func.__module__ = str(self._id)
            self._methods[attribute] = _func
            return _func

    def __getitem__(self, key):
        return self.__getattr__('__getitem__')(key)

    def valid(self):
        """ check this proxy is valid """
        return self._svc.call('', 'valid_proxy', (self._id,), None)

    def get_service(self):
        return self._svc

    def get_proxy(self, name):
        return self._svc.get_proxy(name)

    def get_addr(self):
        return self._addr

    def get_bind_addr(self):
        return self._svc.svr.bind_addr

    def get_proxy_id(self):
        return self._addr, self._id
        #return self._svc.svr.addr, self._id

    def get_export_id(self):
        return self._id

    def on_close(self):
        for func in self._closes.keys():
            try:
                spawn(func, self)
            except StandardError:
                log_except()

    def sub_close(self, func):
        self._closes[func] = None

    def unsub_close(self, func):
        self._closes.pop(func, None)

    @classmethod
    def new_by_local(cls, export, addr):
        """ 子类继承,实现对本地对象的处理 """
        return export

class DictExport(object):
    """ 配合下面代理类的export类 """
    def _call_dict_obj_(self, dict_name, key, attr, args, kw):
        d1 = getattr(self, dict_name)
        obj = d1[key]
        func = getattr(obj, attr)
        return func(*args, **kw)

    def _call_dict_objs_(self, dict_name, keys, attr, args, kw, **others):
        rs = []
        for key in keys:
            rs.append(self._call_dict_obj_(dict_name, key, attr, args, kw))
        return rs


class DictItemProxy(RpcProxy):
    """ 字典元素代理类 """
    def __init__(self, export_id, dict_name=None, key=None, **kw):
        RpcProxy.__init__(self, export_id, **kw)
        self.dict_name = dict_name
        self.key = key
        self.is_local = False
        self.export = None

    def proxy_pack(self):
        return PROXY_DICT_ITEM, self._id, self.dict_name, self.key

    @classmethod
    def proxy_unpack(cls, args, **kw):
        _, export_id, dict_name, key = args
        obj = cls(export_id, dict_name=dict_name, key=key, **kw)
        return obj


    @classmethod
    def new_by_local(cls, export, addr):
        """ 子类继承,实现对本地对象的处理 """
        proxy = DictItemProxy(export._rpc_id_, addr=addr)
        proxy.is_local = True
        proxy.export = export
        return proxy

    def __setstate__(self, adict):
        self.dict_name = adict['dict_name']
        self.key = adict['key']
    def __getstate__(self):
        return dict(dict_name=self.dict_name, key=self.key)

    def __getattr__(self, attribute):
        def _func(*args, **kw):
            no_result, timeout, pickle, proxy = parse_kw(kw, self.timeout)
            params = (self.dict_name, self.key, attribute, args, kw)
            if self.is_local:
                return self.export._call_dict_obj_(*params)
            return self._svc.call(self._id, '_call_dict_obj_',
                params, None,
                no_result=no_result, timeout=timeout, pickle=pickle, proxy=proxy)
        return _func

    def get_owner(self):
        if self.is_local:
            return self.export
        p = RpcProxy(self._id, addr=self._addr, svc=self._svc)
        self._svc.reg_proxy(id(p), p)


def map_items(proxys, attr, *args, **kw):
    """ all proxys in one dict """
    if not len(proxys):
        return True, []
    no_result, timeout, pickle, proxy = parse_kw(kw)
    p0 = proxys[0]
    dict_proxy = get_proxy_by_addr(p0.get_addr(), p0._id)
    keys = [p.key for p in proxys]
    rs = dict_proxy._call_dict_objs_(p0.dict_name, keys, attr, args, kw,
        _pickle=True, _no_result=no_result, _timeout=timeout, _proxy=proxy)
    return rs

def map_items_ex(proxys, attr, *args, **kw):
    """ some proxys in some dict """
    if not len(proxys):
        return []
    maps = {}
    for proxy in proxys:
        addr = proxy.get_addr()
        plist = maps.setdefault(addr, [])
        plist.append(proxy)

    no_result, timeout, pickle, proxy = parse_kw(kw)
    if not no_result:
        result = {}
    for addr, plist in maps.iteritems():
        rs = map_items(plist, attr, *args, **kw)
        if not no_result:
            result[addr] = rs
    if no_result:
        return
    return [result[p.get_addr()].pop(0) for p in proxys]



_service_name_ = '_grpc_svc_'
_my_servers_ = WeakValueDictionary()
_addr_clients = WeakValueDictionary()
_rpcs_ = []
_services_ = []


def uninit():
    """ clear all """
    global _my_servers_, _addr_clients
    clients = _addr_clients.values()
    _addr_clients.clear()
    servers = _my_servers_.values()
    _my_servers_.clear()
    for cli in clients:
        cli.stop()
    for svr in servers:
        svr.stop()
    #printf('_rpcs_:%s \n_services_:%s', _rpcs_, _services_)

def get_service():
    let = getcurrent()
    return getattr(let, _service_name_, None)

def get_rpc_by_addr(addr, force_rpc=0):
    global _addr_clients, _my_servers_
    if isinstance(addr, list):
        addr = tuple(addr)
    if not force_rpc and addr in _my_servers_:
        svr = _my_servers_[addr]
        return svr

    try:
        return _addr_clients[addr]
    except KeyError:
        client = RpcClient()
        try:
            client.connect(addr)
        except socket_error:
            return None
        client.start()
        _addr_clients[addr] = client
        return client

def get_proxy_by_addr(addr, proxy_name, proxy_cls=None):
#    if proxy_name == 'game':
#        printf('get_proxy_by_addr:%s', addr)
    rpc_obj = get_rpc_by_addr(addr)
    if rpc_obj is None:
        return
    if isinstance(rpc_obj, RpcServer):
        svr = rpc_obj
        export = svr.get_export(proxy_name)
        if proxy_cls in (None, RpcProxy):
            return export
        return proxy_cls.new_by_local(export, addr)

    client = rpc_obj
    return client.svc.get_proxy(proxy_name, proxy_cls=proxy_cls)

def get_addr(export_or_proxy):
    if isinstance(export_or_proxy, RpcProxy):
        return export_or_proxy.get_addr()
    export_id = export_or_proxy._rpc_id_
    for addr, svr in _my_servers_.iteritems():
        if export_id not in svr._exports:
            continue
        return svr.addr


PROXY_DICT_ITEM = 1
PROXYS = {
    PROXY_DICT_ITEM: DictItemProxy,
}




#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------

