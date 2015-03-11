from lxml import etree, objectify
import mock
import nose.tools
import requests

from pyvcd import errors
from pyvcd.client import VCloudClient
from pyvcd.edge_gateway import EdgeGatewayDriver


def edge_gateway_records():
    mock_record = objectify.Element('EdgeGatewayRecord')
    mock_record.attrib['name'] = 'test-name'
    mock_record.attrib['href'] = 'test-href'

    mock_records = objectify.Element('QueryResultRecords')
    mock_records.append(mock_record)

    return mock_records


def edge_gateway():
    mock_service_config = objectify.Element('EdgeGatewayServiceConfiguration')

    mock_config = objectify.Element('Configuration')
    mock_config.append(mock_service_config)

    mock_edge_gateway = objectify.Element('EdgeGateway')
    mock_edge_gateway.append(mock_config)

    return mock_edge_gateway


def get_mock_client(
        query_status=200, edge_gateway_status=200, task_status=200):
    mock_query_response = mock.create_autospec(requests.Response)
    mock_query_response.status_code = query_status
    mock_query_response.content = etree.tostring(edge_gateway_records())

    mock_edge_gateway_response = mock.create_autospec(requests.Response)
    mock_edge_gateway_response.status_code = edge_gateway_status
    mock_edge_gateway_response.content = etree.tostring(edge_gateway())

    mock_task = objectify.Element('Task')
    mock_task.attrib['href'] = 'test-task-href'

    mock_task_response = mock.create_autospec(requests.Response)
    mock_task_response.status_code = task_status
    mock_task_response.content = etree.tostring(mock_task)

    mock_client = mock.create_autospec(VCloudClient)
    mock_client.request.side_effect = [
        mock_query_response,
        mock_edge_gateway_response,
        mock_task_response,
    ]

    return mock_client


def test_init():
    mock_client = mock.create_autospec(VCloudClient)
    driver = EdgeGatewayDriver(mock_client, 'test-name')

    assert driver
    assert driver.name == 'test-name'
    assert driver.edge_gateway is None
    assert driver.config is None


def test_load():
    mock_client = get_mock_client()

    driver = EdgeGatewayDriver(mock_client, 'test-name')
    driver.load()

    assert driver.edge_gateway is not None
    assert driver.config is not None


def test_load_failure():
    mock_client = get_mock_client()

    driver = EdgeGatewayDriver(mock_client, 'test-name-fail')

    with nose.tools.assert_raises(errors.VCloudNotFoundError):
        driver.load()


def test_add_service():
    mock_client = get_mock_client()

    driver = EdgeGatewayDriver(mock_client, 'test-name')
    driver.load()
    service = driver.add_service('TestService')

    assert service is not None
    assert service.IsEnabled == 'true'
    assert hasattr(driver.config, 'TestService')


def test_add_firewall_rule():
    mock_client = get_mock_client()

    driver = EdgeGatewayDriver(mock_client, 'test-name')
    driver.load()

    # No existing rules.
    driver.add_firewall_rule('test-rule-one', 'TCP', 'any', 80, 'any')
    assert hasattr(driver.config, 'FirewallService')
    assert hasattr(driver.config.FirewallService, 'FirewallRule')

    # Existing rules.
    driver.add_firewall_rule('test-rule-two', 'TCP', 'any', 80, 'any')
    assert len(driver.config.FirewallService.FirewallRule) == 2


def test_add_firewall_rule_exists():
    mock_client = get_mock_client()

    driver = EdgeGatewayDriver(mock_client, 'test-name')
    driver.load()

    # Add rule.
    driver.add_firewall_rule('test-rule-one', 'TCP', 'any', 80, 'any')

    # Add rule again.
    with nose.tools.assert_raises(errors.VCloudResourceConflict):
        driver.add_firewall_rule('test-rule-one', 'TCP', 'any', 80, 'any')


