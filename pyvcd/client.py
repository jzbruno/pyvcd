from copy import copy
from time import sleep

from lxml import objectify
import requests

import errors


class VCloudClient(object):
    """
    Simple client for making requests to the VCD API.
    """
    def __init__(self, host, version, org):
        self.host = host
        self.version = version
        self.org = org
        self.default_headers = {
            'Accept': 'application/*+xml;version=' + version
        }
        self.auth_token = None

    def request(self, method, url, data=None, headers=None):
        """
        Return the response of a request to the VCD API at the given url.

        :param method: Request method.
        :param url: Request url.
        :param data: Request data payload.
        :param headers: Request headers. Auth headers are automatically added
        for the current client instance.
        :return: Response object.
        """
        if not self.auth_token:
            raise errors.VCloudAuthError(
                'Must call authenticate before making a request.')

        merged_headers = copy(self.default_headers)
        merged_headers['x-vcloud-authorization'] = self.auth_token
        if headers:
            merged_headers.update(headers)

        response = requests.request(
            method, url, headers=merged_headers, data=data)

        if response.status_code < 400:
            return response
        else:
            raise errors.VCloudAPIError(
                'VCloud API request failure.', url, response.content)

    def url(self, path):
        """
        Return the fully qualified url for a VCD API resource.

        :param path: Resource path.
        """
        return 'https://{}/api/{}'.format(self.host, path)

    def authenticate(self, username, password):
        """
        Authenticate the client to the VCD API server.

        :param username:
        :param password:
        """
        username = '{}@{}'.format(username, self.org)
        response = requests.request(
            'post',
            self.url('sessions'),
            headers=self.default_headers,
            auth=(username, password))

        if response.status_code < 400:
            self.auth_token = response.headers['x-vcloud-authorization']
        else:
            raise errors.VCloudAuthError(
                'Failure logging into vcloud.',
                response.status_code,
                response.content)

    def wait_for_task(self, task_url, retries=10, retry_delay=15):
        """
        Poll a VCD API task until it is complete.

        :param task_url: Url of the task.
        :param retries: Number of retry attempts.
        :param retry_delay: Delay between retry attempts in seconds.
        """
        for _ in xrange(retries):
            response = self.request('GET', task_url)
            if response.status_code < 400:
                task = objectify.fromstring(response.content)
                if task.get('status') == 'success':
                    return
                elif task.get('status') != 'running':
                    raise errors.VCloudAPIError(
                        'Task did not complete successfully.',
                        task_url,
                        task.get('operation'),
                        task.get('status'))

            sleep(retry_delay)
        else:
            raise errors.VCloudTimeoutError(
                'Timeout waiting for task to complete.')
