import time


class Action(object):
    def __init__(self, conn):
        self.conn = conn

    def load(self, lib):
        return __import__(lib, fromlist=[''])

    def __getattr__(self, name):
        try:
            return self.load('noaaclass.product.%s' % name).api(self)
        except Exception, e:
            raise Exception('There is no API to the "%s" product.\n%s'
                            % (name, e))

    def has_local_api(self, product):
        try:
            getattr(self, product)
        except Exception:
            return False
        return True

    def products(self):
        html, form_name = self.get_main_form()
        form = dict(self.conn.translator.get_forms(html, list_options=True)
                    [form_name])
        return [k.lower() for k in form['datatype_family']
                if self.has_local_api(k.lower())]


class api(object):
    def __init__(self, action):
        self.action = action
        self.keys = {'get': {}, 'set': {}}
        self.initialize()

    def initialize(self):
        raise Exception('Unregistered API.')

    @property
    def conn(self):
        return self.action.conn

    @property
    def action_name(self):
        return self.action.__class__.__name__.lower()

    def translate(self, structure, local, to_local, name, to_remote):
        self.keys['get'][name] = (local, to_local, structure)
        self.keys['set'][local] = (name, to_remote)

    def local_to_post(self, local):
        var = self.keys['set']
        return {var[k][0]: var[k][1](v) for k, v in local.items()
                if k in var.keys()}

    def post_to_local(self, post):
        get = lambda k: self.keys['get'][k]
        local = lambda k: get(k)[0]
        adapter = lambda k: get(k)[1]
        structure = lambda k, e, a: get(k)[2](e, a)
        keys = self.keys['get'].keys()
        return {local(k): structure(k, e, adapter(k)) for k, e in post.items()
                if k in keys}

    def get(self, *args, **kwargs):
        return getattr(self, '%s_get' % self.action_name)(*args, **kwargs)

    def set(self, *args, **kwargs):
        old_len = len(self.get(**kwargs))
        getattr(self, '%s_set' % self.action_name)(*args, **kwargs)
        local = args[0]
        while True:
            db = self.get(**kwargs)
            if len(db) == len(local) + old_len:
                break
            time.sleep(1)
        return db
