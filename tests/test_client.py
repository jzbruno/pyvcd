from lxml import etree, objectify
import mock
import nose.tools
import requests

from pyvcd import errors
from pyvcd.client import VCloudClient


HOST = 'test-host'
VERSION = '5.1'
ORG = 'test-org'


def test_init():
    client = VCloudClient(HOST, VERSION, ORG)

    assert client
    assert client.host == HOST
    assert client.version == VERSION
    assert client.org == ORG
    assert client.default_headers
    assert not client.auth_token


@mock.patch('requests.request', autospec=True)
def test_request_no_auth_token(mock_request):
    client = VCloudClient(HOST, VERSION, ORG)
    with nose.tools.assert_raises(errors.VCloudAuthError):
        client.request('test-method', 'test-url')


@mock.patch('requests.request', autospec=True)
def test_request(mock_request):
    mock_response = mock.create_autospec(requests.Response)
    mock_response.status_code = 200
    mock_request.return_value = mock_response

    client = VCloudClient(HOST, VERSION, ORG)
    client.auth_token = 'test-token'
    assert client.request(
        'test-method', 'test-url', headers={'test-header': 'test'})


@mock.patch('requests.request', autospec=True)
def test_request_failure(mock_request):
    mock_response = mock.create_autospec(requests.Response)
    mock_response.status_code = 400
    mock_request.return_value = mock_response

    client = VCloudClient(HOST, VERSION, ORG)
    client.auth_token = 'test-token'

    with nose.tools.assert_raises(errors.VCloudAPIError):
        client.request('test-method', 'test-url')


def test_url():
    client = VCloudClient(HOST, VERSION, ORG)
    path = 'test-path'
    assert client.url(path) == 'https://{}/api/{}'.format(HOST, path)


@mock.patch('requests.request', autospec=True)
def test_authenticate(mock_request):
    mock_response = mock.create_autospec(requests.Response)
    mock_response.status_code = 200
    mock_response.headers = {
        'x-vcloud-authorization': 'test-token'
    }
    mock_request.return_value = mock_response

    client = VCloudClient(HOST, VERSION, ORG)
    client.authenticate('test-user', 'test-pass')

    assert client.auth_token == 'test-token'


@mock.patch('requests.request', autospec=True)
def test_authenticate_failure(mock_request):
    mock_response = mock.create_autospec(requests.Response)
    mock_response.status_code = 400
    mock_request.return_value = mock_response

    client = VCloudClient(HOST, VERSION, ORG)

    with nose.tools.assert_raises(errors.VCloudAuthError):
        client.authenticate('test-user', 'test-pass')


@mock.patch('requests.request', autospec=True)
def test_wait_for_task_timeout(mock_request):
    mock_task = objectify.Element('Task')
    mock_task.attrib['operation'] = 'test-operation'
    mock_task.attrib['status'] = 'running'

    mock_response = mock.create_autospec(requests.Response)
    mock_response.status_code = 200
    mock_response.content = etree.tostring(mock_task)
    mock_request.return_value = mock_response

    client = VCloudClient(HOST, VERSION, ORG)
    client.auth_token = 'test-token'

    with nose.tools.assert_raises(errors.VCloudTimeoutError):
        client.wait_for_task('test-task-url', 2, 0)


@mock.patch('requests.request', autospec=True)
def test_wait_for_task_success(mock_request):
    mock_task = objectify.Element('Task')
    mock_task.attrib['operation'] = 'test-operation'
    mock_task.attrib['status'] = 'success'

    mock_response = mock.create_autospec(requests.Response)
    mock_response.status_code = 200
    mock_response.content = etree.tostring(mock_task)
    mock_request.return_value = mock_response

    client = VCloudClient(HOST, VERSION, ORG)
    client.auth_token = 'test-token'

    assert not client.wait_for_task('test-task-url', 2, 0)


@mock.patch('requests.request', autospec=True)
def test_wait_for_task_failure(mock_request):
    mock_task = objectify.Element('Task')
    mock_task.attrib['operation'] = 'test-operation'
    mock_task.attrib['status'] = 'pending'

    mock_response = mock.create_autospec(requests.Response)
    mock_response.status_code = 200
    mock_response.content = etree.tostring(mock_task)
    mock_request.return_value = mock_response

    client = VCloudClient(HOST, VERSION, ORG)
    client.auth_token = 'test-token'

    with nose.tools.assert_raises(errors.VCloudAPIError):
        client.wait_for_task('test-task-url', 2, 0)
