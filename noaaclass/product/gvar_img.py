from noaaclass import core
import re


class Subscriber(object):
    def row_to_dict(self, row):
        elements = row.select('td')
        _id = elements[3].a.text
        enabled = (elements[1].renderContents().strip() == 'Yes')
        result = (_id, {
            'enabled': enabled,
            'name': elements[2].a.text,
            'edit': (self.item_url % (_id, 'Y' if enabled else 'N'))
        })
        return result

    @property
    def list(self):
        rows = self.conn.get('subscriptions').select(
            'table.class_table tr:nth-of-type(2)')
        return dict([self.row_to_dict(r) for r in rows])


class api(core.api):
    def register(self):
        self.name = 'GVAR_IMG'
        direct = lambda x: x
        enabled_to_local = lambda x: x == 'Y'
        enabled_to_remote = lambda x: 'Y' if x else 'N'
        single = lambda x, t: t(x[0])
        multiple = lambda l, t: list(map(t, l))
        self.translate(single, 'enabled', enabled_to_local,
                       'subhead_sub_enabled', enabled_to_remote)
        self.translate(single, 'name', direct, 'subhead_sub_description', str)
        self.translate(single, 'north', float, 'nlat', str)
        self.translate(single, 'south', float, 'slat', str)
        self.translate(single, 'west', float, 'wlon', str)
        self.translate(single, 'east', float, 'elon', str)
        self.translate(multiple, 'coverage', direct, 'Coverage', direct)
        self.translate(multiple, 'schedule', direct, 'Satellite Schedule',
                       direct)
        self.translate(multiple, 'satellite', direct, 'Satellite', direct)
        self.translate(multiple, 'channel', int, 'chan_%s' % self.name, str)
        self.translate(single, 'format', direct, 'format_%s' % self.name, str)

    def subscribe_get(self):
        noaa = self.conn
        page = noaa.get('subscriptions')
        data = page.select('.class_table td a')
        enabled = lambda x: re.match(r'.*%22(.*)%22.*', x).group(1) == 'Y'
        data = [{'id': d.text, 'enabled': enabled(d['href'])}
                for d in data if d.text.isdigit()]
        for d in data:
            noaa.get('sub_details?sub_id=%s&enabled=%s'
                     % (d['id'], 'Y' if d['enabled'] else 'N'))
            forms = noaa.translator.get_forms(noaa.last_response_soup)
            tmp = forms['sub_frm']
            noaa.post('sub_deliver', tmp, form_name='sub_frm')
            forms = noaa.translator.get_forms(noaa.last_response_soup)
            join = lambda x, y: dict(x.items() + y.items())
            tmp = join(tmp, forms['sub_frm'])
            d.update(self.post_to_local(tmp))
        return data

    def subscribe_new(self, e):
        name = __name__.split('.')[-1].upper()
        self.conn.get('sub_details?sub_id=0&'
                      'datatype_family=%s&submit.x=40&submit.y=11' %
                      name)
        data = self.local_to_post(e)
        self.conn.post('sub_deliver', data, form_name='sub_frm')
        channel_mask = list('000000' + 'X' * 24)
        data = self.local_to_post(e)
        for i in e['channel']:
            channel_mask[i-1] = '1'
            data['channels_%s' % name] = ''.join(channel_mask),
        self.conn.post('sub_save', data, form_name='sub_frm')

    def subscribe_edit(self, e):
        pass

    def subscribe_remove(self, e):
        self.conn.get('sub_delete?actionbox=%s' % e['id'])

    def subscribe_set(self, data):
        old_data = self.subscribe_get()
        remove = [e for e in old_data
                  if e['id'] not in [x['id'] for x in data]]
        new = [e for e in data if e['id'] is '+']
        edit = [e for e in data if e not in new and '+' in e['id']]
        [self.subscribe_new(e) for e in new]
        [self.subscribe_edit(e) for e in edit]
        [self.subscribe_remove(e) for e in remove]

    def request_get(self):
        return {}

    def request_set(self, data):
        return {}