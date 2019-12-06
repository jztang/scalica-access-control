#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys, os
import code
import datetime
import logging
import traceback
from pprint import pprint

import rpc

shell_locals = {}
log_code = 'utf-8'
simpleformat = '[%(asctime)s]p%(process)d{%(module)s:%(funcName)s:%(lineno)d}%(levelname)s-%(message)s'
shortformat = '[%(asctime)s]p%(process)d{%(module)s:%(lineno)d}%(levelname)s-%(message)s'
shortdatefmt = '%m-%d %H:%M:%S'

OUT_LOG_FUNC = None

def strftime(fmt='%Y-%m-%d %H:%M:%S', dtime=None):
    """ 获取时间字符串,dt参数是时间对象，如果为None，返回当前时间字符串 """
    if dtime is None:
        dtime = datetime.datetime.now()
    return dtime.strftime(fmt)

class RpcShell(code.InteractiveConsole):
    _PRE_SHELL_ = 'shell_'
    _PRE_LEN_ = len(_PRE_SHELL_)
    def __init__(self, svc, proxy, locals=None, timeout=60 * 5, pre_prompt=''):
        if 0:
            self.proxy = rpc.RpcProxy()
            self.svc = rpc.RpcService()
        self.proxy = proxy
        self.svc = svc
        self.proxy.timeout = timeout
        self.log_hdlr = None
        self.loged = True
        self.pre_prompt = pre_prompt
        self.init(locals)

    def init(self, locals):
        global shell_locals
        if locals is None:
            locals = shell_locals

        try:
            import app
        except ImportError:
            app = None
        self.app = app
        shells = {'app': app}
        for name in dir(self):
            if name.startswith(self._PRE_SHELL_):
                shells[name[self._PRE_LEN_:]] = getattr(self, name)
        shells.update(locals)
        code.InteractiveConsole.__init__(self, locals=shells)

    def start(self):
        self._task = rpc.spawn(self.interact)

    def stop(self):
        self.svc.shells.pop(id(self), None)
        if not self.svc.stoped:
            self.proxy.stop()
        self.proxy = None
        self._unlog()
        if self._task is not None:
            self._task.kill(block = False)
            self._task = None

    def write(self, data):
        try:
            data = data.decode(log_code)
        except UnicodeError:
            pass

        try:
            self.proxy.write(data, _no_result=True)
        except Exception:
            self.stop()

    def flush(self):
        pass

    def raw_input(self, prompt=""):
        if not self.proxy:
            raise EOFError
        if self.pre_prompt and prompt:
            prompt = '%s+%s' % (self.pre_prompt, prompt)
        s1 = self.proxy.raw_input(prompt)
        if s1.strip() and self.loged:
            if OUT_LOG_FUNC:
                rpc.spawn(OUT_LOG_FUNC, self.proxy.get_addr(), s1)
            else:
                logging.warn('RpcShell.raw_input:%s', s1)
        if self.loged and s1 == '<<':
            raise EOFError
        return s1

    def interact(self, banner=None):
        try:
            code.InteractiveConsole.interact(self, banner)
        except Exception as e:
            logging.warn(u'shell close:%s', e)
        finally:
            self.stop()

    def runcode(self, code):
        """Execute a code object.

        When an exception occurs, self.showtraceback() is called to
        display a traceback.  All exceptions are caught except
        SystemExit, which is reraised.

        A note about KeyboardInterrupt: this exception may occur
        elsewhere in this code, and may not always be caught.  The
        caller should be prepared to deal with it.

        """
        old_std = sys.stdout
        old_err = sys.stderr
        sys.stdout = self
        sys.stderr = self
        try:
            exec code in self.locals
        except SystemExit:
            self.stop()
        except Exception:
            self.showtraceback()
        else:
            pass
            #if softspace(sys.stdout, 0):
            #    print
        finally:
            sys.stdout = old_std
            sys.stderr = old_err


    def shell_shell(self, proxy):
        """ 桥接shell """
        if isinstance(proxy, (str, unicode)):
            proxy = self.app.shell_get(proxy)
        addr = proxy.get_addr()
        svc = proxy.get_service()
        pre_prompt = str(addr)
        if self.pre_prompt:
            pre_prompt= '%s@%s' % (self.pre_prompt, pre_prompt)
        try:
            self.loged = False
            svc.start_console(pre_prompt=pre_prompt, shell=self)
        finally:
            self.loged = True


    def shell_pprint(self, obj):
        pprint(obj)

    def shell_log(self):
        """ 提供输出当前进程log信息命令 """
        hdlr = logging.StreamHandler(self)
        fmt = logging.Formatter(simpleformat, shortdatefmt)
        hdlr.setFormatter(fmt)
        logging.root.addHandler(hdlr)
        self.log_hdlr = hdlr
        while 1:
            gevent.sleep(1)

    def _unlog(self):
        if not self.log_hdlr:
            return
        logging.root.removeHandler(self.log_hdlr)

    def shell_mem(self):
        """ memory analyze """
        lmem, d = analyze_mem()
        self.shell_pprint(lmem)
        return lmem, d

    def shell_meliae_dump(self, file_path):
        """ meliae dump for memory analyze """
        meliae_dump(file_path)

    def shell_profile(self, duration=60, pf=None, is_trace=False):
        """ profile """
        if is_trace:
            is_trace = self
        rs, msg = profile(duration, pf, trace_obj=is_trace)
        self.write(msg)

    def shell_dead_check(self):
        start_dead_check()
        self.write(u'dead check install success')

    def shell_test_loop_dead(self):
        while True:
            a = 1 + 1


