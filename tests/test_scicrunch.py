import json
import pytest
from app import app
from app.main import dataset_search
from app.scicrunch_requests import create_query_string


@pytest.fixture
def client():
    # Spin up test flask app
    app.config['TESTING'] = True
    return app.test_client()


def test_scicrunch_keys(client):
    r = client.get('/search/')
    assert r.status_code == 200
    assert 'numberOfHits' in json.loads(r.data).keys()


def test_scicrunch_dataset_doi(client):
    r = client.get('/scicrunch-dataset/DOI%3A10.26275%2Fpzek-91wx')
    assert json.loads(r.data)['hits']['hits'][0]['_id'] == "DOI:10.26275/pzek-91wx"


def test_scicrunch_search(client):
    r = client.get('/search/heart')
    assert r.status_code == 200
    assert json.loads(r.data)['numberOfHits'] > 4


def test_scicrunch_all_data(client):
    r = client.get('/filter-search/')
    assert json.loads(r.data)['numberOfHits'] > 40


def test_scicrunch_filter(client):
    r = client.get('/filter-search/', query_string={'term': 'organ', 'facet': 'heart'})
    assert json.loads(r.data)['numberOfHits'] > 4

def test_scicrunch_filter_scaffolds(client):
    r = client.get('/filter-search/?facet=scaffolds&term=datasets')
    assert json.loads(r.data)['numberOfHits'] > 10

def test_scicrunch_filter_simulations(client):
    r = client.get('/filter-search/?facet=simulations&term=datasets')
    assert json.loads(r.data)['numberOfHits'] > 0

def test_scicrunch_basic_search(client):
    r = client.get('/filter-search/Heart/?facet=All+Species&term=species')
    assert json.loads(r.data)['numberOfHits'] > 10


def test_scicrunch_boolean_logic(client):
    r = client.get('/filter-search/?facet=All+Species&term=species&facet=male&term=gender&facet=female&term=gender')
    assert json.loads(r.data)['numberOfHits'] > 20


def test_scicrunch_combined_facet_text(client):
    r = client.get('/filter-search/heart/?facet=All+Species&term=species&facet=male&term=gender&facet=female&term=gender')
    assert json.loads(r.data)['numberOfHits'] > 1


def test_getting_facets(client):
    r = client.get('/get-facets/organ')
    facet_results = json.loads(r.data)
    facets = [facet_result['key'] for facet_result in facet_results]
    assert 'heart' in facets


def test_response_version(client):
    doi = "10.26275/duz8-mq3n"
    r = client.get('/dataset_info/using_doi', query_string={'doi': doi})
    data = r.data.decode('utf-8')
    json_data = json.loads(data)
    assert len(json_data['result']) == 1
    assert 'version' in json_data['result'][0]


source_structure = {
    'type': dict,
    'required': ['contributors', 'dataItem', 'dates', 'distributions',
                 {'item':
                     {
                         'type': dict,
                         'required': [{'version': {'type': dict, 'required': ['keyword'], 'optional': []}}, 'types', 'contentTypes', 'names', 'statistics', 'keywords', 'published', 'description',
                                      'name', 'readme', 'identifier', 'docid', 'curie'],
                         'optional': ['techniques', 'modalities']
                     }}, 'organization', 'provenance', 'supportingAwards'],
    'optional': ['anatomy', 'attributes', 'diseases',
                 {'objects':
                     {
                         'type': list,
                         'item': {
                             'type': dict,
                             'required': ['bytes', 'dataset', 'distributions', 'identifier', 'mimetype', 'name', 'updated'],
                             'optional': []}
                     }
                 }, 'organisms', 'protocols', 'publication', 'xrefs']
}
raw_structure_base = {
    'type': dict,
    'required': [
        {'hits': {
            'type': dict,
            'required': [
                {'hits':
                     {'type': list,
                      'item': {
                          'type': dict,
                          'required': ['_index', '_type', '_id', '_score',
                                       {'_source': source_structure}
                                       ],
                          'optional': ['_ignored']}
                      }
                 }
            ],
            'optional': [],
        }
        }
    ],
    'optional': []
}


class StructureDefinitionError(Exception):
    pass


def _test_sub_structure(data, structure, required=True):
    for st in structure:
        if isinstance(st, str):
            if required and st not in data:
                print(f'failed: {st}')
                return False

            continue

        # req should have exactly one key
        if not len(st.keys()) == 1:
            raise StructureDefinitionError

        key = next(iter(st))
        if required and key not in data:
            print(f'key failed: {key}')
            return False

        # if key == '_source':
        #     a = list(data[key].keys())
        #     a.sort()
        #     print(a)
        if key in data and not _test_structure(data[key], st[key]):
            print(f'structure failed: {key} - {st[key]["type"]}, {type(data[key])} - {st[key]} - {len(data[key])}')
            return False

    return True


def _test_structure(data, structure):
    structure_type = structure['type']
    # print('=============================')
    # print(structure)
    if isinstance(data, structure_type):
        if structure_type is dict:
            if not _test_sub_structure(data, structure['required'], required=True):
                return False

            if not _test_sub_structure(data, structure['optional'], required=False):
                return False
        elif structure_type is list:
            for list_item in data:
                if not _test_structure(list_item, structure['item']):
                    return False
        else:
            print('type if not dict or list', type(data))

        return True

    return False


def test_raw_response_structure(client):
    # 10.26275/zdxd-84xz
    # 10.26275/duz8-mq3n
    query = create_query_string("computational")
    data = dataset_search(query, raw=True)
    # print(data['hits']['hits'][0]['_source']['objects'])
    # print(data['hits']['hits'][0]['_source']['item'])
    assert _test_structure(data, raw_structure_base)
    assert 'hits' in data
    assert 'hits' in data['hits']
    assert isinstance(data['hits']['hits'], list)
    for hit in data['hits']['hits']:
        if 'version' in hit['_source']['item']:
            print(hit['_source']['item']['version']['keyword'])
        else:
            print('no version')

    for hit in data['hits']['hits']:
        print(hit['_source'].keys())
    objects = data['hits']['hits'][0]['_source']['objects']
    for o in objects:
        mimetype = o.get('mimetype', 'not-specified').get('name', 'no-name')
        # print('mimetype: ', mimetype)
        if mimetype == 'image/png':
            # print(o)
            print('.', end="")

    print()
    # for k in data['hits']['hits'][0]:
    #     print(k, data['hits']['hits'][0][k])

def test_getting_curies(client):
    r = client.get('/get-organ-curies/')
    uberons_results = json.loads(r.data)
    total = len( uberons_results['uberon']['array'])
    assert total > 0
    r = client.get('/get-organ-curies/?species=human')
    uberons_results = json.loads(r.data)
    human = len( uberons_results['uberon']['array'])
    assert total > human


def test_scaffold_files(client):
    r = client.get('/filter-search/?size=30')
    results = json.loads(r.data)
    assert results['numberOfHits'] > 0
    for item in results['results']:
        if 'abi-scaffold-metadata-file' in item and 's3uri'  in item:
            uri = item['s3uri']
            path = item['abi-scaffold-metadata-file'][0]['dataset']['path']
            key = f"{uri}files/{path}".replace('s3://pennsieve-prod-discover-publish-use1/', '')
            r = client.get(f"/s3-resource/{key}")
            assert r.status_code == 200