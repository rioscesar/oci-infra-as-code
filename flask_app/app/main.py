from flask import request, jsonify

import requests
import json

from flask_app.app import app, db
from flask_app.app.models import User, Environment
from flask_app.app.models.function import Function
from flask_app.app.schemas.compute import ComputeSchema
from flask_app.app.schemas.gateway import GatewaySchema
from flask_app.app.schemas.subnet import SubnetSchema
from flask_app.app.schemas.vcn import VCNSchema
from flask_app.app.utils.env import get_environment

headers = app.config['FN_HEADERS']
url = app.config['FN_URL']


@app.route('/')
def hello():
    return 'Hello World!'


@app.route('/setup', methods=['POST'])
def setup():

    data = request.get_json()
    
    user_id = data.get('user_id')
    fingerprint = data.get('fingerprint')
    private_key = data.get('private_key')
    user_ocid = data.get('user_ocid')
    tenancy_ocid = data.get('tenancy_ocid')
    env_name = data.get('env_name')
    region = data.get('region')

    env = Environment(env_name, private_key, user_ocid, tenancy_ocid, fingerprint, region)
    user = User(user_id)
    user.environments.append(env)

    # todo: more error handling for sql inserts

    db.session.add(user)
    db.session.commit()

    return json.dumps({'success': True, 'environment': env_name}), 200, headers


@app.route('/vcn', methods=['POST'])
def vcn():
    request_data = request.get_json()

    data = {
        'compartment_id': request_data.get('compartment_id'),
        'cidr_block': request_data.get('cidr_block'),
        'name': request_data.get('name'),
        'environment': get_environment(request_data)
    }

    r = requests.post(url+'/infra/vcn', data=json.dumps(data), headers=headers)
    return jsonify(VCNSchema().dump(json.loads(r.text)).data)


@app.route('/subnet', methods=['POST'])
def subnet():
    request_data = request.get_json()

    data = {
        'environment': get_environment(request_data),
        'cidr_block': request_data.get('cidr_block'),
        'compartment_id': request_data.get('compartment_id'),
        'vcn_id': request_data.get('vcn_id'),
        'ad': request_data.get('ad'),
        'name': request_data.get('name')
    }

    r = requests.post(url+'/infra/subnet', data=json.dumps(data), headers=headers)
    return jsonify(SubnetSchema().dump(json.loads(r.text)).data)


@app.route('/gateway', methods=['POST'])
def gateway():
    request_data = request.get_json()

    data = {
        'environment': get_environment(request_data),
        'compartment_id': request_data.get('compartment_id'),
        'vcn_id': request_data.get('vcn_id'),
        'name': request_data.get('name'),
        'default_route_table_id': request_data.get('default_route_table_id')
    }

    r = requests.post(url+'/infra/gateway', data=json.dumps(data), headers=headers)
    return jsonify(GatewaySchema().dump(json.loads(r.text)).data)


@app.route('/images', methods=['POST'])
def images():
    request_data = request.get_json()

    data = {
        'environment': get_environment(request_data),
        'compartment_id': request_data.get('compartment_id')
    }

    r = requests.post(url+'/infra/images', data=json.dumps(data), headers=headers)
    return jsonify(json.loads(r.text))


@app.route('/compute', methods=['POST'])
def compute():
    request_data = request.get_json()

    data = {
        'environment': get_environment(request_data),
        'ad': request_data.get('ad'),
        'compartment_id': request_data.get('compartment_id'),
        'name': request_data.get('name'),
        'image_id': request_data.get('image_id'),
        'shape': request_data.get('shape'),
        'subnet_id': request_data.get('subnet_id')
    }

    r = requests.post(url+'/infra/compute', data=json.dumps(data), headers=headers)
    return jsonify(ComputeSchema().dump(json.loads(r.text)))


@app.route('/fnpython', methods=['POST'])
def fnpython():
    request_data = request.get_json()
    user_id = request_data.pop('user_id')
    name = request_data.get('name')
    code = request_data.get('code')

    fn = Function(name, code)
    user = User(user_id)
    user.functions.append(fn)
    # todo: more error handling for sql inserts

    db.session.add(user)
    db.session.commit()

    r = requests.post(url+'/function/fnpython', data=json.dumps(request_data), headers=headers)
    return jsonify(json.loads({'result': r.text}))


# todo: need to return all functions available to user or public


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)
