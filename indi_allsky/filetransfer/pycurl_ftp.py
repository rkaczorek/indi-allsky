from .generic import GenericFileTransfer
from .exceptions import AuthenticationFailure
from .exceptions import ConnectionFailure
#from .exceptions import PermissionFailure

from pathlib import Path
import pycurl
import io
import time
import logging

logger = logging.getLogger('indi_allsky')


class pycurl_ftp(GenericFileTransfer):
    def __init__(self, *args, **kwargs):
        super(pycurl_ftp, self).__init__(*args, **kwargs)

        self._port = 21
        self.url = None


    def connect(self, *args, **kwargs):
        super(pycurl_ftp, self).connect(*args, **kwargs)

        ### The full connect and transfer happens under the put() function
        ### The curl instance is just setup here

        hostname = kwargs['hostname']
        username = kwargs['username']
        password = kwargs['password']

        self.url = 'ftp://{0:s}:{1:d}'.format(hostname, self._port)

        client = pycurl.Curl()
        #client.setopt(pycurl.VERBOSE, 1)
        client.setopt(pycurl.CONNECTTIMEOUT, int(self._timeout))

        client.setopt(pycurl.USERPWD, '{0:s}:{1:s}'.format(username, password))

        return client


    def close(self):
        super(pycurl_ftp, self).close()

        if self.client:
            self.client.close()


    def put(self, *args, **kwargs):
        super(pycurl_ftp, self).put(*args, **kwargs)

        local_file = kwargs['local_file']
        remote_file = kwargs['remote_file']

        local_file_p = Path(local_file)
        remote_file_p = Path(remote_file)

        pre_commands = [
            'SITE CHMOD 755 {0:s}'.format(str(remote_file_p.parent)),
        ]

        post_commands = [
            'SITE CHMOD 644 {0:s}'.format(str(remote_file_p)),
        ]

        url = '{0:s}/{1:s}'.format(self.url, str(remote_file_p))
        logger.info('pycurl URL: %s', url)


        start = time.time()
        f_localfile = io.open(str(local_file_p), 'rb')

        self.client.setopt(pycurl.URL, url)
        self.client.setopt(pycurl.FTP_CREATE_MISSING_DIRS, 1)
        self.client.setopt(pycurl.PREQUOTE, pre_commands)
        self.client.setopt(pycurl.POSTQUOTE, post_commands)
        self.client.setopt(pycurl.UPLOAD, 1)
        self.client.setopt(pycurl.READDATA, f_localfile)
        self.client.setopt(
            pycurl.INFILESIZE_LARGE,
            local_file_p.stat().st_size,
        )

        try:
            self.client.perform()
        except pycurl.error as e:
            rc, msg = e.args

            if rc in [pycurl.E_LOGIN_DENIED]:
                raise AuthenticationFailure(msg) from e
            elif rc in [pycurl.E_COULDNT_RESOLVE_HOST]:
                raise ConnectionFailure(msg) from e
            elif rc in [pycurl.E_COULDNT_CONNECT]:
                raise ConnectionFailure(msg) from e
            elif rc in [pycurl.E_OPERATION_TIMEDOUT]:
                raise ConnectionFailure(msg) from e
            else:
                raise e from e


        f_localfile.close()

        upload_elapsed_s = time.time() - start
        local_file_size = local_file_p.stat().st_size
        logger.info('File transferred in %0.4f s (%0.2f kB/s)', upload_elapsed_s, local_file_size / upload_elapsed_s / 1024)


# alias
class ftp(pycurl_ftp):
    pass

