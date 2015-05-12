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
        # logging.info(self.headers)
        if self.response.status_code == 200:
            self.headers["X-CustomTicket"] = self.response.content[1:-1]
            # logging.info(self.response.text)
        return self.response

def test_logout():
    """
    Test logout DM rest api this also test login
    """
    dmsession = DMsession()
    response = dmsession.login()
    assert response.status_code == 200

    logout_service = "deploymanager/auth/logout"
    url = urljoin(dmsession.url, logout_service)

    response = requests.post(url, \
        headers=dmsession.headers, verify=False)
    logging.info(dmsession.headers)
    assert response.status_code == 200

def test_list_proxy():
    dmsession = DMsession()
    response = dmsession.login()
    assert response.status_code == 200

    list_proxy_service = "deploymanager/proxy"
    url = urljoin(dmsession.url, list_proxy_service)

    # logging.info(dmsession.headers)
    # logging.info(url)

    response = requests.get(url, \
        headers=dmsession.headers, verify=False)

    
    # logging.info(dmsession.headers)
    # logging.info(response.content)

    assert response.status_code == 200
    return response.content


def test_create_recommend():
    dmsession = DMsession()
    response = dmsession.login()
    assert response.status_code == 200

    fn = os.path.join(os.path.dirname(__file__), "recommend_config.json")
    with open(fn) as f:
        recommend_config = ujson.load(f)

    create_recommend_service = "deploymanager/recommend"
    url = urljoin(dmsession.url, create_recommend_service)
    response = requests.post(url, \
        headers=dmsession.headers, data=ujson.dumps(recommend_config), verify=False)    
    logging.info(recommend_config)
    assert response.status_code == 202

def test_delete_proxy():
    dmsession = DMsession()
    response = dmsession.login()
    assert response.status_code == 200 
    # ujson.loads load string json and change into python
    # ujson.dumps load python and serialize to json
    #
    list_proxy = ujson.loads(test_list_proxy())
    for proxy in list_proxy:
        if 'proxy4' in proxy['name']:
            delete_service = "{}/{}".format("deploymanager/proxy", proxy['instanceUUID'])

            logging.info(delete_service)
            url = urljoin(dmsession.url, delete_service)
            response = requests.delete(url, headers=dmsession.headers, verify=False)
            assert response.status_code == 202


def main():

    # test_logout()
    # test_list_proxy()
    # test_create_recommend()

    test_delete_proxy()


if __name__ == "__main__":
    main()