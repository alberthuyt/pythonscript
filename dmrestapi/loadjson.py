#!/usr/bin/env python
import ujson
from urlparse import urljoin

with open("/Users/kevinnguyen/alberthuyt/pythonscript/dmrestapi/login_config.json") as f:
    jsonobj = ujson.load(f)
    print(urljoin(jsonobj[0]["dm_server"]["server"], jsonobj[0]["dm_server"]["port"]))