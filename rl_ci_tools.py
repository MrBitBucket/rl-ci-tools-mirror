VERSION='0.0.2'
import os, sys, glob, time, json
PROG=os.path.basename(sys.argv[0])
debug=verbosity=0

class PyPiRequestor():
    scheme = 'https'
    host = os.environ.get('CITOOLS_SERVER','www.reportlab.com')
    root = '%s://%s' % (scheme,host)
    loginurl = "%s/accounts/login/" % root
    def __init__(self,debug=0):
        self.debug = debug
        import requests
        self.session = requests.session()

    def login(self,u,p,nxt='/test-7491/'):
        s = self.session
        resp = s.get(self.loginurl)
        loginpage = resp.text
        if self.debug>1:
            if self.debug>2: print('=============loginpage\n%r' % loginpage)
        resp = s.post(self.loginurl,
                        data=dict(
                                csrfmiddlewaretoken=s.cookies['csrftoken'],
                                username=u,
                                password=p,
                                next=nxt,
                                ),
                        headers=dict(
                            Referer=self.loginurl,
                            ),
                        )
        text = resp.text
        status_code = resp.status_code
        if debug>2:
            print('!!!!!\n%s\n!!!!!'% text)
            print('%s: test-7491 csrftoken=%r' % (PROG,resp.cookies.get('csrftoken','???')))
        if text!='I am alive!' or status_code!=200:
            raise ValueError('%s: login at %r failed with status_code=%r' % (PROG,self.loginurl,status_code))
        elif verbosity>=2:
            print('%s: logged in OK' % PROG)
        return status_code

    def _download(self,u,p, kind, fn, dst):
        self.login(u,p)
        base = '%s/pypi/%s/' % (self.root,kind)
        url = base + fn + '/'
        resp = self.session.get(url,
                data=dict(csrfmiddlewaretoken=self.session.cookies['csrftoken']),
                headers = dict(Referer=self.loginurl),
                )
        status_code = resp.status_code
        b = resp.content
        if debug>2:
            print('!!!!!\n%r\n!!!!!'% b)
        if status_code!=200:
            raise ValueError('%s: download %r failed with status_code=%r!\n%r' % (PROG,url,status_code,b))
        if dst:
            fn = os.path.join(dst,fn)
        with open(fn,'wb') as f:
            f.write(b)
        if verbosity:
            print('%s: %r(%d bytes) downloaded from %r.' % (PROG, fn, len(b),base))
        return resp.status_code

    def download(self,u,p,kind, fn, dst):
        for i in self.info(u,p,kind[:-1],fn):
            self._download(u,p,kind,i[0],dst)

    def info(self,u,p,kind,pat,subdir=''):
        #self.login(u,p)
        if subdir:
            subdir += '/'
        url = '%s/pypi/%s-info/%s%s/?json=1' % (self.root,kind,subdir,pat)
        resp = self.session.get(url,
                #data=dict(csrfmiddlewaretoken=self.session.cookies['csrftoken']),
                headers = dict(Referer=self.loginurl),
                )
        status_code = resp.status_code
        b = resp.content
        if debug>2:
            print('!!!!!\n%r\n!!!!!'% b)
        if status_code!=200:
            raise ValueError('%s: request %r failed with status_code=%r!\n%r' % (PROG,url,status_code,b))
        I = json.loads(b)
        if verbosity>1:
            print('%s: %r --> %d rows' % (PROG, url, len(I)))
        return I

    def upload(self,u,p,kind,fn,subdir=''):
        self.login(u,p)
        if subdir:
            subdir = '/' + subdir
        url = '%s/pypi/upload-%s%s/' % (self.root,kind,subdir)
        files= dict(file=(os.path.basename(fn),open(fn,'rb'),'application/octet-stream'))
        resp = self.session.post(url,
                data=dict(csrfmiddlewaretoken=self.session.cookies['csrftoken']),
                files=files,
                headers = dict(Referer=self.loginurl),
                )
        status_code = resp.status_code
        text = resp.text
        if text!='OK' or status_code!=200:
            raise ValueError('%s: upload %r failed with status_code=%r!\n%r' % (PROG,url,status_code,text))
        if verbosity:
            print('%s: uploaded %r to %r.' % (PROG,fn,url))
        return resp.status_code

    def clear_cache(self,u,p,fn):
        self.login(u,p)
        url = '%s/pypi/clear-cache/%s/' % (self.root,fn)
        resp = self.session.post(url,
                data=dict(csrfmiddlewaretoken=self.session.cookies['csrftoken']),
                headers = dict(Referer=self.loginurl),
                )
        status_code = resp.status_code
        text = resp.text
        if not text.endswith('OK') or status_code!=200:
            raise ValueError('%s: clear-cache %r failed with status_code=%r!\n%r' % (PROG,url,status_code,text))
        if verbosity:
            print('%s: cleared cache %r.' % (PROG,fn))
        return resp.status_code

    def package_version(self,u,p,pkg):
        I = self.info(u,p,'package','%s-*' % pkg)
        if not I:
            v = 'unknown'
        else:
            v = '.'.join(map(str,list(sorted([tuple([int(x) for x in i[0].split('-',2)[1].split('.') if x and x[0] in '0123456789']) for i in I]))[-1]))
        return (pkg,v)

