import re

from lxml import etree, objectify

import errors
from network import NetworkDriver


class EdgeGatewayDriver(object):
    """
    Use the EdgeGatewayDriver to build and commit configuration updates.
    Requires a VCloudClient object that has already been authenticated.
    """
    def __init__(self, client, name):
        self._client = client
        self.name = name
        self.edge_gateway = None
        self.config = None

    def load(self):
        """
        Load the current edge gateway. Call this method before adding
        service configuration.
        """
        response = self._client.request(
            'GET', self._client.url('query?type=edgeGateway'))
        records = objectify.fromstring(response.content)

        for record in records.EdgeGatewayRecord:
            if record.get('name') == self.name:
                url = record.get('href')
                break
        else:
            raise errors.VCloudNotFoundError(
                'Edge gateway not found.', self.name)

        response = self._client.request('GET', url)

        self.edge_gateway = objectify.fromstring(response.content)
        self.config = \
            self.edge_gateway.Configuration.EdgeGatewayServiceConfiguration

    def add_service(self, service_name):
        """
        Add and return an lxml ObjectifiedElement representing the specified
        edge gateway service. If the service exists, return it.

        :param service_name: Name of the edge gateway service.
        :return: Edge gateway service as an ObjectifiedElement.
        """
        try:
            return self.config[service_name]
        except AttributeError:
            pass

        service = objectify.Element(service_name)
        service.IsEnabled = 'true'

        self.config.append(service)

        return self.config[service_name]

    def add_firewall_rule(
            self, name, protocol,
            src_ip_range, dest_port_range, dest_ip_range,
            src_port=-1, src_port_range='Any', dest_port=None, policy='allow'):
        """
        Add a firewall rule to the current edge gateway firewall service. Adds
        the firewall service to the edge gateway if it doesn't exist.

        This only stages the update. Call the commit method to perform
        the update.

        WARNING: The order of elements added to a firewall rule matters for the
        VCD API!

        :param name: Name of the firewall rule.
        :param protocol: Protocol of the firewall rule.
        :param src_ip_range: Source ip or ip range.
        :param dest_port_range: Destination port or port range.
        :param dest_ip_range: Destination ip or ip range.
        :param src_port: Source port or port range. Default -1 (Any).
        :param src_port_range: Source port or port range. Default 'Any'.
        :param dest_port: Destination port or port range. Default None, sets
        dest_port equal to dest_port_range.
        :param policy: Rule policy, one of 'Allow' or 'Deny'. Default 'Allow'.
        """
        if not dest_port:
            dest_port = dest_port_range

        rule = objectify.Element('FirewallRule')
        rule.IsEnabled = 'true'
        rule.Description = name
        rule.Policy = policy
        rule.Protocols = objectify.Element('Protocols')
        rule.Protocols[protocol.capitalize()] = 'true'
        rule.Port = dest_port
        rule.DestinationPortRange = dest_port_range
        rule.DestinationIp = dest_ip_range
        rule.SourcePort = src_port
        rule.SourcePortRange = src_port_range
        rule.SourceIp = src_ip_range
        rule.EnableLogging = 'true'

        # Get the firewall service, create it if it doesn't exist.
        firewall_service = self.add_service('FirewallService')

        if hasattr(firewall_service, 'FirewallRule'):
            for existing_rule in firewall_service.FirewallRule:
                if existing_rule.Description == name:
                    raise errors.VCloudResourceConflict(
                        'Firewall rule already exists.', name)

        firewall_service.append(rule)

    def add_pool(self, name, service_ports, members, description=''):
        """
        Add a pool to the current edge gateway load balancer service. Adds
        the load balancer service to the edge gateway if it doesn't exist.

        This only stages the update. Call the commit method to perform
        the update.

        WARNING: The order of elements added to a pool matters for the VCD API!

        :param name: Name of the pool.
        :param service_ports: List of lxml ObjectifiedElements representing the
        service ports.
        :param members: List of lxml ObjectifiedElements representing the
        members.
        """
        pool = objectify.Element('Pool')
        pool.Name = name
        pool.Description = description

        for service_port in service_ports:
            pool.append(service_port)

        for member in members:
            pool.append(member)

        # Get the load balancer service, create it if it doesn't exist.
        load_balancer_service = self.add_service('LoadBalancerService')

        if hasattr(load_balancer_service, 'Pool'):
            for existing_pool in load_balancer_service.Pool:
                if existing_pool.Name == name:
                    raise errors.VCloudResourceConflict(
                        'Pool already exists.', name)

        load_balancer_service.append(pool)

    def add_virtual_server(
            self, name, ip_address, pool_name, network_name, service_profiles,
            description=''):
        """
        Add a virtual server to the current edge gateway load balancer service.
        Adds the load balancer service to the edge gateway if it doesn't exist.

        This only stages the update. Call the commit method to perform
        the update.

        WARNING: The order of elements added to a virtual server matters for
        the VCD API!

        :param name: Virtual server name.
        :param ip_address: IP to associate with the virtual server.
        :param pool_name: Pool name to associate with the virtual server.
        :param network_name: Network name to associate with the virtual server.
        :param service_profiles: List of lxml ObjectifiedElements representing
        the service profiles.
        """
        virtual_server = objectify.Element('VirtualServer')
        virtual_server.IsEnabled = 'true'
        virtual_server.Name = name
        virtual_server.Description = description

        network_driver = NetworkDriver(self._client)
        network = network_driver.get_network_by_name(network_name)
        virtual_server.Interface = objectify.Element(
            'Interface',
            type='application/vnd.vmware.vcloud.orgVdcNetwork+xml',
            name=network_name,
            href=network.get('href'))

        virtual_server.IpAddress = ip_address

        for service_profile in service_profiles:
            virtual_server.append(service_profile)

        virtual_server.Logging = 'true'
        virtual_server.Pool = pool_name

        # Get the load balancer service, create it if it doesn't exist.
        load_balancer_service = self.add_service('LoadBalancerService')

        if hasattr(load_balancer_service, 'VirtualServer'):
            for existing_virtual_server in load_balancer_service.VirtualServer:
                if existing_virtual_server.Name == name:
                    raise errors.VCloudResourceConflict(
                        'Virtual server already exists.', name)
                if existing_virtual_server.IpAddress == ip_address:
                    raise errors.VCloudResourceConflict(
                        'IP is already in use by an existing virtual server.',
                        ip_address,
                        existing_virtual_server.Name)

        load_balancer_service.append(virtual_server)

    def commit(self):
        """
        Commit the current edge gateway service configuration. Call after
        calling one or more of the add_* methods.
        """
        data = self.to_xml()

        url = '{}/action/configureServices'.format(
            self.edge_gateway.get('href'))
        headers = {
            'Content-Type':
            'application/vnd.vmware.admin.edgeGatewayServiceConfiguration+xml'
        }
        response = self._client.request(
            'POST', url, data=data, headers=headers)

        if response.status_code < 400:
            task = objectify.fromstring(response.content)
            self._client.wait_for_task(task.get('href'))
        else:
            raise errors.VCloudAPIError(
                'Failure updating edge gateway.', response.content)

    def to_xml(self):
        """
        Return an xml string representation of the edge gateway configuration
        after cleaning up the namespaces.

        :return: String representation of the edge gateway configuration.
        """
        tree = self.config
        objectify.deannotate(self.config, xsi_nil=True)
        etree.cleanup_namespaces(self.config)
        xml = etree.tostring(tree, pretty_print=True)
        xml = re.sub(r'ns\d:', '', xml)
        xml = re.sub(r'\sxmlns:ns\d=".*"', '', xml)
        xml = re.sub(r'\sxmlns:xsi=".*"', '', xml)

        return xml
