# The MIT License (MIT)
# Copyright © 2021 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated 
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, 
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of 
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL 
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION 
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.

import argparse
from typing import Callable

# Bittensor code and protocol version.
__version__ = '1.5.0'
version_split = __version__.split(".")
__version_as_int__ = (100 * int(version_split[0])) + (10 * int(version_split[1])) + (1 * int(version_split[2]))

# Vocabulary dimension.
#__vocab_size__ = len( tokenizer ) + len( tokenizer.additional_special_tokens) + 100 # Plus 100 for eventual token size increase.
__vocab_size__ = 50378

# Tensor dimension.
# NOTE (const): if/when this increases peers must be responsible for trimming or expanding output to this size.
__network_dim__ = 1024 # All network responses have shape = [ __batch_size__, __sequence_dim__, __network_dim__ ]

# Substrate chain block time (seconds).
__blocktime__ = 6

__networks__ = ['akatsuki', 'kusanagi', 'nobunaga']

__akatsuki_entrypoints__ = [
    "main.akatsuki.bittensor.com:9944"
]

__kusanagi_entrypoints__ = [
    "test.kusanagi.bittensor.com:9944"
]

__nobunaga_entrypoints__ = [
    'staging.nobunaga.opentensor.ai:9944'
]

__local_entrypoints__ = [
    '127.0.0.1:9944'
]

__registration_servers__ = [
    'registration.opentensor.ai:5000'
]

# ---- Config ----
from bittensor._config import config as config

# ---- LOGGING ----
from bittensor._logging import logging as logging

# ---- Protos ----
import bittensor._proto.bittensor_pb2 as proto
import bittensor._proto.bittensor_pb2_grpc as grpc

# ---- Factories -----
from bittensor.utils.balance import Balance as Balance
from bittensor._cli import cli as cli
from bittensor._axon import axon as axon
from bittensor._wallet import wallet as wallet
from bittensor._keyfile import keyfile as keyfile
from bittensor._receptor import receptor as receptor
from bittensor._endpoint import endpoint as endpoint
from bittensor._dendrite import dendrite as dendrite
from bittensor._metagraph import metagraph as metagraph
from bittensor._subtensor import subtensor as subtensor
from bittensor._tokenizer import tokenizer as tokenizer
from bittensor._serializer import serializer as serializer
from bittensor._dataset import dataset as dataset
from bittensor._receptor import receptor_pool as receptor_pool
from bittensor._wandb import wandb as wandb
from bittensor._threadpool import prioritythreadpool as prioritythreadpool

# ---- Classes -----
from bittensor._cli.cli_impl import CLI as CLI
from substrateinterface import Keypair as Keypair
from bittensor._axon.axon_impl import Axon as Axon
from bittensor._config.config_impl import Config as Config
from bittensor._wallet.wallet_impl import Wallet as Wallet
from bittensor._keyfile.keyfile_impl import Keyfile as Keyfile
from bittensor._receptor.receptor_impl import Receptor as Receptor
from bittensor._endpoint.endpoint_impl import Endpoint as Endpoint
from bittensor._dendrite.dendrite_impl import Dendrite as Dendrite
from bittensor._metagraph.metagraph_impl import Metagraph as Metagraph
from bittensor._subtensor.subtensor_impl import Subtensor as Subtensor
from bittensor._serializer.serializer_impl import Serializer as Serializer
from bittensor._dataset.dataset_impl import Dataset as Dataset
from bittensor._receptor.receptor_pool_impl import ReceptorPool as ReceptorPool
from bittensor._threadpool.priority_thread_pool_impl import PriorityThreadPoolExecutor as PriorityThreadPoolExecutor

import bittensor.utils.networking as net
from bittensor.utils.networking import get_external_ip as external_ip


# Singluar Neuron instance useful for creating simple miners.
neuron = None

