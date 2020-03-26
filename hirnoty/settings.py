import logging
from os import access, path, R_OK
log = logging.getLogger(__name__)

_REQUIRED = set(["TOKEN"])
_ALLOWED = set(["ACL",
                "BIND_ADDRESS",
                "LOGLEVEL",
                "OTP",
                "SCRIPT_DIR",
                "INDEX_DIR",
                "DOWN_DIR"]).union(_REQUIRED)
SYS_CONFIG_DIR = path.join('/etc', 'hirnoty')
SYS_CONFIG_PATH = path.join(SYS_CONFIG_DIR, "config.py")
CONFIG_DIR = path.join(path.expanduser('~'), '.config', 'hirnoty')
CONFIG_PATH = path.join(CONFIG_DIR, "config.py")
SOURCE_PATH = path.dirname(path.abspath(__file__))
DEFAULT_CONFIG_PATH = path.join(SOURCE_PATH, "default_config.py")
config = {"SOURCE_PATH": SOURCE_PATH}
# lazy way to get config parameters, first load defaults and then
# user configuration (if it exists)

with open(DEFAULT_CONFIG_PATH, 'r') as fhandle:
    exec(fhandle.read(), config)

if access(SYS_CONFIG_PATH, R_OK):
    log.info("Getting system configuration from %s", SYS_CONFIG_PATH)
    with open(SYS_CONFIG_PATH, 'r') as fhandle:
        exec(fhandle.read(), config)

if access(CONFIG_PATH, R_OK):
    log.info("Getting configuration from %s", CONFIG_PATH)
    with open(CONFIG_PATH, 'r') as fhandle:
        exec(fhandle.read(), config)

for key in [item for item in config.keys() if item not in _ALLOWED]:
    del config[key]
