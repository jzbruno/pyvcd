from lxml import objectify

import errors


class NetworkDriver(object):
    """
    Use the NetworkDriver to query information about VCD networks.
    Requires a VCloudClient object that has already been authenticated.
    """
    def __init__(self, client):
        self._client = client

    def get_networks(self):
        """
        Return a list of networks as lxml ObjectifiedElement objects.

        :return: List of networks represented as ObjectifiedElement objects.
        """
        networks = []

        # Get org networks.
        response = self._client.request(
            'GET', self._client.url('query?type=orgNetwork'))
        records = objectify.fromstring(response.content)

        for record in records.OrgNetworkRecord:
            networks.append(record)

        # Get external network.
        response = self._client.request(
            'GET', self._client.url('query?type=externalNetwork'))
        records = objectify.fromstring(response.content)

        for record in records.NetworkRecord:
            networks.append(record)

        return networks

    def get_network_by_name(self, name):
        """
        Return the network as an lxml ObjectifiedElement object for the name
        specified.

        :param name: Network name.
        :return: Network represented as an ObjectifiedElement.
        """
        networks = self.get_networks()

        for network in networks:
            if network.get('name') == name:
                return network
        else:
            raise errors.VCloudNotFoundError('No network found.', name)