def add_args( parser: argparse.ArgumentParser ):
    parser.add_argument('--neuron.use_upnpc', action='store_true', help='''Neuron punches a hole in your router using upnpc''', default=False)
    parser.add_argument('--neuron.use_wandb', action='store_true', help='''Neuron activates its weights and biases powers''', default=False)
    parser.add_argument('--neuron.max_workers', type=int,  help='''Number of maximum threads in the neuron''',default=10)
    logging.add_args( parser )
    wallet.add_args( parser )
    subtensor.add_args( parser )
    metagraph.add_args( parser )
    dataset.add_args( parser )
    dendrite.add_args( parser )
    axon.add_args( parser )
    wandb.add_args( parser )

def check_config( config ):
    logging.check_config( config )
    wallet.check_config( config )
    subtensor.check_config( config )
    metagraph.check_config( config )
    dataset.check_config( config )
    dendrite.check_config( config )
    axon.check_config( config )

def default_config() -> 'Config':
    parser = argparse.ArgumentParser()
    add_args( parser )
    bittensor_config = config( parser )
    check_config(bittensor_config)
    return bittensor_config

class Neuron():

    def __init__(self, 
            config: 'Config',
            root_dir: str = '',
            forward_text: 'Callable' = None,
            backward_text: 'Callable' = None,
            forward_image: 'Callable' = None,
            backward_image: 'Callable' = None,
            forward_tensor: 'Callable' = None,
            backward_tensor: 'Callable' = None,
            blacklist: 'Callable' = None,
        ):
        if config == None: config = default_config()
        self.config = config
        self.root_dir = root_dir
        logging (
            config = self.config,
            logging_dir = root_dir,
        )
        self.wallet = wallet(
            config = self.config
        ).create().register()
        self.dendrite = dendrite(
            config = self.config,
            wallet = self.wallet
        )
        self.subtensor = subtensor(
            config = self.config
        )
        self.metagraph = metagraph(
            config = self.config,
            subtensor = self.subtensor
        )
        self.axon = axon (
            config = self.config,
            wallet = self.wallet,
            forward_text = forward_text,
            backward_text = backward_text,
            forward_image = forward_image,
            backward_image = backward_image,
            forward_tensor = forward_tensor,
            backward_tensor = backward_tensor,
            blacklist = blacklist,
        )

    def __enter__(self):
        # ---- Setup Wallet. ----
        if not self.wallet.coldkeypub_file.exists_on_device() or not self.wallet.hotkey_file.exists_on_device():
            self.wallet.create()
        try:
            self.metagraph.load().sync().save()
        except Exception as e:
            logging.error('Error in loading metagraph: {}'.format(e))
            self.metagraph.sync().save()
        self.axon.start().serve (
            use_upnpc = self.config.neuron.use_upnpc, 
            subtensor = self.subtensor
        )

    def __exit__ ( self, exc_type, exc_value, exc_traceback ):
        self.axon.stop()
            
        print(exc_type, exc_value, exc_traceback)

def init( 
        config: 'Config' = None,
        root_dir: str = None,
        forward_text: 'Callable' = None,
        backward_text: 'Callable' = None,
        forward_image: 'Callable' = None,
        backward_image: 'Callable' = None,
        forward_tensor: 'Callable' = None,
        backward_tensor: 'Callable' = None,
        blacklist: 'Callable' = None,
    ) -> Neuron:

    global neuron
    neuron = Neuron( 
        config = config,
        root_dir = root_dir,
        forward_text = forward_text,
        backward_text = backward_text,
        forward_image = forward_image,
        backward_image = backward_image,
        forward_tensor = forward_tensor,
        backward_tensor = backward_tensor,
        blacklist = blacklist
    )
    return neuron

# DEFAULTS
defaults = Config()
subtensor.add_defaults( defaults )
dendrite.add_defaults( defaults )
axon.add_defaults( defaults )
wallet.add_defaults( defaults )
prioritythreadpool.add_defaults( defaults )
dataset.add_defaults( defaults )
wandb.add_defaults( defaults )
logging.add_defaults( defaults )
