#!/usr/bin/env python3

import json
import os
import socket
import argparse


def proxyssl_decrypt(secret_txt):
    proxyssl_filename = "/var/run/proxyssl/pssl.sockrest"

    if not os.path.exists(proxyssl_filename):
        raise Exception("Error, unix domain socket target file not exist. target={}".format(proxyssl_filename))

    message = "POST /api/v1/configs HTTP/1.1\r\n"
    message += "Host: host\r\n"
    message += "Content-Type: text/plain; charset=utf-8\r\n"
    message += "Content-Length: %d\r\n\r\n" % (len(secret_txt) + 2)
    message += (secret_txt + "\r\n")

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(proxyssl_filename)
        sock.sendall(message.encode())
        res = sock.recv(4096).decode()
        vs = res.split()
        if vs[0] == 'HTTP/1.1' and vs[1] == '200' and vs[2] == 'OK':
            return vs[-1]
        else:
            raise Exception("invalid response. {}".format(vs))
    except socket.error as e:
        raise e
    finally:
        sock.close()


def proxyssl_decrypt_with_retry(secret_txt, retry_times=3):
    for i in range(retry_times):
        try:
            return proxyssl_decrypt(secret_txt)
        except socket.error as e:
            pass
        except Exception as e:
            raise e
    raise e


def proxyssl_decrypt_file(filename, retry_times=3):
    kvs = {}
    with open(filename) as fp:
        obj = json.loads(fp.read())
        for k, v in obj.items():
            kvs[k] = proxyssl_decrypt_with_retry(v, retry_times=retry_times)
    return kvs


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200), description="""example:
  python3 proxyssl.py
  python3 proxyssl.py --retry-times 3
  python3 proxyssl.py --file "/encryptfile/config/config_encrypt.json"
  python3 proxyssl.py --text "҂gSRmYTAxMzA4ZC00YzVhLTRkODktYWFhMC1jY2EzZjdhOTczOGSNDHUYwJV+1it7w9gwoCr0jPIGLILRzmOSTxQdgRAni4gw/Bt3ULPHL5Mo҂"
""")
    parser.add_argument("--text", help="secret text")
    parser.add_argument("--file", default="/encryptfile/config/config_encrypt.json", help="secret file")
    parser.add_argument("--retry-times", default=3, help="retry times on failed")
    args = parser.parse_args()

    if args.text:
        print(proxyssl_decrypt_with_retry(args.text, args.retry_times))
    else:
        print(json.dumps(proxyssl_decrypt_file(args.file, args.retry_times)))


if __name__ == '__main__':
    main()
