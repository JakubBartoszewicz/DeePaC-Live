import getpass
import os
import sys
import traceback
import paramiko
import re


def sftp_push(user_hostname, files, key=None, port=22):
    rsa_key = None
    if key is not None:
        rsa_key = paramiko.RSAKey.from_private_key_file(key)

    username = ""
    hostname = user_hostname
    # get hostname
    if user_hostname.find("@") >= 0:
        username, hostname = user_hostname.split("@")

    if len(hostname) == 0:
        print("*** Hostname required.")
        sys.exit(1)

    path = ""
    if hostname.find(":") >= 0:
        hostname, path = hostname.split(":")

    # get username
    if username == "":
        default_username = getpass.getuser()
        username = default_username
    path = re.sub("^~", "/home/{}".format(username), path)

    # get host key, if we know one
    hostkey = None
    try:
        host_keys = paramiko.util.load_host_keys(
            os.path.expanduser("~/.ssh/known_hosts")
        )
    except IOError:
        try:
            # try ~/ssh/ too, because windows can't have a folder named ~/.ssh/
            host_keys = paramiko.util.load_host_keys(
                os.path.expanduser("~/ssh/known_hosts")
            )
        except IOError:
            print("*** Unable to open host keys file")
            host_keys = {}

    if hostname in host_keys:
        hostkeytype = host_keys[hostname].keys()[0]
        hostkey = host_keys[hostname][hostkeytype]
        print("Using host key of type %s" % hostkeytype)

    # now, connect and use paramiko Transport to negotiate SSH2 across the connection
    try:
        t = paramiko.Transport((hostname, port))
        t.connect(
            hostkey=hostkey,
            username=username,
            pkey=rsa_key
        )
        sftp = paramiko.SFTPClient.from_transport(t)

        try:
            sftp.chdir(path)  # Test if remote_path exists
        except IOError:
            sftp.mkdir(path)  # Create remote_path
            sftp.chdir(path)
        for file in files:
            remotepath = "./{}".format(os.path.basename(file))
            sftp.put(file, remotepath)

        t.close()

    except Exception as e:
        print(str(e))
        try:
            t.close()
        except Exception as et:
            print(str(et))
            pass
        sys.exit(1)
