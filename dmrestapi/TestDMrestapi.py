#!/usr/bin/env
#
# Date: 5/2015
# Test Deploy Manager Rest API
# How to run : nosetests -v -a will_fail dmrestapi/TestDMrestapi.py


import os
import ujson
from urlparse import urljoin
import logging
import requests


class TestDMrestapi:

    def setUp(self):
        fn = os.path.join(os.path.dirname(__file__), "login_config.json")
        with open(fn) as f:
            self.login_config = ujson.load(f)
        # self.url = "https://a4ipn452d1.asl.lab.emc.com:8543"
        # self.headers = {"Accept" : "application/json", "Content-Type": "application/json"}
        # self.vCenterPayload = ujson.dumps({"vcenter" : "winvcenter3.irvineqa.local", \
        #     "user" : "irvineqa\\avamarqa", \
        #     "password" : "changeme"})
        # service = "deploymanager/auth/login

        self.url = self.login_config[0]["dm_server"]["server"]
        service = self.login_config[1]["service"]
        self.headers = self.login_config[2]["headers"]
        self.vCenterPayload = self.login_config[3]["vCenter"]        
        
        url = urljoin(self.url, service)
        logging.info(url)
        logging.info(self.headers)
        response = requests.post(url, headers=self.headers, data=ujson.dumps(self.vCenterPayload), verify=False)
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
        self.list_proxy = ujson.loads(response.content)
    test_list_proxy.will_fail = False

    def test_create_recommend(self):
        service = "deploymanager/recommend"
        url = urljoin(self.url, service)
        fn = os.path.join(os.path.dirname(__file__), "recommend_config.json")
        with open(fn) as f:
            payload = ujson.load(f)
        response = requests.post(url, headers=self.headers, data=ujson.dumps(payload), verify=False)
        assert response.status_code == 202
        # self.recommendId = response.content["recommend"]
    test_create_recommend.will_fail = True

    def test_proxy_health(self):
        self.test_list_proxy()
        for proxy in self.list_proxy:
            service = "{}/{}/{}".format("deploymanager/proxy", proxy["instanceUUID"], "health")
            url = urljoin(self.url, service)
            response = requests.get(url, headers=self.headers, verify=False)
            assert response.status_code == 200
    test_proxy_health.will_fail = False

    def test_deploy_proxy(self):
        """
        deploy proxy based on json file
        """
        service = "deploymanager/proxy"
        url = urljoin(self.url, service)
        fn = os.path.join(os.path.dirname(__file__), "proxy", "proxy4-winvcenter3.json")
        with open(fn) as f:
            payload = ujson.load(f)
        # logging.info(payload)
        response = requests.post(url, headers=self.headers, data=ujson.dumps(payload), verify=False)
        assert response.status_code == 202
    test_deploy_proxy.will_fail = False

    def test_delete_proxy(self):
        self.test_list_proxy()
        for proxy in self.list_proxy:
            if "proxy4" in proxy["name"]:
                service = "{}/{}".format("deploymanager/proxy", proxy["instanceUUID"])
                url = urljoin(self.url, service)
                response = requests.delete(url, headers=self.headers, verify=False)
                assert response.status_code == 202
    test_delete_proxy.will_fail = False            
