from prometheus_client import start_http_server, Gauge

from json import JSONDecodeError
from datetime import datetime

import requests
import configparser
import time

# prometheus vars
peers = Gauge("gaia_peers_count", "Count of peers")
latest_chain_height = Gauge('gaia_chain_block_heigh', 'Height of latest block in the chain')
block_height = Gauge('gaia_block_height', 'Height of block')
block_gap = Gauge("gaia_block_time_gap", "Gap between blocks")
height_gap = Gauge("gaia_block_height_gap", "Gap between local and external height")

# config instance
config = configparser.ConfigParser()


def get_data(address, port, path) :
    ''' Get http request. Return value is dictionary '''
    url = 'http://{}:{}/{}'.format( address, port, path)
    return make_request(url)
    
def make_request(url) :
    ''' Get http request. Return value is dictionary '''
    try:
        body = requests.get(url).json()
    except JSONDecodeError:
        print ("error while json parsing")
        return {}
    return body

def export(ip, port):
    ''' Get data from Gaia and push it to the Prometheus vars '''

    # get data from app
    status_data  = get_data(address = ip, port = port, path = 'status')
    netinfo_data = get_data(address = ip, port = port, path = 'net_info')
    external_data = make_request(config['external_data']['url'])

    if (status_data == {} or netinfo_data == {} or external_data == {}) :
        print ("error while getting data")
        return

    # get latest block height
    external_height = external_data['block']['header']['height']
    # get latest block time
    external_time_string = external_data['block']['header']['time']
    # get local block time
    local_time_string = status_data['result']['sync_info']['latest_block_time']
    
    # time gap calculation    
    external_block_time = datetime.strptime(external_time_string.split(".")[0], '%Y-%m-%dT%H:%M:%S')
    local_block_time = datetime.strptime(local_time_string.split(".")[0], '%Y-%m-%dT%H:%M:%S')

    # height gap calculation
    local_height = int(status_data['result']['sync_info']['latest_block_height'])
    height_diff = int(external_height) - local_height

    # set prometheus data
    block_gap.set((external_block_time - local_block_time).total_seconds())
    peers.set( netinfo_data['result']['n_peers'] )
    latest_chain_height.set(external_height)
    block_height.set(local_height)
    height_gap.set(height_diff)
    
    # debug
    print (datetime.now().time(), 
                        "\texternal_status_time_gap: ", (external_block_time - local_block_time).total_seconds(),
                        "\tpeers: ", netinfo_data['result']['n_peers'],
                        "\tchain_height: ", external_height,
                        "\tlocal_height: ", local_height,
                        "\theight_diff: ", height_diff,
                        "\tcatching_up: ", status_data['result']['sync_info']['catching_up'])

def main() :
    # read config
    try:
        config.read('config.ini')
    except:
        print ("error while config reading")
        exit (1)

    # get parameters from config
    port = config['DEFAULT']['port']
    interval = config['DEFAULT']['interval']

    app_address = config['gaia']['address']
    app_port = config['gaia']['port']

    # start 
    start_http_server(int(port))
    while True:
        export(app_address, int(app_port))
        time.sleep(int(interval))

if __name__ == '__main__':
    main()