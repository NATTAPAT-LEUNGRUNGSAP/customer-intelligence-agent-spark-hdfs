"""Optional resumable parallel cache from Apache's official archive only."""
import concurrent.futures
import hashlib
import re
from pathlib import Path
from urllib.request import Request, urlopen

VERSION = '3.4.1'
URL = f'https://archive.apache.org/dist/hadoop/common/hadoop-{VERSION}/hadoop-{VERSION}.tar.gz'
ROOT = Path(__file__).resolve().parents[1] / 'infra/hadoop/cache'


def fetch_part(bounds):
    start, end = bounds
    target = ROOT / f'part-{start}-{end}'
    if target.exists() and target.stat().st_size == end-start+1:
        return target
    request = Request(URL, headers={'Range':f'bytes={start}-{end}'})
    with urlopen(request, timeout=120) as response:
        if response.status != 206 or not response.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/'):
            raise ValueError('Server did not honor the byte range')
        with target.with_suffix('.partial').open('wb') as out:
            while chunk := response.read(1024*1024):
                out.write(chunk)
    if target.with_suffix('.partial').stat().st_size != end-start+1:
        raise ValueError('Truncated range download')
    target.with_suffix('.partial').replace(target)
    print(f'Cached bytes {start}-{end}',flush=True)
    return target


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    with urlopen(URL+'.sha512',timeout=60) as response:
        checksum = response.read().decode()
    expected = re.search(r'(?i)\b[0-9a-f]{128}\b',checksum).group().lower()
    with urlopen(Request(URL,headers={'Range':'bytes=0-0'}),timeout=60) as response:
        total = int(response.headers['Content-Range'].split('/')[-1])
    size = 32*1024*1024
    bounds = [(start,min(start+size,total)-1) for start in range(0,total,size)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        paths = list(pool.map(fetch_part,bounds))
    digest = hashlib.sha512()
    archive = ROOT / 'hadoop.tgz.partial'
    with archive.open('wb') as out:
        for path in paths:
            with path.open('rb') as source:
                while chunk := source.read(1024*1024):
                    digest.update(chunk)
                    out.write(chunk)
    if digest.hexdigest() != expected:
        raise ValueError('Apache SHA-512 mismatch; refusing cache publication')
    archive.replace(ROOT/'hadoop.tgz')
    (ROOT/'hadoop.sha512').write_text(checksum)
    print('Verified Apache archive SHA-512: '+expected,flush=True)


if __name__=='__main__':
    main()