class RpcConsole(rpc.AbsExport):
    def __init__(self, svc):
        if 0:
            self.svc = rpc.RpcService()
        self.svc = svc
        from gevent.event import Event
        self.wait_event = Event()

    def write(self, data):
        sys.stderr.write(data)

    def raw_input(self, prompt=""):
        return raw_input(prompt)

    def stop(self):
        self.wait_event.set()

    def wait(self, shell_id):
        try:
            while not self.svc.stoped:
                if self.wait_event.wait(1):
                    break
        finally:
            pass

class RpcLocalConsole(RpcConsole):
    def raw_input(self, prompt=""):
        return raw_input(prompt)



class RpcProxyConsole(RpcConsole):
    def __init__(self, svc, shell):
        if 0:
            self.shell = RpcShell()
        RpcConsole.__init__(self, svc)
        self.shell = shell

    def write(self, data):
        self.shell.write(data)

    def raw_input(self, prompt=""):
        try:
            sinput = self.shell.raw_input(prompt)
            return sinput
        except rpc.RpcRuntimeError:
            self.stop()



def analyze_mem():
    """ memory analyze """
    import gc, sys
    d = {}
    objects = gc.get_objects()
    print 'gc objects size:', len(objects)
    for o in objects:
        o_type = type(o)
        if o_type in d:
            data = d[o_type]
        else:
            data = [0, 0, sys.getsizeof(0)]
        data[0] += 1
        data[1] += data[2]
        d[o_type] = data
    lmem = [[v, k] for k, v in d.iteritems()]
    lmem.sort()

    return lmem, d

def meliae_dump(file_path):
    """ 内存分析
辅助函数：
objs = om.objs
ft=lambda tname: [o for o in objs.values() if o.type_str == tname]
fp=lambda id: [objs.get(rid) for rid in objs.get(id).parents]
fr=lambda id: [objs.get(rid) for rid in objs.get(id).children]
#exec 'def fp1(id):\n obj = fo1(id)\n return fp(obj)'
exec 'def fps(obj, rs=None):\n    if rs is None:\n        rs = []\n    if len(rs) > 2000:\n        return rs\n    if obj is not None and obj not in rs:\n        rs.append(obj)\n        for p in fr(obj):\n            fps(p, rs=rs)\n    return rs'
exec 'def fps1(obj, rs=None):\n    if rs is None:\n        rs = []\n    if len(rs) > 2000:\n        return rs\n    if obj is not None and obj not in rs:\n        if obj.num_parents == 0:\n                rs.append(obj)\n        for p in fp(obj):\n            fps(p, rs=rs)\n    return rs'
fo=lambda id: objs.get(id)

运行时辅助：
import gc
get_objs = lambda :dict([(id(o), o) for o in gc.get_objects()])
fid = lambda oid: [o for o in gc.get_objects() if (id(o) == oid)]
fr = lambda o: gc.get_referents(o)
fp = lambda o: gc.get_referrers(o)
"""
    from meliae import scanner
    scanner.dump_all_objects(file_path)

def profile(duration=60, pf=None, trace_obj=None):
    """ profile """
    import gevent_profiler

    if gevent_profiler._attach_expiration is not None:
        return False, 'profile has running!\n'

    start_time = strftime('%y%m%d-%H%M%S')
    if pf is None:
        save_path = os.environ.get('LOG_PATH', None)
        if not save_path:
            save_path = os.path.join(os.environ['ROOT_PATH'], 'log')
        pf = os.path.join(save_path, 'profile-%s.profile' % start_time)
    gevent_profiler.set_summary_output(pf)
    gevent_profiler._attach_duration = duration

    if trace_obj:
        gevent_profiler.set_trace_output(trace_obj)
        gevent_profiler.enable_trace_output(True)
    else:
        gevent_profiler.set_trace_output(None)
        gevent_profiler.enable_trace_output(False)

    gevent_profiler.attach()
    return True, 'profile start:%s\n' % start_time


_dead_checker = None

def start_dead_check():
    global _dead_checker
    if _dead_checker:
        return True
    _dead_checker = DeadChecker()
    _dead_checker.start()
    return True

class DeadCheckError(StandardError):
    pass

class DeadChecker(object):
    """ 进程挂起的检查类 """
    DEAD_TIME = 60
    def __init__(self):
        self._hb_task = None


    def start(self):
        self._hb_time = time.time()
        sys.settrace(self._globaltrace)
        self._hb_task = rpc.spawn(self._heartbeat)


    def _heartbeat(self):
        while True:
            self._hb_time = time.time()
            sleep(1)

    def _globaltrace(self, frame, event, arg):
        return self._localtrace

    def _localtrace(self, frame, event, arg):
        if time.time() - self._hb_time > self.DEAD_TIME:
            msg = 'log_stack:dead check\n%s' % (''.join(traceback.format_stack()), )
            logging.warn(msg)
            raise DeadCheckError
        return self._localtrace

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------


