# acs_binary_scripts
Includes acs binary build script, acs runner script, acs environment installation script


## ACS Silent install

### On Linux (recommended Ubuntu 16.04):

* $sudo acs_silent_install.sh

## Build ACS binary package

* $pip install Cython
* $python build_acs_bin_package.py -p Path/to/ACS/code -o Path/to/output

## Execute ACS runner

* $python run_acs.py -c [campaign name]

## Build docker image in Intel internal environment

* $docker build -f celadon-aft.internal -t celadon-aft --build-arg http_proxy=http://proxy:port/ --build-arg https_proxy=http://proxy:port/ --build-arg ftp_proxy=http://proxy:port --build-arg no_proxy=localhost,127.0.0.1,company.com
