from lxml import etree, objectify
import mock
import nose.tools
import requests

from pyvcd import errors
from pyvcd.client import VCloudClient
from pyvcd.network import NetworkDriver


def networks():
    org_network = objectify.Element('OrgNetworkRecord')
    org_network.attrib['name'] = 'test-org-network'

    external_network = objectify.Element('NetworkRecord')
    external_network.attrib['name'] = 'test-external-network'

    return [
        org_network,
        external_network,
    ]


def org_networks():
    results = objectify.Element('QueryResultRecords')
    results.append(networks()[0])
    return etree.tostring(results)


def external_networks():
    results = objectify.Element('QueryResultRecords')
    results.append(networks()[1])
    return etree.tostring(results)


def test_init():
    mock_client = mock.create_autospec(VCloudClient)
    driver = NetworkDriver(mock_client)

    assert driver
    assert driver._client


def test_get_networks():
    mock_org_response = mock.create_autospec(requests.Response)
    mock_org_response.status_code = 200
    mock_org_response.content = org_networks()

    mock_external_response = mock.create_autospec(requests.Response)
    mock_external_response.status_code = 200
    mock_external_response.content = external_networks()

    mock_client = mock.create_autospec(VCloudClient)
    mock_client.request.side_effect = [
        mock_org_response,
        mock_external_response,
    ]

    driver = NetworkDriver(mock_client)
    assert driver.get_networks()


@mock.patch('pyvcd.network.NetworkDriver.get_networks', autospec=True)
def test_get_network_by_name(mock_get_networks):
    mock_get_networks.return_value = networks()
    mock_client = mock.create_autospec(VCloudClient)

    driver = NetworkDriver(mock_client)
    name = 'test-org-network'
    network = driver.get_network_by_name(name)

    assert network.get('name') == name


@mock.patch('pyvcd.network.NetworkDriver.get_networks', autospec=True)
def test_get_network_by_name_failure(mock_get_networks):
    mock_get_networks.return_value = []
    mock_client = mock.create_autospec(VCloudClient)

    driver = NetworkDriver(mock_client)

    with nose.tools.assert_raises(errors.VCloudNotFoundError):
        driver.get_network_by_name('test-network')
