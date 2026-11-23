import os


#################
# ENV load .env file
from dotenv import load_dotenv
load_dotenv()

def get_config():

    # log_dir / temp_dir come from .env. Defaults keep CI and frozen builds runnable.
    log_dir = os.getenv('log_dir') or '_logs'
    temp_dir = os.getenv('temp_dir') or '_temp'
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    ret = {
        'log_dir': log_dir,
        'temp_dir': temp_dir
    }

    print('get_config().return=', ret)

    return ret
