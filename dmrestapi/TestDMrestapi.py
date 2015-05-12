#!/usr/bin/env
#
# Date: 5/2015
# Test Deploy Manager Rest API
#


import os
import ujson
from urlparse import urljoin
import logging
import requests


class TestDMrestapi:

    def setUp(self):
        self.url = "https://ave11.irvineqa.local:8543"
        self.headers = {"Accept" : "application/json", "Content-Type": "application/json"}
        self.vCenterPayload = ujson.dumps({"vcenter" : "winvcenter10.irvineqa.local", \
            "user" : "irvineqa\\avamarqa", \
            "password" : "changeme"})
        service = "deploymanager/auth/login"
        url = urljoin(self.url, service)
        response = requests.post(url, headers=self.headers, data=self.vCenterPayload, verify=False)
        assert response.status_code == 200
        self.response = response.content[1:-1]
        self.headers["X-CustomTicket"] = self.response


    def tearDown(self):
        
        service = "deploymanager/auth/logout"
        url = urljoin(self.url, service)
        response = requests.post(url, headers=self.headers, verify=False)
        logging.info(self.headers)
        assert response.status_code == 200

    def test_login(self):
        """
        This test actually executed by setUp
        """
        pass
    test_login.will_fail = False

    def test_logout(self):
        """
        This test actually executed by tearDown
        """
        pass
    test_logout.will_fail = False

    def test_list_proxy(self):
        service = "deploymanager/proxy"
        url = urljoin(self.url, service)
        response = requests.get(url, headers=self.headers, verify=False)
        assert response.status_code == 200
    test_list_proxy.will_fail = False

    def test_create_recommend(self):
        service = "deploymanager/recommend"
        url = urljoin(self.url, service)
        fn = os.path.join(os.path.dirname(__file__), "recommend_config.json")
        with open(fn) as f:
            payload = ujson.load(f)
        response = requests.post(url, headers=self.headers, data=ujson.dumps(payload), verify=False)
        assert response.status_code == 202
    test_create_recommend.will_fail = True