def test_add_pool():
    mock_client = get_mock_client()

    driver = EdgeGatewayDriver(mock_client, 'test-name')
    driver.load()

    # No existing pools.
    mock_service_port = objectify.Element('ServicePort')
    mock_member = objectify.Element('Member')

    driver.add_pool('test-pool-one', [mock_service_port], [mock_member])
    assert hasattr(driver.config, 'LoadBalancerService')
    assert hasattr(driver.config.LoadBalancerService, 'Pool')

    # Existing rules.
    driver.add_pool('test-pool-two', [mock_service_port], [mock_member])
    assert len(driver.config.LoadBalancerService.Pool) == 2


def test_add_pool_exists():
    mock_client = get_mock_client()

    driver = EdgeGatewayDriver(mock_client, 'test-name')
    driver.load()

    mock_service_port = objectify.Element('ServicePort')
    mock_member = objectify.Element('Member')

    # Add pool.
    driver.add_pool('test-pool-one', [mock_service_port], [mock_member])

    # Add pool again.
    with nose.tools.assert_raises(errors.VCloudResourceConflict):
        driver.add_pool('test-pool-one', [mock_service_port], [mock_member])


@mock.patch(
    'pyvcd.edge_gateway.NetworkDriver.get_network_by_name', autospec=True)
def test_add_virtual_server(mock_get_network):
    mock_network = objectify.Element('NetworkRecord')
    mock_network.attrib['name'] = 'test-network'
    mock_network.attrib['href'] = 'test-network-href'
    mock_get_network.return_value = mock_network
    mock_client = get_mock_client()

    driver = EdgeGatewayDriver(mock_client, 'test-name')
    driver.load()

    # No existing virtual servers.
    mock_service_profile = objectify.Element('ServiceProfile')

    driver.add_virtual_server(
        'test-vs-one', '0.0.0.0', 'test-pool', 'test-network',
        [mock_service_profile])
    assert hasattr(driver.config, 'LoadBalancerService')
    assert hasattr(driver.config.LoadBalancerService, 'VirtualServer')

    # Existing virtual servers.
    driver.add_virtual_server(
        'test-vs-two', '0.0.0.1', 'test-pool', 'test-network',
        [mock_service_profile])
    assert len(driver.config.LoadBalancerService.VirtualServer) == 2


@mock.patch(
    'pyvcd.edge_gateway.NetworkDriver.get_network_by_name', autospec=True)
def test_add_virtal_server_exists(mock_get_network):
    mock_network = objectify.Element('NetworkRecord')
    mock_network.attrib['name'] = 'test-network'
    mock_network.attrib['href'] = 'test-network-href'
    mock_get_network.return_value = mock_network
    mock_client = get_mock_client()

    driver = EdgeGatewayDriver(mock_client, 'test-name')
    driver.load()

    mock_service_profile = objectify.Element('ServiceProfile')

    # Add virtual server.
    driver.add_virtual_server(
        'test-vs-one', '0.0.0.0', 'test-pool', 'test-network',
        [mock_service_profile])

    # Add virtual server again.
    with nose.tools.assert_raises(errors.VCloudResourceConflict):
        driver.add_virtual_server(
            'test-vs-one', '0.0.0.1', 'test-pool', 'test-network',
            [mock_service_profile])

    # Add virtual server with same IP.
    with nose.tools.assert_raises(errors.VCloudResourceConflict):
        driver.add_virtual_server(
            'test-vs-two', '0.0.0.0', 'test-pool', 'test-network',
            [mock_service_profile])


def test_commit():
    mock_client = get_mock_client()
    mock_client.wait_for_task.return_value = True

    driver = EdgeGatewayDriver(mock_client, 'test-name')
    driver.load()
    driver.commit()


def test_commit_failure():
    mock_client = get_mock_client(task_status=400)
    mock_client.wait_for_task.return_value = True

    driver = EdgeGatewayDriver(mock_client, 'test-name')
    driver.load()
    with nose.tools.assert_raises(errors.VCloudAPIError):
        driver.commit()
