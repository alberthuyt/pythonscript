#!/usr/bin/env python
import os
import requests
from urlparse import urljoin
import logging
import ujson


class DMsession:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)

    def login(self):
        """
        Test login DM server
        """
        fn = os.path.join(os.path.dirname(__file__), 'login_config.json')
        with open(fn) as f:
            self.login_config = ujson.load(f)

        self.url = self.login_config[0]["dm_server"]["server"]
        self.login_service = self.login_config[1]["service"]
        self.headers = self.login_config[2]["headers"]
        self.payload = self.login_config[3]["vCenter"]

        self.response = requests.post(urljoin(self.url, self.login_service), \
            headers=self.headers, data=ujson.dumps(self.payload), verify=False)

        if self.response.status_code == 200:
            self.headers["X-CustomTicket"] = self.response.text
        return self.response

def test_logout():
    """
    Test logout DM rest api this also test login
    """
    dmsession = DMsession()
    response = dmsession.login()
    assert response.status_code == 200
    logout_service = "deploymanager/auth/logout"
    response = requests.post(urljoin(dmsession.url, logout_service), \
        headers=dmsession.headers, verify=False)
    assert response.status_code == 200

def main():

    test_logout()


if __name__ == "__main__":
    main()