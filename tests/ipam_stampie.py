from collections import Counter


def ensure_location(ipam, location):
    locs = ipam.tools._locations
    locs.get_catalog('name')
    if location not in locs.catalog:
        got = locs.post(json=dict(name=location))
        got.raise_for_status()
        return got.json()['data']
    else:
        return locs[location]


def ensure_racks(ipam, db, loc_id, rack_size='47'):
    locations = Counter(d['location'] for d in db.devices.col.all() if 'location' in d)
    racks_names = {loc.rpartition('.')[0] for loc in locations}

    racks_api = ipam.tools._racks
    racks_api.get_catalog(('name', 'location'))

    for rack_name in racks_names:
        if (rack_name, loc_id) in racks_api.catalog:
            continue
        racks_api.post(json=dict(name=rack_name, location=loc_id, size=rack_size))


def ensure_devices_in_racks(ipam, db, loc_id):
    racks_api = ipam.tools._racks
    racks_api.get_catalog(('name', 'location'))

    dev_types_api = ipam.tools._device_types
    dev_types_api.get_catalog('tname')

    devices_api = ipam.devices
    devices_api.get_catalog(('hostname', 'location'))

    rack_devices = filter(lambda d: all(f in d for f in ('location', 'size_ru')), db.devices.col.all())
    for dev_node in rack_devices:
        d_name = dev_node['hostname']
        if (d_name, loc_id) in devices_api.catalog:
            continue

        rack_name, _, rack_start = dev_node['location'].rpartition('.')
        rack_id = racks_api[(rack_name, loc_id)]['id']
        rack_size = str(dev_node['size_ru'])
        dev_type = dev_types_api.catalog.get(dev_node['role']) or dev_types_api.catalog['Switch']

        got = devices_api.post(json=dict(hostname=d_name, location=loc_id, rack=rack_id,
                                         rack_start=rack_start, rack_size=rack_size, type=dev_type['id']))

        got.raise_for_status()
