#!/usr/bin/env python3

import argparse
import os

import requests
import re
from urllib.parse import urljoin
from PIL import Image

REQUEST = """
<?xml version="1.0" encoding="UTF-8"?>
<ScanSettings xmlns="http://www.hp.com/schemas/imaging/con/cnx/scan/2008/08/19">
   <XResolution>{dpi}</XResolution>
   <YResolution>{dpi}</YResolution>
   <XStart>0</XStart>
   <Width>{width}</Width>
   <YStart>0</YStart>
   <Height>{height}</Height>
   <Format>Raw</Format>
   <CompressionQFactor>0</CompressionQFactor>
   <ColorSpace>Color</ColorSpace>
   <BitDepth>8</BitDepth>
   <InputSource>Platen</InputSource>
   <InputSourceType>Platen</InputSourceType>
   <GrayRendering>NTSC</GrayRendering>
   <ToneMap>
      <Gamma>0</Gamma>
      <Brightness>1000</Brightness>
      <Contrast>1000</Contrast>
      <Highlite>0</Highlite>
      <Shadow>0</Shadow>
   </ToneMap>
   <ContentType>Photo</ContentType>
</ScanSettings>
""".strip()


SIZES = {
    'a4': '2480x3508',
    'a5': '1748x2480',
    'a6': '1240x1748'
}


def main(args):
    http = requests.Session()
    base_url = 'http://192.168.1.34:8080'

    size = args.size
    if size in SIZES:
        size = SIZES[size]

    width, height = [int(x) for x in size.split('x')]

    if args.landscape and height > width:
        width, height = height, width

    print("Issuing scan command...")
    resp = http.post(
        urljoin(base_url, '/Scan/Jobs'),
        data=REQUEST.format(
            dpi=args.dpi,
            width=width,
            height=height,
        ),
        headers={'Content-Type': 'application/xml'},
    )
    resp.raise_for_status()

    print("Downloading metadata...")
    metadata_url = urljoin(base_url, resp.headers['Location'])
    resp = http.get(metadata_url)
    resp.raise_for_status()

    metadata = str(resp.content)
    binary_url = re.search('<BinaryURL>(.*)</BinaryURL>', metadata).group(1)
    image_width = int(re.search('<ImageWidth>(.*)</ImageWidth>', metadata).group(1))
    image_height = int(re.search('<ImageHeight>(.*)</ImageHeight>', metadata).group(1))

    print("Downloading image...")
    resp = http.get(urljoin(base_url, binary_url))
    resp.raise_for_status()

    out = args.out
    i = 0
    while os.path.exists(out):
        i += 1
        filename, extension = args.out.rsplit('.', 1)
        out = f'{filename}{i}.{extension}'

    print(f"Saving image to {out}...")
    image = Image.frombytes('RGB', (image_width, image_height), resp.content, 'raw')
    image.save(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-d', '--dpi', default='300', help='scan DPI [%(default)s]')
    ap.add_argument('-o', '--out', default='scan.png', help='output file name [%(default)s]')
    ap.add_argument('-s', '--size', default='2550x3508', help='size in WxH or ISO size [%(default)s]')
    ap.add_argument('-l', '--landscape', action='store_true', help='scan in landscape')
    main(ap.parse_args())