def getoption(key,default=0,cnv=int):
    key = '--%s=' % key
    v = [x for x in sys.argv if x.startswith(key)]
    if v:
        for x in v:
            sys.argv.remove(x)
        v = cnv(v[-1][len(key):])
    else:
        v = default
    return v

def _file_info(fn):
    st = os.stat(fn)
    return (fn,st.st_size,st.st_mtime)

def _list_fs(patterns,recur=False):
    for pat in patterns:
        for fn in glob.glob(pat):
            if not recur:
                yield fn
            elif os.path.isdir(fn):
                for r,s,F in os.walk(fn):
                    yield r
                    for f in F:
                        yield os.path.join(r,f)
            else:
                yield fn

def tabulate(I,
                hdrs=['Name','Length',(5*' ')+'Modified'],
                fmtmpl8='{:<%d}\x20{:>%d}\x20\x20{:<%d}',
                cnvf=(str,str,lambda t: time.strftime('%Y%m%d %H:%M:%S',time.localtime(t))),
                ):
    if I:
        rows = [hdrs]
        for row in I:
            rows.append([c(r) for c,r in zip(cnvf,row)])
        W = [max(map(len,col)) for col in [list(i) for i in zip(*rows)]]
        if debug>3:
            print('tabluate: rows=%s' % repr(rows))
            print('tabluate: W=%s' % repr(W))
        fmt = fmtmpl8 % tuple(W)
        print('\n'.join(fmt.format(*i) for i in rows))

def main():
    u = os.environ.get('CITOOLS_USER','beta')
    p = os.environ.get('CITOOLS_PASSWORD','???')
    global debug, verbosity
    debug = getoption('debug')
    verbosity = getoption('verbosity')

    if debug>3:
        import logging

        # These two lines enable debugging at httplib level (requests->urllib3->http.client)
        # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
        # The only thing missing will be the response.body which is not logged.
        try:
            import http.client as http_client
        except ImportError:
            # Python 2
            import httplib as http_client
        http_client.HTTPConnection.debuglevel = 1

        # You must initialize logging, otherwise you'll not see debug output.
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    dst = getoption('dst',None,cnv=str)
    try:
        cmd = sys.argv[1]
    except:
        cmd = 'help'
    if cmd=='env':
        print('Environment')
        print('===========')
        I = list(sorted(os.environ.iteritems()))
        i = max([len(i[0]) for i in I])
        print(('{:<%d}  {}' % i).format('Key','Value'))
        fmt  = '{:<%d} = {}' % i
        for i in I:
            print(fmt.format(*i))
    elif cmd=='info':
        recur = [fn for fn in sys.argv[2:] if fn=='--recur']
        if recur:
            map(sys.argv.remove,recur)
            recur = True
        tabulate([_file_info(i) for i in _list_fs(sys.argv[2:],recur)])
    elif cmd=='help':
        print('Usage %s [test|info|env|download-[resources|packages]|upload-[resources|packages]|[packages|resources]-info] path....' % PROG)
    else:
        pypi = PyPiRequestor(debug=debug)
        if cmd=='test':
            status_code = pypi.login(u,p)
            if debug:
                print('status=%s' % status_code)
        elif cmd.startswith('download-'):
            kind = cmd.split('-')[1]
            if not kind in ('resources','packages', 'caches'):
                raise ValueError('%s: invalid download kind: %r' % (PROG,kind))
            if dst and not os.path.isdir(dst):
                raise ValueError('%s: %r is not a directory!' % (PROG,dst))
            for fn in sys.argv[2:]:
                pypi.download(u,p,kind,fn,dst)
        elif cmd.endswith('-info'):
            kind = cmd.split('-')[0]
            if not kind in ('resource','package', 'cache'):
                raise ValueError('%s: invalid info kind: %r' % (PROG,kind))
            subdir = getoption('subdir','',str) if kind=='cache' else None
            tabulate([i for fn in sys.argv[2:] for i in pypi.info(u,p,kind,fn,subdir)])
        elif cmd.startswith('upload-'):
            kind = cmd.split('-')[1]
            if not kind in ('resources','packages', 'caches'):
                raise ValueError('%s: invalid upload kind: %r' % (PROG,kind))
            subdir = getoption('subdir','',str) if kind=='caches' else None
            for pat in sys.argv[2:]:
                for fn in glob.glob(pat):
                    pypi.upload(u,p,kind[:-1],fn,subdir)
        elif cmd=='clear-cache':
            for fn in sys.argv[2:]:
                pypi.clear_cache(u,p,fn)
        elif cmd=='package-version':
            tabulate([pypi.package_version(u,p,fn) for fn in sys.argv[2:]],
                    hdrs = ['Package','Version'],
                    fmtmpl8 = '{:<%d}  {:>%d}',
                    cnvf = (str,str),
                    )
        else:
            raise ValueError('%s: unknown command %r' % (PROG,cmd))
if __name__=='__main__':
    main()
