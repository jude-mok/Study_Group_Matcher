pass
import argparse
import sys
from urllib.parse import urlsplit
import httpx


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',required=True)
    parser.add_argument('--origin')
    args=parser.parse_args()
    url=urlsplit(args.base_url)
    if url.scheme not in ('http','https') or not url.netloc or url.username or url.password or url.query or url.fragment:
        parser.error('Use an HTTP(S) origin without credentials, query or fragment')
    failures=[]
    with httpx.Client(base_url=args.base_url.rstrip('/'),timeout=75,follow_redirects=False) as client:
        checks=[('health','/health',200),('root','/',200),('OpenAPI','/openapi.json',200),('course catalog','/courses/',200)]
        checks += [('unauthenticated '+p,p,403) for p in ['/users/me','/user-courses/','/study-groups/me','/rooms','/schedules/me']]
        for name,path,status in checks:
            try:
                r=client.get(path)
                assert r.status_code==status, f'expected {status}, got {r.status_code}'
                if path=='/health':assert r.json().get('status')=='healthy'
                elif path=='/courses/':assert isinstance(r.json(),list)
                elif path=='/openapi.json':assert '/meetings/votes' in r.json()['paths']
                print('PASS',name)
            except (httpx.HTTPError,AssertionError,ValueError,KeyError) as error:
                failures.append(name)
                print('FAIL',name,type(error).__name__) # Never print server bodies or credentials.
        if args.origin:
            r=client.options('/users/me',headers={'Origin':args.origin,'Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'authorization'})
            ok=r.status_code==200 and r.headers.get('access-control-allow-origin')==args.origin
            print('PASS' if ok else 'FAIL','CORS')
            if not ok:failures.append('CORS')
    print(f'{len(failures)} failures. This does not verify authenticated workflows or DB writes.')
    return bool(failures)


if __name__=='__main__':sys.exit(main())
