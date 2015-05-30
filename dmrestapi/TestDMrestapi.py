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

    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)

    def write_file(self, msg):
        fn = os.path.join(os.path.dirname(__file__), "deleteme.txt")
        with open(fn, 'w') as f:
            f.write(msg)

    def setUp(self):
        fn = os.path.join(os.path.dirname(__file__), "login_config.json")
        with open(fn) as f:
            # convert Json file to dictionary
            self.login_config = ujson.load(f)

        self.url = self.login_config[0]["dm_server"]["server"]
        service = self.login_config[1]["service"]
        self.headers = self.login_config[2]["headers"]
        self.vCenterPayload = self.login_config[3]["vCenter"]        
        
        url = urljoin(self.url, service)
        logging.info(url)
        logging.info(self.headers)
        response = requests.post(url, headers=self.headers, data=ujson.dumps(self.vCenterPayload), verify=False)
        self.response = response.content[1:-1]
        self.headers["X-CustomTicket"] = self.response
        assert response.status_code == 200            

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
        """
        TEST LIST DEPLOYED PROXY. DONE
        """
        service = "deploymanager/proxy"
        url = urljoin(self.url, service)
        response = requests.get(url, headers=self.headers, verify=False)
        assert response.status_code == 200
        self.list_proxy = ujson.loads(response.content)
    test_list_proxy.will_fail = False

    def test_create_recommend(self):
        """
        TEST CREATE RECOMMEND. DONE.
        return headers with 'Location' key point to task link
        """
        service = "deploymanager/recommend"
        url = urljoin(self.url, service)
        fn = os.path.join(os.path.dirname(__file__), "recommend_config.json")
        with open(fn) as f:
            payload = ujson.load(f)
        response = requests.post(url, headers=self.headers, data=ujson.dumps(payload), verify=False)
        
        self.task_link = response.headers['Location']

        logging.info("PROFESSIONAL")
        logging.info(self.task_link)
        assert response.status_code == 202
    test_create_recommend.will_fail = False

    def test_get_recommendation(self):
        """
        TEST GET RECOMMENDATION.
        DONE.
        """
        self.test_create_recommend()
        url = self.task_link

        state = ""
        while(state != "success"):
            response = requests.get(url, headers=self.headers, verify=False)
            res_dict = ujson.loads(response.content)
            state = res_dict['state']
     
        self.recommendationId = res_dict['result']['recommendationId']
        logging.info(self.recommendationId)
        assert response.status_code == 200
    test_get_recommendation.will_fail = False

    def test_get_specific_recommend(self):
        self.test_get_recommendation()
        service = "{}/{}".format("deploymanager/recommend", self.recommendationId)
        url = urljoin(self.url, service)
        response = requests.get(url, headers=self.headers, verify=False)
        res_dict = ujson.loads(response.content)
        self.write_file(response.content)
        # logging.info(response.content)
    test_get_specific_recommend.will_faile = False


    def test_proxy_health(self):
        """
        TEST GET PROXY HEALTH. DONE.
        """
        self.test_list_proxy()
        for proxy in self.list_proxy:
            service = "{}/{}/{}".format("deploymanager/proxy", proxy["instanceUUID"], "health")
            url = urljoin(self.url, service)
            response = requests.get(url, headers=self.headers, verify=False)
            assert response.status_code == 200
    test_proxy_health.will_fail = False

    def test_deploy_proxy(self):
        """
        TEST DEPLOY PROXY. DONE
        deploy proxy based on json file
        """
        service = "deploymanager/proxy"
        url = urljoin(self.url, service)
        fn = os.path.join(os.path.dirname(__file__), "proxy", "proxy53-linuxvcenter3.json")
        with open(fn) as f:
            payload = ujson.load(f)
        # logging.info(payload)
        response = requests.post(url, headers=self.headers, data=ujson.dumps(payload), verify=False)
        assert response.status_code == 202
    test_deploy_proxy.will_fail = True

    def test_delete_proxy(self):
        """
        TEST DELETE PROXY. DONE.
        """
        self.test_list_proxy()
        for proxy in self.list_proxy:
            if "proxy4" in proxy["name"]:
                service = "{}/{}".format("deploymanager/proxy", proxy["instanceUUID"])
                url = urljoin(self.url, service)
                response = requests.delete(url, headers=self.headers, verify=False)
                assert response.status_code == 202
    test_delete_proxy.will_fail = False    

    def test_change_password_proxy(self):
        """
        TEST CHANGE PASSWORD PROXY 
        """        
        self.test_list_proxy()
        for proxy in self.list_proxy:
            if "proxy53" in proxy["name"]:
                service = "{}/{}/{}".format("deploymanager/proxy", proxy["instanceUUID"], "/password")
                logging.info(service)
                url = urljoin(self.url, service)
                fn = os.path.join(os.path.dirname(__file__), "proxy_password.json")
                with open(fn) as f:
                    payload = ujson.load(f)
                response = requests.put(url, headers=self.headers, data=ujson.dumps(payload), verify=False)
    test_change_password_proxy.will_fail = False


def main():
    testDMobj = TestDMrestapi()
    print("test log on ")
    testDMobj.setUp()
    print("test create recommend")
    testDMobj.test_get_specific_recommend()
    print("test log out")
    testDMobj.tearDown()

if __name__ == "__main__":
    main()