import cherrypy
import glob
import os
import os.path
import json
import future
import re
import logging
import uuid
import random
import time
from cherrypy._cpdispatch import Dispatcher
from cherrypy.lib import static

class Repo:
    fakes = {}
    rootpath = ""
    def __init__(self, rootpath):
        self.rootpath = rootpath

    # Convert headers as string to dict
    def setHeaders(self, dict, headers):
        if headers is None:
            return None
        lines = headers.split("\n")
        for line in lines:
            parts = line.split(":")
            if (len(parts) > 1):
                dict[parts[0].strip()] = parts[1].strip()
        return dict

    def load(self):
        print(os.path.join(self.rootpath, '*.json'))
        for fname in glob.glob(os.path.join(self.rootpath, '*.json')):
            with open(fname) as f:
                tail = os.path.split(fname)[1]
                (id, ext) = os.path.splitext(tail)
                fake = json.load(f)
                self.fakes[id]=fake

    def search(self, path, httpmethod):
        for id, fake in self.fakes.items():
            if httpmethod == fake.get("httpMethod"):
                if fake.get("urlIsRegexp"):
                    if re.match(fake["url"], path):
                        return fake
                else:
                    if fake["url"] == path:
                        return fake
        return None

    def get(self, id):
        return self.fakes.get(id)

    def add(self, fake):
        id = str(uuid.uuid4())
        self.fakes[id] = fake
        fname = os.path.join(self.rootpath, id + ".json")
        with open(fname, 'w') as f:
            json.dump(fake, f)
        return id

    def update(self, id, fake):
        self.fakes[id] = fake
        fname = os.path.join(self.rootpath, id + ".json")
        with open(fname, 'w') as f:
            json.dump(fake, f)
        return id

    def delete(self, id):
        fname = os.path.join(self.rootpath, id + ".json")
        del self.fakes[id]
        os.remove(fname)

    def urls(self):
        urls = [{
            "id": id,
            "httpMethod": fake.get('httpMethod'),
            "url": fake["url"], "urlIsRegexp": fake.get("urlIsRegexp")} for id, fake in self.fakes.items()]
        return sorted(urls, key=lambda url: url["url"])

#@cherrypy.tools.json_out()
class Faker(object):
    def _cp_dispatch(self, vpath):
        return self

    @cherrypy.expose()
    #@cherrypy.tools.json_out()
    def index(self,**args):
        path = cherrypy.request.path_info.replace("$","/")
        if path.endswith('/'):
            path = path[:-1]
        url = path
        httpmethod = cherrypy.request.method
        if cherrypy.request.query_string:
            url = url + '?' + cherrypy.request.query_string
        print(url)
        fake = repo.search(url, httpmethod)
        if fake:
            latency = fake.get('latency')
            if latency:
                min = latency.get('min')
                max = latency.get('max', min)
                if min and max:
                    delay = random.uniform(min/1000, max/1000 )
                    time.sleep(delay)
            cherrypy.response.status = fake.get('httpStatusCode', 200)

            cherrypy.response.headers = repo.setHeaders(cherrypy.response.headers, fake.get('headers'))
            responsefilepath = fake.get('responsefilepath')
            if responsefilepath:
                filepath = responsefilepath
                # si on a un filepath et qu'on supporte les regexp, on remplace les champs de l'url
                if fake.get('urlIsRegexp'):
                    filepath = re.sub(fake['url'], filepath, url)
                filepath = os.getcwd() + "/" + filepath
                if os.path.exists(filepath):
                    return static.serve_file(filepath, content_type='application/json')
                else:
                    raise cherrypy.HTTPError(404, "No static file %s" % filepath)

            return json.dumps(fake['response'])
        else:
            raise cherrypy.HTTPError(404, "No mock for %s" % url)

class NoDispatcher(Dispatcher):
    def __call__(self, path_info):
        return Dispatcher.__call__(self, path_info.replace("/","$"))

@cherrypy.expose()
@cherrypy.tools.json_out()
@cherrypy.tools.json_in()
class Manager(object):
    def GET(self, id = None):
        if id == None:
            return repo.urls()
        else:
            return repo.get(id)

    def POST(self, id = None):
        if id:
            raise cherrypy.HTTPError(405, "Method POST not allowed on a mock ressource. Must be done on root element")
        else:
            json = cherrypy.request.json
            id = repo.add(json)
            cherrypy.response.headers['Location'] = cherrypy.request.base + cherrypy.request.script_name + cherrypy.request.path_info + id
            cherrypy.response.status = 201

    def PUT(self, id = None):
        if id == None:
            raise cherrypy.HTTPError(405, "Method PUT not allowed. Must be done on an existing mock element")
        else:
            json = cherrypy.request.json
            id = repo.update(id, json)
            cherrypy.response.status = 200

    def DELETE(self, id = None):
        if id == None:
            raise cherrypy.HTTPError(405, "Method DELETE not allowed")
        else:
            return repo.delete(id)


rootpath = os.path.join(os.getcwd(), "fakes")
repo = Repo(rootpath)
repo.load()

serverconf = {
    '/': {
        'tools.trailing_slash.on': False,
        'request.dispatch': NoDispatcher()
    }
}

cherrypy.tree.mount(Faker(), '/', serverconf)

managerconf = {'/': {
    'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
}

cherrypy.tree.mount(Manager(), '/manage', managerconf)

# Static files
current_dir = os.path.dirname(os.path.abspath(__file__))
staticconf = {'/': {
    'tools.staticdir.on': True,
    'tools.staticdir.dir': os.path.join(os.getcwd(), "static"),
    'tools.staticdir.index': "index.html"}
}


class Home(object):
    @cherrypy.expose
    def index():
        return "Home"


cherrypy.tree.mount(Home(), '/ihm', staticconf)

cherrypy.server.socket_host = '0.0.0.0'

cherrypy.engine.start()
cherrypy.engine.block()
